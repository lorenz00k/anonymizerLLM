"""
Presidio-basierte Erkennung.
Findet Kandidaten (v.a. Personennamen, Orte) im ORIGINALTEXT und
ordnet ihnen einen Fake-Wert zu. Ersetzt selbst nichts im Text -
das uebernimmt combined.py zentral.
"""
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider

from piifilter.detection.rule_based.regex_rules import FAKE_POOLS
from piifilter.detection.rule_based.types import Match, Finding

NLP_CONFIGURATION = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "de", "model_name": "de_core_news_lg"}],
}

provider = NlpEngineProvider(nlp_configuration=NLP_CONFIGURATION)
nlp_engine = provider.create_engine()

analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["de"])

ENTITIES = ["PERSON", "LOCATION"]

GREETING_WORDS = {"hallo", "hi", "hey", "liebe", "lieber", "sehr", "guten", "moin"}


def _trim_greeting(text: str, start: int, end: int) -> tuple[int, int]:
    """
    Presidio erkennt manchmal ein vorangestelltes Gruss-/Anredewort
    faelschlich als Teil einer PERSON-Entitaet (z.B. "Hallo Erika" statt
    nur "Erika"). Schneidet ein bekanntes Gruss-Wort vom Anfang der
    erkannten Spanne ab, falls vorhanden.
    """
    snippet = text[start:end]
    words = snippet.split()
    if len(words) > 1 and words[0].lower().rstrip(",") in GREETING_WORDS:
        offset = len(words[0]) + 1  # Wort + folgendes Leerzeichen
        return start + offset, end
    return start, end


def find_matches(text: str, language: str = "de") -> tuple[list[Match], list[Finding]]:
    """
    Durchsucht den Originaltext nach PERSON/LOCATION-Entitaeten.
    Gibt zwei Listen zurueck:
    - matches: Fundstellen mit Position, die combined.py im Text
      ersetzen soll.
    - extra_findings: zusaetzliche, positionslose Vault-Eintraege
      (Vor-/Nachname einzeln), damit Teilerwaehnungen in Claudes
      Antwort spaeter trotzdem deanonymisiert werden koennen.
    """
    results = analyzer.analyze(text=text, entities=ENTITIES, language=language)

    matches: list[Match] = []
    extra_findings: list[Finding] = []
    assigned: dict[str, str] = {}
    used_counts: dict[str, int] = {}

    for r in results:
        start, end = r.start, r.end
        if r.entity_type == "PERSON":
            start, end = _trim_greeting(text, start, end)

        original = text[start:end]
        if not original.strip():
            continue
        category = r.entity_type

        if original in assigned:
            fake_value = assigned[original]
        else:
            pool = FAKE_POOLS.get(category, [f"[REDACTED_{category}]"])
            count = used_counts.get(category, 0)
            fake_value = pool[count % len(pool)] if isinstance(pool, list) else pool
            used_counts[category] = count + 1
            assigned[original] = fake_value

            if category == "PERSON":
                original_parts = original.split()
                fake_parts = fake_value.split()
                if len(original_parts) >= 2 and len(fake_parts) >= 2:
                    extra_findings.append(Finding(fake_parts[0], original_parts[0], category))
                    extra_findings.append(Finding(fake_parts[-1], original_parts[-1], category))

        matches.append(Match(start, end, original, fake_value, category))

    return matches, extra_findings