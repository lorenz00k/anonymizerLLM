from piifilter.languages.base import LanguageConfig


FAKE_EMAILS = [
    "maxmustermann@example.com",
    "erika.musterfrau@example.com",
    "list_müller@example.com",
]
FAKE_IBANS = ["DE00000000000000000000", "DE11111111111111111111"]
FAKE_PHONES = ["+49 30 1234567", "+49 89 7654321"]
FAKE_NAMES = ["Max Mustermann", "Erika Musterfrau", "Lisa Müller", "Anna Schmidt"]
FAKE_LOCATIONS = ["Musterstadt", "Beispielhausen", "Testdorf"]

FAKE_POOLS = {
    "EMAIL": FAKE_EMAILS,
    "IBAN": FAKE_IBANS,
    "PHONE": FAKE_PHONES,
    "PERSON": FAKE_NAMES,
    "LOCATION": FAKE_LOCATIONS,
}

GERMAN = LanguageConfig(
    lang_code="de",
    spacy_model="de_core_news_lg",
    fake_pools=FAKE_POOLS,
    presidio_entities=("PERSON", "LOCATION"),
    presidio_greeting_words=frozenset(
        {"hallo", "hi", "hey", "liebe", "lieber", "sehr", "guten", "moin"}
    ),
    score_threshold=0.5,
)
