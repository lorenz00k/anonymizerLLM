from types import SimpleNamespace

import pytest

from piifilter.detection.rule_based import presidio_engine
from piifilter.detection.rule_based.fakes import FakeAssigner
from piifilter.languages import LANGUAGES, get_language


def run(text, lang_code="de", assigner=None):
    """Ruft presidio_engine.find_matches so auf, wie combined.py es tut."""
    assigner = assigner or FakeAssigner(get_language(lang_code))
    return presidio_engine.find_matches(text, assigner, lang_code)


def _r(text, snippet, entity, score=0.9):
    start = text.index(snippet)
    return SimpleNamespace(start=start, end=start + len(snippet), entity_type=entity, score=score)


def _at(start, end, entity="PERSON", score=0.9):
    return SimpleNamespace(start=start, end=end, entity_type=entity, score=score)


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


def _pool(lang_code, category):
    return LANGUAGES[lang_code].fake_pools[category]


# ---------- _trim_greeting (reine Funktion) ----------

GREET = frozenset({"hallo", "sehr"})


@pytest.mark.parametrize(
    "snippet,trimmed",
    [
        ("Hallo Erika", "Erika"),
        ("hallo Erika", "Erika"),
        ("Hallo, Erika", "Erika"),
        ("Erika Müller", "Erika Müller"),  # keine Anrede
        ("Hallo", "Hallo"),  # nur ein Wort: nichts abschneiden
    ],
)
def test_trim_greeting(snippet, trimmed):
    s, e = presidio_engine._trim_greeting(snippet, 0, len(snippet), GREET)
    assert snippet[s:e] == trimmed


# ---------- find_matches mit Fake-Analyzer ----------


def test_config_values_reach_analyzer(engine):
    fake = engine([])
    for code, lang_conf in LANGUAGES.items():
        run("irgendein Text", lang_code=code)
        call = fake.calls[-1]
        assert call["language"] == lang_conf.lang_code
        assert call["entities"] == list(lang_conf.presidio_entities)
        assert call["score_threshold"] == lang_conf.score_threshold


def test_german_greeting_is_trimmed_and_pool_is_german(engine):
    text = "Hallo Erika Müller wohnt in Berlin."
    engine([_r(text, "Hallo Erika Müller", "PERSON"), _r(text, "Berlin", "LOCATION")])
    matches, extra = run(text, lang_code="de")
    person, loc = matches
    assert person.original == "Erika Müller"
    assert text[person.start : person.end] == "Erika Müller"
    assert person.fake_value == LANGUAGES["de"].fake_pools["PERSON"][0]
    assert loc.fake_value == LANGUAGES["de"].fake_pools["LOCATION"][0]
    assert len(extra) == 2  # Vor- und Nachname einzeln


def test_english_uses_english_pool_and_greeting(engine):
    text = "Dear John Smith lives in London."
    engine([_r(text, "Dear John Smith", "PERSON"), _r(text, "London", "LOCATION")])
    matches, _ = run(text, lang_code="en")
    assert matches[0].original == "John Smith"
    assert matches[0].fake_value == LANGUAGES["en"].fake_pools["PERSON"][0]
    assert matches[1].fake_value == LANGUAGES["en"].fake_pools["LOCATION"][0]


def test_same_original_gets_same_fake(engine):
    text = "Anna und Anna"
    engine(
        [
            _r(text, "Anna", "PERSON"),
            SimpleNamespace(start=9, end=13, entity_type="PERSON", score=0.9),
        ]
    )
    matches, _ = run(text, lang_code="de")
    assert matches[0].fake_value == matches[1].fake_value


def test_different_originals_get_different_fakes(engine):
    text = "Anna und Bert"
    engine([_r(text, "Anna", "PERSON"), _r(text, "Bert", "PERSON")])
    matches, _ = run(text, lang_code="de")
    assert matches[0].fake_value != matches[1].fake_value


def test_unknown_category_is_numbered_placeholder(engine):
    text = "Quelle: Foo und Bar"
    engine([_r(text, "Foo", "ORGANIZATION"), _r(text, "Bar", "ORGANIZATION")])
    matches, _ = run(text)
    assert [m.fake_value for m in matches] == ["[ORGANIZATION_1]", "[ORGANIZATION_2]"]


