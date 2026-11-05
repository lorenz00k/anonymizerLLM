"""
Einstiegspunkt des lokalen Hosts.
Wird von Chrome als eigener Prozess gestartet, sobald die Extension
chrome.runtime.connectNative() aufruft.
"""

import threading

from piifilter.detection.rule_based import presidio_engine
from piifilter.logger import log
from piifilter.native_messaging import read_message
from piifilter.detection.llm import ollama_client

from piifilter.host.dispatch import dispatch


def _read_next():
    try:
        return read_message()
    except Exception:
        log.exception("Fehler beim Lesen der Nachricht")
        return None


def main() -> None:
    log.info("Native host gestartet")

    # Modelle im Hintergrund vorladen, damit die erste echte Nachricht
    # nicht den Cold-Start zahlt. Blockiert den Host-Start nicht.
    threading.Thread(target=ollama_client.warmup, daemon=True).start()
    threading.Thread(target=presidio_engine.warmup, daemon=True).start()

    while (message := _read_next()) is not None:
        dispatch(message)

    log.info("Verbindung geschlossen, beende.")


if __name__ == "__main__":
    main()
