"""Tests fuer die Regex-Stufe (Stufe 2). Rein deterministisch, keine Modelle noetig."""
import pytest

from piifilter.detection.rule_based import regex_rules
from piifilter.detection.rule_based.regex_rules import find_matches
from piifilter.languages import LANGUAGES, get_language


def _by_category(matches, category):
    return [m for m in matches if m.category == category]


def test_finds_email_with_correct_span():
    text = "Schreib an max.muster@firma.de bitte."
    matches = _by_category(find_matches(text), "EMAIL")
    assert len(matches) == 1
    m = matches[0]
    assert m.original == "max.muster@firma.de"
    assert text[m.start : m.end] == m.original


def test_finds_iban():
    matches = _by_category(find_matches("IBAN: DE89370400440532013000"), "IBAN")
    assert [m.original for m in matches] == ["DE89370400440532013000"]


def test_finds_phone_number():
    matches = _by_category(find_matches("Ruf mich an: +49 30 1234567"), "PHONE")
    assert len(matches) == 1
    assert "1234567" in matches[0].original


def test_plain_text_has_no_matches():
    assert find_matches("Wie schreibe ich eine Einkaufsliste fuer Milch und Brot?") == []


def test_same_value_gets_same_fake_value():
    text = "a@x.de und nochmal a@x.de"
    matches = _by_category(find_matches(text), "EMAIL")
    assert len(matches) == 2
    assert matches[0].fake_value == matches[1].fake_value


def test_different_values_get_different_fake_values():
    matches = _by_category(find_matches("a@x.de und b@y.de"), "EMAIL")
    assert matches[0].fake_value != matches[1].fake_value


def test_fake_value_comes_from_pool():
    (m,) = _by_category(find_matches("a@x.de"), "EMAIL")
    assert m.fake_value in get_language("de").fake_pools["EMAIL"]

@pytest.mark.parametrize("lang_code", LANGUAGES)
def test_regex_uses_pool_of_language(lang_code):
    text = "Mail an max@firma.de bitte"
    (m,) = [x for x in regex_rules.find_matches(text, lang_code) if x.category == "EMAIL"]
    assert m.fake_value in LANGUAGES[lang_code].fake_pools["EMAIL"]

def test_regex_default_is_german():
    (m,) = [x for x in regex_rules.find_matches("a@b.de") if x.category == "EMAIL"]
    assert m.fake_value in LANGUAGES["de"].fake_pools["EMAIL"]
