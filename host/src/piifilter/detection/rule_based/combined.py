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

from piifilter.detection.rule_based.detectors import CustomRulesDetector, RegexDetector, PresidioDetector
from piifilter.detection.rule_based.postprocess import propagate_matches, resolve_overlaps
from piifilter.detection.rule_based.types import Finding, Match

DETECTORS = [CustomRulesDetector(), RegexDetector(), PresidioDetector()]

def _collect(text: str, chat_id: str | None, lang:str | None) -> tuple[list[Match], list[Finding]]:
    matches: list[Match] = []
    extra: list[Finding] = []
    for d in DETECTORS:
        found, extra_findings = d.find(text, chat_id, lang)
        for m in found:
            m.priority = d.priority
        matches += found
        extra += extra_findings
    return matches, extra


def detect_and_anonymize(text: str, chat_id: str | None = None, lang: str | None = None) -> tuple[str, list[Finding]]:
    matches, extra = _collect(text, chat_id, lang)

    accepted = resolve_overlaps(matches)
    accepted = propagate_matches(text, accepted)

    # Von hinten nach vorne ersetzen, damit die Positionen der noch
    # nicht verarbeiteten Matches gueltig bleiben.
    result = text
    for m in sorted(accepted, key=lambda m: m.start, reverse=True):
        result = result[: m.start] + m.fake_value + result[m.end :]

    findings = [Finding(m.fake_value, m.original, m.category) for m in accepted]
    findings.extend(extra)

    return result, findings
