"""
Presidio-basierte Erkennung.

Ersetzt/ergaenzt die reine Regex-Erkennung aus regex_rules.py um
NLP-gestuetzte Erkennung (v.a. Personennamen, Orte, Organisationen).
"""
from dataclasses import dataclass
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

from piifilter.detection.regex_rules import FAKE_POOLS

# Presidio muss explizit wissen, welches spaCy-Modell zu welcher Sprache
# gehoert - ohne diese Konfiguration laedt es nur Englisch-Recognizer.
NLP_CONFIGURATION = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "de", "model_name": "de_core_news_lg"}],
}

provider = NlpEngineProvider(nlp_configuration=NLP_CONFIGURATION)
nlp_engine = provider.create_engine()

analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["de"])
anonymizer = AnonymizerEngine()

ENTITIES = ["PERSON", "LOCATION"]


@dataclass
class Finding:
    placeholder: str
    original: str
    category: str


def detect_and_anonymize(text: str, language: str = "de") -> tuple[str, list[Finding]]:
    results = analyzer.analyze(text=text, entities=ENTITIES, language=language)

    findings: list[Finding] = []
    assigned: dict[str, str] = {}
    used_counts: dict[str, int] = {}

    result = text
    for r in sorted(results, key=lambda r: r.start, reverse=True):
        original = text[r.start:r.end]
        category = r.entity_type

        if original in assigned:
            fake_value = assigned[original]
        else:
            pool = FAKE_POOLS.get(category, [f"[REDACTED_{category}]"])
            count = used_counts.get(category, 0)
            fake_value = pool[count % len(pool)] if isinstance(pool, list) else pool
            used_counts[category] = count + 1
            assigned[original] = fake_value
            findings.append(Finding(fake_value, original, category))

        result = result[:r.start] + fake_value + result[r.end:]

    return result, findings