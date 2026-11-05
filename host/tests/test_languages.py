import pytest

from piifilter.detection.rule_based import regex_rules
from piifilter.languages import DEFAULT_LANG, LANGUAGES, get_language
from piifilter.languages.detect import detect_language

# Presidio-Namen, die bei uns der Regex-Teil abdeckt bzw. die es so nicht gibt
NOT_PRESIDIO = {"EMAIL", "IBAN", "PHONE"}


@pytest.mark.parametrize("lang_code", LANGUAGES)
class TestEveryLanguageConfig:
    def test_basic_fields(self, lang_code):
        lang_conf = LANGUAGES[lang_code]
        assert lang_conf.lang_code == lang_code
        assert lang_conf.spacy_model

    def test_presidio_entities_have_fake_pools(self, lang_code):
        lang_conf = LANGUAGES[lang_code]
        for entity in lang_conf.presidio_entities:
            assert lang_conf.fake_pools.get(entity), f"{lang_code}: kein Pool fuer {entity}"

    def test_presidio_entities_are_real_presidio_names(self, lang_code):
        lang_conf = LANGUAGES[lang_code]
        assert not NOT_PRESIDIO & set(lang_conf.presidio_entities)

    def test_greeting_words_are_lowercase(self, lang_code):
        # _trim_greeting vergleicht mit .lower()
        for w in LANGUAGES[lang_code].presidio_greeting_words:
            assert w == w.lower()

    def test_pools_have_no_duplicates(self, lang_code):
        for category, pool in LANGUAGES[lang_code].fake_pools.items():
            assert len(pool) == len(set(pool)), f"{lang_code}/{category}"

    def test_threshold_in_range(self, lang_code):
        assert 0.0 <= LANGUAGES[lang_code].score_threshold <= 1.0


def test_german_pool_has_no_english_default_name():
    assert "John Doe" not in LANGUAGES["de"].fake_pools["PERSON"]


@pytest.mark.parametrize("lang_code", [None, "", "fr", "xx"])
def test_get_language_falls_back_to_default(lang_code):
    assert get_language(lang_code).lang_code == DEFAULT_LANG


@pytest.mark.parametrize("lang_code", list(LANGUAGES))
def test_get_language_known(lang_code):
    assert get_language(lang_code).lang_code == lang_code


@pytest.mark.parametrize("lang_code", LANGUAGES)
def test_every_language_has_pool_for_each_regex_category(lang_code):
    for category in regex_rules.PATTERNS:
        assert LANGUAGES[lang_code].fake_pools.get(category), f"{lang_code}: {category}"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Ich wohne seit drei Jahren in Hamburg und arbeite dort als Entwickler.", "de"),
        ("I have been living in London for three years and work there as a developer.", "en"),
        ("", "de"),  # leer
        ("ok", "de"),  # zu kurz
        (
            "Bonjour, je m'appelle Pierre et j'habite a Paris depuis trois ans.",
            "de",
        ),  # nicht unterstuetzt
    ],
)
def test_detect_language(text, expected):
    assert detect_language(text) == expected


def test_detect_language_is_deterministic():
    text = "Das ist ein ziemlich kurzer, aber eindeutig deutscher Satz."
    assert len({detect_language(text) for _ in range(20)}) == 1
