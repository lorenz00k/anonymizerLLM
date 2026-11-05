import threading

from piifilter.detection.rule_based.combined import detect_and_anonymize
from piifilter.host.handlers.llm import handle_llm_async
from piifilter.host.session import chat_languages
from piifilter.host.transport import safe_handler, send
from piifilter.logger import log


@safe_handler("anonymize_result", lambda m: {"result": m.get("text", ""), "replacements": {}})
def handle_anonymize(message: dict) -> None:
    """Phase 1: Custom/Regex/Presidio, sofort, automatisch."""
    text = message.get("text", "")
    chat_id = message.get("chatId")
    request_id = message.get("requestId")
    llm_enabled = message.get("llmEnabled", False)
    lang_code = chat_languages.resolve(chat_id, text, message.get("lang_code"))
    log.debug(
        "Nachricht empfangen (%d Zeichen), Chat-ID: %s, LLM aktiv: %s, Sprache: %s",
        len(text),
        chat_id,
        llm_enabled,
        lang_code,
    )

    result_text, findings = detect_and_anonymize(text, chat_id, lang_code)

    replacements = {f.placeholder: f.original for f in findings}
    log.trace("Ersetzungen (Klartext): %s", replacements)
    log.info("Verarbeitet: %d Ersetzung(en)", len(findings))

    send(
        {
            "type": "anonymize_result",
            "requestId": request_id,
            "result": result_text,
            "replacements": replacements,
        }
    )

    if llm_enabled:
        threading.Thread(
            target=handle_llm_async,
            args=(result_text, chat_id, request_id, lang_code),
            daemon=True,
        ).start()
    else:
        send({"type": "llm_suggestions", "requestId": request_id, "suggestions": []})
