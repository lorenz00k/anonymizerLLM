"""
Formuliert einen bereits von llm_find.py erkannten sensiblen Ausschnitt um.

Bewusst als eigenes Modul von der Erkennung getrennt: zwei unabhaengige
Aufgaben mit unabhaengigen Fehlerquellen - ein fokussierter Prompt pro
Aufgabe ist zuverlaessiger als ein kombinierter, und der sorgfaeltig
getunte Erkennungs-Prompt in llm_find.py bleibt dadurch unangetastet.
"""
import logging

from piifilter.detection.llm import ollama_client

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 20  # kuerzer als die Erkennung: kleinerer Prompt, kuerzere Antwort

SYSTEM_PROMPT = """Du bekommst einen kurzen Textausschnitt, der eine sensible Information enthält (Firmengeheimnis, Personenkennung oder technisches Secret). Deine einzige Aufgabe: schreibe eine natürliche, kurze Umformulierung, die den sensiblen Kern entfernt, aber grammatikalisch in den ursprünglichen Satz passt.

WICHTIG:
- Erfinde KEINE neuen sensiblen Fakten (keine erfundenen Zahlen, Namen, Codenamen als Ersatz)
- Verallgemeinere stattdessen (z.B. "ein internes Projekt", "eine bestimmte Summe", "zu einem späteren Zeitpunkt")
- Antworte AUSSCHLIESSLICH mit der Umformulierung selbst, ohne Anführungszeichen, ohne Erklärung, ohne zusätzlichen Text davor oder danach.

Beispiel:
Ausschnitt (Kategorie FIRMENGEHEIMNIS): "Projekt Phoenix launcht jetzt doch erst im Q3 2027 statt wie geplant im Q1, das darf noch nicht nach außen dringen"
Umformulierung: ein internes Projekt hat sich zeitlich verschoben und die Details sind derzeit noch vertraulich

Beispiel:
Ausschnitt (Kategorie TECHNISCHES_SECRET): "sk-live-9f8a7b6c5d4e3f2a1b0c"
Umformulierung: <DEIN_API_KEY>"""


def rewrite_finding(
    snippet: str,
    category: str,
    model: str = ollama_client.DEFAULT_MODEL,
    temperature: float = 0,
) -> str:
    """
    Bei Fehlern (Ollama nicht erreichbar, leere Antwort) faellt es auf
    einen generischen Kategorie-Platzhalter zurueck statt zu crashen - die
    Erkennung selbst darf davon nicht betroffen sein.

    temperature=0 (Standard) fuer die erste, deterministische Umformulierung
    direkt nach der Erkennung. Fuer "Neu umformulieren" wird bewusst ein
    hoeherer Wert uebergeben, sonst kaeme bei gleichem Prompt/Snippet exakt
    dasselbe Ergebnis zurueck.
    """
    logger.info("Rewrite angefordert fuer %r (Kategorie %s, temperature=%s)", snippet, category, temperature)

    content = ollama_client.chat(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f'Ausschnitt (Kategorie {category}): "{snippet}"'},
        ],
        timeout=REQUEST_TIMEOUT_SECONDS,
        model=model,
        options={"temperature": temperature},
    )
    if content is None:
        logger.warning("Umformulierung nicht erreichbar, verwende Fallback")
        return f"[{category}]"

    rewritten = content.strip().strip('"')
    if not rewritten:
        logger.warning("Leere Umformulierung erhalten, verwende Fallback")
        return f"[{category}]"

    logger.info("Rewrite Ergebnis fuer %r: %r", snippet, rewritten)
    return rewritten