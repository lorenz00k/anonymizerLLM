"""
Regex-basierte PII-Erkennung.
Findet Kandidaten im ORIGINALTEXT und ordnet ihnen einen plausiblen,
synthetischen Fake-Wert zu. Ersetzt selbst nichts im Text - das
uebernimmt combined.py zentral, nachdem alle Stufen ihre Funde
gemeldet haben.
"""

import re

from piifilter.detection.rule_based.types import Match

PATTERNS = {
    "EMAIL": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "IBAN": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"),
    "PHONE": re.compile(r"\b(?:\+\d{1,3}[\s-]?)?\(?\d{2,5}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}\b"),
}


def find_matches(text: str, assigner, lang_code: str | None = None) -> list[Match]:
    """
    Durchsucht den Originaltext nach allen Regex-Mustern. Jeder
    EINZIGARTIGE Original-Wert bekommt konsequent denselben Fake-Wert
    innerhalb eines Aufrufs.
    """
    matches: list[Match] = []

    for category, pattern in PATTERNS.items():
        for m in pattern.finditer(text):
            original = m.group(0)
            matches.append(
                Match(m.start(), m.end(), original, assigner.get(category, original), category)
            )

    return matches
