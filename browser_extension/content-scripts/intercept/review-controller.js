/**
 * Orchestrierung: haelt den Review-Zustand (activeReview), reagiert auf die
 * asynchrone LLM_SUGGESTIONS-Nachricht und entscheidet, ob/wann tatsaechlich
 * gesendet wird. Nutzt host-client.js (Kommunikation) und review-panel.js
 * (Darstellung), kennt aber selbst kein DOM-Markup.
 *
 * Live-Vorschau: das Eingabefeld wird schon WAEHREND der Review-Phase live
 * aktualisiert (nicht erst beim Senden), damit sichtbar ist, was sich
 * aendert, sobald der Nutzer Haekchen setzt/entfernt. Die Berechnung laeuft
 * komplett client-seitig (computeCurrentText) - kein Host-Roundtrip mehr
 * pro Klick noetig, da alle Daten (Original, Umformulierung, Position)
 * schon im Vorschlag stecken.
 */

let isProcessing = false;

// Pro laufender Anfrage der Review-Zustand, keyed nach requestId - falls der
// Nutzer zwischenzeitlich eine neue Nachricht losschickt, wird der alte
// Zustand einfach verworfen (siehe LLM_SUGGESTIONS-Listener unten).
let activeReview = null;
// true waehrend WIR selbst per setText() das Feld aendern (Live-Vorschau).
// Der input-Listener in intercept-send.js soll das NICHT als "Nutzer tippt"
// werten - anders als event.isTrusted zuverlaessig unterscheidbar, weil
// von execCommand ausgeloeste input-Events vom Browser als isTrusted=true
// gelten, obwohl sie programmatisch von uns kommen.
let suppressInputTracking = false;

function buildPhase1Items(replacements) {
  return Object.entries(replacements).map(([placeholder, original]) => ({
    placeholder,
    original,
    accepted: true, // Phase 1: vorausgewaehlt - zuverlaessige Quelle
  }));
}

function buildPhase2Items(suggestions) {
  return suggestions.map((s) => ({
    id: s.id,
    original: s.text,
    suggestedReplacement: s.suggestedReplacement,
    category: s.category,
    accepted: false, // Phase 2: bewusst NICHT vorausgewaehlt
  }));
}

/**
 * Berechnet den aktuellen Vorschau-/Sendetext rein aus dem Review-Zustand,
 * ohne Host-Aufruf. Reihenfolge ist wichtig:
 *  1. Phase-2-Ersetzungen ZUERST anwenden, solange der Text noch exakt dem
 *     Stand entspricht, auf den sich die start/end-Positionen der
 *     Vorschlaege beziehen (phase1ResultText, unveraendert).
 *  2. Danach Phase-1-Reverts (abgelehnte Phase-1-Funde zurueck auf Original)
 *     per split/join - das ist positionsunabhaengig, weil Fake-Werte
 *     eindeutige Strings sind, und darf deshalb NACH den positionsbasierten
 *     Phase-2-Ersetzungen laufen, ohne deren Positionen zu verschieben.
 */
function computeCurrentText(review) {
  let text = review.phase1ResultText;

  const acceptedPhase2 = review.phase2Items
    .filter((i) => i.accepted)
    .map((i) => review.phase2ItemsRaw.find((raw) => raw.id === i.id))
    .filter(Boolean)
    .sort((a, b) => b.start - a.start); // absteigend, damit fruehere Positionen gueltig bleiben

  for (const s of acceptedPhase2) {
    if (text.slice(s.start, s.end) !== s.text) continue; // Sicherheitscheck: Position passt nicht mehr
    text = text.slice(0, s.start) + s.suggestedReplacement + text.slice(s.end);
  }

  for (const item of review.phase1Items) {
    if (!item.accepted) {
      text = text.split(item.placeholder).join(item.original);
    }
  }

  return text;
}

function updateLivePreview() {
  if (!activeReview) return;
  suppressInputTracking = true;
  setText(activeReview.inputEl, computeCurrentText(activeReview));
  // Das input-Event feuert synchron waehrend setText() - erst NACH dem
  // aktuellen Tick wieder freigeben, damit der Listener es sicher sieht.
  setTimeout(() => {
    suppressInputTracking = false;
  }, 0);
}

function getReviewHandlers() {
  return {
    onAcceptAll: () => {
      activeReview.phase1Items.forEach((i) => (i.accepted = true));
      activeReview.phase2Items.forEach((i) => (i.accepted = true));
      refreshPanel();
      updateLivePreview();
    },
    onRescan: () => {
      if (!activeReview) return;
      const inputEl = activeReview.inputEl;
      logInfo("Neu ueberpruefen ausgeloest - verwerfe aktuelle Review, scanne aktuellen Text neu");
      cancelActiveReview();
      processAndResend(inputEl);
    },
    onToggle: (item, accepted) => {
      item.accepted = accepted;
      updateLivePreview();
    },
    onRetryRewrite: (item) => retryRewriteItem(item),
    onSend: () => finalizeAndSend(),
    onSkipLlm: () => finalizeAndSend(),
  };
}

function refreshPanel() {
  renderReviewPanel(activeReview, getReviewHandlers());
}

