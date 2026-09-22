"""
Vierte Erkennungsstufe: lokales LLM (via Ollama) fuer Firmengeheimnisse,
Personenkennungen und technische Secrets, die Regex/Presidio nicht als
Standardmuster fangen.

Ausschliesslich ERKENNUNG - liefert Matches mit einem generischen
Kategorie-Platzhalter als fake_value zurueck. Die eigentliche Umformulierung
uebernimmt llm_rewrite.py (bewusst als eigenes Modul getrennt, damit dieser
sorgfaeltig getunte Erkennungs-Prompt stabil bleibt).
"""
import difflib
import json
import logging
import re

from piifilter.detection.llm import ollama_client
from piifilter.detection.rule_based.types import Match

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 45

VALID_CATEGORIES = {"FIRMENGEHEIMNIS", "PERSONENKENNUNG", "TECHNISCHES_SECRET"}
NEGATION_MARKERS = ("kein finding", "keine sensible", "nicht sensibel", "kein sensib")

SYSTEM_PROMPT = """Du bist ein Erkennungssystem für drei ganz konkrete Arten sensibler Informationen in Texten, die an eine externe KI geschickt werden sollen.

Deine Aufgabe ist NICHT, offensichtliche Standard-PII wie normale Namen, E-Mail-Adressen oder Telefonnummern zu finden - das übernehmen bereits andere, vorgeschaltete Systeme (Regex, Presidio).

Du suchst AUSSCHLIESSLICH nach genau diesen drei Dingen:

1. FIRMENGEHEIMNIS: Interne, nicht-öffentliche Informationen aus Firma/Projekten - z.B. interne Projektnamen/Codenamen, unveröffentlichte Produkt-/Launch-Pläne, interne Kennzahlen (Umsatz, Budget, Stückzahlen), Sicherheitslücken die noch nicht öffentlich/gepatcht sind, interne Strategiepapiere, vertrauliche Kundennamen in einem Geschäftskontext.

2. PERSONENKENNUNG: Eindeutig identifizierende Merkmale, die klassische PII-Erkennung NICHT als Standardmuster fängt - z.B. Personalnummer, Mitarbeiter-ID, Gehaltsangaben (Betrag), firmeninterne Benutzer-/Rechnerkennungen (wie "vorname.nachname@FIRMENRECHNER" oder Windows-Benutzernamen in Dateipfaden), Sozialversicherungsnummer.

3. TECHNISCHES_SECRET: Zugangsdaten/Geheimnisse aus Code oder Konfiguration - z.B. API-Keys, Passwörter, Tokens (JWT, OAuth, etc.), Datenbank-Connection-Strings mit Zugangsdaten, private SSH-/TLS-Schlüssel, interne (nicht-öffentliche) Server-URLs oder Endpunkte, Secrets in Umgebungsvariablen/Config-Dateien.

WICHTIG - was NICHT markiert wird:
- Allgemeine Gesundheits-, Beziehungs- oder Lebenssituationen (Krankheit, Depression, Scheidung, sexuelle Orientierung, Sucht, Schwangerschaft, usw.) - auch wenn sie persönlich/privat sind, sind sie NICHT Teil dieser Erkennungsstufe, solange kein Firmengeheimnis oder keine eindeutige Personenkennung enthalten ist
- Die bloße Tatsache, dass jemand betroffen ist und Kontakt zu anderen Betroffenen sucht (z.B. bei einer Krankheit) - das ist eine bewusste, selbstbestimmte Angabe der Person, keine versteckte Re-Identifizierung
- Allgemeine Wissensfragen, egal zu welchem Thema
- Hypothetische/fiktive Szenarien ("stell dir vor...", Kurzgeschichten, Rollenspiele)
- Humor, Sarkasmus, offensichtlich übertriebene Aussagen
- Öffentliche Personen (Politiker, Prominente) in einem allgemeinen Meinungs-/Diskussionskontext - deren Namen sind ohnehin öffentlich bekannt
- Private Meinungen, Vorlieben, Alltagskram ohne Firmen-/Identifizierungsbezug

Im Zweifel NICHTS markieren. Diese Stufe soll selten und präzise auslösen, nicht bei jeder irgendwie persönlichen Aussage.

Nutze AUSSCHLIESSLICH eine dieser drei Kategorien:
- FIRMENGEHEIMNIS
- PERSONENKENNUNG
- TECHNISCHES_SECRET

Fasse zusammengehörige Stellen zu EINEM Finding zusammen, statt sie in mehrere kleine Findings aufzuteilen.

### Beispiel 1 (Firmengeheimnis: Projektname + Launch-Termin)
Text: "Kannst du mir helfen eine interne Ankündigung zu schreiben? Projekt Phoenix launcht jetzt doch erst im Q3 2027 statt wie geplant im Q1, das darf noch nicht nach außen dringen."
Antwort: {"findings": [{"text": "Projekt Phoenix launcht jetzt doch erst im Q3 2027 statt wie geplant im Q1, das darf noch nicht nach außen dringen", "category": "FIRMENGEHEIMNIS", "reason": "Unveröffentlichter interner Projektname und Launch-Termin"}]}

### Beispiel 2 (Personenkennung: Gehalt)
Text: "Mein aktuelles Gehalt beträgt 58.000€ brutto im Jahr, wie verhandle ich am besten eine Erhöhung auf 65.000€?"
Antwort: {"findings": [{"text": "Mein aktuelles Gehalt beträgt 58.000€ brutto im Jahr", "category": "PERSONENKENNUNG", "reason": "Konkrete Gehaltsangabe der Person"}]}

### Beispiel 3 (Personenkennung: Personalnummer)
Text: "Ich habe unter meiner Personalnummer PN-48213 ein Problem mit der Zeiterfassung, kannst du mir eine Mail an die IT formulieren?"
Antwort: {"findings": [{"text": "Personalnummer PN-48213", "category": "PERSONENKENNUNG", "reason": "Eindeutige interne Mitarbeiter-Kennung"}]}

### Beispiel 4 (Firmengeheimnis: Sicherheitslücke, nicht öffentlich)
Text: "Wir haben eine kritische Sicherheitslücke in unserem Zahlungssystem gefunden, die noch nicht gepatcht ist - wie formuliere ich das für den internen Vorfallsbericht?"
Antwort: {"findings": [{"text": "eine kritische Sicherheitslücke in unserem Zahlungssystem gefunden, die noch nicht gepatcht ist", "category": "FIRMENGEHEIMNIS", "reason": "Nicht-öffentliche, ungepatchte Sicherheitslücke"}]}

### Beispiel 5 (System-/Rechnerkennung, isolierter String)
Text: "a121212@ASUS_Zenbook"
Antwort: {"findings": [{"text": "a121212@ASUS_Zenbook", "category": "PERSONENKENNUNG", "reason": "Benutzername/Rechnername-Kombination"}]}

### Beispiel 6 (Kein Finding: allgemeine Gesundheitsangabe ohne Firmen-/Kennungsbezug)
Text: "Ich bin an Mukoviszidose erkrankt und suche Kontakt zu anderen Betroffenen in meiner Region."
Antwort: {"findings": []}

### Beispiel 7 (Kein Finding: öffentliche Person, allgemeine Frage)
Text: "Was denkst du über die Wirtschaftspolitik von Christian Lindner in den letzten Jahren?"
Antwort: {"findings": []}

### Beispiel 8 (Kein Finding: harmlose Frage)
Text: "Wie schreibe ich eine Einkaufsliste für Milch, Brot und Eier?"
Antwort: {"findings": []}

### Beispiel 9 (Personenkennung: Rechnername eingebettet in einem Satz, nicht als isolierter String)
Text: "Der Fehler tritt auf meinem Rechner m.schneider-PC-Finance auf, wenn ich mich ins interne Portal einlogge."
Antwort: {"findings": [{"text": "m.schneider-PC-Finance", "category": "PERSONENKENNUNG", "reason": "Rechnername enthält Benutzernamen und Abteilung, identifiziert die Person"}]}

### Beispiel 10 (Technisches Secret: API-Key in Code)
Text: "Kannst du diesen Code debuggen?\\n\\nAPI_KEY = \\"sk-live-9f8a7b6c5d4e3f2a1b0c\\"\\nresponse = requests.get(url, headers={'Authorization': API_KEY})"
Antwort: {"findings": [{"text": "sk-live-9f8a7b6c5d4e3f2a1b0c", "category": "TECHNISCHES_SECRET", "reason": "Live-API-Key, der Zugriff auf einen externen Dienst erlaubt"}]}

WICHTIG: Jedes Beispiel oben ist nur ein Muster für die jeweilige Kategorie. Wende das gleiche Prinzip auf den tatsächlichen Text unten an - kopiere NIEMALS Text oder Ergebnisse aus einem dieser Beispiele, auch wenn der Text ähnlich aussieht. Extrahiere ausschließlich aus dem tatsächlich gegebenen Text.

Wenn du nichts findest, antworte IMMER exakt mit {"findings": []} - gib niemals ein Finding-Objekt mit einer Begründung wie "kein Finding" oder ähnlichem zurück. Ein Finding-Objekt bedeutet automatisch: hier wurde etwas Sensibles gefunden.

Antworte AUSSCHLIESSLICH mit validem JSON in exakt diesem Format, ohne zusätzlichen Text davor oder danach:

{"findings": [{"text": "<exakter Textausschnitt aus der Originalnachricht, wörtlich kopiert>", "category": "<FIRMENGEHEIMNIS, PERSONENKENNUNG oder TECHNISCHES_SECRET>", "reason": "<kurze Begründung>"}]}

Wichtig: Der Wert von "text" muss ZEICHENGENAU aus der Originalnachricht kopiert sein, damit er dort wiedergefunden werden kann."""


