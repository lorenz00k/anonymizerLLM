const params = new URLSearchParams(window.location.search);
const currentChatId = params.get("id");
const currentChatLabel = params.get("label") || currentChatId;

function showTab(name) {
  for (const tab of ["global", "folders", "chat"]) {
    document.getElementById("tab" + capitalize(tab)).classList.toggle("active", tab === name);
    document.getElementById("tab" + capitalize(tab) + "Btn").classList.toggle("active", tab === name);
  }
}

function capitalize(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// Laeuft erst nachdem alle Scripts (global.js/folders.js/chat.js)
// geladen und ihre Funktionen definiert haben.
document.addEventListener("DOMContentLoaded", () => {
  loadGlobalRules();
  loadFolders();
  loadChatRules();
  showTab(params.get("scope") === "chat" ? "chat" : "global");
});