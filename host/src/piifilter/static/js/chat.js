let editingChatOriginal = null;

async function loadChatRules() {
  if (!currentChatId) {
    document.getElementById("noChatHint").style.display = "block";
    document.getElementById("chatSection").style.display = "none";
    return;
  }

  document.getElementById("chatHeading").textContent = `Regeln für: ${currentChatLabel}`;
  document.getElementById("noChatHint").style.display = "none";
  document.getElementById("chatSection").style.display = "block";

  const res = await fetch(`/chats/${encodeURIComponent(currentChatId)}`);
  const data = await res.json();
  const body = document.getElementById("chatBody");
  body.innerHTML = Object.entries(data.rules || {}).map(([o, f]) => {
    if (o === editingChatOriginal) {
      return `
        <tr>
          <td><input id="editChatOriginal" value="${o}"></td>
          <td><input id="editChatFake" value="${f}"></td>
          <td>
            <button onclick="saveChatRule('${o}')">Speichern</button>
            <button onclick="cancelEditChat()">Abbrechen</button>
          </td>
        </tr>
      `;
    }
    return `
      <tr>
        <td>${o}</td>
        <td>${f}</td>
        <td>
          <button onclick="editChatRule('${o}')">Bearbeiten</button>
          <button onclick="removeChatRule('${o}')">Löschen</button>
        </td>
      </tr>
    `;
  }).join("");
}

function editChatRule(original) {
  editingChatOriginal = original;
  loadChatRules();
}

function cancelEditChat() {
  editingChatOriginal = null;
  loadChatRules();
}

async function saveChatRule(oldOriginal) {
  const newOriginal = document.getElementById("editChatOriginal").value.trim();
  const newFake = document.getElementById("editChatFake").value.trim();
  if (!newOriginal || !newFake) return;

  if (newOriginal !== oldOriginal) {
    await fetch(`/chats/${encodeURIComponent(currentChatId)}/rules/${encodeURIComponent(oldOriginal)}`, { method: "DELETE" });
  }
  await fetch(`/chats/${encodeURIComponent(currentChatId)}/rules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ original: newOriginal, fake_value: newFake, label: currentChatLabel })
  });

  editingChatOriginal = null;
  loadChatRules();
}

async function addChatRule() {
  const original = document.getElementById("chatOriginal").value;
  const fake_value = document.getElementById("chatFake").value;
  if (!original || !fake_value || !currentChatId) return;
  await fetch(`/chats/${encodeURIComponent(currentChatId)}/rules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ original, fake_value, label: currentChatLabel })
  });
  document.getElementById("chatOriginal").value = "";
  document.getElementById("chatFake").value = "";
  loadChatRules();
}

async function removeChatRule(original) {
  await fetch(`/chats/${encodeURIComponent(currentChatId)}/rules/${encodeURIComponent(original)}`, {
    method: "DELETE"
  });
  loadChatRules();
}