"""
Minimaler Logger mit einstellbarem Level, spiegelt das Schema von
logger.js (JS-Seite): trace < debug < info < warn < error.

trace/debug duerfen Klartext (Original-PII, Nutzereingaben) enthalten.
info/warn/error NICHT - dort nur Metadaten (Anzahl Funde, Status).
"""

import logging
import os
from pathlib import Path

TRACE_LEVEL = 5
logging.addLevelName(TRACE_LEVEL, "TRACE")


def _trace(self, message, *args, **kwargs):
    if self.isEnabledFor(TRACE_LEVEL):
        self._log(TRACE_LEVEL, message, args, **kwargs)


logging.Logger.trace = _trace

# Zentral hier einstellen: TRACE_LEVEL waehrend der Entwicklung,
# logging.INFO oder hoeher fuer normale Nutzung
CURRENT_LOG_LEVEL = logging.INFO

#chmod 700 (only user has full access) for directory & chmod 600 (only user can read& write file) for file
LOG_DIR = Path.home() / ".piifilter"
LOG_DIR.mkdir(mode=0o700, exist_ok=True)
LOG_FILE = LOG_DIR / "host.log"
LOG_FILE.touch(mode=0o600, exist_ok=True)
os.chmod(LOG_FILE, 0o600)

logging.basicConfig(
    filename=LOG_FILE,
    level=CURRENT_LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(message)s",
)

# Presidios eigene, sehr gespraechige Logs separat gedaempft,
# unabhaengig vom eigenen Level oben
logging.getLogger("presidio-analyzer").setLevel(logging.WARNING)

log = logging.getLogger("piifilter")
