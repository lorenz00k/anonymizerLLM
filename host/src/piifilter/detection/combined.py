"""
Kombiniert Regex- und Presidio-Erkennung.
"""
from piifilter.detection.regex_rules import detect_and_anonymize as regex_detect
from piifilter.detection.presidio_engine import detect_and_anonymize as presidio_detect


def detect_and_anonymize(text: str) -> tuple[str, list]:
    # Erst Regex (E-Mail, IBAN, Telefon - strukturierte Muster)
    text_after_regex, regex_findings = regex_detect(text)

    # Dann Presidio auf dem bereits teil-anonymisierten Text
    # (Namen, Orte - kontextbasiert)
    final_text, presidio_findings = presidio_detect(text_after_regex)

    return final_text, regex_findings + presidio_findings