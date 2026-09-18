let editingGlobalOriginal = null;

async function loadGlobalRules() {
  const res = await fetch("/rules");
  const rules = await res.json();
  const body = document.getElementById("globalBody");
  body.innerHTML = Object.entries(rules).map(([o, f]) => {
    if (o === editingGlobalOriginal) {
      return `
        <tr>
          <td><input id="editGlobalOriginal" value="${o}"></td>
          <td><input id="editGlobalFake" value="${f}"></td>
          <td>
            <button onclick="saveGlobalRule('${o}')">Speichern</button>
            <button onclick="cancelEditGlobal()">Abbrechen</button>
          </td>
        </tr>
      `;
    }
    return `
      <tr>
        <td>${o}</td>
        <td>${f}</td>
        <td>
          <button onclick="editGlobalRule('${o}')">Bearbeiten</button>
          <button onclick="removeGlobalRule('${o}')">Löschen</button>
        </td>
      </tr>
    `;
  }).join("");
}

function editGlobalRule(original) {
  editingGlobalOriginal = original;
  loadGlobalRules();
}

function cancelEditGlobal() {
  editingGlobalOriginal = null;
  loadGlobalRules();
}

async function saveGlobalRule(oldOriginal) {
  const newOriginal = document.getElementById("editGlobalOriginal").value.trim();
  const newFake = document.getElementById("editGlobalFake").value.trim();
  if (!newOriginal || !newFake) return;

  if (newOriginal !== oldOriginal) {
    await fetch("/rules/" + encodeURIComponent(oldOriginal), { method: "DELETE" });
  }
  await fetch("/rules", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ original: newOriginal, fake_value: newFake })
  });

  editingGlobalOriginal = null;
  loadGlobalRules();
}

async function addGlobalRule() {
  const original = document.getElementById("globalOriginal").value;
  const fake_value = document.getElementById("globalFake").value;
  if (!original || !fake_value) return;
  await fetch("/rules", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ original, fake_value })
  });
  document.getElementById("globalOriginal").value = "";
  document.getElementById("globalFake").value = "";
  loadGlobalRules();
}

async function removeGlobalRule(original) {
  await fetch("/rules/" + encodeURIComponent(original), { method: "DELETE" });
  loadGlobalRules();
}