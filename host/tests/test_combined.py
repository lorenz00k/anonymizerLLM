"""
Tests fuer die kombinierte Pipeline (Custom > Regex > Presidio).

Presidio laedt beim Import das grosse spaCy-Modell. Fuer die Pipeline-Logik
(Ueberlappungen, Prioritaet, Ersetzen) ersetzen wir die Presidio-Stufe durch
einen Stub, damit die Tests schnell laufen und kein Modell brauchen.
"""

import importlib
import sys
import types

import pytest

from piifilter.detection.rule_based.types import Match

PRESIDIO_MODULE = "piifilter.detection.rule_based.presidio_engine"
COMBINED_MODULE = "piifilter.detection.rule_based.combined"


@pytest.fixture
def pipeline(monkeypatch):
    """Liefert (combined_modul, set_presidio, set_custom_rules)."""
    state = {"presidio": ([], []), "rules": {}}

    fake_presidio = types.ModuleType(PRESIDIO_MODULE)
    fake_presidio.find_matches = lambda text, language="de": state["presidio"]
    monkeypatch.setitem(sys.modules, PRESIDIO_MODULE, fake_presidio)
    monkeypatch.delitem(sys.modules, COMBINED_MODULE, raising=False)
    combined = importlib.import_module(COMBINED_MODULE)

    monkeypatch.setattr(combined, "get_effective_rules", lambda chat_id=None: state["rules"])

    def set_presidio(matches, extra=()):
        state["presidio"] = (list(matches), list(extra))

    def set_rules(rules):
        state["rules"] = rules

    yield combined, set_presidio, set_rules
    sys.modules.pop(COMBINED_MODULE, None)


def test_text_without_pii_is_unchanged(pipeline):
    combined, _, _ = pipeline
    result, findings = combined.detect_and_anonymize("Hallo Welt, alles gut.")
    assert result == "Hallo Welt, alles gut."
    assert findings == []


def test_email_is_replaced_and_recorded(pipeline):
    combined, _, _ = pipeline
    result, findings = combined.detect_and_anonymize("Mail an max@firma.de bitte")
    assert "max@firma.de" not in result
    assert len(findings) == 1
    assert findings[0].original == "max@firma.de"
    assert findings[0].placeholder in result


def test_custom_rule_wins_over_regex_on_overlap(pipeline):
    combined, _, set_rules = pipeline
    set_rules({"max@firma.de": "kunde"})
    result, findings = combined.detect_and_anonymize("Mail an max@firma.de bitte")
    assert result == "Mail an kunde bitte"
    assert findings[0].category == "CUSTOM"


def test_custom_rule_preserves_case(pipeline):
    combined, _, set_rules = pipeline
    set_rules({"phoenix": "projekt x"})
    result, _ = combined.detect_and_anonymize("PHOENIX und phoenix und Phoenix")
    assert result == "PROJEKT X und projekt x und Projekt X"


def test_presidio_match_is_applied(pipeline):
    combined, set_presidio, _ = pipeline
    text = "Hallo Jonas Wüst, wie geht es dir?"
    set_presidio([Match(6, 16, "Jonas Wüst", "Max Mustermann", "PERSON")])
    result, _ = combined.detect_and_anonymize(text)
    assert result == "Hallo Max Mustermann, wie geht es dir?"


def test_repeated_name_is_masked_everywhere(pipeline):
    """Presidio findet nur das erste Vorkommen - der Rest wird nachgezogen."""
    combined, set_presidio, _ = pipeline
    text = "Jonas Wüst schreibt. Danach antwortet jonas wüst."
    set_presidio([Match(0, 10, "Jonas Wüst", "Max Mustermann", "PERSON")])
    result, _ = combined.detect_and_anonymize(text)
    assert "wüst" not in result.lower()
    assert result.count("ax ") + result.count("AX ") >= 2  # beide Stellen ersetzt


def test_overlapping_matches_are_not_applied_twice(pipeline):
    combined, set_presidio, _ = pipeline
    text = "Kontakt: max@firma.de"
    # Presidio "erkennt" faelschlich dieselbe Stelle noch einmal
    set_presidio([Match(9, 21, "max@firma.de", "Max Mustermann", "PERSON")])
    result, findings = combined.detect_and_anonymize(text)
    assert len(findings) == 1
    assert findings[0].category == "EMAIL"  # Regex hat Vorrang vor Presidio
    assert result.count("Max Mustermann") == 0
