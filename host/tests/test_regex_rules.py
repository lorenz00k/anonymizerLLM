"""Tests fuer die Regex-Stufe (Stufe 2). Rein deterministisch, keine Modelle noetig."""

import pytest

from piifilter.detection.rule_based import regex_rules
from piifilter.detection.rule_based.fakes import FakeAssigner
from piifilter.languages import LANGUAGES, get_language


def run(text, lang_code="de", assigner=None):
    """Ruft regex_rules.find_matches so auf, wie combined.py es tut."""
    assigner = assigner or FakeAssigner(get_language(lang_code))
    return regex_rules.find_matches(text, assigner, lang_code)


def _by_category(matches, category):
    return [m for m in matches if m.category == category]


def _pool(lang_code, category):
    return LANGUAGES[lang_code].fake_pools[category]


def test_finds_email_with_correct_span():
    text = "Schreib an max.muster@firma.de bitte."
    matches = _by_category(run(text), "EMAIL")
    assert len(matches) == 1
    m = matches[0]
    assert m.original == "max.muster@firma.de"
    assert text[m.start : m.end] == m.original


def test_finds_iban():
    matches = _by_category(run("IBAN: DE89370400440532013000"), "IBAN")
    assert [m.original for m in matches] == ["DE89370400440532013000"]


def test_finds_phone_number():
    matches = _by_category(run("Ruf mich an: +49 30 1234567"), "PHONE")
    assert len(matches) == 1
    assert "1234567" in matches[0].original


def test_plain_text_has_no_matches():
    assert run("Wie schreibe ich eine Einkaufsliste fuer Milch und Brot?") == []


def test_same_value_gets_same_fake_value():
    text = "a@x.de und nochmal a@x.de"
    matches = _by_category(run(text), "EMAIL")
    assert len(matches) == 2
    assert matches[0].fake_value == matches[1].fake_value


def test_different_values_get_different_fake_values():
    matches = _by_category(run("a@x.de und b@y.de"), "EMAIL")
    assert matches[0].fake_value != matches[1].fake_value


def test_fake_value_comes_from_pool():
    (m,) = _by_category(run("a@x.de"), "EMAIL")
    assert m.fake_value in get_language("de").fake_pools["EMAIL"]


@pytest.mark.parametrize("lang_code", LANGUAGES)
def test_fake_value_comes_from_pool_of_language(lang_code):
    (m,) = _by_category(run("Mail an max@firma.de bitte", lang_code), "EMAIL")
    assert m.fake_value in _pool(lang_code, "EMAIL")


def test_default_language_is_german():
    (m,) = _by_category(run("a@b.de"), "EMAIL")
    assert m.fake_value in _pool("de", "EMAIL")


def test_distinct_originals_stay_distinct_past_pool_end():
    n = len(_pool("de", "EMAIL")) + 3
    text = " ".join(f"a{i}@x.de" for i in range(n))
    fakes = [m.fake_value for m in _by_category(run(text), "EMAIL")]
    assert len(fakes) == n
    assert len(set(fakes)) == n
    assert fakes[-1].startswith("[EMAIL_")


def test_phone_pool_overflow_stays_unique():
    n = len(_pool("de", "PHONE")) + 2
    text = " ".join(f"0151 {1000000 + i}" for i in range(n))
    fakes = [m.fake_value for m in _by_category(run(text), "PHONE")]
    assert len(fakes) == n
    assert len(set(fakes)) == n


def test_repeated_original_past_pool_end_keeps_its_fake():
    n = len(_pool("de", "EMAIL")) + 1
    originals = [f"a{i}@x.de" for i in range(n)]
    text = " ".join(originals) + f" {originals[-1]}"
    fakes = [m.fake_value for m in _by_category(run(text), "EMAIL")]
    assert fakes[-1] == fakes[-2]


# assigner
def test_categories_are_counted_independently():
    matches = run("a@x.de DE89370400440532013000")
    (email,) = _by_category(matches, "EMAIL")
    (iban,) = _by_category(matches, "IBAN")
    assert email.fake_value == _pool("de", "EMAIL")[0]
    assert iban.fake_value == _pool("de", "IBAN")[0]


def test_shared_assigner_continues_counting():
    assigner = FakeAssigner(get_language("de"))
    first = run("a@x.de", assigner=assigner)
    second = run("b@x.de", assigner=assigner)
    assert first[0].fake_value == _pool("de", "EMAIL")[0]
    assert second[0].fake_value == _pool("de", "EMAIL")[1]


def test_separate_assigners_do_not_share_state():
    assert run("a@x.de")[0].fake_value == run("b@x.de")[0].fake_value


@pytest.mark.parametrize("lang_code", LANGUAGES)
def test_every_language_has_a_pool_for_each_regex_category(lang_code):
    for category in regex_rules.PATTERNS:
        assert _pool(lang_code, category), f"{lang_code}: kein Pool fuer {category}"