/**
 * Verwirft eine laufende Review komplett (z.B. weil der Nutzer waehrend
 * das Panel offen ist weitergetippt hat). Setzt alles auf den Zustand
 * zurueck, den es vor dem ersten Enter/Klick hatte - das naechste Enter
 * startet dann ganz normal einen frischen processAndResend()-Durchlauf.
 */
function cancelActiveReview() {
  activeReview = null;
  isProcessing = false;
  removeReviewPanel();
}


/**
 * Sendet den aktuellen Stand ab: berechnet den finalen Text genauso wie die
 * Live-Vorschau (computeCurrentText), traegt die akzeptierten Ersetzungen in
 * die Vault ein (fuer die spaetere Rueckuebersetzung von Claudes Antwort)
 * und klickt danach den echten Sende-Button.
 */
async function finalizeAndSend() {
  if (!activeReview) return;
  const review = activeReview;
  activeReview = null;
  removeReviewPanel();

  const text = computeCurrentText(review);
  const vault = getVault();

  for (const item of review.phase1Items) {
    if (item.accepted) {
      vault[item.placeholder] = item.original;
    }
  }
  for (const item of review.phase2Items) {
    if (item.accepted && item.suggestedReplacement) {
      vault[item.suggestedReplacement] = item.original;
    }
  }

  saveVaults();
  logInfo("Gesendet:", Object.keys(vault).length, "Ersetzung(en) insgesamt in der Vault");

  setText(review.inputEl, text);
  setTimeout(() => {
    const sendButton = getSendButton(review.inputEl);
    if (sendButton) sendButton.click();
    isProcessing = false;
  }, 50);
}

// Unaufgefordert vom background.js gepushte Phase-2-Nachricht
chrome.runtime.onMessage.addListener((message) => {
  if (message.type !== "LLM_SUGGESTIONS") return;
  if (!activeReview || activeReview.requestId !== message.requestId) {
    // Gehoert nicht (mehr) zur aktuell laufenden Anfrage - z.B. weil der
    // Nutzer per "Trotzdem jetzt senden" schon vorher gesendet hat, oder
    // inzwischen eine neue Nachricht losgeschickt wurde.
    return;
  }

  activeReview.phase2ItemsRaw = message.suggestions;
  activeReview.phase2Items = buildPhase2Items(message.suggestions);
  activeReview.phase2Status = "done";

  if (activeReview.phase1Items.length === 0 && activeReview.phase2Items.length === 0) {
    // Weder Phase 1 noch Phase 2 haben etwas gefunden - kein Grund fuer ein
    // Panel, einfach direkt senden.
    finalizeAndSend();
  } else {
    refreshPanel();
  }
});

async function processAndResend(inputEl) {
  logInfo("processAndResend GESTARTET, Zeitstempel: ", Date.now());
  const originalText = inputEl.innerText;
  if (!originalText.trim()) return;

  const chatId = getChatId();
  logDebug("Abgefangener Text: ", originalText, " Chat-ID: ", chatId);

  isProcessing = true;
  try {
    const llmEnabled = await getLlmEnabled();
    const response = await callHost(originalText, chatId, llmEnabled);

    activeReview = {
      requestId: response.requestId,
      inputEl,
      phase1ResultText: response.result,
      phase1Items: buildPhase1Items(response.replacements),
      phase2Items: [],
      phase2ItemsRaw: [],
      phase2Status: llmEnabled ? "pending" : "disabled",
    };

    logInfo("Phase 1 verarbeitet:", activeReview.phase1Items.length, "Ersetzung(en), LLM aktiv:", llmEnabled);

    // Zeigt die Phase-1-Ersetzungen sofort im Eingabefeld an, noch bevor
    // der Nutzer irgendetwas im Panel anklickt.
    updateLivePreview();

    if (!llmEnabled && activeReview.phase1Items.length === 0) {
      // Nichts zu entscheiden - direkt senden, kein Panel.
      finalizeAndSend();
      return;
    }

    // Zeigt das Panel bereits mit den Phase-1-Funden (falls vorhanden); ist
    // das LLM aktiv, erscheint dort zusaetzlich "Prüfe auf weitere sensible
    // Stellen…", bis die LLM_SUGGESTIONS-Nachricht oben eintrifft.
    refreshPanel();
  } catch (err) {
    logError("Fehler beim Host-Aufruf:", err);
    showInlineError(inputEl, "Filter nicht erreichbar - Nachricht wurde NICHT gesendet");
    isProcessing = false;
    activeReview = null;
  }
}

async function retryRewriteItem(item) {
  if (!activeReview) return;
  const raw = activeReview.phase2ItemsRaw.find((r) => r.id === item.id);
  if (!raw) return;

  const previous = item.suggestedReplacement;
  item.suggestedReplacement = "…"; // kurzes visuelles Feedback waehrend der Anfrage
  refreshPanel();

  try {
    const rewritten = await callRetryRewrite(raw.text, raw.category);
    raw.suggestedReplacement = rewritten; // wichtig: auch im "raw"-Eintrag, computeCurrentText liest von dort
    item.suggestedReplacement = rewritten;
    logInfo("Neu umformuliert:", raw.text, "->", rewritten);
  } catch (err) {
    logError("Fehler beim Neu-Umformulieren:", err);
    item.suggestedReplacement = previous; // Fallback: alten Vorschlag behalten
  }

  refreshPanel();
  updateLivePreview();
}