import pytest

from piifilter.detection.rule_based import combined, custom_rules
from piifilter.detection.rule_based.detectors import CustomRulesDetector, RegexDetector
from piifilter.detection.rule_based.types import Match, Finding


class FakeDetector:
    def __init__(self, priority=10):
        self.priority = priority
        self.matches, self.extra = [], []
        self.lang_code = []

    def set(self, matches, extra=()):
        self.matches, self.extra = list(matches), list(extra)

    def find(self, text, chat_id=None, lang_code=None):
        # Kopien, weil _collect die priority auf den Matches setzt
        self.lang_code.append(lang_code)
        return [Match(m.start, m.end, m.original, m.fake_value, m.category)
                for m in self.matches], list(self.extra)


@pytest.fixture
def pipeline(monkeypatch):
    """Echte Custom-Rules- und Regex-Detektoren, Presidio ist ein Fake.
    Liefert (combined, set_presidio, set_rules)."""
    state = {"rules": {}, "chat_ids": []}
    fake_presidio = FakeDetector(priority=10)

    def fake_rules(chat_id=None):
        state["chat_ids"].append(chat_id)
        return state["rules"]

    monkeypatch.setattr(custom_rules, "get_effective_rules", fake_rules)
    monkeypatch.setattr(combined, "DETECTORS",
                        [CustomRulesDetector(), RegexDetector(), fake_presidio])

    def set_presidio(matches, extra=()):
        fake_presidio.set(matches, extra)

    def set_rules(rules):
        state["rules"] = rules

    combined.state = state  # fuer den chat_id-Test
    return combined, set_presidio, set_rules


@pytest.fixture
def fakes(monkeypatch):
    """Nur Fake-Detektoren mit frei waehlbarer Prioritaet."""
    def make(*priorities):
        detectors = [FakeDetector(p) for p in priorities]
        monkeypatch.setattr(combined, "DETECTORS", detectors)
        return detectors
    return make

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
    set_presidio([Match(6, 16, "Jonas Wüst", "Max Mustermann", "PERSON")])
    result, _ = combined.detect_and_anonymize("Hallo Jonas Wüst, wie geht es dir?")
    assert result == "Hallo Max Mustermann, wie geht es dir?"


def test_repeated_name_is_masked_everywhere(pipeline):
    """Presidio findet nur das erste Vorkommen, der Rest wird nachgezogen."""
    combined, set_presidio, _ = pipeline
    set_presidio([Match(0, 10, "Jonas Wüst", "Max Mustermann", "PERSON")])
    result, _ = combined.detect_and_anonymize("Jonas Wüst schreibt. Danach antwortet jonas wüst.")
    # match_case: kleingeschriebenes Vorkommen bekommt kleingeschriebenen Fake
    assert result == "Max Mustermann schreibt. Danach antwortet max mustermann."


def test_overlapping_matches_are_not_applied_twice(pipeline):
    combined, set_presidio, _ = pipeline
    set_presidio([Match(9, 21, "max@firma.de", "Max Mustermann", "PERSON")])
    result, findings = combined.detect_and_anonymize("Kontakt: max@firma.de")
    assert len(findings) == 1
    assert findings[0].category == "EMAIL"   # Regex vor Presidio
    assert "Max Mustermann" not in result


# ---------- Edge Cases: Prioritaet und Ueberschneidung ----------

def test_higher_priority_beats_longer_span(fakes):
    custom, presidio = fakes(30, 10)
    custom.set([Match(0, 5, "Jonas", "Kunde", "CUSTOM")])
    presidio.set([Match(0, 10, "Jonas Wüst", "Max Mustermann", "PERSON")])
    result, findings = combined.detect_and_anonymize("Jonas Wüst")
    assert result == "Kunde Wüst"
    assert [f.category for f in findings] == ["CUSTOM"]


def test_same_priority_longer_span_wins(fakes):
    (det,) = fakes(10)
    det.set([Match(0, 5, "Jonas", "Max", "PERSON"),
             Match(0, 10, "Jonas Wüst", "Max Mustermann", "PERSON")])
    result, _ = combined.detect_and_anonymize("Jonas Wüst")
    assert result == "Max Mustermann"


