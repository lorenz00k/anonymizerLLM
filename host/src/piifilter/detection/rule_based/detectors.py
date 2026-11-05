from piifilter.detection.rule_based import regex_rules, custom_rules

class CustomRulesDetector:
    priority = 30
    def find(self, text, chat_id=None, lang_code=None):
        matches = custom_rules.find_custom_matches(text, chat_id)
        return matches, []

class RegexDetector:
    priority = 20
    def find(self, text, chat_id=None, lang_code=None):
        matches = regex_rules.find_matches(text)
        return matches, []

class PresidioDetector:
    priority = 10
    def find(self, text, chat_id=None, lang_code=None):
        from piifilter.detection.rule_based import presidio_engine # lazy: erst spaCy bei gebrauch laden
        return presidio_engine.find_matches(text, lang_code)