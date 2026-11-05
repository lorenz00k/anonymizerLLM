"""
Regex-basierte PII-Erkennung.
Findet Kandidaten im ORIGINALTEXT und ordnet ihnen einen plausiblen,
synthetischen Fake-Wert zu. Ersetzt selbst nichts im Text - das
uebernimmt combined.py zentral, nachdem alle Stufen ihre Funde
gemeldet haben.
"""

import re

from piifilter.detection.rule_based.types import Match
from piifilter.languages import get_language

PATTERNS = {
    "EMAIL": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "IBAN": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"),
    "PHONE": re.compile(r"\b(?:\+\d{1,3}[\s-]?)?\(?\d{2,5}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}\b"),
}

def find_matches(text: str, lang_code: str | None = None) -> list[Match]:
    """
    Durchsucht den Originaltext nach allen Regex-Mustern. Jeder
    EINZIGARTIGE Original-Wert bekommt konsequent denselben Fake-Wert
    innerhalb eines Aufrufs.
    """
    pools = get_language(lang_code).fake_pools
    matches: list[Match] = []
    assigned: dict[str, str] = {}
    used_counts: dict[str, int] = {}

    for category, pattern in PATTERNS.items():
        pool = pools[category]
        for m in pattern.finditer(text):
            original = m.group(0)

            if original in assigned:
                fake_value = assigned[original]
            else:
                count = used_counts.get(category, 0)
                fake_value = pool[count % len(pool)]
                used_counts[category] = count + 1
                assigned[original] = fake_value

            matches.append(Match(m.start(), m.end(), original, fake_value, category))

    return matches
