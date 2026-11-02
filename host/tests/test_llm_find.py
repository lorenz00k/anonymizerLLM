"""
Tests fuer die LLM-Stufe (Stufe 4). Ollama wird gemockt, es laeuft also
kein Modell - getestet wird die Verarbeitung der Modellantwort.
"""

import json

import pytest

from piifilter.detection.llm import llm_find


@pytest.fixture
def fake_llm(monkeypatch):
    """Liefert eine Funktion, die die naechste Ollama-Antwort festlegt."""
    calls = []

    def _set(raw):
        def fake_chat(*args, **kwargs):
            calls.append((args, kwargs))
            return raw

        monkeypatch.setattr(llm_find.ollama_client, "chat", fake_chat)
        return calls

    return _set


def _answer(*findings) -> str:
    return json.dumps({"findings": list(findings)})


def test_valid_finding_becomes_match(fake_llm):
    text = "Mein aktuelles Gehalt beträgt 58.000€ brutto, wie verhandle ich?"
    fake_llm(
        _answer(
            {
                "text": "Mein aktuelles Gehalt beträgt 58.000€ brutto",
                "category": "PERSONENKENNUNG",
                "reason": "Gehaltsangabe",
            }
        )
    )
    (m,) = llm_find.find_matches(text)
    assert m.category == "PERSONENKENNUNG"
    assert m.fake_value == "[PERSONENKENNUNG_1]"
    assert text[m.start : m.end] == "Mein aktuelles Gehalt beträgt 58.000€ brutto"


def test_empty_findings_returns_nothing(fake_llm):
    fake_llm(_answer())
    assert llm_find.find_matches("Wie schreibe ich eine Einkaufsliste?") == []


def test_invalid_category_is_dropped(fake_llm):
    fake_llm(_answer({"text": "Milch", "category": "GESUNDHEIT", "reason": "x"}))
    assert llm_find.find_matches("Ich kaufe Milch") == []


def test_negation_in_reason_is_dropped(fake_llm):
    fake_llm(
        _answer(
            {
                "text": "Milch",
                "category": "FIRMENGEHEIMNIS",
                "reason": "Kein Finding, harmlos",
            }
        )
    )
    assert llm_find.find_matches("Ich kaufe Milch") == []


def test_snippet_not_in_text_is_dropped(fake_llm):
    fake_llm(
        _answer(
            {
                "text": "völlig anderer erfundener Satz",
                "category": "FIRMENGEHEIMNIS",
                "reason": "x",
            }
        )
    )
    assert llm_find.find_matches("Ich kaufe Milch und Brot") == []


def test_slightly_wrong_snippet_is_anchored_by_fuzzy_match(fake_llm):
    text = "Das Passwort lautet hunter2abc und gilt für den Server."
    fake_llm(
        _answer(
            {
                "text": "Passwort lautet hunter2abd",  # ein Zeichen daneben
                "category": "TECHNISCHES_SECRET",
                "reason": "Passwort",
            }
        )
    )
    (m,) = llm_find.find_matches(text)
    assert "hunter2abc" in text[m.start : m.end]


def test_ollama_unreachable_returns_empty(fake_llm):
    fake_llm(None)  # ollama_client.chat gibt None bei Verbindungsfehler
    assert llm_find.find_matches("Irgendein Text") == []


def test_non_json_answer_returns_empty(fake_llm):
    fake_llm("Das ist kein JSON")
    assert llm_find.find_matches("Irgendein Text") == []


def test_empty_text_does_not_call_the_model(fake_llm):
    calls = fake_llm(_answer())
    assert llm_find.find_matches("   ") == []
    assert calls == []


def test_close_findings_are_merged():
    findings = [
        {"start": 0, "end": 5, "text": "abcde", "category": "FIRMENGEHEIMNIS", "reason": "a"},
        {"start": 8, "end": 12, "text": "hijk", "category": "FIRMENGEHEIMNIS", "reason": "b"},
    ]
    merged = llm_find._merge_close_findings(findings)
    assert len(merged) == 1
    assert (merged[0]["start"], merged[0]["end"]) == (0, 12)
