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

// Persistenter Vault, pro Chat getrennt: { [chatId]: {placeholder: original} }
let vaults = {};

//Bei reload gespeicherte Werte aus vault auslesen
chrome.storage.local.get(["vaults"], (result) => {
  if (result.vaults) {
    vaults = result.vaults;
    logDebug("Vaults aus Storage geladen, Chats:", Object.keys(vaults).length);
  }
});

// Einmalig beim Laden den echten gespeicherten Wert holen
chrome.storage.local.get(["filterEnabled"], (result) => {
  filterEnabled = result.filterEnabled !== false;
  logDebug("Initialer Filter-Zustand:", filterEnabled);
});

// Bei Aenderung im Popup sofort synchron nachziehen
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "local" && "filterEnabled" in changes) {
    filterEnabled = changes.filterEnabled.newValue !== false;
    logDebug("Filter-Zustand geaendert:", filterEnabled);
  }
});


let deanonymizeEnabled = true;

chrome.storage.local.get(["deanonymizeEnabled"], (data) => {
  deanonymizeEnabled = data.deanonymizeEnabled !== false;
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "local" && "deanonymizeEnabled" in changes) {
    deanonymizeEnabled = changes.deanonymizeEnabled.newValue !== false;
  }
});

function getInputElement() {
  return document.querySelector(INPUT_SELECTOR);
}

function getSendButton(inputEl) {
  return document.querySelector('button[aria-label*="senden" i], button[aria-label*="send" i]');
}

function getChatId() {
  const match = window.location.pathname.match(/\/chat\/([a-f0-9-]+)/);
  return match ? match[1] : null;
}

function getVault(){
  const id = getChatId() || "unbekannt";
  if (!vaults[id]) vaults[id] = {};
  return vaults[id];
}

function saveVaults() {
  chrome.storage.local.set({vaults});
}