def _extract_json(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"Kein JSON im Modell-Output gefunden: {raw!r}")
    return json.loads(match.group(0))


def _fuzzy_find(text: str, snippet: str, min_ratio: float = 0.75):
    """Exaktes find(), sonst ueber SequenceMatcher.find_longest_match direkt den
    Ankerpunkt im Originaltext bestimmen (robuster als ein Sliding-Window)."""
    start = text.find(snippet)
    if start != -1:
        return start, start + len(snippet)

    n = len(snippet)
    if n == 0 or n > len(text):
        return None

    matcher = difflib.SequenceMatcher(None, text, snippet, autojunk=False)
    m = matcher.find_longest_match(0, len(text), 0, n)
    if m.size == 0:
        return None

    anchor = m.a - m.b
    candidate_start = max(0, min(anchor, len(text) - 1))
    candidate_end = min(len(text), candidate_start + n)
    candidate = text[candidate_start:candidate_end]

    ratio = difflib.SequenceMatcher(None, snippet, candidate).ratio()
    if ratio >= min_ratio:
        return candidate_start, candidate_end
    return None


def _merge_close_findings(findings: list[dict], gap: int = 15) -> list[dict]:
    """Sicherheitsnetz: falls das Modell trotz Prompt-Anweisung fragmentiert,
    werden Findings, die sich ueberlappen oder nur wenige Zeichen auseinanderliegen,
    zu einem zusammenhaengenden Finding verschmolzen."""
    if not findings:
        return findings

    ordered = sorted(findings, key=lambda f: f["start"])
    merged = [dict(ordered[0])]

    for current in ordered[1:]:
        last = merged[-1]
        if current["start"] <= last["end"] + gap:
            last["end"] = max(last["end"], current["end"])
            if len(current.get("text", "")) > len(last.get("text", "")):
                last["category"] = current["category"]
            if current["reason"] not in last["reason"]:
                last["reason"] = f"{last['reason']}; {current['reason']}"
        else:
            merged.append(dict(current))

    return merged


