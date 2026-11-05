"""
Presidio-basierte Erkennung.
Findet Kandidaten (v.a. Personennamen, Orte) im ORIGINALTEXT und
ordnet ihnen einen Fake-Wert zu. Ersetzt selbst nichts im Text -
das uebernimmt combined.py zentral.
"""
import threading
from functools import lru_cache

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider

from piifilter.detection.rule_based.types import Match, Finding
from piifilter.languages import get_language

_build_lock = threading.Lock()

@lru_cache(maxsize=None)
def _build_analyzer(lang_code: str) -> AnalyzerEngine:
    lang_config = get_language(lang_code)
    nlp = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": lang_config.lang_code, "model_name": lang_config.spacy_model}],
    }).create_engine()
    registry = RecognizerRegistry(supported_languages=[lang_config.lang_code])
    registry.load_predefined_recognizers(nlp_engine=nlp, languages=[lang_config.lang_code])
    return AnalyzerEngine(nlp_engine=nlp, registry=registry, supported_languages=[lang_config.lang_code])

def get_analyzer(lang_code: str) -> AnalyzerEngine:
    # Lock: Warmup-Thread und erste Nachricht sollen nicht beide laden
    with _build_lock:
        return _build_analyzer(lang_code)

def warmup(lang: str = "de") -> None:
    get_analyzer(lang)

def _trim_greeting(text: str, start: int, end: int, greeting_words: frozenset[str]) -> tuple[int, int]:
    """Schneidet ein vorangestelltes Gruss-/Anredewort ab, das das NER-Modell
    faelschlich zur PERSON-Entitaet gezaehlt hat ("Hallo Erika" -> "Erika")."""
    snippet = text[start:end]
    words = snippet.split()
    if len(words) > 1 and words[0].lower().rstrip(",") in greeting_words:
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
    lang_config = get_language(language)
    analyzer = get_analyzer(lang_config.lang_code)

    results = analyzer.analyze(
        text=text,
        entities=list(lang_config.presidio_entities),
        language=lang_config.lang_code,
        score_threshold=lang_config.score_threshold,
    )

    matches: list[Match] = []
    extra_findings: list[Finding] = []
    assigned: dict[str, str] = {}
    used_counts: dict[str, int] = {}

    for r in results:
        start, end = r.start, r.end
        if r.entity_type == "PERSON":
            start, end = _trim_greeting(text, start, end, lang_config.presidio_greeting_words)

        original = text[start:end]
        if not original.strip():
            continue
        category = r.entity_type

        if original in assigned:
            fake_value = assigned[original]
        else:
            pool = lang_config.fake_pools.get(category, [f"[REDACTED_{category}]"])
            count = used_counts.get(category, 0)
            fake_value = pool[count % len(pool)]
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
