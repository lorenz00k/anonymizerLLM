"""
Einstiegspunkt des lokalen Hosts.
Wird von Chrome als eigener Prozess gestartet, sobald die Extension
chrome.runtime.connectNative() aufruft.
"""
import logging
from pathlib import Path

from piifilter.native_messaging import read_message, send_message
from piifilter.detection.regex_rules import detect_and_anonymize

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

        text = message.get("text", "")
        logging.debug("Empfangen: %s", text)

        try:
            result_text, findings = detect_and_anonymize(text)

            # replacements gehen zurueck an die Extension, damit sie den
            # lokalen JS-Vault (in shared.js) damit befuellen kann
            replacements = {f.placeholder: f.original for f in findings}

            send_message({"result": result_text, "replacements": replacements})
            logging.debug("Gesendet: %s (Funde: %d)", result_text, len(findings))
        except Exception:
            logging.exception("Fehler bei der Verarbeitung")
            send_message({"result": text, "replacements": {}})

if __name__ == "__main__":
    main()