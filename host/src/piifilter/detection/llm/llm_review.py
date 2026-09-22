"""
Review-Workflow fuer die LLM-Stufe (vierte Erkennungsstufe).

Anders als Custom/Regex/Presidio (die synchron und automatisch ersetzen)
laeuft die LLM-Stufe zweiphasig:

  Phase 1 (sofort, im bestehenden Fluss):
      detect_and_anonymize() - unveraendert, ersetzt Custom/Regex/Presidio
      automatisch. Ergebnis geht wie bisher direkt an die Extension.

  Phase 2 (asynchron, on top):
      get_llm_suggestions() laeuft auf dem bereits anonymisierten Text aus
      Phase 1 und liefert nur VORSCHLAEGE zurueck (Position, Kategorie,
      Begruendung, vorgeschlagener Platzhalter). Nichts wird hier ersetzt.

  Phase 3 (nach Nutzer-Entscheidung im UI):
      apply_llm_suggestions() wendet genau die vom Nutzer akzeptierten
      Vorschlaege an (Text-Ersetzung + Finding fuer die Vault), verworfene
      werden ignoriert und bleiben im Text stehen.

Diese Aufteilung existiert bewusst, weil (a) die LLM-Ergebnisse unschaerfer
sind als die anderen drei Quellen und blindes Ersetzen ganzer Satzteile
riskanter ist als bei einzelnen PII-Werten, und (b) das LLM mit 0.5-3s klar
langsamer ist und den bisher synchronen/schnellen Sendevorgang sonst
ausbremsen wuerde.
"""
import logging

logger = logging.getLogger(__name__)

from piifilter.detection.llm import llm_find, llm_rewrite
from piifilter.detection.rule_based.types import Finding


def get_llm_suggestions(anonymized_text: str, chat_id: str = None) -> list[dict]:
    """
    Phase 2. `anonymized_text` MUSS der bereits von detect_and_anonymize()
    zurueckgegebene Text sein, nicht das Original - sonst markiert das LLM
    Stellen erneut, die von Custom/Regex/Presidio schon ersetzt wurden.

    Gibt eine JSON-serialisierbare Liste von Vorschlaegen zurueck, die 1:1
    als Native-Messaging-Nachricht an die Extension geschickt werden kann.
    Jeder Eintrag hat eine "id", damit die Extension bei apply_llm_suggestions
    einfach die Liste der akzeptierten ids zurueckschicken kann.
    """
    matches = llm_find.find_matches(anonymized_text, chat_id=chat_id)

    suggestions = []
    for i, m in enumerate(matches):
        rewritten = llm_rewrite.rewrite_finding(m.original, m.category)
        suggestions.append({
            "id": f"llm-{i}",
            "start": m.start,
            "end": m.end,
            "text": m.original,
            "suggestedReplacement": rewritten,
            "category": m.category,
        })

    logger.info("get_llm_suggestions fertig, %d Vorschlag/Vorschläge: %s", len(suggestions), suggestions)
    return suggestions


def apply_llm_suggestions(
    anonymized_text: str,
    suggestions: list[dict],
    accepted_ids: set[str],
) -> tuple[str, list[Finding]]:
    """
    Phase 3. `suggestions` ist die Liste aus get_llm_suggestions() (muss der
    Extension zwischengespeichert und hier wieder mitgegeben werden, da
    Positionen sich nur auf GENAU diesen `anonymized_text`-Stand beziehen -
    falls der Nutzer den Text zwischenzeitlich manuell editiert hat, sind
    die Positionen ungueltig, siehe Hinweis unten).

    `accepted_ids` sind die ids der vom Nutzer im Review-Panel bestaetigten
    Vorschlaege. Alles andere wird verworfen und bleibt im Text stehen.

    Gibt den finalen Text (nach Ersetzung der akzeptierten Stellen) und die
    Findings fuer die Vault zurueck - gleiche Form wie detect_and_anonymize(),
    damit sich das Vault-Handling der Extension nicht unterscheiden muss.
    """
    accepted = [s for s in suggestions if s["id"] in accepted_ids]

    # Von hinten nach vorne ersetzen (wie bei detect_and_anonymize), damit
    # Positionen der noch offenen Ersetzungen gueltig bleiben.
    result = anonymized_text
    for s in sorted(accepted, key=lambda s: s["start"], reverse=True):
        # Sicherheitscheck: falls der Text sich seit get_llm_suggestions()
        # geaendert hat (Nutzer hat waehrenddessen weitergetippt), passt die
        # Position evtl. nicht mehr exakt - dann lieber ueberspringen als
        # eine falsche Stelle im Text zu zerschneiden.
        if result[s["start"]:s["end"]] != s["text"]:
            continue
        result = result[:s["start"]] + s["suggestedReplacement"] + result[s["end"]:]

    findings = [
        Finding(s["suggestedReplacement"], s["text"], s["category"])
        for s in accepted
        if anonymized_text[s["start"]:s["end"]] == s["text"]
    ]

    return result, findings