def test_whitespace_only_span_is_skipped(engine):
    engine([_at(0, 2)])
    assert run("  x", lang_code="de") == ([], [])


def test_unknown_lang_code_uses_german(engine):
    fake = engine([])
    run("Text", lang_code="fr")
    assert fake.calls[-1]["language"] == "de"


def test_default_lang_is_german(engine):
    fake = engine([])
    presidio_engine.find_matches("Text", FakeAssigner(get_language("de")))
    assert fake.calls[-1]["language"] == "de"


def test_many_persons_never_share_a_fake(engine):
    names = [f"Person{i}" for i in range(10)]
    text = " ".join(names)
    engine([_r(text, n, "PERSON") for n in names])
    matches, _ = run(text)
    assert len({m.fake_value for m in matches}) == 10


def test_overflow_fake_produces_no_partial_name_findings(engine):
    pool_len = len(_pool("de", "PERSON"))
    names = [f"Vorname{i} Nachname{i}" for i in range(pool_len + 1)]
    text = ". ".join(names)
    engine([_r(text, n, "PERSON") for n in names])
    _, extra = run(text)
    # Der Ueberlauf-Name ("[PERSON_n]") hat nur ein Wort, also keine Teilnamen.
    # Voraussetzung: jeder Pool-Name besteht aus mindestens zwei Woertern.
    assert len(extra) == 2 * pool_len


def test_repeated_person_creates_extra_findings_once(engine):
    text = "Anna Müller und Anna Müller"
    engine([_r(text, "Anna Müller", "PERSON"), _at(16, 27)])
    _, extra = run(text)
    assert len(extra) == 2


def test_shared_assigner_continues_counting(engine):
    assigner = FakeAssigner(get_language("de"))
    assigner.get("PERSON", "Schon da")  # belegt Pool-Eintrag 0
    text = "Anna"
    engine([_r(text, "Anna", "PERSON")])
    (m,), _ = run(text, assigner=assigner)
    assert m.fake_value == _pool("de", "PERSON")[1]


def test_person_and_location_with_same_text_get_independent_fakes(engine):
    text = "Berlin Berlin"
    engine([_at(0, 6, "PERSON"), _at(7, 13, "LOCATION")])
    matches, _ = run(text)
    assert matches[0].fake_value == _pool("de", "PERSON")[0]
    assert matches[1].fake_value == _pool("de", "LOCATION")[0]


def test_positions_point_into_original_text(engine):
    text = "Hallo Erika Müller wohnt in Berlin."
    engine([_r(text, "Hallo Erika Müller", "PERSON"), _r(text, "Berlin", "LOCATION")])
    for m in run(text)[0]:
        assert text[m.start : m.end] == m.original


def test_no_results_gives_empty_lists(engine):
    engine([])
    assert run("Nichts zu finden") == ([], [])


# ---------- echte Modelle ----------

CASES = [
    # (lang_code, text, erwarteter Originaltext, Kategorie)
    ("de", "Sehr geehrte Frau Merz, danke für die Nachricht.", "Merz", "PERSON"),
    ("de", "Hallo Erika, wie geht es dir?", "Erika", "PERSON"),
    ("de", "Ich wohne seit Jahren in Hamburg.", "Hamburg", "LOCATION"),
    ("en", "Dear Mr. Smith, thanks for your message.", "Smith", "PERSON"),
    ("en", "I have lived in London for years.", "London", "LOCATION"),
]


@pytest.mark.slow
@pytest.mark.parametrize("lang_code,text,original,category", CASES)
def test_real_model_finds_entities(lang_code, text, original, category):
    matches, _ = run(text, lang_code=lang_code)
    assert any(original in m.original and m.category == category for m in matches), matches


@pytest.mark.slow
def test_real_model_trims_greeting():
    matches, _ = run("Hallo Erika, wie geht es dir?", lang_code="de")
    assert all(not m.original.lower().startswith("hallo") for m in matches)


@pytest.mark.slow
def test_english_text_with_german_model_does_not_crash():
    run("I live in London.", lang_code="de")


@pytest.mark.slow
def test_only_requested_model_is_built():
    presidio_engine._build_analyzer.cache_clear()
    run("Ich wohne in Hamburg.", lang_code="de")
    assert presidio_engine._build_analyzer.cache_info().currsize == 1
