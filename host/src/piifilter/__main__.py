"""
Einstiegspunkt des lokalen Hosts.
Wird von Chrome als eigener Prozess gestartet, sobald die Extension
chrome.runtime.connectNative() aufruft.
"""
from pathlib import Path
from piifilter.logger import log

from piifilter.native_messaging import read_message, send_message
from piifilter.detection.combined import detect_and_anonymize

def main() -> None:
    log.info("Native host gestartet")
    while True:
        try:
            message = read_message()
        except Exception:
            log.exception("Fehler beim Lesen der Nachricht")
            break

        if message is None:
            log.info("Verbindung geschlossen, beende.")
            break

        text = message.get("text", "")
        log.debug("Empfangen (Klartext): %s", text)
        log.debug("Nachricht empfangen (%d Zeichen)", len(text))

        try:
            result_text, findings = detect_and_anonymize(text)

            # replacements gehen zurueck an die Extension, damit sie den
            # lokalen JS-Vault (in shared.js) damit befuellen kann
            replacements = {f.placeholder: f.original for f in findings}
            log.trace("Ersetzungen (Klartext): %s", replacements)
            log.info("Verarbeitet: %d Ersetzung(en)", len(findings))

            send_message({"result": result_text, "replacements": replacements})
        except Exception:
            log.exception("Fehler bei der Verarbeitung")
            send_message({"result": text, "replacements": {}})

if __name__ == "__main__":
    main()