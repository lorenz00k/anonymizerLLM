"""
Einstiegspunkt des lokalen Hosts.
Wird von Chrome als eigener Prozess gestartet, sobald die Extension
chrome.runtime.connectNative() aufruft.
"""
import threading
from piifilter.logger import log

from piifilter.native_messaging import read_message, send_message
from piifilter.detection.rule_based.combined import detect_and_anonymize
from piifilter.detection.llm.llm_review import get_llm_suggestions, apply_llm_suggestions
from piifilter.detection.llm import ollama_client, llm_rewrite

# Native Messaging schreibt laengenpraefigierte Nachrichten auf stdout. Wenn
# der Haupt-Thread (Phase 1, sofort) und ein Hintergrund-Thread (Phase 2,
# LLM-Vorschlaege) gleichzeitig schreiben wuerden, koennten sich die Bytes
# ueberlappen. Der Lock stellt sicher, dass jede Nachricht am Stueck
# geschrieben wird.
_send_lock = threading.Lock()


def _send(payload: dict) -> None:
    with _send_lock:
        send_message(payload)


def _handle_llm_suggestions_async(text: str, chat_id, request_id) -> None:
    """Phase 2, in einem Hintergrund-Thread: laeuft auf dem bereits von
    Phase 1 anonymisierten Text und meldet sich mit einer eigenen,
    unaufgeforderten Nachricht zurueck, sobald sie fertig ist. Blockiert
    NICHT die read_message()-Schleife im Haupt-Thread."""
    try:
        suggestions = get_llm_suggestions(text, chat_id)
    except Exception:
        log.exception("Fehler bei der LLM-Erkennung")
        suggestions = []

    if suggestions:
        log.info("LLM-Vorschlaege: %d", len(suggestions))

    _send({
        "type": "llm_suggestions",
        "requestId": request_id,
        "suggestions": suggestions,
    })


def _handle_anonymize(message: dict) -> None:
    """Phase 1, wie bisher: Custom/Regex/Presidio, sofort, automatisch."""
    text = message.get("text", "")
    chat_id = message.get("chatId")
    request_id = message.get("requestId")
    llm_enabled = message.get("llmEnabled", False)
    log.debug("Empfangen (Klartext): %s", text)
    log.debug("Nachricht empfangen (%d Zeichen), Chat-ID: %s, LLM aktiv: %s", len(text), chat_id, llm_enabled)

    try:
        result_text, findings = detect_and_anonymize(text, chat_id)

        replacements = {f.placeholder: f.original for f in findings}
        log.trace("Ersetzungen (Klartext): %s", replacements)
        log.info("Verarbeitet: %d Ersetzung(en)", len(findings))

        _send({
            "type": "anonymize_result",
            "requestId": request_id,
            "result": result_text,
            "replacements": replacements,
        })

        # Phase 2 startet erst NACHDEM die schnelle Antwort raus ist, und
        # laeuft parallel weiter - der Haupt-Thread geht sofort zurueck zu
        # read_message() und kann die naechste Nachricht bearbeiten.
        if llm_enabled:
            threading.Thread(
                target=_handle_llm_suggestions_async,
                args=(result_text, chat_id, request_id),
                daemon=True,
            ).start()
        else:
            _send({
                "type": "llm_suggestions",
                "requestId": request_id,
                "suggestions": [],
            })

    except Exception:
        log.exception("Fehler bei der Verarbeitung")
        _send({
            "type": "anonymize_result",
            "requestId": request_id,
            "result": text,
            "replacements": {},
        })


def _handle_apply_llm(message: dict) -> None:
    """Phase 3: die Extension schickt das hier erst, wenn der Nutzer im
    Review-Panel entschieden hat, welche LLM-Vorschlaege angewendet werden
    sollen (typischerweise unmittelbar vor dem tatsaechlichen Senden)."""
    text = message.get("text", "")
    suggestions = message.get("suggestions", [])
    accepted_ids = set(message.get("acceptedIds", []))
    request_id = message.get("requestId")

    try:
        result_text, findings = apply_llm_suggestions(text, suggestions, accepted_ids)
        replacements = {f.placeholder: f.original for f in findings}
        log.info("LLM-Vorschlaege angewendet: %d von %d", len(findings), len(suggestions))

        _send({
            "type": "apply_llm_result",
            "requestId": request_id,
            "result": result_text,
            "replacements": replacements,
        })
    except Exception:
        log.exception("Fehler beim Anwenden der LLM-Vorschlaege")
        _send({
            "type": "apply_llm_result",
            "requestId": request_id,
            "result": text,
            "replacements": {},
        })

def _handle_retry_rewrite(message: dict) -> None:
    """Auf Wunsch aus dem Review-Panel ('Neu umformulieren' bei einem
    einzelnen LLM-Finding): ruft fuer GENAU dieses eine Finding einen
    frischen Rewrite-Call auf, mit erhoehter Temperature, damit sich die
    neue Formulierung vom vorherigen Vorschlag unterscheidet. Laeuft
    synchron im Haupt-Thread (kein eigener Thread noetig - Rewrite ist
    schon kurz/fokussiert, siehe REQUEST_TIMEOUT_SECONDS in llm_rewrite.py)."""
    text = message.get("text", "")
    category = message.get("category", "")
    request_id = message.get("requestId")

    try:
        rewritten = llm_rewrite.rewrite_finding(text, category, temperature=0.7)
        _send({
            "type": "retry_rewrite_result",
            "requestId": request_id,
            "suggestedReplacement": rewritten,
        })
    except Exception:
        log.exception("Fehler beim Neu-Umformulieren")
        _send({
            "type": "retry_rewrite_result",
            "requestId": request_id,
            "suggestedReplacement": f"[{category}]",
        })


def main() -> None:
    log.info("Native host gestartet")

    # Modell im Hintergrund vorladen, damit die erste ECHTE Nachricht vom
    # Nutzer nicht den vollen Cold-Start-Preis (kann >15s dauern) zahlen
    # muss. Laeuft parallel zur read_message()-Schleife unten, blockiert
    # also nicht den Host-Start selbst.
    threading.Thread(target=ollama_client.warmup, daemon=True).start()

    while True:
        try:
            message = read_message()
        except Exception:
            log.exception("Fehler beim Lesen der Nachricht")
            break

        if message is None:
            log.info("Verbindung geschlossen, beende.")
            break

        # Kein "type" im Feld = altes Nachrichtenformat = "anonymize".
        # Rueckwaertskompatibel, falls die Extension noch nicht ueberall
        # angepasst ist.
        message_type = message.get("type", "anonymize")

        if message_type == "anonymize":
            _handle_anonymize(message)
        elif message_type == "apply_llm":
            _handle_apply_llm(message)
        elif message_type == "retry_rewrite":
            _handle_retry_rewrite(message)
        else:
            log.warning("Unbekannter Nachrichtentyp: %s", message_type)


if __name__ == "__main__":
    main()