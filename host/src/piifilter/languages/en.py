from piifilter.languages.base import LanguageConfig


FAKE_EMAILS = ["john_doe@example.com", "lisa.hanna@example.com", "ray.hudson@example.com"]
FAKE_IBANS = ["GB00000000000000000000", "GB11111111111111111111"]
FAKE_PHONES = ["+44 30 1234567", "+44 89 7654321"]
FAKE_NAMES = ["John Doe", "Lisa Eriksen", "Hannah Dumpy", "Ray Hudson"]
FAKE_LOCATIONS = ["Exmapletown", "Capital"]

FAKE_POOLS = {
    "EMAIL": FAKE_EMAILS,
    "IBAN": FAKE_IBANS,
    "PHONE": FAKE_PHONES,
    "PERSON": FAKE_NAMES,
    "LOCATION": FAKE_LOCATIONS,
}

ENGLISH = LanguageConfig(
    lang_code="en",
    spacy_model="en_core_web_lg",
    fake_pools= FAKE_POOLS,
    presidio_entities=("PERSON", "LOCATION"),
    presidio_greeting_words=frozenset(
        {"hello", "hi", "hey", "dear", "love", "good", "welcome", "greetings"}
    ),
    score_threshold=0.5,
)

