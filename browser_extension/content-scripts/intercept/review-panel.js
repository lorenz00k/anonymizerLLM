/**
 * Reines Rendering des Review-Panels. Kennt die Form eines "review"-Objekts
 * ({ phase1Items, phase2Items, phase2Status, inputEl }), aber NICHT wie
 * dieser Zustand entsteht oder veraendert wird - Aenderungen laufen
 * ausschliesslich ueber die uebergebenen `handlers`-Callbacks.
 *
 * handlers:
 *   onAcceptAll()               - "Alle akzeptieren" geklickt
 *   onToggle(item, accepted)    - eine einzelne Checkbox geaendert
 *   onSend()                    - "Senden" geklickt (nur aktiv wenn nicht wartend)
 *   onSkipLlm()                 - "Trotzdem jetzt senden" geklickt
 */

function removeReviewPanel() {
  const existing = document.getElementById("pii-filter-review-panel");
  if (existing) existing.remove();
}

function reviewHasAnythingToShow(review) {
  return review.phase1Items.length > 0 || review.phase2Items.length > 0 || review.phase2Status === "pending";
}

function renderReviewPanel(review, handlers) {
  removeReviewPanel();
  if (!review || !reviewHasAnythingToShow(review)) return;

  const { phase1Items, phase2Items, phase2Status, inputEl } = review;

  const panel = document.createElement("div");
  panel.id = "pii-filter-review-panel";
  panel.style.cssText = `
    position: absolute;
    z-index: 9999;
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.15);
    padding: 12px;
    width: 340px;
    max-height: 400px;
    overflow-y: auto;
    font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    font-size: 13px;
    color: #1f1f1f;
  `;

  const rect = inputEl.getBoundingClientRect();
  panel.style.left = `${rect.left}px`;
  panel.style.bottom = `${window.innerHeight - rect.top + 8}px`;

  panel.appendChild(renderPanelTitle(handlers));
  phase1Items.forEach((item) => panel.appendChild(renderReviewItem(item, "Filter", handlers)));
  phase2Items.forEach((item) => panel.appendChild(renderReviewItem(item, "LLM", handlers)));

  if (phase2Status === "pending") {
    panel.appendChild(renderPendingHint());
  }

  panel.appendChild(renderActions(phase2Status, handlers));

  document.body.appendChild(panel);
}

function renderPanelTitle(handlers) {
  const title = document.createElement("div");
  title.style.cssText = "font-weight:600;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;gap:6px;";
  title.innerHTML = `<span>Gefundene sensible Stellen</span>`;

  const buttonGroup = document.createElement("div");
  buttonGroup.style.cssText = "display:flex;gap:6px;";

  const rescanBtn = document.createElement("button");
  rescanBtn.textContent = "Neu überprüfen";
  rescanBtn.title = "Aktuellen Text erneut scannen (z.B. nach eigenen Aenderungen im Vorschau-Text)";
  rescanBtn.style.cssText = "font-size:11px;padding:3px 8px;border:1px solid #ddd;border-radius:4px;background:#f7f7f7;cursor:pointer;";
  rescanBtn.addEventListener("click", handlers.onRescan);
  buttonGroup.appendChild(rescanBtn);

  const acceptAllBtn = document.createElement("button");
  acceptAllBtn.textContent = "Alle akzeptieren";
  acceptAllBtn.style.cssText = "font-size:11px;padding:3px 8px;border:1px solid #ddd;border-radius:4px;background:#f7f7f7;cursor:pointer;";
  acceptAllBtn.addEventListener("click", handlers.onAcceptAll);
  buttonGroup.appendChild(acceptAllBtn);

  title.appendChild(buttonGroup);
  return title;
}

function renderReviewItem(item, sourceLabel, handlers) {
  const row = document.createElement("label");
  row.style.cssText = "display:flex;align-items:flex-start;gap:6px;padding:4px 0;border-bottom:1px solid #f0f0f0;cursor:pointer;";

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = item.accepted;
  checkbox.style.marginTop = "2px";
  checkbox.addEventListener("change", () => handlers.onToggle(item, checkbox.checked));

  const replacementValue = item.suggestedReplacement || item.placeholder;

  const text = document.createElement("div");
  text.style.flex = "1";
  text.innerHTML = `<div style="color:#666;font-size:11px;">${sourceLabel}${item.category ? " · " + item.category : ""}</div>
                     <div>${escapeHtml(item.original)}</div>
                     ${replacementValue ? `<div style="color:#4f46e5;font-size:11px;margin-top:2px;">→ ${escapeHtml(replacementValue)}</div>` : ""}
                     ${item.reason ? `<div style="color:#888;font-size:11px;margin-top:1px;">${escapeHtml(item.reason)}</div>` : ""}`;

  row.appendChild(checkbox);
  row.appendChild(text);

  if (sourceLabel === "LLM") {
    const retryBtn = document.createElement("button");
    retryBtn.textContent = "🔄";
    retryBtn.title = "Neu umformulieren";
    retryBtn.style.cssText = "border:none;background:none;cursor:pointer;font-size:13px;padding:0 2px;align-self:flex-start;";
    retryBtn.addEventListener("click", (e) => {
      // row ist ein <label> um die Checkbox - ohne preventDefault wuerde
      // der Klick auf den Button gleichzeitig die Checkbox toggeln.
      e.preventDefault();
      e.stopPropagation();
      handlers.onRetryRewrite(item);
    });
    row.appendChild(retryBtn);
  }

  return row;
}

function renderPendingHint() {
  const loading = document.createElement("div");
  loading.style.cssText = "padding:6px 0;color:#888;font-size:12px;";
  loading.textContent = "Prüfe auf weitere sensible Stellen …";
  return loading;
}

function renderActions(phase2Status, handlers) {
  const actions = document.createElement("div");
  actions.style.cssText = "display:flex;justify-content:space-between;align-items:center;margin-top:10px;";

  const waitingForLlm = phase2Status === "pending";

  const sendBtn = document.createElement("button");
  sendBtn.textContent = waitingForLlm ? "Warte auf LLM-Prüfung …" : "Senden";
  sendBtn.disabled = waitingForLlm;
  sendBtn.style.cssText = `
    padding:6px 14px;border:none;border-radius:6px;font-size:13px;cursor:${waitingForLlm ? "default" : "pointer"};
    background:${waitingForLlm ? "#ccc" : "#4f46e5"};color:white;
  `;
  sendBtn.addEventListener("click", () => {
    if (!waitingForLlm) handlers.onSend();
  });
  actions.appendChild(sendBtn);

  if (waitingForLlm) {
    const overrideLink = document.createElement("a");
    overrideLink.textContent = "Trotzdem jetzt senden";
    overrideLink.href = "#";
    overrideLink.style.cssText = "font-size:12px;color:#666;text-decoration:underline;";
    overrideLink.addEventListener("click", (e) => {
      e.preventDefault();
      handlers.onSkipLlm();
    });
    actions.appendChild(overrideLink);
  }

  return actions;
}