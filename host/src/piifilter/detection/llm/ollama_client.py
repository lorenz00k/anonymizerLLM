"""
Duenne, gemeinsame HTTP-Schicht fuer alle Ollama-Aufrufe der LLM-Stufe.
Kennt weder Erkennung (llm_find.py) noch Umformulierung (llm_rewrite.py) -
nur wie man mit Ollama redet.
"""
import logging

import requests

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "llama3.2"

# Haelt das Modell nach jedem Call laenger im RAM (Ollama-Default ist 5min
# Inaktivitaet, dann wird es entladen). 30 Minuten passt zu einer Chat-
# Session, ohne dauerhaft RAM zu blockieren wenn der Host laenger nicht
# genutzt wird.
KEEP_ALIVE = "30m"

WARMUP_TIMEOUT_SECONDS = 60


def chat(messages: list[dict], timeout: float, model: str = DEFAULT_MODEL,
         options: dict = None, json_format: bool = False) -> str | None:
    """
    Fuehrt einen einzelnen Chat-Call gegen Ollama aus und gibt den
    Antworttext zurueck, oder None bei einem Verbindungsfehler (Ollama
    nicht erreichbar/Timeout) - Find und Rewrite behandeln das gleich:
    beide sind best-effort und duerfen die anderen drei Erkennungsstufen
    niemals blockieren oder crashen lassen.
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": options or {},
        "keep_alive": KEEP_ALIVE,
    }
    if json_format:
        payload["format"] = "json"

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Ollama-Call fehlgeschlagen: %s", e)
        return None

    return response.json()["message"]["content"]


def warmup(model: str = DEFAULT_MODEL) -> bool:
    """
    Laedt das Modell vorab in den RAM, damit die ERSTE echte Anfrage vom
    Nutzer nicht den vollen Cold-Start-Preis zahlt (kann alleine schon
    mehr als 15s dauern). Sollte vom Host beim Start in einem Hintergrund-
    Thread aufgerufen werden (siehe main.py), NICHT im Haupt-Thread.

    "num_predict": 1 begrenzt die Antwort auf 1 Token - uns interessiert nur
    das Laden des Modells in den RAM, nicht die generierte Antwort.
    """
    content = chat(
        messages=[{"role": "user", "content": "Hallo"}],
        timeout=WARMUP_TIMEOUT_SECONDS,
        model=model,
        options={"num_predict": 1},
    )
    if content is None:
        logger.warning("LLM-Warmup fehlgeschlagen, wird bei der ersten echten Anfrage nachgeholt")
        return False
    logger.info("LLM-Warmup erfolgreich (%s)", model)
    return True