/** Чат (первая вкладка): имя, роль, история, сообщения */
(function () {
  const API = "/api/v1";
  const SESSION_KEY = "mkg_user_session";
  const $ = (id) => document.getElementById(id);

  let roles = [];
  let currentUser = null;
  let threads = [];
  let activeThreadId = null;
  let agentModes = [];
  let selectedAgentMode = null;
  let selectedRoleId = "researcher";
  let pollTimer = null;

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function roleMeta(roleId) {
    return roles.find((r) => r.id === roleId) || { name_ru: roleId, id: roleId };
  }

  function loadSession() {
    try {
      const raw = localStorage.getItem(SESSION_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  function showNotice(msg, isError = false) {
    const el = $("chatIdentityStatus");
    if (!el) return;
    if (!msg) {
      el.textContent = "";
      el.classList.remove("chat-notice-error");
      return;
    }
    el.textContent = msg;
    el.classList.toggle("chat-notice-error", isError);
  }

  function saveSession(user) {
    currentUser = user;
    selectedRoleId = user.role_id;
    localStorage.setItem(SESSION_KEY, JSON.stringify(user));
    updateIdentityUI();
    applyPermissions();
    renderRoleCards();
    showNotice("");
  }

  function updateIdentityUI() {
    const status = $("chatIdentityStatus");
    const nameInput = $("chatUserName");
    if (currentUser) {
      if (nameInput) nameInput.value = currentUser.display_name;
      const role = roleMeta(currentUser.role_id);
      if (status) {
        status.innerHTML = `<span class="user-role-badge role-${esc(currentUser.role_id)}">${esc(role.name_ru)}</span>`;
        status.classList.remove("chat-notice-error");
      }
    } else if (status && !status.classList.contains("chat-notice-error")) {
      status.textContent = "Выберите роль";
    }
  }

  function renderRoleCards() {
    const grid = $("roleCardGrid");
    if (!grid) return;
    if (!roles.length) {
      grid.innerHTML = '<span class="muted small">Роли недоступны — перезагрузите страницу</span>';
      return;
    }
    const activeId = currentUser?.role_id || selectedRoleId;
    grid.innerHTML = roles.map((ro) => {
      const active = activeId === ro.id ? " active" : "";
      return `
        <button type="button" class="role-card role-card-compact role-${esc(ro.id)}${active}" data-role="${esc(ro.id)}" title="${esc(ro.description || "")}">
          <span class="role-card-name">${esc(ro.name_ru)}</span>
        </button>`;
    }).join("");
    grid.querySelectorAll(".role-card").forEach((btn) => {
      btn.addEventListener("click", () => {
        selectedRoleId = btn.dataset.role;
        renderRoleCards();
        loginWithRole(btn.dataset.role);
      });
    });
  }

  function applyPermissions() {
    if (!currentUser) return;
    const role = roleMeta(currentUser.role_id);
    const uploadPanel = document.getElementById("homeTabUpload");
    const uploadBtn = $("uploadBtn");
    const clearBtn = $("clearDbBtn");
    const homeRun = $("homeAgentRunBtn");
    if (uploadPanel) uploadPanel.style.display = role.can_upload === false ? "none" : "";
    if (uploadBtn && role.can_upload === false) uploadBtn.disabled = true;
    if (clearBtn) clearBtn.style.display = role.can_admin ? "" : "none";
    if (homeRun) homeRun.disabled = role.can_run_agents === false;
    const homeTabUploadBtn = document.querySelector('.home-tab[data-home-tab="upload"]');
    if (homeTabUploadBtn && role.can_upload === false) {
      homeTabUploadBtn.classList.add("hidden");
      if (window.MKG?.switchHomeTab) window.MKG.switchHomeTab("query");
    } else {
      homeTabUploadBtn?.classList.remove("hidden");
    }
  }

  async function fetchRoles() {
    try {
      const r = await fetch(`${API}/roles`);
      if (!r.ok) throw new Error("roles unavailable");
      const data = await r.json();
      roles = data.roles || [];
      renderRoleCards();
    } catch {
      const grid = $("roleCardGrid");
      if (grid) grid.innerHTML = '<span class="muted small chat-notice-error">Не удалось загрузить роли</span>';
    }
  }

  async function loginWithRole(roleId) {
    const name = ($("chatUserName")?.value || "").trim();
    if (!name) {
      showNotice("Введите имя", true);
      $("chatUserName")?.focus();
      $("chatUserName")?.classList.add("input-error");
      setTimeout(() => $("chatUserName")?.classList.remove("input-error"), 1500);
      return false;
    }
    try {
      const r = await fetch(`${API}/users/session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ display_name: name, role_id: roleId }),
      });
      if (!r.ok) {
        const data = await r.json().catch(() => ({}));
        showNotice(data.detail || "Ошибка входа", true);
        return false;
      }
      saveSession(await r.json());
      await loadThreads();
      return true;
    } catch (e) {
      showNotice(e.message || "Ошибка сети", true);
      return false;
    }
  }

  async function requireIdentity() {
    if (currentUser) return true;
    const name = ($("chatUserName")?.value || "").trim();
    if (!name) {
      showNotice("Введите имя и выберите роль", true);
      $("chatUserName")?.focus();
      return false;
    }
    return loginWithRole(selectedRoleId || "researcher");
  }

  async function restoreSession() {
    const saved = loadSession();
    if (!saved?.display_name || !saved?.role_id) return;
    selectedRoleId = saved.role_id;
    try {
      const r = await fetch(`${API}/users/session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(saved),
      });
      if (r.ok) saveSession(await r.json());
    } catch { /* ignore */ }
  }

  async function loadThreads() {
    try {
      const r = await fetch(`${API}/chat/threads`);
      if (!r.ok) return;
      const data = await r.json();
      threads = data.items || [];
      renderThreadList();
      if (!activeThreadId && threads.length) {
        activeThreadId = threads[0].id;
        await loadMessages(activeThreadId);
      }
    } catch { /* ignore */ }
  }

  function renderThreadList() {
    const el = $("chatThreadList");
    if (!el) return;
    if (!threads.length) {
      el.innerHTML = '<p class="muted small">Пока нет чатов — нажмите «+ Новый»</p>';
      return;
    }
    el.innerHTML = threads.map((t) => `
      <button type="button" class="chats-thread-item ${t.id === activeThreadId ? "active" : ""}" data-id="${esc(t.id)}">
        <span class="chats-thread-title">${esc(t.title)}</span>
        <span class="muted chats-thread-meta">${t.message_count || 0} сообщ.</span>
      </button>`).join("");
    el.querySelectorAll(".chats-thread-item").forEach((btn) => {
      btn.addEventListener("click", () => {
        activeThreadId = btn.dataset.id;
        renderThreadList();
        loadMessages(activeThreadId);
      });
    });
  }

  async function loadMessages(threadId) {
    if (!threadId) return;
    try {
      const r = await fetch(`${API}/chat/threads/${encodeURIComponent(threadId)}/messages`);
      if (!r.ok) return;
      const data = await r.json();
      renderMessages(data.items || []);
      const t = threads.find((x) => x.id === threadId);
      if ($("chatActiveTitle") && t) $("chatActiveTitle").textContent = t.title;
    } catch { /* ignore */ }
  }

  function renderMessages(items) {
    const el = $("chatMessages");
    if (!el) return;
    if (!items.length) {
      el.innerHTML = '<p class="muted">Напишите первое сообщение…</p>';
      return;
    }
    el.innerHTML = items.map((m) => {
      const role = roleMeta(m.author_role);
      const cls = m.msg_type === "agent" ? "msg-agent" : m.msg_type === "system" ? "msg-system" : "";
      const time = m.created_at ? new Date(m.created_at).toLocaleString("ru-RU") : "";
      return `
        <article class="chat-msg ${cls}">
          <header>
            <strong>${esc(m.author_name)}</strong>
            <span class="user-role-badge role-${esc(m.author_role)}">${esc(role.name_ru || m.author_role)}</span>
            <span class="chat-msg-time">${esc(time)}</span>
          </header>
          <div class="chat-msg-body">${esc(m.body)}</div>
        </article>`;
    }).join("");
    el.scrollTop = el.scrollHeight;
  }

  async function createThread(kind) {
    const btn = kind === "agent" ? $("chatNewAgentBtn") : $("chatNewBtn");
    const prevText = btn?.textContent;
    if (btn) { btn.disabled = true; btn.textContent = "…"; }
    try {
      if (!await requireIdentity()) return;
      const n = threads.filter((t) => t.kind === kind).length + 1;
      const title = kind === "agent" ? `Агент ${n}` : `Чат ${n}`;
      const r = await fetch(`${API}/chat/threads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, kind, created_by: currentUser.id }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        showNotice(data.detail || "Не удалось создать чат", true);
        return;
      }
      activeThreadId = data.id;
      if ($("chatActiveTitle")) $("chatActiveTitle").textContent = data.title;
      await loadThreads();
      await loadMessages(activeThreadId);
      $("chatMessageInput")?.focus();
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = prevText; }
    }
  }

  async function sendChatMessage() {
    const input = $("chatMessageInput");
    const text = (input?.value || "").trim();
    if (!text) return;
    const btn = $("chatSendBtn");
    if (btn) btn.disabled = true;
    try {
      if (!await requireIdentity()) return;
      if (!activeThreadId) {
        await createThread("team");
        if (!activeThreadId) return;
      }
      input.value = "";
      const r = await fetch(`${API}/chat/threads/${encodeURIComponent(activeThreadId)}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          author_id: currentUser.id,
          author_name: currentUser.display_name,
          author_role: currentUser.role_id,
          body: text,
          msg_type: "user",
        }),
      });
      if (!r.ok) {
        const data = await r.json().catch(() => ({}));
        showNotice(data.detail || "Не удалось отправить", true);
        input.value = text;
        return;
      }
      await loadMessages(activeThreadId);
      await loadThreads();
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function renderModeChips() {
    const grid = $("homeAgentModes");
    if (!grid) return;
    if (!agentModes.length) {
      grid.innerHTML = '<span class="muted small">Режимы agents недоступны</span>';
      return;
    }
    if (!selectedAgentMode) selectedAgentMode = agentModes[0].id;
    grid.innerHTML = agentModes.map((m) =>
      `<button type="button" class="mode-chip ${m.id === selectedAgentMode ? "active" : ""}" data-mode="${esc(m.id)}" title="${esc(m.description || "")}">${esc(m.title)}</button>`,
    ).join("");
    grid.querySelectorAll(".mode-chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        selectedAgentMode = btn.dataset.mode;
        renderModeChips();
      });
    });
  }

  function setAgentStatus(text) {
    const el = $("homeAgentStatus");
    if (el) el.textContent = text;
  }

  async function loadAgentModes() {
    try {
      const r = await fetch(`${API}/agents-service/modes`);
      if (!r.ok) throw new Error("offline");
      const data = await r.json();
      agentModes = data.modes || [];
      renderModeChips();
      setAgentStatus("Agents: online");
    } catch {
      agentModes = [];
      renderModeChips();
      setAgentStatus("Agents: offline");
    }
  }

  function formatAgentResult(data, query) {
    return [
      data.summary || "",
      data.warnings?.length ? `\n\n⚠ ${data.warnings.join("\n")}` : "",
      data.hypotheses?.length
        ? `\n\nГипотезы:\n${data.hypotheses.map((h, i) => `${i + 1}. ${h.title || h.text || JSON.stringify(h)}`).join("\n")}`
        : "",
      data.recommendations?.length
        ? `\n\nРекомендации:\n${data.recommendations.map((x, i) => `${i + 1}. ${x.title || x.text || JSON.stringify(x)}`).join("\n")}`
        : "",
    ].join("") || JSON.stringify(data, null, 2) || query;
  }

  async function runAgentQuery() {
    const query = ($("homeAgentQuery")?.value || "").trim();
    if (!query) return;
    if (!await requireIdentity()) {
      window.MKG?.switchPage?.("chats");
      return;
    }
    const role = roleMeta(currentUser.role_id);
    if (role.can_run_agents === false) {
      window.MKG?.switchPage?.("chats");
      showNotice("Эта роль не может запускать агентов", true);
      return;
    }
    const out = $("homeAgentResult");
    const btn = $("homeAgentRunBtn");
    if (btn) { btn.disabled = true; btn.textContent = "Думаю…"; }
    if (out) { out.textContent = "Запрос к LangGraph agents…"; out.classList.remove("empty"); }
    try {
      const docIds = window.MKG?.selectedDoc ? [window.MKG.selectedDoc] : [];
      const r = await fetch(`${API}/agents-service/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          mode: selectedAgentMode,
          doc_ids: docIds,
          user_role: role.agents_user_role || currentUser.role_id,
          limit: 5,
        }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "agent error");
      const summary = formatAgentResult(data, query);
      if (out) out.textContent = summary;
      if (!activeThreadId) await createThread("agent");
      if (activeThreadId) {
        await fetch(`${API}/chat/threads/${encodeURIComponent(activeThreadId)}/messages`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            author_id: currentUser.id,
            author_name: currentUser.display_name,
            author_role: currentUser.role_id,
            body: query,
            msg_type: "user",
          }),
        });
        await fetch(`${API}/chat/threads/${encodeURIComponent(activeThreadId)}/messages`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            author_id: null,
            author_name: "MKG Agents",
            author_role: currentUser.role_id,
            body: summary,
            msg_type: "agent",
            meta: { elapsed_ms: data.elapsed_ms, mode: data.mode },
          }),
        });
        window.MKG?.switchPage?.("chats");
        await loadMessages(activeThreadId);
        await loadThreads();
      }
    } catch (e) {
      if (out) out.textContent = `Ошибка: ${e.message}`;
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = "Спросить"; }
    }
  }

  async function refreshChatsPage() {
    await restoreSession();
    updateIdentityUI();
    await loadThreads();
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(() => {
      if (window.MKG?.currentPage === "chats" && activeThreadId) {
        loadMessages(activeThreadId);
        loadThreads();
      }
    }, 3000);
  }

  function bindEvents() {
    $("chatNewBtn")?.addEventListener("click", (e) => {
      e.preventDefault();
      createThread("team");
    });
    $("chatNewAgentBtn")?.addEventListener("click", (e) => {
      e.preventDefault();
      createThread("agent");
    });
    $("chatSendBtn")?.addEventListener("click", (e) => {
      e.preventDefault();
      sendChatMessage();
    });
    $("chatMessageInput")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChatMessage(); }
    });
    $("homeAgentRunBtn")?.addEventListener("click", runAgentQuery);
    $("homeAgentQuery")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); runAgentQuery(); }
    });
    $("chatUserName")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const active = $("roleCardGrid")?.querySelector(".role-card.active")
          || $("roleCardGrid")?.querySelector(".role-card");
        if (active) active.click();
      }
    });
  }

  bindEvents();

  async function init() {
    await fetchRoles();
    const saved = loadSession();
    if (saved?.display_name && $("chatUserName")) {
      $("chatUserName").value = saved.display_name;
    }
    if (saved?.role_id) selectedRoleId = saved.role_id;
    await restoreSession();
    updateIdentityUI();
    applyPermissions();
    await loadAgentModes();
    await refreshChatsPage();
  }

  window.MKGAuth = {
    init,
    refreshChatsPage,
    requireIdentity,
    getCurrentUser: () => currentUser,
    getRole: () => roleMeta(currentUser?.role_id),
    applyPermissions,
  };
})();
