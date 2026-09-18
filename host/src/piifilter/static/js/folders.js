let editingFolderRule = null; // { folder, original }

async function loadFolders() {
  const res = await fetch("/folders");
  const folders = await res.json();
  const container = document.getElementById("foldersContainer");

  const entries = Object.entries(folders);
  if (entries.length === 0) {
    container.innerHTML = '<p class="hint">Noch keine Ordner angelegt.</p>';
    return;
  }

  container.innerHTML = entries.map(([name, data]) => `
    <div class="folder-card">
      <div class="folder-header">
        <span class="name">${name}</span>
        <span>
          <label>
            <input type="checkbox" ${data.enabled ? "checked" : ""}
                   onchange="toggleFolder('${name}', this.checked)">
            aktiv
          </label>
          <button onclick="deleteFolder('${name}')">Ordner löschen</button>
        </span>
      </div>
      <table>
        <thead><tr><th>Original</th><th>Fake-Wert</th><th></th></tr></thead>
        <tbody>
          ${Object.entries(data.rules).map(([o, f]) => {
            if (editingFolderRule && editingFolderRule.folder === name && editingFolderRule.original === o) {
              return `
                <tr>
                  <td><input id="editFolderOriginal_${name}" value="${o}"></td>
                  <td><input id="editFolderFake_${name}" value="${f}"></td>
                  <td>
                    <button onclick="saveFolderRule('${name}', '${o}')">Speichern</button>
                    <button onclick="cancelEditFolderRule()">Abbrechen</button>
                  </td>
                </tr>
              `;
            }
            return `
              <tr>
                <td>${o}</td>
                <td>${f}</td>
                <td>
                  <button onclick="editFolderRule('${name}', '${o}')">Bearbeiten</button>
                  <button onclick="removeFolderRule('${name}', '${o}')">Löschen</button>
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
      <input id="folderOriginal_${name}" placeholder="Original">
      <input id="folderFake_${name}" placeholder="Fake-Wert">
      <button onclick="addFolderRule('${name}')">Hinzufügen</button>
    </div>
  `).join("");
}

function editFolderRule(folder, original) {
  editingFolderRule = { folder, original };
  loadFolders();
}

function cancelEditFolderRule() {
  editingFolderRule = null;
  loadFolders();
}

async function saveFolderRule(folder, oldOriginal) {
  const newOriginal = document.getElementById(`editFolderOriginal_${folder}`).value.trim();
  const newFake = document.getElementById(`editFolderFake_${folder}`).value.trim();
  if (!newOriginal || !newFake) return;

  if (newOriginal !== oldOriginal) {
    await fetch(`/folders/${encodeURIComponent(folder)}/rules/${encodeURIComponent(oldOriginal)}`, { method: "DELETE" });
  }
  await fetch(`/folders/${encodeURIComponent(folder)}/rules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ original: newOriginal, fake_value: newFake })
  });

  editingFolderRule = null;
  loadFolders();
}

async function createFolder() {
  const nameInput = document.getElementById("newFolderName");
  const name = nameInput.value.trim();
  if (!name) return;
  await fetch("/folders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name })
  });
  nameInput.value = "";
  loadFolders();
}

async function deleteFolder(name) {
  await fetch("/folders/" + encodeURIComponent(name), { method: "DELETE" });
  loadFolders();
}

async function toggleFolder(name, enabled) {
  await fetch(`/folders/${encodeURIComponent(name)}/toggle`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled })
  });
  loadFolders();
}

async function addFolderRule(name) {
  const original = document.getElementById(`folderOriginal_${name}`).value;
  const fake_value = document.getElementById(`folderFake_${name}`).value;
  if (!original || !fake_value) return;
  await fetch(`/folders/${encodeURIComponent(name)}/rules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ original, fake_value })
  });
  loadFolders();
}

async function removeFolderRule(name, original) {
  await fetch(`/folders/${encodeURIComponent(name)}/rules/${encodeURIComponent(original)}`, {
    method: "DELETE"
  });
  loadFolders();
}