def find_matches(text: str, chat_id: str = None, model: str = ollama_client.DEFAULT_MODEL) -> list[Match]:
    """
    Analysiert `text` auf Firmengeheimnisse/Personenkennungen/technische Secrets.

    Wichtig fuer den Aufrufer: `text` sollte der bereits von Custom/Regex/Presidio
    anonymisierte Text sein (nicht das Original) - sonst markiert das LLM
    Stellen, die von den vorherigen Stufen schon ersetzt wurden.

    fake_value ist hier ein generischer Kategorie-Platzhalter, kein Vorschlag
    fuer eine natuerliche Umformulierung - das macht llm_rewrite.py separat.
    """
    if not text or not text.strip():
        return []

    raw = ollama_client.chat(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        timeout=REQUEST_TIMEOUT_SECONDS,
        model=model,
        options={"temperature": 0},
        json_format=True,
    )
    if raw is None:
        return []

    logger.info("LLM Rohantwort: %s", raw)

    try:
        parsed = _extract_json(raw)
    except (ValueError, json.JSONDecodeError) as e:
        logger.warning("LLM-Antwort konnte nicht geparst werden: %s", e)
        return []
    logger.info("LLM Rohantwort: %s", raw)

    findings = []
    for finding in parsed.get("findings", []):
        category = finding.get("category", "")
        reason = finding.get("reason", "")
        snippet = finding.get("text", "")

        if category not in VALID_CATEGORIES:
            logger.warning("LLM lieferte ungueltige Kategorie %r, Finding verworfen", category)
            continue
        if any(marker in reason.lower() for marker in NEGATION_MARKERS):
            logger.info("Verworfen (Negation erkannt): %r", snippet)
            continue

        snippet = finding.get("text", "")
        span = _fuzzy_find(text, snippet)
        if span is None:
            logger.warning("LLM-Snippet nicht im Text gefunden, verworfen: %r", snippet)
            continue

        start, end = span
        actual_text = text[start:end]
        if actual_text != snippet:
            logger.info(
                "Fuzzy-Match: Modell lieferte %r, tatsaechlich verankert auf %r (Position %d-%d)",
                snippet, actual_text, start, end,
            )

        findings.append({
            "start": start,
            "end": end,
            "text": text[start:end],
            "category": category,
            "reason": reason,
        })

    before_merge = len(findings)
    findings = _merge_close_findings(findings)
    if len(findings) != before_merge:
        logger.info("Merge: %d Findings zu %d zusammengefasst", before_merge, len(findings))


    matches: list[Match] = []
    counters: dict[str, int] = {}
    for f in findings:
        counters[f["category"]] = counters.get(f["category"], 0) + 1
        placeholder = f"[{f['category']}_{counters[f['category']]}]"
        original_text = text[f["start"]:f["end"]]
        matches.append(Match(f["start"], f["end"], original_text, placeholder, f["category"]))

    logger.info("LLM Erkennung fertig: %d Fund(e) nach Filterung: %s", len(matches),
                [(m.original, m.category) for m in matches])

    return matches