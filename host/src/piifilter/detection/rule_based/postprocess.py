import re

from piifilter.detection.rule_based.text_utils import match_case
from piifilter.detection.rule_based.types import Match


def propagate_matches(text: str, accepted: list[Match]) -> list[Match]:
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
            actual_fake = match_case(m.fake_value, occ.group(0))
            new_matches.append(Match(occ.start(), occ.end(), occ.group(0), actual_fake, m.category))
            covered.append((occ.start(), occ.end()))

    return accepted + new_matches


def resolve_overlaps(matches: list[Match]) -> list[Match]:
    """Hoechste Prioritaet gewinnt, bei Gleichstand der laengere Span,
    danach der weiter vorne stehende."""
    ordered = sorted(matches, key=lambda m: (-m.priority, -(m.end - m.start), m.start))
    accepted: list[Match] = []
    for m in ordered:
        if not any(m.start < a.end and a.start < m.end for a in accepted):
            accepted.append(m)
    return sorted(accepted, key=lambda m: m.start)
