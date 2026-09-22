/**
 * Kleine, wiederverwendbare DOM-/Text-Helfer ohne eigenen Zustand.
 * Kennt weder den Host noch das Review-Panel - nur generische DOM-Arbeit.
 */

function setText(inputEl, newText) {
  inputEl.focus();
  const selection = window.getSelection();
  const range = document.createRange();
  range.selectNodeContents(inputEl);
  selection.removeAllRanges();
  selection.addRange(range);
  document.execCommand("insertText", false, newText);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function showInlineError(inputEl, message) {
  const original = inputEl.style.outline;
  inputEl.style.outline = "2px solid #dc2626";

  let hint = document.getElementById("pii-filter-error-hint");
  if (!hint) {
    hint = document.createElement("div");
    hint.id = "pii-filter-error-hint";
    hint.style.cssText = `
      position: absolute;
      background: #dc2626;
      color: white;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 12px;
      z-index: 9999;
    `;
    document.body.appendChild(hint);
  }

  const rect = inputEl.getBoundingClientRect();
  hint.style.top = `${rect.top - 30}px`;
  hint.style.left = `${rect.left}px`;
  hint.textContent = message;
  hint.style.display = "block";

  setTimeout(() => {
    inputEl.style.outline = original;
    hint.style.display = "none";
  }, 3000);
}