def test_adjacent_matches_are_both_applied(fakes):
    (det,) = fakes(10)
    det.set([Match(0, 3, "foo", "X", "T"), Match(3, 6, "bar", "Y", "T")])
    result, findings = combined.detect_and_anonymize("foobar")
    assert result == "XY"
    assert len(findings) == 2


def test_replacements_with_different_lengths_keep_positions(fakes):
    (det,) = fakes(10)
    det.set([Match(0, 4, "Anna", "Zoe", "PERSON"),
             Match(9, 13, "Bert", "Maximilian", "PERSON")])
    result, _ = combined.detect_and_anonymize("Anna und Bert")
    assert result == "Zoe und Maximilian"


def test_detector_order_in_list_does_not_matter(fakes):
    low, high = fakes(10, 30)   # niedrige Prioritaet steht zuerst in der Liste
    low.set([Match(0, 10, "Jonas Wüst", "Max Mustermann", "PERSON")])
    high.set([Match(0, 10, "Jonas Wüst", "Kunde", "CUSTOM")])
    result, _ = combined.detect_and_anonymize("Jonas Wüst")
    assert result == "Kunde"


# ---------- Edge Cases: Propagation ----------

def test_propagation_respects_word_boundaries(fakes):
    (det,) = fakes(10)
    det.set([Match(0, 5, "Jonas", "Max", "PERSON")])
    result, _ = combined.detect_and_anonymize("Jonas und Jonasson")
    assert result == "Max und Jonasson"


def test_propagation_skips_already_covered_spans(fakes):
    (det,) = fakes(10)
    det.set([Match(0, 5, "Jonas", "Max", "PERSON"),
             Match(10, 20, "Jonas Wüst", "Erika Beispiel", "PERSON")])
    result, _ = combined.detect_and_anonymize("Jonas und. Jonas Wüst")
    assert "Erika Beispiel" in result
    assert result.count("Max") == 1


# ---------- Edge Cases: Sonderfaelle ----------

def test_empty_text(pipeline):
    combined, _, _ = pipeline
    assert combined.detect_and_anonymize("") == ("", [])


def test_presidio_extra_findings_are_included(pipeline):
    combined, set_presidio, _ = pipeline
    extra = [Finding("Max", "Jonas", "PERSON"), Finding("Mustermann", "Wüst", "PERSON")]
    set_presidio([Match(0, 10, "Jonas Wüst", "Max Mustermann", "PERSON")], extra)
    _, findings = combined.detect_and_anonymize("Jonas Wüst")
    assert extra[0] in findings and extra[1] in findings
    assert len(findings) == 3   # 1 Match + 2 positionslose


def test_custom_rule_pattern_is_escaped(pipeline):
    combined, _, set_rules = pipeline
    set_rules({"a.b": "X"})
    result, _ = combined.detect_and_anonymize("axb und a.b")
    assert result == "axb und x"   # '.' ist kein Regex-Wildcard


def test_umlauts_and_case_in_custom_rule(pipeline):
    combined, _, set_rules = pipeline
    set_rules({"müller": "schmidt"})
    result, _ = combined.detect_and_anonymize("MÜLLER, Müller, müller")
    assert result == "SCHMIDT, Schmidt, schmidt"


def test_chat_id_reaches_custom_rules(pipeline):
    combined, _, _ = pipeline
    combined.detect_and_anonymize("irgendwas", chat_id="chat-42")
    assert "chat-42" in combined.state["chat_ids"]


def test_original_text_is_not_mutated_between_detectors(pipeline):
    """Alle Detektoren sehen den Originaltext, auch wenn Custom schon trifft."""
    combined, set_presidio, set_rules = pipeline
    set_rules({"Jonas": "Kunde"})
    set_presidio([Match(6, 16, "Jonas Wüst", "Max Mustermann", "PERSON")])
    result, _ = combined.detect_and_anonymize("Hallo Jonas Wüst")
    assert result == "Hallo Kunde Wüst"

def test_lang_is_passed_to_detectors(fakes):
    (det,) = fakes(10)
    combined.detect_and_anonymize("Hello there", chat_id="c", lang_code="en")
    assert det.lang_code == ["en"]