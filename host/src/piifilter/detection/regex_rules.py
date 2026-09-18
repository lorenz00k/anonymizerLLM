"""
Regex-basierte PII-Erkennung.
Findet Kandidaten im ORIGINALTEXT und ordnet ihnen einen plausiblen,
synthetischen Fake-Wert zu. Ersetzt selbst nichts im Text - das
uebernimmt combined.py zentral, nachdem alle Stufen ihre Funde
gemeldet haben.
"""
import re

from piifilter.detection.types import Match

PATTERNS = {
    "EMAIL": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "IBAN": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"),
    "PHONE": re.compile(r"\b(?:\+\d{1,3}[\s-]?)?\(?\d{2,5}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}\b"),
}

FAKE_EMAILS = ["maxmustermann@example.com", "erika.musterfrau@example.com", "john.doe@example.com"]
FAKE_IBANS = ["DE00000000000000000000", "DE11111111111111111111"]
FAKE_PHONES = ["+49 30 1234567", "+49 89 7654321"]
FAKE_NAMES = ["Max Mustermann", "Erika Musterfrau", "John Doe", "Anna Schmidt"]
FAKE_LOCATIONS = ["Musterstadt", "Beispielhausen", "Testdorf"]

FAKE_POOLS = {
    "EMAIL": FAKE_EMAILS,
    "IBAN": FAKE_IBANS,
    "PHONE": FAKE_PHONES,
    "PERSON": FAKE_NAMES,
    "LOCATION": FAKE_LOCATIONS,
}


def find_matches(text: str) -> list[Match]:
    """
    Durchsucht den Originaltext nach allen Regex-Mustern. Jeder
    EINZIGARTIGE Original-Wert bekommt konsequent denselben Fake-Wert
    innerhalb eines Aufrufs.
    """
    matches: list[Match] = []
    assigned: dict[str, str] = {}
    used_counts: dict[str, int] = {}

    for category, pattern in PATTERNS.items():
        pool = FAKE_POOLS[category]
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