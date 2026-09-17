"""
Regex-basierte PII-Erkennung - Phase 1.
Ersetzt Funde durch plausible, synthetische Fake-Werte statt reiner
[REDACTED_...]-Tags, damit der Text fuer das LLM natuerlicher wirkt.
"""
import re
from dataclasses import dataclass


@dataclass
class Finding:
    placeholder: str
    original: str
    category: str


PATTERNS = {
    "EMAIL": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "IBAN": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"),
    "PHONE": re.compile(r"\b(?:\+\d{1,3}[\s-]?)?\(?\d{2,5}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}\b"),
}

# Feste Pools an Fake-Werten pro Kategorie. Einfach gehalten fuer Phase 1 -
# Phase 2 (Presidio/LLM Guard) kann hier durch einen richtigen Faker
# ersetzt werden (z.B. die Python-Library "Faker").
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


def detect_and_anonymize(text: str) -> tuple[str, list[Finding]]:
    """
    Durchsucht den Text, ersetzt Funde durch synthetische Fake-Werte
    (statt [REDACTED_...] Tags). Innerhalb eines Aufrufs bekommt
    jeder EINZIGARTIGE Original-Wert konsequent denselben Fake-Wert -
    wichtig, falls dieselbe E-Mail mehrfach im Text vorkommt.
    """
    findings: list[Finding] = []
    result = text

    # Original -> bereits zugewiesener Fake-Wert (fuer Konsistenz
    # innerhalb einer Nachricht)
    assigned: dict[str, str] = {}
    used_counts: dict[str, int] = {}

    for category, pattern in PATTERNS.items():
        pool = FAKE_POOLS[category]

        def replace_match(match: re.Match) -> str:
            original = match.group(0)

            if original in assigned:
                return assigned[original]

            count = used_counts.get(category, 0)
            fake_value = pool[count % len(pool)]
            used_counts[category] = count + 1

            assigned[original] = fake_value
            findings.append(Finding(fake_value, original, category))
            return fake_value

        result = pattern.sub(replace_match, result)

    return result, findings