/**
 * Gemeinsamer Zustand und Hilfsfunktionen fuer alle Content Scripts auf
 * claude.ai. Muss als erstes Script geladen werden (siehe manifest.json),
 * da intercept-send.js und deanonymize-response.js auf die hier
 * definierten Variablen/Funktionen zugreifen.
 */

const INPUT_SELECTOR = 'div[contenteditable="true"][data-testid="chat-input"]';

// true/false ob der Filter aktuell aktiv ist. Wird synchron in den
// Event-Handlern gelesen (siehe intercept-send.js) - deshalb eine
// normale Variable statt jedes Mal chrome.storage.local.get() aufzurufen,
// was asynchron ist und preventDefault() zu spaet auslösen wuerde.
let filterEnabled = true;

// wird von intercept-send.js zur Laufzeit befuellt
const vault = {};

// Einmalig beim Laden den echten gespeicherten Wert holen
chrome.storage.local.get(["filterEnabled"], (result) => {
  filterEnabled = result.filterEnabled !== false;
  console.log("[PII Filter] Initialer Filter-Zustand:", filterEnabled);
});

// Bei Aenderung im Popup sofort synchron nachziehen
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