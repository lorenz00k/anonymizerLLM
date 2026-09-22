import difflib
import json
import re

import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"

SYSTEM_PROMPT = """Du bist ein Erkennungssystem für zwei ganz konkrete Arten sensibler Informationen in Texten, die an eine externe KI geschickt werden sollen.

Deine Aufgabe ist NICHT, offensichtliche Standard-PII wie normale Namen, E-Mail-Adressen oder Telefonnummern zu finden - das übernehmen bereits andere, vorgeschaltete Systeme (Regex, Presidio).

Du suchst AUSSCHLIESSLICH nach genau diesen drei Dingen:

1. FIRMENGEHEIMNIS: Interne, nicht-öffentliche Informationen aus Firma/Projekten - z.B. interne Projektnamen/Codenamen, unveröffentlichte Produkt-/Launch-Pläne, interne Kennzahlen (Umsatz, Budget, Stückzahlen), Sicherheitslücken die noch nicht öffentlich/gepatcht sind, interne Strategiepapiere, vertrauliche Kundennamen in einem Geschäftskontext.

2. PERSONENKENNUNG: Eindeutig identifizierende Merkmale, die klassische PII-Erkennung NICHT als Standardmuster fängt - z.B. Personalnummer, Mitarbeiter-ID, Gehaltsangaben (Betrag), firmeninterne Benutzer-/Rechnerkennungen (wie "vorname.nachname@FIRMENRECHNER" oder Windows-Benutzernamen in Dateipfaden), Sozialversicherungsnummer.

3. TECHNISCHES_SECRET: Zugangsdaten/Geheimnisse aus Code oder Konfiguration - z.B. API-Keys, Passwörter, Tokens (JWT, OAuth, etc.), Datenbank-Connection-Strings mit Zugangsdaten, private SSH-/TLS-Schlüssel, interne (nicht-öffentliche) Server-URLs oder Endpunkte, Secrets in Umgebungsvariablen/Config-Dateien.

WICHTIG - was NICHT markiert wird (das war früher Teil der Erkennung, ist es jetzt NICHT mehr):
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

### Beispiel 5 (System-/Rechnerkennung)
Text: "a121212@ASUS_Zenbook"
Antwort: {"findings": [{"text": "a121212@ASUS_Zenbook", "category": "PERSONENKENNUNG", "reason": "Benutzername/Rechnername-Kombination"}]}

### Beispiel 6 (Kein Finding: allgemeine Gesundheitsangabe ohne Firmen-/Kennungsbezug - NICHT mehr markieren)
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


def extract_json(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"Kein JSON im Modell-Output gefunden: {raw!r}")
    return json.loads(match.group(0))


def fuzzy_find(text: str, snippet: str, min_ratio: float = 0.75):
    start = text.find(snippet)
    if start != -1:
        return start, start + len(snippet)

    n = len(snippet)
    if n == 0 or n > len(text):
        return None

    matcher = difflib.SequenceMatcher(None, text, snippet, autojunk=False)
    match = matcher.find_longest_match(0, len(text), 0, n)
    if match.size == 0:
        return None

    anchor = match.a - match.b
    candidate_start = max(0, min(anchor, len(text) - 1))
    candidate_end = min(len(text), candidate_start + n)
    candidate = text[candidate_start:candidate_end]

    ratio = difflib.SequenceMatcher(None, snippet, candidate).ratio()
    if ratio >= min_ratio:
        return candidate_start, candidate_end
    return None


def merge_close_findings(findings: list[dict], gap: int = 15) -> list[dict]:
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


def find_contextual_matches(text: str, model: str = MODEL) -> list[dict]:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        },
    )
    response.raise_for_status()
    raw = response.json()["message"]["content"]

    try:
        parsed = extract_json(raw)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"  [WARNUNG] Konnte Antwort nicht parsen: {e}")
        return []

    VALID_CATEGORIES = {"FIRMENGEHEIMNIS", "PERSONENKENNUNG", "TECHNISCHES_SECRET"}
    NEGATION_MARKERS = ("kein finding", "keine sensible", "nicht sensibel", "kein sensib")

    findings = []
    for finding in parsed.get("findings", []):
        category = finding.get("category", "")
        reason = finding.get("reason", "")

        if category not in VALID_CATEGORIES:
            print(f"  [WARNUNG] Ungültige Kategorie {category!r}, Finding verworfen")
            continue
        if any(marker in reason.lower() for marker in NEGATION_MARKERS):
            print(f"  [WARNUNG] Widersprüchliche Begründung ({reason!r}), Finding verworfen")
            continue

        snippet = finding.get("text", "")
        span = fuzzy_find(text, snippet)
        if span is None:
            print(f"  [WARNUNG] Snippet nicht im Original gefunden (auch fuzzy nicht), verworfen: {snippet!r}")
            continue
        start, end = span
        findings.append({
            "start": start,
            "end": end,
            "text": text[start:end],
            "category": category,
            "reason": reason,
        })

    findings = merge_close_findings(findings)
    for f in findings:
        f["text"] = text[f["start"]:f["end"]]

    return findings


TEST_TEXTS = [
    # --- FIRMENGEHEIMNIS: sollte anschlagen ---

    "Kannst du mir helfen eine interne Ankündigung zu schreiben? Projekt Phoenix launcht jetzt doch "
    "erst im Q3 2027 statt wie geplant im Q1. Schreibe es bitte auf Englisch wie besprochen.",

    "Wir haben eine kritische Sicherheitslücke in unserem Zahlungssystem gefunden, die noch nicht "
    "gepatcht ist - wie formuliere ich das für den internen Vorfallsbericht?",

    "Unser größter Kunde, die Musterfirma GmbH, will den Vertrag um 40% kürzen. Das ist natürlich eine "
    "blöde Nachricht. Wie bereite ich das intern für den Vorstand auf? Mach es bitte sehr professionell.",

    "Der Umsatz in Q2 lag bei 2,3 Millionen Euro, 15% unter Plan, das ist noch nicht kommuniziert - "
    "hilf mir das für die interne Quartalsmail zu formulieren.",

    # --- PERSONENKENNUNG: sollte anschlagen ---

    "Mein aktuelles Gehalt beträgt 58.000€ brutto im Jahr, wie verhandle ich am besten eine Erhöhung auf 65.000€?",

    "Ich habe unter meiner Personalnummer PN-48213 ein Problem mit der Zeiterfassung, kannst du mir "
    "eine Mail an die IT formulieren?",

    "a121212@ASUS_Zenbook",

    "Der Fehler tritt auf meinem Rechner m.schneider-PC-Finance auf, wenn ich mich ins interne Portal einlogge.",

    "Ich bekomme einen Fehler beim Öffnen von C:\\Users\\jkovac\\Documents\\Gehaltsabrechnung_2026.xlsx",

    # --- TECHNISCHES_SECRET: sollte anschlagen ---
    "Kannst du diesen Code debuggen?\n\n"
    "API_KEY = \"sk-live-9f8a7b6c5d4e3f2a1b0c\"\n"
    "response = requests.get(url, headers={'Authorization': API_KEY})",

    "Meine .env Datei sieht so aus:\n\n"
    "DB_HOST=internal-db-prod.company.local\n"
    "DB_PASSWORD=Tr0ub4dor&3xyz\n\n"
    "warum bekomme ich trotzdem einen Connection-Timeout?",

    # --- Negativ-Fälle: sollten NICHTS finden (neuer, engerer Scope) ---

    # Allgemeine Gesundheitsangabe ohne Firmen-/Kennungsbezug - jetzt explizit NICHT mehr sensibel
    "Ich bin an Mukoviszidose erkrankt und suche Kontakt zu anderen Betroffenen in meiner Region.",

    # Beziehung/Coming-Out - jetzt explizit NICHT mehr sensibel (alter Testfall)
    "Ich möchte meinen Eltern einen Brief schreiben, in dem ich ihnen erzähle, dass ich seit einem Jahr "
    "einen festen Freund habe und mich als schwul geoutet habe.",

    # Scheidung/Kirchenaustritt - jetzt explizit NICHT mehr sensibel (alter Testfall)
    "Ich bin seit letztem Monat aus der Kirche ausgetreten, weil meine Gemeinde meine Scheidung "
    "nicht akzeptiert hat. Welches Motto würdest du für eine Einhorn-Party für meine Tochter empfehlen?",

    # Öffentliche Person
    "Was denkst du über die Wirtschaftspolitik von Christian Lindner in den letzten Jahren?",

    # Sarkasmus
    "Mein Chef ist bestimmt ein Alien, der glaubt jeden Montag um 7 Uhr ein Meeting anzusetzen sei eine gute Idee 😄",

    # Hypothetisch
    "Stell dir vor, jemand hätte eine schwere Krankheit und müsste seinem Arbeitgeber davon erzählen - "
    "wie würdest du das formulieren?",

    # Harmlos
    "Wie schreibe ich eine Einkaufsliste für Milch, Brot und Eier?",

    # Allgemeine Fachfrage zu Unternehmen/Wirtschaft, aber ohne konkretes eigenes Firmengeheimnis
    "Wie berechnet man den EBITDA einer Firma und wofür wird die Kennzahl typischerweise verwendet?",
]


if __name__ == "__main__":
    import sys
    model = sys.argv[1] if len(sys.argv) > 1 else MODEL
    print(f"=== Modell: {model} ===")
    for i, text in enumerate(TEST_TEXTS, 1):
        print(f"\n--- Testtext {i} ---")
        print(text)
        print("Findings:")
        findings = find_contextual_matches(text, model=model)
        if not findings:
            print("  (keine)")
        for f in findings:
            print(f"  [{f['start']}:{f['end']}] '{f['text']}' -> {f['category']}: {f['reason']}")