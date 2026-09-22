"""
Kombiniert eigene Regeln, Regex- und Presidio-Erkennung.

Alle drei Stufen suchen unabhaengig voneinander im ORIGINALTEXT nach
Funden - statt wie frueher nacheinander auf dem bereits veraenderten
Text der vorherigen Stufe zu arbeiten. Das verhindert, dass eine
Stufe faelschlich einen bereits eingesetzten Fake-Wert einer anderen
Stufe erneut "erkennt" und ueberschreibt (z.B. Presidio, das einen
gerade erst eingesetzten Fake-Namen faelschlich nochmal als PERSON
markiert).

Reihenfolge = Prioritaet bei Ueberlappungen: Custom Rules > Regex >
Presidio. Erst nachdem alle Funde gesammelt und Ueberlappungen
aufgeloest sind, wird EINMAL ersetzt (von hinten nach vorne, damit
sich die Positionen der noch offenen Funde nicht verschieben).
"""
import re

from piifilter.custom_rules import get_effective_rules
from piifilter.detection.rule_based.regex_rules import find_matches as regex_find_matches
from piifilter.detection.rule_based.presidio_engine import find_matches as presidio_find_matches
from piifilter.detection.rule_based.types import Match, Finding


def _match_case(fake_value: str, matched_text: str) -> str:
    if matched_text.isupper():
        return fake_value.upper()
    if matched_text.istitle():
        return fake_value.title()
    if matched_text.islower():
        return fake_value.lower()
    return fake_value


def _find_custom_matches(text: str, chat_id: str = None) -> list[Match]:
    rules = get_effective_rules(chat_id)
    matches: list[Match] = []
    for original, fake_value in rules.items():
        pattern = re.compile(re.escape(original), re.IGNORECASE)
        for m in pattern.finditer(text):
            actual_fake = _match_case(fake_value, m.group(0))
            matches.append(Match(m.start(), m.end(), m.group(0), actual_fake, "CUSTOM"))
    return matches


def _resolve_overlaps(matches: list[Match]) -> list[Match]:
    """
    Erwartet matches bereits in Prioritaets-Reihenfolge (wichtigste
    Quelle zuerst). Bei ueberlappenden Spans gewinnt der zuerst
    gefundene (= hoeher priorisierte) Match.
    """
    accepted: list[Match] = []
    for m in matches:
        overlaps = any(m.start < a.end and a.start < m.end for a in accepted)
        if not overlaps:
            accepted.append(m)
    return accepted


def _propagate_matches(text: str, accepted: list[Match]) -> list[Match]:
    """
    Presidio/Regex/Custom finden Vorkommen z.T. kontextabhaengig - z.B.
    "Jonas Wüst" als vollen Namen erkannt, aber ein spaeteres
    alleinstehendes "Jonas" im selben Text nicht (das NER-Modell erkennt
    dort keinen Namen). Ergebnis ohne diesen Schritt: derselbe Name wird
    an einer Stelle maskiert, an einer anderen nicht.

    Sucht fuer JEDEN akzeptierten Fund alle weiteren Vorkommen desselben
    Wortlauts (case-insensitiv, ganzes Wort) im Rest des Textes und
    maskiert sie mit demselben Fake-Wert - unabhaengig davon, ob eine der
    drei Erkennungsstufen diese Stelle selbst erkannt haette.
    """
    covered = [(m.start, m.end) for m in accepted]
    new_matches: list[Match] = []
    seen_originals: set[str] = set()

    for m in accepted:
        key = m.original.lower()
        if key in seen_originals:
            # Fall doppelt vorhanden (z.B. "Jonas" UND "jonas" schon als
            # getrennte Funde akzeptiert) - der erste Durchlauf deckt via
            # IGNORECASE ohnehin schon alle Schreibweisen ab.
            continue
        seen_originals.add(key)

        pattern = re.compile(r"\b" + re.escape(m.original) + r"\b", re.IGNORECASE)
        for occ in pattern.finditer(text):
            if any(occ.start() < c_end and c_start < occ.end() for c_start, c_end in covered):
                continue  # ueberschneidet sich mit einem bereits abgedeckten Fund
            actual_fake = _match_case(m.fake_value, occ.group(0))
            new_matches.append(Match(occ.start(), occ.end(), occ.group(0), actual_fake, m.category))
            covered.append((occ.start(), occ.end()))

    return accepted + new_matches


def detect_and_anonymize(text: str, chat_id: str = None) -> tuple[str, list[Finding]]:
    custom_matches = _find_custom_matches(text, chat_id)
    regex_matches = regex_find_matches(text)
    presidio_matches, presidio_extra_findings = presidio_find_matches(text)

    # Reihenfolge bestimmt Prioritaet: Custom > Regex > Presidio
    all_matches = custom_matches + regex_matches + presidio_matches
    accepted = _resolve_overlaps(all_matches)
    accepted = _propagate_matches(text, accepted)

    # Von hinten nach vorne ersetzen, damit die Positionen der noch
    # nicht verarbeiteten Matches gueltig bleiben.
    result = text
    for m in sorted(accepted, key=lambda m: m.start, reverse=True):
        result = result[:m.start] + m.fake_value + result[m.end:]

    findings = [Finding(m.fake_value, m.original, m.category) for m in accepted]
    findings.extend(presidio_extra_findings)

    return result, findings