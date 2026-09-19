/**
 * Faengt das Absenden von Nachrichten ab (Enter oder Klick auf Senden),
 * verarbeitet den Text und loest das Senden danach selbst erneut aus.
 *
 * Nutzt filterEnabled, getInputElement, getSendButton aus shared.js.
 */

let isProcessing = false;

function setText(inputEl, newText) {
  inputEl.focus();
  const selection = window.getSelection();
  const range = document.createRange();
  range.selectNodeContents(inputEl);
  selection.removeAllRanges();
  selection.addRange(range);
  document.execCommand("delete", false, null);
  document.execCommand("insertText", false, newText);
}

function callHost(text, chatId) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ type: "PROCESS_TEXT", text, chatId }, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      if (response && response.ok) {
        resolve(response);
      } else {
        reject(new Error(response ? response.error : "keine Antwort vom Host"));
      }
    });
  });
}

function showInlineError(inputEl, message) {
  // Kurzzeitige rote Umrandung + Tooltip-artiger Hinweis
  const original = inputEl.style.outline;
  inputEl.style.outline = "2px solid #dc2626";

  let hint = document.getElementById("pii-filter-error-hint");
  if (!hint) {
    hint = document.createElement("div");
    hint.id = "pii-filter-error-hint";
    hint.style.cssText = `
      position: absolute;
      background: #dc2626;
      color: white;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 12px;
      z-index: 9999;
    `;
    document.body.appendChild(hint);
  }

  const rect = inputEl.getBoundingClientRect();
  hint.style.top = `${rect.top - 30}px`;
  hint.style.left = `${rect.left}px`;
  hint.textContent = message;
  hint.style.display = "block";

  setTimeout(() => {
    inputEl.style.outline = original;
    hint.style.display = "none";
  }, 3000);
}

async function processAndResend(inputEl) {
    logInfo("processAndResend GESTARTET, Zeitstempel: ", Date.now());
  const originalText = inputEl.innerText;
  if (!originalText.trim()) return;

  const chatId = getChatId();
  logDebug("Abgefangener Text: ", originalText, " Chat-ID: ", chatId);

  isProcessing = true;
  try {
    const response = await callHost(originalText, chatId);

    // Vault (aus shared.js) mit den neuen Funden befuellen
    const vault = getVault();
    Object.assign(vault, response.replacements);
    saveVaults();
    logInfo("Anonymisiert:", Object.keys(response.replacements).length, "Ersetzung(en)");
    logDebug("Erkannt und ersetzt:", response.replacements);

    setText(inputEl, response.result);

    setTimeout(() => {
      const sendButton = getSendButton(inputEl);
      logInfo("Klicke Sendebutton JETZT, Zeitstempel:", Date.now(), "Text im Feld:", inputEl.innerText);
      if (sendButton) sendButton.click();
      isProcessing = false;
    }, 50);
  } catch (err) {
      logError("Fehler beim Host-Aufruf:", err);
      showInlineError(inputEl, "Filter nicht erreichbar - Nachricht wurde NICHT gesendet");
      isProcessing = false;
  }
}

document.addEventListener(
  "keydown",
  (event) => {

      const inputEl = getInputElement();
      if (!inputEl || !inputEl.contains(event.target)) return;
      if (event.key !== "Enter" || event.shiftKey) return;
      if (isProcessing) return;
      if (!filterEnabled) {
        logTrace("Observer: filter deaktiviert");
        return;
      }

    event.preventDefault();
    event.stopPropagation();
    processAndResend(inputEl);
  },
  true
);

document.addEventListener(
  "click",
  (event) => {
    const inputEl = getInputElement();
    if (!inputEl) return;
    const sendButton = getSendButton(inputEl);
    logInfo("Klick erkannt. sendButton:", sendButton, "event.target:", event.target, "contains:", sendButton?.contains(event.target));

    if (!sendButton || !sendButton.contains(event.target)) return;
    if (isProcessing) return;
    if (!filterEnabled) {
        logTrace("Observer: filter deaktiviert");
        return;
      }

    event.preventDefault();
    event.stopPropagation();
    logInfo("preventDefault ausgefuehrt, starte processAndResend");
    processAndResend(inputEl);
  },
  true
);

logInfo("intercept-send.js geladen");

