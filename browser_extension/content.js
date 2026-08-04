const INPUT_SELECTOR = 'div[contenteditable="true"][data-testid="chat-input"]';
const SETTLE_DELAY_MS = 1000;

let isProcessing = false;
let settleTimer = null;
let filterEnabled = true; // wird unten sofort aus dem Storage initialisiert

const vault = {
  "[REDACTED_PERSON_1]": "Frau Müller",
};

// Einmalig beim Laden den echten Wert holen
chrome.storage.local.get(["filterEnabled"], (result) => {
  filterEnabled = result.filterEnabled !== false;
  console.log("[PII Filter] Initialer Filter-Zustand:", filterEnabled);
});

// Bei jeder Änderung (z.B. Toggle im Popup) sofort synchron aktualisieren
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "local" && "filterEnabled" in changes) {
    filterEnabled = changes.filterEnabled.newValue !== false;
    console.log("[PII Filter] Filter-Zustand geaendert:", filterEnabled);
  }
});

function getInputElement() {
  return document.querySelector(INPUT_SELECTOR);
}

function getSendButton(inputEl) {
  let container = inputEl.closest('div[class*="relative"]')?.parentElement;
  if (!container) container = inputEl.parentElement?.parentElement?.parentElement;
  if (!container) return null;
  const buttons = container.querySelectorAll('button[data-cds="Button"]');
  return buttons[buttons.length - 1] || null;
}

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
  const transformed = originalText.toUpperCase();

  isProcessing = true;
  setText(inputEl, transformed);

  setTimeout(() => {
    const sendButton = getSendButton(inputEl);
    if (sendButton) sendButton.click();
    isProcessing = false;
  }, 50);
}

function deanonymizeLastMessage() {
  const messages = document.querySelectorAll('[data-testid="conversation-turn"]');
  if (messages.length === 0) return;

  const lastMessage = messages[messages.length - 1];
  const currentText = lastMessage.innerText;

  let replaced = currentText;
  let foundAny = false;
  for (const [placeholder, real] of Object.entries(vault)) {
    if (replaced.includes(placeholder)) {
      foundAny = true;
      replaced = replaced.replaceAll(placeholder, real);
    }
  }

  if (foundAny) {
    console.log("[PII Filter] Deanonymisiere Antwort:", replaced);
    lastMessage.innerText = replaced;
  }
}

const responseObserver = new MutationObserver(() => {
  clearTimeout(settleTimer);
  settleTimer = setTimeout(() => {
    if (filterEnabled) deanonymizeLastMessage();
  }, SETTLE_DELAY_MS);
});

responseObserver.observe(document.body, {
  childList: true,
  subtree: true,
  characterData: true,
});

document.addEventListener(
  "keydown",
  (event) => {
    if (isProcessing) return;
    if (!filterEnabled) return; // jetzt SYNCHRON, kein Warten mehr
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

console.log("[PII Filter] content.js geladen");