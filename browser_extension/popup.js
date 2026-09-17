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

document.getElementById("openRulesUi").addEventListener("click", () => {
  chrome.tabs.create({ url: "http://127.0.0.1:8756" });
});