import re
from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageConfig:
    lang_code: str
    spacy_model: str
    fake_pools: dict[str, list[str]] #all categories
    presidio_entities: tuple[str, ...] = ("PERSON", "LOCATION")
    presidio_greeting_words: frozenset[str] = frozenset()
    score_threshold: float = 0.5 # for spaCy model


