"""
Einstiegspunkt des lokalen Hosts.
Wird von Chrome als eigener Prozess gestartet, sobald die Extension
chrome.runtime.connectNative() aufruft.
"""
import logging
from pathlib import Path

from piifilter.native_messaging import read_message, send_message

LOG_FILE = Path("/tmp/pii_filter_host.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
)


def process_text(text: str) -> str:
    """Platzhalter-Logik für Phase 0.
    Phase 1 ersetzt das durch Regex-Erkennung (siehe detection/regex_rules.py)."""
    return text.upper()


def main() -> None:
    logging.info("Native host gestartet")
    while True:
        try:
            message = read_message()
        except Exception:
            logging.exception("Fehler beim Lesen der Nachricht")
            break

        if message is None:
            logging.info("Verbindung geschlossen, beende.")
            break

        logging.debug("Empfangen: %s", message)
        result = process_text(message.get("text", ""))
        send_message({"result": result})
        logging.debug("Gesendet: %s", result)


if __name__ == "__main__":
    main()