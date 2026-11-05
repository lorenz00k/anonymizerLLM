from types import SimpleNamespace

import pytest

from piifilter.detection.rule_based import presidio_engine
from piifilter.languages import LANGUAGES


def _r(text, snippet, entity, score=0.9):
    start = text.index(snippet)
    return SimpleNamespace(start=start, end=start + len(snippet),
                           entity_type=entity, score=score)


class FakeAnalyzer:
    def __init__(self, results):
        self.results, self.calls = results, []

    def analyze(self, **kwargs):
        self.calls.append(kwargs)
        return list(self.results)


@pytest.fixture
def engine(monkeypatch):
    def install(results):
        fake = FakeAnalyzer(results)
        monkeypatch.setattr(presidio_engine, "get_analyzer", lambda code: fake)
        return fake
    return install


# ---------- _trim_greeting (reine Funktion) ----------

GREET = frozenset({"hallo", "sehr"})

@pytest.mark.parametrize("snippet,trimmed", [
    ("Hallo Erika", "Erika"),
    ("hallo Erika", "Erika"),
    ("Hallo, Erika", "Erika"),
    ("Erika Müller", "Erika Müller"),   # keine Anrede
    ("Hallo", "Hallo"),                 # nur ein Wort: nichts abschneiden
])
def test_trim_greeting(snippet, trimmed):
    s, e = presidio_engine._trim_greeting(snippet, 0, len(snippet), GREET)
    assert snippet[s:e] == trimmed


# ---------- find_matches mit Fake-Analyzer ----------

def test_config_values_reach_analyzer(engine):
    fake = engine([])
    for code, lang_conf in LANGUAGES.items():
        presidio_engine.find_matches("irgendein Text", language=code)
        call = fake.calls[-1]
        assert call["language"] == lang_conf.lang_code
        assert call["entities"] == list(lang_conf.presidio_entities)
        assert call["score_threshold"] == lang_conf.score_threshold


def test_german_greeting_is_trimmed_and_pool_is_german(engine):
    text = "Hallo Erika Müller wohnt in Berlin."
    engine([_r(text, "Hallo Erika Müller", "PERSON"), _r(text, "Berlin", "LOCATION")])
    matches, extra = presidio_engine.find_matches(text, language="de")
    person, loc = matches
    assert person.original == "Erika Müller"
    assert text[person.start:person.end] == "Erika Müller"
    assert person.fake_value == LANGUAGES["de"].fake_pools["PERSON"][0]
    assert loc.fake_value == LANGUAGES["de"].fake_pools["LOCATION"][0]
    assert len(extra) == 2                      # Vor- und Nachname einzeln


def test_english_uses_english_pool_and_greeting(engine):
    text = "Dear John Smith lives in London."
    engine([_r(text, "Dear John Smith", "PERSON"), _r(text, "London", "LOCATION")])
    matches, _ = presidio_engine.find_matches(text, language="en")
    assert matches[0].original == "John Smith"
    assert matches[0].fake_value == LANGUAGES["en"].fake_pools["PERSON"][0]
    assert matches[1].fake_value == LANGUAGES["en"].fake_pools["LOCATION"][0]


def test_same_original_gets_same_fake(engine):
    text = "Anna und Anna"
    engine([_r(text, "Anna", "PERSON"),
            SimpleNamespace(start=9, end=13, entity_type="PERSON", score=0.9)])
    matches, _ = presidio_engine.find_matches(text, language="de")
    assert matches[0].fake_value == matches[1].fake_value


def test_different_originals_get_different_fakes(engine):
    text = "Anna und Bert"
    engine([_r(text, "Anna", "PERSON"), _r(text, "Bert", "PERSON")])
    matches, _ = presidio_engine.find_matches(text, language="de")
    assert matches[0].fake_value != matches[1].fake_value


def test_unknown_category_falls_back_to_placeholder(engine):
    text = "Quelle: Foo"
    engine([_r(text, "Foo", "ORGANIZATION")])
    (m,), _ = presidio_engine.find_matches(text, language="de")
    assert m.fake_value == "[REDACTED_ORGANIZATION]"


def test_whitespace_only_span_is_skipped(engine):
    engine([SimpleNamespace(start=0, end=2, entity_type="PERSON", score=0.9)])
    assert presidio_engine.find_matches("  x", language="de") == ([], [])


def test_unknown_language_uses_german(engine):
    fake = engine([])
    presidio_engine.find_matches("Text", language="fr")
    assert fake.calls[-1]["language"] == "de"


def test_default_lang_is_german(engine):
    fake = engine([])
    presidio_engine.find_matches("Text")
    assert fake.calls[-1]["language"] == "de"


# ---------- echte Modelle ----------

CASES = [
    # (lang, text, erwarteter Originaltext, Kategorie)
    ("de", "Sehr geehrte Frau Merz, danke für die Nachricht.", "Merz", "PERSON"),
    ("de", "Hallo Erika, wie geht es dir?", "Erika", "PERSON"),
    ("de", "Ich wohne seit Jahren in Hamburg.", "Hamburg", "LOCATION"),
    ("en", "Dear Mr. Smith, thanks for your message.", "Smith", "PERSON"),
    ("en", "I have lived in London for years.", "London", "LOCATION"),
]


@pytest.mark.slow
@pytest.mark.parametrize("lang,text,original,category", CASES)
def test_real_model_finds_entities(lang, text, original, category):
    matches, _ = presidio_engine.find_matches(text, language=lang)
    assert any(original in m.original and m.category == category for m in matches), matches


@pytest.mark.slow
def test_real_model_trims_greeting():
    matches, _ = presidio_engine.find_matches("Hallo Erika, wie geht es dir?", language="de")
    assert all(not m.original.lower().startswith("hallo") for m in matches)


@pytest.mark.slow
def test_english_text_with_german_model_does_not_crash():
    presidio_engine.find_matches("I live in London.", language="de")


@pytest.mark.slow
def test_only_requested_model_is_built():
    presidio_engine._build_analyzer.cache_clear()
    presidio_engine.find_matches("Ich wohne in Hamburg.", language="de")
    assert presidio_engine._build_analyzer.cache_info().currsize == 1