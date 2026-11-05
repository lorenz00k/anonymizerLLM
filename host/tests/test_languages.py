import pytest

from piifilter.languages import DEFAULT_LANG, LANGUAGES, get_language
from piifilter.languages.detect import detect_language

# Presidio-Namen, die bei uns der Regex-Teil abdeckt bzw. die es so nicht gibt
NOT_PRESIDIO = {"EMAIL", "IBAN", "PHONE"}


@pytest.mark.parametrize("lang", LANGUAGES)
class TestEveryLanguageConfig:
    def test_basic_fields(self, lang):
        lang_conf = LANGUAGES[lang]
        assert lang_conf.lang_code == lang
        assert lang_conf.spacy_model

    def test_presidio_entities_have_fake_pools(self, lang):
        lang_conf = LANGUAGES[lang]
        for entity in lang_conf.presidio_entities:
            assert lang_conf.fake_pools.get(entity), f"{lang}: kein Pool fuer {entity}"

    def test_presidio_entities_are_real_presidio_names(self, lang):
        lang_conf = LANGUAGES[lang]
        assert not NOT_PRESIDIO & set(lang_conf.presidio_entities)

    def test_greeting_words_are_lowercase(self, lang):
        # _trim_greeting vergleicht mit .lower()
        for w in LANGUAGES[lang].presidio_greeting_words:
            assert w == w.lower()

    def test_pools_have_no_duplicates(self, lang):
        for category, pool in LANGUAGES[lang].fake_pools.items():
            assert len(pool) == len(set(pool)), f"{lang}/{category}"

    def test_threshold_in_range(self, lang):
        assert 0.0 <= LANGUAGES[lang].score_threshold <= 1.0


def test_german_pool_has_no_english_default_name():
    assert "John Doe" not in LANGUAGES["de"].fake_pools["PERSON"]


@pytest.mark.parametrize("lang_code", [None, "", "fr", "xx"])
def test_get_language_falls_back_to_default(lang_code):
    assert get_language(lang_code).lang_code == DEFAULT_LANG


@pytest.mark.parametrize("lang_code", list(LANGUAGES))
def test_get_language_known(lang_code):
    assert get_language(lang_code).lang_code == lang_code


@pytest.mark.parametrize("text,expected", [
    ("Ich wohne seit drei Jahren in Hamburg und arbeite dort als Entwickler.", "de"),
    ("I have been living in London for three years and work there as a developer.", "en"),
    ("", "de"),                        # leer
    ("ok", "de"),                      # zu kurz
    ("Bonjour, je m'appelle Pierre et j'habite a Paris depuis trois ans.", "de"),  # nicht unterstuetzt
])
def test_detect_language(text, expected):
    assert detect_language(text) == expected


def test_detect_language_is_deterministic():
    text = "Das ist ein ziemlich kurzer, aber eindeutig deutscher Satz."
    assert len({detect_language(text) for _ in range(20)}) == 1