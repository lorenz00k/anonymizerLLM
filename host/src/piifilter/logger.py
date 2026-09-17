"""
Minimaler Logger mit einstellbarem Level, spiegelt das Schema von
logger.js (JS-Seite): trace < debug < info < warn < error.

trace/debug duerfen Klartext (Original-PII, Nutzereingaben) enthalten.
info/warn/error NICHT - dort nur Metadaten (Anzahl Funde, Status).
"""
import logging

TRACE_LEVEL = 5
logging.addLevelName(TRACE_LEVEL, "TRACE")


def _trace(self, message, *args, **kwargs):
    if self.isEnabledFor(TRACE_LEVEL):
        self._log(TRACE_LEVEL, message, args, **kwargs)


logging.Logger.trace = _trace

# Zentral hier einstellen: TRACE_LEVEL waehrend der Entwicklung,
# logging.INFO oder hoeher fuer normale Nutzung
CURRENT_LOG_LEVEL = logging.INFO

logging.basicConfig(
    filename="/tmp/pii_filter_host.log",
    level=CURRENT_LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(message)s",
)

# Presidios eigene, sehr gespraechige Logs separat gedaempft,
# unabhaengig vom eigenen Level oben
logging.getLogger("presidio-analyzer").setLevel(logging.WARNING)

log = logging.getLogger("piifilter")