const filterToggle = document.getElementById("filterToggle");

// Aktuellen Zustand beim Öffnen des Popups laden
chrome.storage.local.get(["filterEnabled"], (result) => {
  filterToggle.checked = result.filterEnabled !== false; // Standard: an
});

filterToggle.addEventListener("change", () => {
  chrome.storage.local.set({ filterEnabled: filterToggle.checked });
  console.log("[PII Filter] Filter", filterToggle.checked ? "aktiviert" : "deaktiviert");
  isFilterEnabled((enabled) => {
    console.log("[PII Filter] Enabled-Wert beim Enter-Druck:", enabled);
    if (!enabled) return;
    event.preventDefault();
    event.stopPropagation();
    processAndResend(inputEl);
  });
});


document.getElementById("send").addEventListener("click", () => {
  const text = document.getElementById("input").value;
  const statusEl = document.getElementById("status");
  const outputEl = document.getElementById("output");

  statusEl.textContent = "Sende an lokale App...";
  outputEl.textContent = "";

  chrome.runtime.sendMessage({ type: "PROCESS_TEXT", text }, (response) => {
    if (chrome.runtime.lastError) {
      statusEl.textContent = "Fehler: " + chrome.runtime.lastError.message;
      return;
    }
    if (response && response.ok) {
      outputEl.textContent = response.result;
      statusEl.textContent = "OK - Antwort von der lokalen App erhalten.";
    } else {
      statusEl.textContent = "Fehler: " + (response ? response.error : "keine Antwort");
    }
  });
});