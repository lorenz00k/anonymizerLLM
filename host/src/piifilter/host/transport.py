import functools
import threading

from piifilter.logger import log
from piifilter.native_messaging import send_message

_send_lock = threading.Lock()   # verhindert ueberlappende Bytes auf stdout


def send(payload: dict) -> None:
    with _send_lock:
        send_message(payload)


def safe_handler(error_type: str, fallback):
    """fallback(message) -> dict: Antwort, falls der Handler eine Exception wirft."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(message):
            try:
                fn(message)
            except Exception:
                log.exception("Fehler in %s", fn.__name__)
                send({"type": error_type,
                      "requestId": message.get("requestId"),
                      **fallback(message)})
        return wrapper
    return deco