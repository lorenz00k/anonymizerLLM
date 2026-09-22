importScripts("logger.js");

// Muss exakt mit dem "name" im native-host manifest json übereinstimmen
const NATIVE_HOST_NAME = "com.piifilter.host";

function makeRequestId() {
  return crypto.randomUUID();
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "PROCESS_TEXT") {
    const requestId = makeRequestId();
    const tabId = sender.tab ? sender.tab.id : null;

    try {
      const port = chrome.runtime.connectNative(NATIVE_HOST_NAME);
      let phase1Responded = false;

      // Phase 1 (Custom/Regex/Presidio) ist immer schnell (<1ms beim Host),
      // 5s bleibt hier also ein sinnvoller Timeout NUR fuer diese erste
      // Antwort - die LLM-Stufe (Phase 2) hat ihre eigene, laengere Frist
      // und blockiert diesen Timeout nicht.
      const phase1Timeout = setTimeout(() => {
        if (!phase1Responded) {
          phase1Responded = true;
          sendResponse({ ok: false, error: "Host hat nicht rechtzeitig geantwortet" });
          port.disconnect();
        }
      }, 5000);

      port.onMessage.addListener((response) => {
        if (response.type === "anonymize_result") {
          if (phase1Responded) return; // Sicherheitsnetz gegen doppelte Antworten
          phase1Responded = true;
          clearTimeout(phase1Timeout);
          sendResponse({
            ok: true,
            result: response.result,
            replacements: response.replacements,
            requestId,
          });
          // WICHTIG: Port bewusst OFFEN LASSEN (anders als vorher) - der Host
          // schickt ueber genau diesen Port gleich noch die llm_suggestions-
          // Nachricht nach, egal ob leer (LLM deaktiviert) oder mit echten
          // Vorschlaegen. sendResponse() ist an dieser Stelle "verbraucht"
          // (Chrome erlaubt nur einen Aufruf pro Nachricht), deshalb wird
          // die zweite Nachricht unten aktiv an den Tab gepusht statt ueber
          // sendResponse zurueckgegeben.
        } else if (response.type === "llm_suggestions") {
          if (tabId !== null) {
            chrome.tabs.sendMessage(tabId, {
              type: "LLM_SUGGESTIONS",
              requestId,
              suggestions: response.suggestions,
            });
          } else {
            logError("Keine tabId fuer LLM-Vorschlaege vorhanden, kann nicht zustellen");
          }
          // Fuer diese eine PROCESS_TEXT-Anfrage ist jetzt nichts mehr zu
          // erwarten (egal ob leer oder mit Inhalt) - Port sauber schliessen.
          port.disconnect();
        }
      });

      port.onDisconnect.addListener(() => {
        if (chrome.runtime.lastError) {
          logError("Native host disconnect:", chrome.runtime.lastError.message);
        }
      });

      port.postMessage({
        type: "anonymize",
        text: message.text,
        chatId: message.chatId,
        requestId,
        llmEnabled: message.llmEnabled === true,
      });
    } catch (err) {
      logError("Fehler in background.js:", err);
      sendResponse({ ok: false, error: err.message });
    }

    // wichtig: signalisiert Chrome, dass sendResponse asynchron kommt
    return true;
  }

  if (message.type === "APPLY_LLM") {
    // Eigene, kurzlebige Verbindung fuer Phase 3 - unabhaengig vom Port
    // oben, der zu diesem Zeitpunkt schon wieder geschlossen ist.
    try {
      const port = chrome.runtime.connectNative(NATIVE_HOST_NAME);
      const requestId = makeRequestId();
      let responded = false;

      const timeout = setTimeout(() => {
        if (!responded) {
          responded = true;
          sendResponse({ ok: false, error: "Host hat nicht rechtzeitig geantwortet (apply_llm)" });
          port.disconnect();
        }
      }, 10000);

      port.onMessage.addListener((response) => {
        if (response.type === "apply_llm_result" && !responded) {
          responded = true;
          clearTimeout(timeout);
          sendResponse({ ok: true, result: response.result, replacements: response.replacements });
          port.disconnect();
        }
      });

      port.onDisconnect.addListener(() => {
        if (chrome.runtime.lastError) {
          logError("Native host disconnect (apply_llm):", chrome.runtime.lastError.message);
        }
      });

      port.postMessage({
        type: "apply_llm",
        text: message.text,
        suggestions: message.suggestions,
        acceptedIds: message.acceptedIds,
        requestId,
      });
    } catch (err) {
      logError("Fehler in background.js (apply_llm):", err);
      sendResponse({ ok: false, error: err.message });
    }

    return true;
  }

  if (message.type === "RETRY_REWRITE") {
    // Eigene, kurzlebige Verbindung, analog zu APPLY_LLM oben.
    try {
      const port = chrome.runtime.connectNative(NATIVE_HOST_NAME);
      const requestId = makeRequestId();
      let responded = false;

      const timeout = setTimeout(() => {
        if (!responded) {
          responded = true;
          sendResponse({ ok: false, error: "Host hat nicht rechtzeitig geantwortet (retry_rewrite)" });
          port.disconnect();
        }
      }, 20000); // grosszuegig, Rewrite-Call braucht ein paar Sekunden

      port.onMessage.addListener((response) => {
        if (response.type === "retry_rewrite_result" && !responded) {
          responded = true;
          clearTimeout(timeout);
          sendResponse({ ok: true, suggestedReplacement: response.suggestedReplacement });
          port.disconnect();
        }
      });

      port.onDisconnect.addListener(() => {
        if (chrome.runtime.lastError) {
          logError("Native host disconnect (retry_rewrite):", chrome.runtime.lastError.message);
        }
      });

      port.postMessage({
        type: "retry_rewrite",
        text: message.text,
        category: message.category,
        requestId,
      });
    } catch (err) {
      logError("Fehler in background.js (retry_rewrite):", err);
      sendResponse({ ok: false, error: err.message });
    }

    return true;
  }
});