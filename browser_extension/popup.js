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