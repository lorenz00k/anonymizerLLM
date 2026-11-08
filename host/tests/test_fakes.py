import pytest

from piifilter.detection.rule_based.fakes import FakeAssigner
from piifilter.languages import LANGUAGES, get_language


def make(lang_code="de"):
    return FakeAssigner(get_language(lang_code))


def test_same_original_same_fake():
    a = make()
    assert a.get("PERSON", "Anna") == a.get("PERSON", "Anna")


def test_pool_values_are_used_in_order():
    a = make()
    pool = get_language("de").fake_pools["PERSON"]
    assert [a.get("PERSON", f"P{i}") for i in range(len(pool))] == pool


def test_never_repeats_past_pool_end():
    a = make()
    fakes = [a.get("PERSON", f"P{i}") for i in range(20)]
    assert len(set(fakes)) == 20
    assert fakes[-1].startswith("[PERSON_")


def test_numbering_continues_after_pool():
    a = make()
    pool_len = len(get_language("de").fake_pools["IBAN"])
    fakes = [a.get("IBAN", f"X{i}") for i in range(pool_len + 2)]
    assert fakes[pool_len] == f"[IBAN_{pool_len + 1}]"
    assert fakes[pool_len + 1] == f"[IBAN_{pool_len + 2}]"


def test_unknown_category_is_numbered_not_shared():
    a = make()
    assert a.get("ORGANIZATION", "X") == "[ORGANIZATION_1]"
    assert a.get("ORGANIZATION", "Y") == "[ORGANIZATION_2]"


def test_same_original_in_different_categories_is_independent():
    a = make()
    assert a.get("PERSON", "Berlin") != a.get("LOCATION", "Berlin")


def test_categories_count_independently():
    a = make()
    a.get("PERSON", "A")
    assert a.get("LOCATION", "B") == get_language("de").fake_pools["LOCATION"][0]


def test_instances_do_not_share_state():
    a, b = make(), make()
    a.get("PERSON", "Anna")
    assert b.get("PERSON", "Bert") == get_language("de").fake_pools["PERSON"][0]


@pytest.mark.parametrize("lang_code", LANGUAGES)
def test_uses_pool_of_language(lang_code):
    a = make(lang_code)
    assert a.get("PERSON", "X") == LANGUAGES[lang_code].fake_pools["PERSON"][0]


def test_repeated_original_does_not_consume_a_pool_entry():
    a = make()
    pool = get_language("de").fake_pools["PERSON"]
    a.get("PERSON", "Anna")
    a.get("PERSON", "Anna")
    a.get("PERSON", "Anna")
    assert a.get("PERSON", "Bert") == pool[1]


def test_repeated_original_past_pool_end_keeps_its_fake():
    a = make()
    n = len(get_language("de").fake_pools["PERSON"]) + 2
    fakes = [a.get("PERSON", f"P{i}") for i in range(n)]
    assert a.get("PERSON", f"P{n - 1}") == fakes[-1]
    assert a.get("PERSON", "P0") == fakes[0]


def test_next_new_original_after_overflow_gets_next_number():
    a = make()
    n = len(get_language("de").fake_pools["PERSON"])
    for i in range(n + 1):
        a.get("PERSON", f"P{i}")
    a.get("PERSON", "P0")  # Wiederholung darf den Zaehler nicht erhoehen
    assert a.get("PERSON", "Neu") == f"[PERSON_{n + 2}]"


def test_overflow_placeholders_differ_between_categories():
    a = make()
    n_person = len(get_language("de").fake_pools["PERSON"])
    n_loc = len(get_language("de").fake_pools["LOCATION"])
    person = [a.get("PERSON", f"P{i}") for i in range(n_person + 1)][-1]
    loc = [a.get("LOCATION", f"L{i}") for i in range(n_loc + 1)][-1]
    assert person.startswith("[PERSON_")
    assert loc.startswith("[LOCATION_")
    assert person != loc


def test_overflow_in_one_category_does_not_affect_another():
    a = make()
    for i in range(30):
        a.get("PERSON", f"P{i}")
    assert a.get("LOCATION", "Berlin") == get_language("de").fake_pools["LOCATION"][0]


def test_category_missing_in_config_is_numbered_from_one():
    a = make()
    assert a.get("DOES_NOT_EXIST", "x") == "[DOES_NOT_EXIST_1]"


def test_originals_are_case_sensitive():
    # Bewusst so: Gross-/Kleinschreibung faengt combined.propagate_matches ab.
    a = make()
    assert a.get("PERSON", "Anna") != a.get("PERSON", "anna")


def test_originals_differing_by_whitespace_are_distinct():
    a = make()
    assert a.get("PERSON", "Anna") != a.get("PERSON", "Anna ")


def test_assigner_does_not_mutate_language_pools():
    cfg = get_language("de")
    before = {k: list(v) for k, v in cfg.fake_pools.items()}
    a = FakeAssigner(cfg)
    for i in range(30):
        a.get("PERSON", f"P{i}")
        a.get("EMAIL", f"e{i}")
    assert cfg.fake_pools == before


def test_empty_original_gets_a_value_without_crashing():
    a = make()
    assert a.get("PERSON", "")


def _all_pairs():
    return [(code, cat) for code, cfg in LANGUAGES.items() for cat in cfg.fake_pools]


@pytest.mark.parametrize("lang_code,category", _all_pairs())
def test_pool_is_used_in_order_then_numbered(lang_code, category):
    a = make(lang_code)
    pool = LANGUAGES[lang_code].fake_pools[category]
    fakes = [a.get(category, f"o{i}") for i in range(len(pool) + 2)]
    assert fakes[: len(pool)] == pool
    assert fakes[len(pool)] == f"[{category}_{len(pool) + 1}]"
    assert len(set(fakes)) == len(fakes)
