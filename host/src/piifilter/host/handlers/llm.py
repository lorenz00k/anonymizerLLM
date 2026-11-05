from piifilter.detection.llm import llm_rewrite
from piifilter.detection.llm.llm_review import get_llm_suggestions, apply_llm_suggestions
from piifilter.host.transport import send, safe_handler
from piifilter.logger import log


def handle_llm_async(text: str, chat_id, request_id) -> None:
    """Phase 2, im Hintergrund-Thread (von handle_anonymize gestartet).
    Keine Fehlerantwort, sondern bei Fehler eine leere Vorschlagsliste."""
    try:
        # lang wird erst in 'handle_apply_llm' an das LLM weitergereicht
        suggestions = get_llm_suggestions(text, chat_id)
    except Exception:
        log.exception("Fehler bei der LLM-Erkennung")
        suggestions = []

    if suggestions:
        log.info("LLM-Vorschlaege: %d", len(suggestions))

    send({"type": "llm_suggestions", "requestId": request_id, "suggestions": suggestions})


@safe_handler("apply_llm_result",
              lambda m: {"result": m.get("text", ""), "replacements": {}})
def handle_apply_llm(message: dict) -> None:
    """Phase 3: Nutzer hat im Review-Panel entschieden, welche Vorschlaege gelten."""
    text = message.get("text", "")
    suggestions = message.get("suggestions", [])
    accepted_ids = set(message.get("acceptedIds", []))

    result_text, findings = apply_llm_suggestions(text, suggestions, accepted_ids)
    replacements = {f.placeholder: f.original for f in findings}
    log.info("LLM-Vorschlaege angewendet: %d von %d", len(findings), len(suggestions))

    send({
        "type": "apply_llm_result",
        "requestId": message.get("requestId"),
        "result": result_text,
        "replacements": replacements,
    })


@safe_handler("retry_rewrite_result",
              lambda m: {"suggestedReplacement": f"[{m.get('category', '')}]"})
def handle_retry_rewrite(message: dict) -> None:
    """'Neu umformulieren' fuer genau ein Finding, mit erhoehter Temperature.
    Laeuft synchron im Haupt-Thread (kurzer, fokussierter Call)."""
    text = message.get("text", "")
    category = message.get("category", "")

    rewritten = llm_rewrite.rewrite_finding(text, category, temperature=0.7)

    send({
        "type": "retry_rewrite_result",
        "requestId": message.get("requestId"),
        "suggestedReplacement": rewritten,
    })