"""
Kombiniert eigene Regeln, Regex- und Presidio-Erkennung.
Eigene Regeln haben Vorrang - sie werden zuerst angewendet, damit sie
garantiert greifen, unabhaengig davon, was Presidio/Regex sonst finden.
"""

from piifilter.custom_rules import load_rules
from piifilter.detection.regex_rules import detect_and_anonymize as regex_detect
from piifilter.detection.presidio_engine import detect_and_anonymize as presidio_detect
from piifilter.detection.regex_rules import Finding
import re


def _match_case(fake_value: str, matched_text: str) -> str:
    if matched_text.isupper():
        return fake_value.upper()
    if matched_text.istitle():
        return fake_value.title()
    if matched_text.islower():
        return fake_value.lower()
    return fake_value

def apply_custom_rules(text: str) -> tuple[str, list[Finding]]:
    rules = load_rules()
    findings = []
    result = text
    for original, fake_value in rules.items():
        pattern = re.compile(re.escape(original), re.IGNORECASE)
        matches = list(pattern.finditer(result))
        if matches:
            def _replacer(m):
                return _match_case(fake_value, m.group(0))
            result = pattern.sub(_replacer, result)
            findings.append(Finding(fake_value, original, "CUSTOM"))
    return result, findings

def detect_and_anonymize(text: str) -> tuple[str, list]:
    text_after_custom, custom_findings = apply_custom_rules(text)
    text_after_regex, regex_findings = regex_detect(text_after_custom)
    final_text, presidio_findings = presidio_detect(text_after_regex)
    return final_text, custom_findings + regex_findings + presidio_findings