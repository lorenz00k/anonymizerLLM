const filterToggle = document.getElementById("filterToggle");

// Aktuellen Zustand beim Öffnen des Popups laden
chrome.storage.local.get(["filterEnabled"], (result) => {
  filterToggle.checked = result.filterEnabled !== false; // Standard: an
});

filterToggle.addEventListener("change", () => {
  chrome.storage.local.set({ filterEnabled: filterToggle.checked });
  logInfo("[PII Filter] Filter", filterToggle.checked ? "aktiviert" : "deaktiviert");
});

const deanonymizeToggle = document.getElementById("deanonymizeToggle");

chrome.storage.local.get(["deanonymizeEnabled"], (result) => {
  deanonymizeToggle.checked = result.deanonymizeEnabled !== false; // Standard: an
});

deanonymizeToggle.addEventListener("change", () => {
  chrome.storage.local.set({ deanonymizeEnabled: deanonymizeToggle.checked });
  logInfo("[PII Filter] Rückübersetzen", deanonymizeToggle.checked ? "aktiviert" : "deaktiviert");
});

const llmToggle = document.getElementById("llmToggle");

chrome.storage.local.get(["llmEnabled"], (result) => {
  llmToggle.checked = result.llmEnabled === true; // Standard: aus
});

llmToggle.addEventListener("change", () => {
  chrome.storage.local.set({ llmEnabled: llmToggle.checked });
  logInfo("[PII Filter] KI-Erkennung", llmToggle.checked ? "aktiviert" : "deaktiviert");
});

document.getElementById("openRulesUi").addEventListener("click", () => {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const tab = tabs[0];
    const match = tab.url ? tab.url.match(/\/chat\/([a-f0-9-]+)/) : null;
    const chatId = match ? match[1] : null;

    let url = "http://127.0.0.1:8756";
    if (chatId) {
      const label = encodeURIComponent(tab.title || chatId);
      url += `?scope=chat&id=${chatId}&label=${label}`;
    }

    chrome.tabs.create({ url });
  });
});