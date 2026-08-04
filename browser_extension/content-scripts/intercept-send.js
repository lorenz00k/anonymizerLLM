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

function processAndResend(inputEl) {
  const originalText = inputEl.innerText;
  if (!originalText.trim()) return;

  console.log("[PII Filter] Abgefangener Text:", originalText);
  const transformed = originalText.toUpperCase(); // Platzhalter, spaeter echte Erkennung

  isProcessing = true;
  setText(inputEl, transformed);

  setTimeout(() => {
    const sendButton = getSendButton(inputEl);
    if (sendButton) sendButton.click();
    isProcessing = false;
  }, 50);
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