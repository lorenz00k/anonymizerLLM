"""
Tests fuer die Presidio-Stufe (Stufe 3). Brauchen das grosse spaCy-Modell
und werden uebersprungen, wenn es nicht installiert ist (z.B. in der CI).
Lokal ausfuehren nach: python -m spacy download de_core_news_lg
"""

import pytest

pytest.importorskip("presidio_analyzer")
pytest.importorskip("de_core_news_lg")

from piifilter.detection.rule_based import presidio_engine


def test_trim_greeting_removes_leading_greeting_word():
    text = "Hallo Erika"
    start, end = presidio_engine._trim_greeting(text, 0, len(text))
    assert text[start:end] == "Erika"


def test_trim_greeting_keeps_normal_names():
    text = "Erika Musterfrau"
    assert presidio_engine._trim_greeting(text, 0, len(text)) == (0, len(text))


def test_finds_person_name():
    matches, _ = presidio_engine.find_matches("Gestern hat Angela Merkel eine Rede gehalten.")
    assert any(m.category == "PERSON" for m in matches)
