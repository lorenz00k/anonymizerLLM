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

function callHost(text) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ type: "PROCESS_TEXT", text }, (response) => {
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
async function processAndResend(inputEl) {
  const originalText = inputEl.innerText;
  if (!originalText.trim()) return;

  console.log("[PII Filter] Abgefangener Text:", originalText);

  isProcessing = true;
  try {
    const response = await callHost(originalText);

    // Vault (aus shared.js) mit den neuen Funden befuellen
    Object.assign(vault, response.replacements);
    console.log("[PII Filter] Erkannt und ersetzt:", response.replacements);

    setText(inputEl, response.result);

    setTimeout(() => {
      const sendButton = getSendButton(inputEl);
      if (sendButton) sendButton.click();
      isProcessing = false;
    }, 50);
  } catch (err) {
    console.error("[PII Filter] Fehler beim Host-Aufruf:", err);
    isProcessing = false;
    // Bewusste Entscheidung: bei Fehler NICHT senden, damit nichts
    // ungeprueft rausgeht. Alternative waere: unveraendert senden -
    // aber das widerspricht dem eigentlichen Zweck des Tools.
  }
}

document.addEventListener(
  "keydown",
  (event) => {
    if (isProcessing) return;
    if (!filterEnabled) return;
    if (event.key !== "Enter" || event.shiftKey) return;

    const inputEl = getInputElement();
    if (!inputEl || !inputEl.contains(event.target)) return;

    event.preventDefault();
    event.stopPropagation();
    processAndResend(inputEl);
  },
  true
);

document.addEventListener(
  "click",
  (event) => {
    if (isProcessing) return;
    if (!filterEnabled) return;

    const inputEl = getInputElement();
    if (!inputEl) return;
    const sendButton = getSendButton(inputEl);
    if (!sendButton || !sendButton.contains(event.target)) return;

    event.preventDefault();
    event.stopPropagation();
    processAndResend(inputEl);
  },
  true
);

console.log("[PII Filter] intercept-send.js geladen");