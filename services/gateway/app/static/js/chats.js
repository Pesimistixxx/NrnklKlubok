/** Чат: роль + AI-режим + история */
(function () {
  const API = "/api/v1";
  const SESSION_KEY = "mkg_user_session";
  const $ = (id) => document.getElementById(id);

  const FALLBACK_ROLES = [
    { id: "researcher", name_ru: "Исследователь", can_run_agents: true },
    { id: "analyst", name_ru: "Аналитик", can_run_agents: true },
    { id: "validator", name_ru: "Валидатор", can_run_agents: true },
    { id: "engineer", name_ru: "Инженер", can_run_agents: false },
    { id: "admin", name_ru: "Администратор", can_run_agents: true },
    { id: "viewer", name_ru: "Наблюдатель", can_run_agents: false },
  ];

  const FALLBACK_AGENT_MODES = [
    { id: null, title: "Диалог", description: "Быстрый ответ LLM по роли" },
    { id: "hypothesis_mode", title: "Гипотезы", description: "Гипотезы и связи" },
    { id: "audit_mode", title: "Аудит", description: "Проверка фактов" },
    { id: "literature_review_mode", title: "Обзор", description: "Обзор литературы" },
    { id: "recommendation_mode", title: "Советы", description: "Рекомендации" },
  ];

  let roles = [...FALLBACK_ROLES];
  let agentModes = [...FALLBACK_AGENT_MODES];
  let currentUser = null;
  let threads = [];
  let activeThreadId = null;
  let selectedAgentMode = null;
  let selectedRoleId = null;
  let pollTimer = null;
  let rolePromptData = null;

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function roleMeta(roleId) {
    return roles.find((r) => r.id === roleId) || FALLBACK_ROLES.find((r) => r.id === roleId) || { id: roleId, name_ru: roleId };
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
      el.classList.add("hidden");
      el.classList.remove("chat-notice-error");
      return;
    }
    el.textContent = msg;
    el.classList.remove("hidden");
    el.classList.toggle("chat-notice-error", isError);
  }

  function saveSession(user) {
    currentUser = user;
    selectedRoleId = user.role_id;
    localStorage.setItem(SESSION_KEY, JSON.stringify(user));
    renderRoleCards();
    applyPermissions();
    showNotice("");
    togglePromptPanel(true);
    loadRolePrompt(user.role_id);
  }

  function togglePromptPanel(show) {
    const panel = $("rolePromptPanel");
    if (panel) panel.classList.toggle("hidden", !show);
  }

  function updatePromptBadge() {
    const badge = $("rolePromptBadge");
    if (!badge) return;
    if (!rolePromptData) {
      badge.textContent = "";
      return;
    }
    badge.textContent = rolePromptData.is_custom ? "· изменён" : "· по умолчанию";
  }

  async function loadRolePrompt(roleId) {
    const textarea = $("rolePromptText");
    if (!roleId || !textarea) return;
    try {
      const r = await fetch(`${API}/roles/${encodeURIComponent(roleId)}/prompt`);
      if (!r.ok) return;
      rolePromptData = await r.json();
      textarea.value = rolePromptData.system_prompt || "";
      updatePromptBadge();
    } catch { /* ignore */ }
  }

  async function saveRolePrompt() {
    if (!currentUser?.role_id) {
      showNotice("Сначала выберите роль", true);
      return;
    }
    const text = ($("rolePromptText")?.value || "").trim();
    if (!text) {
      showNotice("Промпт не может быть пустым", true);
      return;
    }
    const btn = $("rolePromptSave");
    const prev = btn?.textContent;
    if (btn) { btn.disabled = true; btn.textContent = "…"; }
    try {
      const r = await fetch(`${API}/roles/${encodeURIComponent(currentUser.role_id)}/prompt`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ system_prompt: text }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        showNotice(data.detail || "Не удалось сохранить промпт", true);
        return;
      }
      rolePromptData = data;
      updatePromptBadge();
      showNotice("Промпт сохранён");
      setTimeout(() => showNotice(""), 2000);
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = prev; }
    }
  }

  async function resetRolePrompt() {
    if (!currentUser?.role_id) return;
    const btn = $("rolePromptReset");
    const prev = btn?.textContent;
    if (btn) { btn.disabled = true; btn.textContent = "…"; }
    try {
      const r = await fetch(`${API}/roles/${encodeURIComponent(currentUser.role_id)}/prompt`, {
        method: "DELETE",
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        showNotice(data.detail || "Не удалось сбросить", true);
        return;
      }
      rolePromptData = data;
      if ($("rolePromptText")) $("rolePromptText").value = data.system_prompt || "";
      updatePromptBadge();
      showNotice("Промпт по умолчанию");
      setTimeout(() => showNotice(""), 2000);
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = prev; }
    }
  }

  function renderRoleCards() {
    const grid = $("roleCardGrid");
    if (!grid) return;
    const activeId = currentUser?.role_id || selectedRoleId;
    grid.innerHTML = roles.map((ro) => {
      const active = activeId === ro.id ? " active" : "";
      return `<button type="button" class="chip role-chip role-${esc(ro.id)}${active}" data-role="${esc(ro.id)}" title="${esc(ro.description || "")}">${esc(ro.name_ru)}</button>`;
    }).join("");
    grid.querySelectorAll(".chip[data-role]").forEach((btn) => {
      btn.addEventListener("click", () => loginWithRole(btn.dataset.role));
    });
  }

  function renderChatAgentModes() {
    const grid = $("chatAgentModes");
    if (!grid) return;
    grid.innerHTML = agentModes.map((m) => {
      const id = m.id || "";
      const active = (selectedAgentMode || "") === (id || "") ? " active" : "";
      return `<button type="button" class="chip agent-chip${active}" data-mode="${esc(id)}" title="${esc(m.description || "")}">${esc(m.title)}</button>`;
    }).join("");
    grid.querySelectorAll(".agent-chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        selectedAgentMode = btn.dataset.mode || null;
        renderChatAgentModes();
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
    if (role.can_run_agents === false && selectedAgentMode) {
      selectedAgentMode = null;
      renderChatAgentModes();
    }
  }

  async function fetchRoles() {
    try {
      const r = await fetch(`${API}/roles`);
      if (!r.ok) return;
      const data = await r.json();
      if (data.roles?.length) {
        roles = data.roles;
        renderRoleCards();
      }
    } catch { /* fallback ok */ }
  }

  async function fetchAgentModes() {
    const status = $("chatAgentStatus");
    try {
      const r = await fetch(`${API}/agents-service/modes`);
      if (!r.ok) throw new Error("offline");
      const data = await r.json();
      const fromApi = (data.modes || []).map((m) => ({
        id: m.id,
        title: AGENT_MODE_RU[m.id] || m.title,
        description: m.description || "",
      }));
      agentModes = [{ id: null, title: "Диалог", description: "Быстрый ответ LLM" }, ...fromApi];
      if (status) status.textContent = "LangGraph online";
      renderChatAgentModes();
      renderModeChips();
    } catch {
      agentModes = [...FALLBACK_AGENT_MODES];
      if (status) status.textContent = "LangGraph offline";
      renderChatAgentModes();
    }
  }

  const AGENT_MODE_RU = {
    audit_mode: "Аудит",
    hypothesis_mode: "Гипотезы",
    literature_review_mode: "Обзор",
    recommendation_mode: "Советы",
  };

  async function loginWithRole(roleId) {
    selectedRoleId = roleId;
    const saved = loadSession();
    try {
      const r = await fetch(`${API}/users/session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role_id: roleId, user_id: saved?.id || undefined }),
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
    if (!selectedRoleId) {
      showNotice("Сначала выберите роль", true);
      return false;
    }
    return loginWithRole(selectedRoleId);
  }

  async function restoreSession() {
    const saved = loadSession();
    if (!saved?.role_id) return;
    selectedRoleId = saved.role_id;
    try {
      const r = await fetch(`${API}/users/session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role_id: saved.role_id, user_id: saved.id }),
      });
      if (r.ok) {
        saveSession(await r.json());
      } else {
        togglePromptPanel(false);
      }
    } catch {
      togglePromptPanel(false);
    }
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
      el.innerHTML = '<p class="muted small">Нет чатов</p>';
      return;
    }
    el.innerHTML = threads.map((t) => `
      <div class="chats-thread-row">
        <button type="button" class="chats-thread-item ${t.id === activeThreadId ? "active" : ""}" data-id="${esc(t.id)}">
          <span class="chats-thread-title">${esc(t.title)}</span>
          <span class="muted chats-thread-meta">${t.message_count || 0}</span>
        </button>
        <button type="button" class="chats-thread-delete" data-id="${esc(t.id)}" title="Удалить чат" aria-label="Удалить чат">×</button>
      </div>`).join("");
    el.querySelectorAll(".chats-thread-item").forEach((btn) => {
      btn.addEventListener("click", () => {
        activeThreadId = btn.dataset.id;
        renderThreadList();
        loadMessages(activeThreadId);
      });
    });
    el.querySelectorAll(".chats-thread-delete").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        deleteThread(btn.dataset.id);
      });
    });
  }

  async function deleteThread(threadId) {
    if (!threadId) return;
    if (!confirm("Удалить этот чат? Сообщения будут удалены безвозвратно.")) return;
    try {
      const r = await fetch(`${API}/chat/threads/${encodeURIComponent(threadId)}`, { method: "DELETE" });
      if (!r.ok) {
        const data = await r.json().catch(() => ({}));
        showNotice(data.detail || "Не удалось удалить чат", true);
        return;
      }
      if (activeThreadId === threadId) {
        activeThreadId = null;
        if ($("chatActiveTitle")) $("chatActiveTitle").textContent = "Диалог";
        const msgEl = $("chatMessages");
        if (msgEl) msgEl.innerHTML = '<p class="chat-empty-hint">Напишите первое сообщение…</p>';
      }
      await loadThreads();
      if (!activeThreadId && threads.length) {
        activeThreadId = threads[0].id;
        await loadMessages(activeThreadId);
      }
    } catch (e) {
      showNotice(e.message || "Ошибка сети", true);
    }
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

  function showTyping(on) {
    const el = $("chatTyping");
    if (el) el.classList.toggle("hidden", !on);
    if (on) {
      const box = $("chatMessages");
      if (box) box.scrollTop = box.scrollHeight;
    }
  }

  function buildHistory(items) {
    return (items || [])
      .filter((m) => m.msg_type === "user" || m.msg_type === "agent")
      .slice(-12)
      .map((m) => ({
        role: m.msg_type === "agent" ? "assistant" : "user",
        content: m.body,
      }));
  }

  function renderMessages(items) {
    const el = $("chatMessages");
    if (!el) return;
    if (!items.length) {
      el.innerHTML = '<p class="chat-empty-hint">Выберите роль и напишите первое сообщение — AI ответит в режиме «Диалог».</p>';
      return;
    }
    el.innerHTML = items.map((m) => {
      const role = roleMeta(m.author_role);
      const isUser = m.msg_type === "user";
      const isAgent = m.msg_type === "agent";
      const cls = isAgent ? "msg-agent" : m.msg_type === "system" ? "msg-system" : "msg-user";
      const time = m.created_at ? new Date(m.created_at).toLocaleString("ru-RU", { hour: "2-digit", minute: "2-digit" }) : "";
      const avatar = isAgent ? "AI" : isUser ? (role.name_ru || "?").slice(0, 1) : "·";
      return `
        <article class="chat-msg ${cls}">
          <div class="chat-msg-avatar" aria-hidden="true">${esc(avatar)}</div>
          <div class="chat-msg-content">
            <header>
              <strong>${esc(m.author_name)}</strong>
              ${!isUser ? `<span class="user-role-badge role-${esc(m.author_role)}">${esc(role.name_ru || m.author_role)}</span>` : ""}
              <span class="chat-msg-time">${esc(time)}</span>
            </header>
            <div class="chat-msg-body">${esc(m.body)}</div>
          </div>
        </article>`;
    }).join("");
    el.scrollTop = el.scrollHeight;
  }

  async function createThread() {
    const btn = $("chatNewBtn");
    const prev = btn?.textContent;
    if (btn) { btn.disabled = true; btn.textContent = "…"; }
    try {
      if (!await requireIdentity()) return;
      const n = threads.length + 1;
      const r = await fetch(`${API}/chat/threads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: `Чат ${n}`, kind: "team", created_by: currentUser.id }),
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
      if (btn) { btn.disabled = false; btn.textContent = prev; }
    }
  }

  async function postMessage(text, msgType = "user", authorName = null, authorId = null) {
    await fetch(`${API}/chat/threads/${encodeURIComponent(activeThreadId)}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        author_id: authorId ?? currentUser.id,
        author_name: authorName ?? currentUser.display_name,
        author_role: currentUser.role_id,
        body: text,
        msg_type: msgType,
      }),
    });
  }

  function parseApiError(data, fallback = "AI недоступен") {
    const d = data?.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d[0]?.msg || fallback;
    return fallback;
  }

  async function runChatLLM(query, history) {
    const prompt = (rolePromptData?.system_prompt || $("rolePromptText")?.value || "").trim();
    const r = await fetch(`${API}/chat/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: query,
        role_id: currentUser.role_id,
        history,
        system_prompt: prompt || undefined,
      }),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(parseApiError(data, "LLM недоступен"));
    return data.reply || "";
  }

  async function runAgentInChat(query) {
    const role = roleMeta(currentUser.role_id);
    const prompt = (rolePromptData?.system_prompt || $("rolePromptText")?.value || "").trim();
    const enriched = prompt
      ? `[Системный промпт роли «${role.name_ru}»]\n${prompt}\n\n[Запрос пользователя]\n${query}`
      : query;
    const r = await fetch(`${API}/agents-service/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: enriched,
        mode: selectedAgentMode,
        doc_ids: window.MKG?.selectedDoc ? [window.MKG.selectedDoc] : [],
        user_role: role.agents_user_role || currentUser.role_id,
        limit: 5,
      }),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(parseApiError(data, "AI недоступен"));
    return formatAgentResult(data, query);
  }

  function formatAgentResult(data, query) {
    return [
      data.summary || "",
      data.warnings?.length ? `\n⚠ ${data.warnings.join("\n")}` : "",
      data.hypotheses?.length
        ? `\n\nГипотезы:\n${data.hypotheses.map((h, i) => `${i + 1}. ${h.title || h.text || JSON.stringify(h)}`).join("\n")}`
        : "",
      data.recommendations?.length
        ? `\n\nРекомендации:\n${data.recommendations.map((x, i) => `${i + 1}. ${x.title || x.text || JSON.stringify(x)}`).join("\n")}`
        : "",
    ].join("") || query;
  }

  async function sendChatMessage() {
    const input = $("chatMessageInput");
    const text = (input?.value || "").trim();
    if (!text) return;
    const btn = $("chatSendBtn");
    if (btn) { btn.disabled = true; btn.textContent = "…"; }
    let history = [];
    try {
      if (!await requireIdentity()) return;
      if (!activeThreadId) {
        await createThread();
        if (!activeThreadId) return;
      }
      try {
        const mr = await fetch(`${API}/chat/threads/${encodeURIComponent(activeThreadId)}/messages`);
        if (mr.ok) {
          const md = await mr.json();
          history = buildHistory(md.items || []);
        }
      } catch { /* ignore */ }

      input.value = "";
      await postMessage(text);
      await loadMessages(activeThreadId);

      const role = roleMeta(currentUser.role_id);
      showTyping(true);
      try {
        let answer;
        if (selectedAgentMode && role.can_run_agents !== false) {
          answer = await runAgentInChat(text);
        } else {
          answer = await runChatLLM(text, history);
        }
        await postMessage(answer, "agent", "MKG AI", null);
      } catch (e) {
        const msg = typeof e.message === "string" ? e.message : "AI недоступен";
        await postMessage(`⚠ ${msg}`, "system", "Система", null);
      } finally {
        showTyping(false);
      }

      await loadMessages(activeThreadId);
      await loadThreads();
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = "Отправить"; }
    }
  }

  function renderModeChips() {
    const grid = $("homeAgentModes");
    if (!grid) return;
    const modes = agentModes.filter((m) => m.id);
    if (!modes.length) {
      grid.innerHTML = '<span class="muted small">AI offline</span>';
      return;
    }
    grid.innerHTML = modes.map((m) =>
      `<button type="button" class="mode-chip ${m.id === selectedAgentMode ? "active" : ""}" data-mode="${esc(m.id)}" title="${esc(m.description || "")}">${esc(m.title)}</button>`,
    ).join("");
    grid.querySelectorAll(".mode-chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        selectedAgentMode = btn.dataset.mode;
        renderModeChips();
        renderChatAgentModes();
      });
    });
  }

  function setAgentStatus(text) {
    const el = $("homeAgentStatus");
    if (el) el.textContent = text;
  }

  async function loadAgentModes() {
    await fetchAgentModes();
    setAgentStatus($("chatAgentStatus")?.textContent || "");
  }

  async function runAgentQuery() {
    const query = ($("homeAgentQuery")?.value || "").trim();
    if (!query) return;
    window.MKG?.switchPage?.("chats");
    selectedAgentMode = selectedAgentMode || "hypothesis_mode";
    renderChatAgentModes();
    $("chatMessageInput").value = query;
    await sendChatMessage();
    const out = $("homeAgentResult");
    if (out) out.textContent = "Ответ в чате ↑";
  }

  async function refreshChatsPage() {
    await restoreSession();
    renderRoleCards();
    await loadThreads();
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(() => {
      if (window.MKG?.currentPage === "chats" && activeThreadId) {
        loadMessages(activeThreadId);
        loadThreads();
      }
    }, 4000);
  }

  function bindEvents() {
    $("chatNewBtn")?.addEventListener("click", (e) => { e.preventDefault(); createThread(); });
    $("chatSendBtn")?.addEventListener("click", (e) => { e.preventDefault(); sendChatMessage(); });
    $("chatMessageInput")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChatMessage(); }
    });
    $("homeAgentRunBtn")?.addEventListener("click", runAgentQuery);
    $("homeAgentQuery")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); runAgentQuery(); }
    });
    $("rolePromptSave")?.addEventListener("click", (e) => { e.preventDefault(); saveRolePrompt(); });
    $("rolePromptReset")?.addEventListener("click", (e) => { e.preventDefault(); resetRolePrompt(); });
  }

  bindEvents();
  renderRoleCards();
  renderChatAgentModes();

  async function init() {
    await fetchRoles();
    const saved = loadSession();
    if (saved?.role_id) selectedRoleId = saved.role_id;
    await restoreSession();
    applyPermissions();
    await fetchAgentModes();
    await refreshChatsPage();
  }

  init();

  window.MKGAuth = {
    init,
    refreshChatsPage,
    requireIdentity,
    getCurrentUser: () => currentUser,
    getRole: () => roleMeta(currentUser?.role_id),
    applyPermissions,
  };
})();
