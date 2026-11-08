from piifilter.detection.rule_based import regex_rules, custom_rules
from piifilter.languages import DEFAULT_LANG


class CustomRulesDetector:
    priority = 30

    def find(self, text, assigner, chat_id: str | None = None, lang_code=None):
        matches = custom_rules.find_custom_matches(text, chat_id)
        return matches, []


class RegexDetector:
    priority = 20

    def find(self, text, assigner, chat_id: str | None = None, lang_code=None):
        matches = regex_rules.find_matches(text, assigner, lang_code or DEFAULT_LANG)
        return matches, []


class PresidioDetector:
    priority = 10

    def find(self, text, assigner, chat_id: str | None = None, lang_code=None):
        from piifilter.detection.rule_based import (
            presidio_engine,
        )  # lazy: erst spaCy bei gebrauch laden

        return presidio_engine.find_matches(text, assigner, lang_code or DEFAULT_LANG)
