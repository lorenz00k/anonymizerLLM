from piifilter.host.handlers.anonymize import handle_anonymize
from piifilter.host.handlers.llm import handle_apply_llm, handle_retry_rewrite
from piifilter.logger import log

HANDLERS = {
    "anonymize": handle_anonymize,
    "apply_llm": handle_apply_llm,
    "retry_rewrite": handle_retry_rewrite,
}

def dispatch(message: dict) -> None:
    mtype = message.get("type", "anonymize")   # altes Format = anonymize
    handler = HANDLERS.get(mtype)
    if handler is None:
        log.warning("Unbekannter Nachrichtentyp: %s", mtype)
        return
    handler(message)