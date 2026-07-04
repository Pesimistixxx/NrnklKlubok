/** Чат: роль + AI-режим + история */
(function () {
  const API = "/api/v1";
  const SESSION_KEY = "mkg_user_session";
  const ROLE_PROMPT_OPEN_KEY = "mkg_role_prompt_open";
  const $ = (id) => document.getElementById(id);

  const FALLBACK_ROLES = [
    { id: "researcher", name_ru: "Исследователь", can_run_agents: true, icon: "🔬", tagline: "Гипотезы и связи", capability_ru: "Синтез из графа MKG" },
    { id: "analyst", name_ru: "Аналитик", can_run_agents: true, icon: "📊", tagline: "Паттерны в данных", capability_ru: "Qdrant + графики" },
    { id: "anomaly_hunter", name_ru: "Охотник за аномалиями", can_run_agents: true, icon: "🎯", tagline: "Выбросы L4", capability_ru: "Режим «Аномалии»" },
    { id: "validator", name_ru: "Валидатор", can_run_agents: true, icon: "✓", tagline: "Проверка фактов", capability_ru: "Режим «Аудит»" },
    { id: "engineer", name_ru: "Инженер", can_run_agents: false, icon: "🛠", tagline: "Пайплайн данных", capability_ru: "OCR → MD → Neo4j → Qdrant" },
    { id: "admin", name_ru: "Администратор", can_run_agents: true, icon: "⚙️", tagline: "Полный доступ", capability_ru: "Настройки и очистка" },
    { id: "viewer", name_ru: "Наблюдатель", can_run_agents: false, icon: "👁", tagline: "Только просмотр", capability_ru: "Read-only" },
  ];

  const ROLE_ICONS = {
    admin: "⚙️", researcher: "🔬", engineer: "🛠", analyst: "📊",
    validator: "✓", security: "🔒", viewer: "👁", anomaly_hunter: "🎯",
  };

  const AGENT_MODE_TRACE = {
    hypothesis_mode: "Гипотезы",
    audit_mode: "Аудит",
    literature_review_mode: "Обзор",
    recommendation_mode: "Советы",
    anomaly_mode: "Аномалии",
  };

  let chartInstances = [];
  let chatGraphCollapsed = false;

  const FALLBACK_AGENT_MODES = [
    { id: null, title: "Диалог", description: "Быстрый ответ LLM по роли" },
    { id: "hypothesis_mode", title: "Гипотезы", description: "Гипотезы и связи" },
    { id: "audit_mode", title: "Аудит", description: "Проверка фактов" },
    { id: "anomaly_mode", title: "Аномалии", description: "Обход L4-выбросов графа" },
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
  const threadDocIds = new Map();
  const uploadPollers = new Map();
  const uploadPreviewCache = new Map();
  const TERMINAL_DOC_STATUSES = new Set(["loaded", "failed"]);
  let pollTimer = null;
  let rolePromptData = null;
  let pendingUploadFiles = null;

  function showChatUploadError(msg) {
    const el = $("chatUploadError");
    if (!el) return;
    if (!msg) {
      el.textContent = "";
      el.classList.add("hidden");
      return;
    }
    el.textContent = msg;
    el.classList.remove("hidden");
  }

  function getThreadDocIds(threadId) {
    if (!threadId) return [];
    const set = threadDocIds.get(threadId);
    return set ? [...set] : [];
  }

  function addThreadDocId(threadId, docId) {
    if (!threadId || !docId) return;
    if (!threadDocIds.has(threadId)) threadDocIds.set(threadId, new Set());
    threadDocIds.get(threadId).add(docId);
  }

  function syncThreadDocsFromMessages(items) {
    if (!activeThreadId) return;
    const set = new Set(threadDocIds.get(activeThreadId) || []);
    (items || []).forEach((m) => {
      const docId = m.meta?.document_id;
      if (docId) set.add(docId);
      (m.meta?.document_ids || []).forEach((id) => set.add(id));
    });
    threadDocIds.set(activeThreadId, set);
  }

  function getMergedDocIds() {
    const ids = getThreadDocIds(activeThreadId);
    const sel = window.MKG?.selectedDoc;
    if (sel && !ids.includes(sel)) ids.push(sel);
    return ids;
  }

  function statusLabelRu(status, step) {
    const map = {
      uploaded: "В очереди",
      processing: "OCR / ingestion…",
      md_ready: "Markdown готов",
      extracting: "Извлечение графа…",
      loaded: "Готово",
      failed: "Ошибка",
    };
    const base = map[status] || status || "—";
    return step ? `${base} · ${step}` : base;
  }

  function renderUploadCardInner(docId, preview, fileName) {
    const data = preview || { document_id: docId, file_name: fileName, status: "uploaded" };
    const pipeHtml = window.MKG?.renderDocPipelineHtml
      ? window.MKG.renderDocPipelineHtml(data, { compact: true })
      : "";
    const statusText = statusLabelRu(data.status, data.step);
    const md = (data.markdown || "").trim();
    const mdPreview = md
      ? `<div class="chat-upload-md-preview">${esc(md.slice(0, 600))}${md.length > 600 ? "…" : ""}</div>`
      : "";
    const openBtn = docId
      ? `<button type="button" class="btn btn-ghost btn-small chat-upload-open" data-doc-id="${esc(docId)}">Открыть MD</button>`
      : "";
    return `
      <div class="chat-upload-card" data-upload-doc="${esc(docId)}">
        <div class="chat-upload-card-head">
          <span aria-hidden="true">📎</span>
          <strong>${esc(data.file_name || fileName || docId)}</strong>
          <span class="chat-upload-status">${esc(statusText)}</span>
        </div>
        ${pipeHtml}
        ${mdPreview}
        <div class="chat-upload-actions">${openBtn}</div>
        <details class="chat-upload-logs" data-logs-doc="${esc(docId)}">
          <summary>Логи обработки</summary>
          <div class="chat-upload-logs-body empty muted">Загрузка логов…</div>
        </details>
      </div>`;
  }

  async function loadChatUploadLogs(docId, container) {
    if (!docId || !container) return;
    try {
      const r = await fetch(`${API}/documents/${encodeURIComponent(docId)}/logs?limit=80`);
      if (!r.ok) {
        container.textContent = "Логи недоступны";
        container.classList.add("empty");
        return;
      }
      const data = await r.json();
      const items = (data.items || []).filter((item) => !item.doc_id || item.doc_id === docId);
      if (!items.length) {
        container.textContent = "Пока нет записей. Логи появятся во время OCR и извлечения.";
        container.classList.add("empty");
        return;
      }
      const fmt = window.MKG?.formatLogEntry || ((item) => `<div>${esc(item.kind || "?")}</div>`);
      container.innerHTML = items.map(fmt).join("");
      container.classList.remove("empty");
    } catch {
      container.textContent = "Ошибка загрузки логов";
      container.classList.add("empty");
    }
  }

  function bindUploadCardEvents(root) {
    root?.querySelectorAll(".chat-upload-open").forEach((btn) => {
      btn.addEventListener("click", () => {
        const docId = btn.dataset.docId;
        if (docId && window.MKG?.openDocWithMd) window.MKG.openDocWithMd(docId);
      });
    });
    window.MKG?.bindRetryButtons?.(root);
    root?.querySelectorAll(".chat-upload-logs").forEach((det) => {
      if (det.dataset.bound) return;
      det.dataset.bound = "1";
      det.addEventListener("toggle", () => {
        if (!det.open) return;
        const docId = det.dataset.logsDoc;
        const body = det.querySelector(".chat-upload-logs-body");
        if (docId && body) loadChatUploadLogs(docId, body);
      });
    });
  }

  function updateUploadCardDom(docId, preview) {
    uploadPreviewCache.set(docId, preview);
    document.querySelectorAll(`[data-upload-doc="${CSS.escape(docId)}"]`).forEach((card) => {
      const fileName = preview.file_name || card.querySelector("strong")?.textContent || docId;
      const wrapper = card.parentElement;
      const logsWasOpen = card.querySelector(".chat-upload-logs")?.open;
      const tmp = document.createElement("div");
      tmp.innerHTML = renderUploadCardInner(docId, preview, fileName);
      const fresh = tmp.firstElementChild;
      if (fresh && wrapper) {
        card.replaceWith(fresh);
        bindUploadCardEvents(wrapper);
        const logsDet = fresh.querySelector(".chat-upload-logs");
        if (logsWasOpen && logsDet) {
          logsDet.open = true;
          loadChatUploadLogs(docId, fresh.querySelector(".chat-upload-logs-body"));
        }
      }
    });
  }

  async function pollUploadDoc(docId) {
    try {
      const r = await fetch(`${API}/documents/${encodeURIComponent(docId)}/preview`);
      if (!r.ok) return;
      const data = await r.json();
      updateUploadCardDom(docId, data);
      document.querySelectorAll(`.chat-upload-logs[data-logs-doc="${CSS.escape(docId)}"]`).forEach((det) => {
        if (det.open) {
          const body = det.querySelector(".chat-upload-logs-body");
          if (body) loadChatUploadLogs(docId, body);
        }
      });
      if (window.MKG?.ensurePipeline) await window.MKG.ensurePipeline(docId);
      const answersOnly = data.processing_mode === "answers_only";
      if (data.status === "loaded" && data.graph_nodes > 0 && window.MKG?.indexEmbeddings && !window.MKG.isDocIndexed(docId)) {
        await window.MKG.indexEmbeddings(docId, { silent: true });
      } else if (data.status === "loaded" && answersOnly && window.MKG?.markDocIndexed) {
        window.MKG.markDocIndexed(docId);
      }
      if (TERMINAL_DOC_STATUSES.has(data.status)) {
        stopUploadPoll(docId);
      }
    } catch { /* retry on next tick */ }
  }

  function startUploadPoll(docId) {
    if (!docId || uploadPollers.has(docId)) return;
    pollUploadDoc(docId);
    uploadPollers.set(docId, setInterval(() => pollUploadDoc(docId), 1500));
  }

  function stopUploadPoll(docId) {
    const t = uploadPollers.get(docId);
    if (t) clearInterval(t);
    uploadPollers.delete(docId);
  }

  function stopAllUploadPolls() {
    uploadPollers.forEach((t) => clearInterval(t));
    uploadPollers.clear();
  }

  function hideChatUploadModal() {
    pendingUploadFiles = null;
    $("chatUploadModal")?.classList.add("hidden");
    const input = $("chatFileInput");
    if (input) input.value = "";
  }

  function showChatUploadModal(fileList) {
    const files = [...(fileList || [])].filter((f) => f && f.size > 0);
    if (!files.length) return;
    pendingUploadFiles = files;
    const names = files.map((f) => f.name).join(", ");
    const hint = $("chatUploadModalFiles");
    if (hint) {
      hint.textContent = files.length === 1
        ? `Файл: ${names}`
        : `Файлов: ${files.length} — ${names.length > 80 ? `${names.slice(0, 80)}…` : names}`;
    }
    $("chatUploadModal")?.classList.remove("hidden");
  }

  function queueChatUpload(fileList) {
    showChatUploadModal(fileList);
  }

  async function uploadChatFiles(fileList, processingMode = "full") {
    const files = [...(fileList || [])].filter((f) => f && f.size > 0);
    if (!files.length) return;
    showChatUploadError("");
    const attachBtn = $("chatAttachBtn");
    if (attachBtn) attachBtn.disabled = true;
    try {
      if (!await requireIdentity()) return;
      if (!activeThreadId) {
        await createThread();
        if (!activeThreadId) return;
      }
      const useBatch = files.length > 1;
      const fd = new FormData();
      if (useBatch) {
        files.forEach((f) => fd.append("files", f));
      } else {
        fd.append("file", files[0]);
      }
      fd.append("classification", "открытый");
      fd.append("processing_mode", processingMode === "answers_only" ? "answers_only" : "full");
      const url = useBatch ? `${API}/documents/batch` : `${API}/documents`;
      const r = await fetch(url, { method: "POST", body: fd });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "Ошибка загрузки");
      const uploaded = useBatch
        ? (data.items || []).filter((x) => x.document?.id).map((x) => ({ id: x.document.id, name: x.document.file_name || x.file_name }))
        : [{ id: data.id, name: data.file_name || files[0].name }];
      const bad = useBatch ? (data.items || []).filter((x) => x.error) : [];
      if (bad.length) {
        showChatUploadError(bad.map((x) => `${x.file_name}: ${x.error}`).join("; "));
      }
      const modeLabel = processingMode === "answers_only" ? " (только для ответов)" : "";
      for (const item of uploaded) {
        addThreadDocId(activeThreadId, item.id);
        await postMessage(`📎 Загружен: ${item.name}${modeLabel}`, "system", "Система", null, {
          kind: "upload",
          document_id: item.id,
          file_name: item.name,
          processing_mode: processingMode,
        });
        startUploadPoll(item.id);
        if (window.MKG?.trackPipelineDoc) window.MKG.trackPipelineDoc(item.id);
        if (window.MKG?.ensurePipeline) window.MKG.ensurePipeline(item.id).catch(() => {});
      }
      await loadMessages(activeThreadId);
      await loadThreads();
      scrollChatToBottom(true);
    } catch (e) {
      showChatUploadError(e.message || "Ошибка загрузки");
    } finally {
      if (attachBtn) attachBtn.disabled = false;
      hideChatUploadModal();
    }
  }

  function setupChatDragDrop() {
    const main = document.querySelector(".chats-main");
    if (!main || main.dataset.dndBound) return;
    main.dataset.dndBound = "1";
    const prevent = (e) => { e.preventDefault(); e.stopPropagation(); };
    ["dragenter", "dragover"].forEach((ev) => {
      main.addEventListener(ev, (e) => {
        prevent(e);
        main.classList.add("drag-over");
      });
    });
    ["dragleave", "drop"].forEach((ev) => {
      main.addEventListener(ev, (e) => {
        prevent(e);
        if (ev === "dragleave" && !main.contains(e.relatedTarget)) {
          main.classList.remove("drag-over");
        }
        if (ev === "drop") {
          main.classList.remove("drag-over");
          const files = e.dataTransfer?.files;
          if (files?.length) queueChatUpload(files);
        }
      });
    });
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function downloadTextAsMd(filename, content) {
    const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename.endsWith(".md") ? filename : `${filename}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function buildChatMdExport(msg) {
    const lines = [msg.body || ""];
    const sources = msg.meta?.sources;
    if (sources?.length) {
      lines.push("", "## Источники MKG", "");
      sources.forEach((s, i) => {
        const name = s.file_name || s.document_id || "?";
        const layer = s.layer ? ` · ${s.layer}` : "";
        lines.push(`${i + 1}. **${name}**${layer}`);
        if (s.text) lines.push(`   > ${String(s.text).replace(/\n/g, " ").slice(0, 300)}`);
        if (s.md_file) lines.push(`   - md: \`${s.md_file}\``);
      });
    }
    return lines.join("\n");
  }

  function renderSourcesHtml(sources) {
    if (!sources?.length) return "";
    const items = sources.map((s) => {
      const docId = s.document_id || "";
      const name = esc(s.file_name || docId.slice(-12) || "?");
      const layer = s.layer ? `<span class="chat-source-layer">${esc(s.layer)}</span>` : "";
      const snippet = s.text ? `<span class="chat-source-snippet">${esc(String(s.text).slice(0, 120))}${s.text.length > 120 ? "…" : ""}</span>` : "";
      return `<li><button type="button" class="chat-source-link" data-doc-id="${esc(docId)}" title="Открыть Markdown документа">${name}</button>${layer}${snippet ? `<br>${snippet}` : ""}</li>`;
    }).join("");
    return `<div class="chat-sources"><strong>Источники:</strong><ul>${items}</ul></div>`;
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
    updateRoleHeader();
    applyPermissions();
    showNotice("");
    togglePromptPanel(true);
    loadRolePrompt(user.role_id);
  }

  function setRolePromptOpen(open, { persist = true } = {}) {
    const panel = $("rolePromptPanel");
    if (!panel) return;
    panel.open = open;
    if (persist) localStorage.setItem(ROLE_PROMPT_OPEN_KEY, open ? "1" : "0");
  }

  function restoreRolePromptOpenState() {
    const panel = $("rolePromptPanel");
    if (!panel || panel.classList.contains("hidden")) return;
    setRolePromptOpen(localStorage.getItem(ROLE_PROMPT_OPEN_KEY) === "1", { persist: false });
  }

  function togglePromptPanel(show) {
    const panel = $("rolePromptPanel");
    if (!panel) return;
    panel.classList.toggle("hidden", !show);
    if (show) restoreRolePromptOpenState();
  }

  function bindRolePromptPanel() {
    const panel = $("rolePromptPanel");
    if (!panel || panel.dataset.bound) return;
    panel.dataset.bound = "1";
    panel.addEventListener("toggle", () => {
      if (!panel.classList.contains("hidden")) {
        localStorage.setItem(ROLE_PROMPT_OPEN_KEY, panel.open ? "1" : "0");
      }
    });
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
      setRolePromptOpen(false);
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
      setRolePromptOpen(false);
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
      const icon = ro.icon || ROLE_ICONS[ro.id] || "•";
      const tagline = ro.tagline || ro.description || "";
      const diff = ro.differs_from ? ` title="${esc(ro.differs_from)}"` : "";
      return `<button type="button" class="role-card role-${esc(ro.id)}${active}" data-role="${esc(ro.id)}"${diff}>
        <span class="role-card-icon">${icon}</span>
        <span class="role-card-name">${esc(ro.name_ru)}</span>
        <span class="role-card-desc">${esc(tagline)}</span>
      </button>`;
    }).join("");
    grid.querySelectorAll(".role-card[data-role]").forEach((btn) => {
      btn.addEventListener("click", () => loginWithRole(btn.dataset.role));
    });
    updateRoleHeader();
  }

  function updateRoleHeader() {
    const header = $("chatRoleHeader");
    const badge = $("chatRoleBadge");
    const cap = $("chatRoleCapability");
    const roleId = currentUser?.role_id || selectedRoleId;
    if (!roleId || !header) return;
    const role = roleMeta(roleId);
    header.classList.remove("hidden");
    if (badge) {
      badge.className = `user-role-badge role-${esc(role.id)}`;
      badge.textContent = `${role.icon || ROLE_ICONS[role.id] || ""} ${role.name_ru || role.id}`.trim();
    }
    if (cap) {
      cap.textContent = role.capability_ru || role.description || "";
      cap.title = role.differs_from || "";
    }
  }

  function renderChatAgentModes() {
    const grid = $("chatAgentModes");
    if (!grid) return;
    grid.innerHTML = agentModes.map((m) => {
      const id = m.id || "";
      const active = (selectedAgentMode || "") === (id || "") ? " active" : "";
      const traceHint = id ? AGENT_MODE_TRACE[id] || m.title : "Диалог";
      return `<button type="button" class="chip agent-chip${active}" data-mode="${esc(id)}" title="${esc(m.description || "")}">
        <span class="agent-chip-title">${esc(m.title)}</span>
        <span class="agent-chip-trace muted">${esc(traceHint)}</span>
      </button>`;
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
    const chatAttach = $("chatAttachBtn");
    const chatHint = $("chatUploadHint");
    if (chatAttach) chatAttach.style.display = role.can_upload === false ? "none" : "";
    if (chatHint) chatHint.style.display = role.can_upload === false ? "none" : "";
    if (chatAttach && role.can_upload === false) chatAttach.disabled = true;
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
    anomaly_mode: "Аномалии",
  };

  const TRACE_LABELS = {
    chat_role: "Роль",
    qdrant_search: "Qdrant",
    qdrant_l3: "Qdrant L3",
    qdrant_l4_cluster: "L4 кластеры",
    graph_traversal: "Neo4j обход",
    llm_compose: "LLM",
    capabilities_check: "Проверка",
    llm_scope_planner: "План",
    document_selector: "Документы",
    retrieval_search: "Поиск",
    graph_context_loader: "Neo4j",
    evidence_collector: "Evidence",
    llm_evidence_analyzer: "Анализ",
    agent_loop_controller: "Цикл",
    literature_grouper: "Группы",
    technology_coverage_analyzer: "Покрытие",
    consensus_detector: "Консенсус",
    route_by_mode: "Режим",
    pattern_discovery: "Паттерны",
    audit_mode_builder: "Аудит",
    hypothesis_mode_builder: "Гипотезы",
    hypothesis_critic: "Критик",
    literature_review_mode_builder: "Обзор",
    recommendation_mode_builder: "Советы",
    expert_finder: "Эксперты",
    ranking_agent: "Ранжир.",
    final_report_builder: "Отчёт",
    anomaly_seed_loader: "Аномалии",
    anomaly_graph_walker: "Neo4j walk",
    anomaly_qdrant_refine: "Qdrant",
    anomaly_mode_builder: "Объяснение",
  };

  const DIALOG_TRACE_PREVIEW = ["chat_role", "qdrant_l3", "qdrant_l4_cluster", "graph_traversal", "llm_compose"];

  const AGENT_TRACE_PREVIEW = [
    "capabilities_check", "llm_scope_planner", "document_selector",
    "retrieval_search", "graph_context_loader", "evidence_collector",
    "llm_evidence_analyzer", "final_report_builder",
  ];

  const ANOMALY_TRACE_PREVIEW = [
    "capabilities_check", "llm_scope_planner", "document_selector",
    "anomaly_seed_loader", "anomaly_graph_walker", "anomaly_qdrant_refine",
    "graph_context_loader", "evidence_collector", "llm_evidence_analyzer",
    "anomaly_mode_builder", "final_report_builder",
  ];

  function traceStepLabel(step) {
    return TRACE_LABELS[step] || step.replace(/_/g, " ");
  }

  function traceStepDetail(item) {
    if (item.step === "qdrant_search" || item.step === "qdrant_l3") {
      if (item.skipped) return item.error ? "ошибка" : "нет индекса";
      return `${item.hit_count ?? 0} хитов`;
    }
    if (item.step === "qdrant_l4_cluster") {
      if (item.skipped) return "пропуск";
      const clusters = item.cluster_ids?.length ? ` · кл.${item.cluster_ids.length}` : "";
      const extra = item.cluster_hit_count ? `+${item.cluster_hit_count}` : "";
      return `${item.hit_count ?? 0}${extra}${clusters}`;
    }
    if (item.step === "chat_role") return item.name_ru || item.role_id || "";
    if (item.step === "graph_traversal" || item.step === "graph_context_loader") {
      if (item.skipped) return item.reason === "no_index" ? "нет данных" : "пропуск";
      const fb = item.fallback ? " · fallback" : "";
      return `${item.node_count ?? 0} узл.${fb}`;
    }
    if (item.doc_count != null) return `${item.doc_count} док.`;
    if (item.evidence_count != null) return `${item.evidence_count} ev.`;
    if (item.elapsed_ms != null && item.elapsed_ms > 0) return `${item.elapsed_ms} ms`;
    return "";
  }

  function traceStepReasoningDetail(item) {
    const step = typeof item === "string" ? item : item.step;
    const parts = [];
    if (item.hit_count != null) parts.push(`хитов: ${item.hit_count}`);
    if (item.cluster_hit_count != null) parts.push(`соседей кластера: ${item.cluster_hit_count}`);
    if (item.cluster_ids?.length) parts.push(`cluster_id: ${item.cluster_ids.join(", ")}`);
    if (item.node_count != null) parts.push(`узлов: ${item.node_count}`);
    if (item.rel_count != null) parts.push(`связей: ${item.rel_count}`);
    if (item.seed_count != null) parts.push(`seed: ${item.seed_count}`);
    if (item.source) parts.push(`источник: ${item.source}`);
    if (item.fallback) parts.push("режим fallback (без Qdrant-хитов)");
    if (item.collection) parts.push(`коллекция: ${item.collection}`);
    if (item.indexed_total != null) parts.push(`индекс: ${item.indexed_total} точек`);
    if (item.error) parts.push(`ошибка: ${item.error}`);
    if (item.elapsed_ms != null) parts.push(`${item.elapsed_ms} ms`);
    return parts.length ? parts.join(" · ") : traceStepLabel(step);
  }

  function renderReasoningChainHtml(trace) {
    if (!trace?.length) return "";
    const rows = trace.map((item) => {
      const step = typeof item === "string" ? item : item.step;
      const label = traceStepLabel(step);
      const detail = traceStepReasoningDetail(item);
      return `<li><strong>${esc(label)}</strong><span class="chat-reasoning-detail">${esc(detail)}</span></li>`;
    }).join("");
    return `<details class="chat-reasoning-chain">
      <summary>Цепочка рассуждений</summary>
      <ol class="chat-reasoning-steps">${rows}</ol>
    </details>`;
  }

  function renderAgentTraceHtml(trace, { live = false, activeIdx = -1 } = {}) {
    if (!trace?.length) return "";
    const steps = trace.map((item, i) => {
      const step = typeof item === "string" ? item : item.step;
      const detail = typeof item === "string" ? "" : traceStepDetail(item);
      let cls = "agent-trace-step";
      if (live) {
        if (i < activeIdx) cls += " done";
        else if (i === activeIdx) cls += " active";
      } else {
        cls += " done";
      }
      const title = detail ? `${traceStepLabel(step)} · ${detail}` : traceStepLabel(step);
      return `<span class="${cls}" title="${esc(title)}">${esc(traceStepLabel(step))}${detail ? `<span class="agent-trace-meta">${esc(detail)}</span>` : ""}</span>`;
    });
    const joined = [];
    steps.forEach((chip, i) => {
      joined.push(chip);
      if (i < steps.length - 1) joined.push('<span class="agent-trace-arrow">→</span>');
    });
    return `<div class="agent-trace-flow">${joined.join("")}</div>`;
  }

  let traceLiveTimer = null;

  function showTraceLive(previewSteps) {
    const el = $("chatTraceLive");
    if (!el || !previewSteps?.length) return;
    let idx = 0;
    clearInterval(traceLiveTimer);
    const render = () => {
      el.innerHTML = renderAgentTraceHtml(previewSteps, { live: true, activeIdx: idx });
    };
    render();
    traceLiveTimer = setInterval(() => {
      idx = (idx + 1) % previewSteps.length;
      render();
    }, 700);
  }

  function hideTraceLive() {
    clearInterval(traceLiveTimer);
    traceLiveTimer = null;
    const el = $("chatTraceLive");
    if (el) el.innerHTML = "";
  }

  function setChatGraphBuilding(on, text = "Поиск в Qdrant…") {
    const el = $("chatGraphBuilding");
    const txt = $("chatGraphBuildingText");
    if (el) el.classList.toggle("hidden", !on);
    if (txt && text) txt.textContent = text;
  }

  function updateChatGraphStats(graph) {
    const stats = $("chatGraphStats");
    const empty = $("chatGraphEmpty");
    const canvas = $("chatGraphCanvas");
    const nodes = graph?.nodes?.length || 0;
    const rels = graph?.relationships?.length || 0;
    if (stats) stats.textContent = nodes ? `${nodes} узл · ${rels} св` : "0 узлов";
    if (empty) empty.classList.toggle("hidden", nodes > 0);
    if (canvas) canvas.classList.toggle("hidden", nodes === 0);
  }

  function renderChatGraph(graph, { animate = true } = {}) {
    const canvas = $("chatGraphCanvas");
    if (!canvas || chatGraphCollapsed) return;
    updateChatGraphStats(graph);
    if (!graph?.nodes?.length) {
      window.MKGMiniGraph?.destroy(canvas);
      return;
    }
    window.MKGMiniGraph?.render(canvas, graph, { animate });
  }

  function toggleChatGraphPanel(force) {
    const panel = $("chatGraphPanel");
    const btn = $("chatGraphToggle");
    if (!panel) return;
    chatGraphCollapsed = force !== undefined ? !force : !chatGraphCollapsed;
    panel.classList.toggle("collapsed", chatGraphCollapsed);
    if (btn) {
      btn.textContent = chatGraphCollapsed ? "‹" : "›";
      btn.title = chatGraphCollapsed ? "Развернуть панель" : "Свернуть панель";
    }
  }

  function destroyMessageCharts() {
    chartInstances.forEach((c) => { try { c.destroy(); } catch { /* ignore */ } });
    chartInstances = [];
  }

  function renderArtifactsHtml(artifacts, msgId) {
    if (!artifacts?.length) return "";
    return artifacts.map((a, i) => {
      if (a.type === "chart") {
        return `<figure class="chat-artifact chat-artifact-chart">
          <figcaption>${esc(a.title || "График")}</figcaption>
          <canvas id="chart-${esc(msgId)}-${i}" height="180"></canvas>
        </figure>`;
      }
      if (a.type === "image" && a.content) {
        return `<figure class="chat-artifact chat-artifact-image">
          <figcaption>${esc(a.title || "Изображение")}</figcaption>
          <div class="chat-artifact-svg">${a.content}</div>
        </figure>`;
      }
      return "";
    }).join("");
  }

  function mountMessageCharts(items) {
    if (typeof Chart === "undefined") return;
    (items || []).forEach((m) => {
      const artifacts = m.meta?.artifacts;
      if (!artifacts?.length || m.msg_type !== "agent") return;
      artifacts.forEach((a, i) => {
        if (a.type !== "chart") return;
        const canvas = document.getElementById(`chart-${m.id}-${i}`);
        if (!canvas) return;
        const chart = new Chart(canvas, {
          type: a.chart_type || "bar",
          data: {
            labels: a.labels || [],
            datasets: (a.datasets || []).map((ds) => ({
              label: ds.label || "",
              data: ds.data || [],
              backgroundColor: ds.backgroundColor || "#0071e3",
              borderColor: ds.borderColor || "#005bb5",
              borderWidth: 1,
            })),
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: (a.datasets || []).length > 1 } },
            scales: a.chart_type === "doughnut" || a.chart_type === "pie" ? {} : {
              y: { beginAtZero: true, ticks: { precision: 2 } },
            },
          },
        });
        chartInstances.push(chart);
      });
    });
  }

  function scrollChatToBottom(force = false) {
    const box = $("chatMessages");
    if (!box) return;
    const nearBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 120;
    if (!force && !nearBottom) return;
    const scroll = () => { box.scrollTop = box.scrollHeight; };
    scroll();
    requestAnimationFrame(() => {
      scroll();
      requestAnimationFrame(scroll);
    });
  }

  function showTyping(on, previewSteps = null) {
    const el = $("chatTyping");
    if (!el) return;
    el.classList.toggle("hidden", !on);
    if (on) {
      showTraceLive(previewSteps);
      scrollChatToBottom(true);
    } else {
      hideTraceLive();
    }
  }

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
      const items = data.items || [];
      syncThreadDocsFromMessages(items);
      renderMessages(items);
      items.forEach((m) => {
        if (m.meta?.kind === "upload" && m.meta?.document_id) {
          const st = uploadPreviewCache.get(m.meta.document_id)?.status;
          if (!st || !TERMINAL_DOC_STATUSES.has(st)) startUploadPoll(m.meta.document_id);
        }
      });
      const t = threads.find((x) => x.id === threadId);
      if ($("chatActiveTitle") && t) $("chatActiveTitle").textContent = t.title;
    } catch { /* ignore */ }
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
    destroyMessageCharts();
    if (!items.length) {
      el.innerHTML = '<p class="chat-empty-hint">Выберите роль и напишите первое сообщение — AI ответит в режиме «Диалог».</p>';
      updateChatGraphStats(null);
      window.MKGMiniGraph?.destroy($("chatGraphCanvas"));
      return;
    }
    el.innerHTML = items.map((m) => {
      const role = roleMeta(m.author_role);
      const isUser = m.msg_type === "user";
      const isAgent = m.msg_type === "agent";
      const isUpload = m.msg_type === "system" && m.meta?.kind === "upload";
      const cls = isUpload ? "msg-upload" : isAgent ? "msg-agent" : m.msg_type === "system" ? "msg-system" : "msg-user";
      const time = m.created_at ? new Date(m.created_at).toLocaleString("ru-RU", { hour: "2-digit", minute: "2-digit" }) : "";
      const avatar = isUpload ? "📎" : isAgent ? "AI" : isUser ? (role.name_ru || "?").slice(0, 1) : "·";
      const trace = m.meta?.trace;
      const traceHtml = (isAgent && trace?.length) ? renderAgentTraceHtml(trace) : "";
      const reasoningHtml = (isAgent && trace?.length) ? renderReasoningChainHtml(trace) : "";
      const artifactsHtml = (isAgent && m.meta?.artifacts?.length)
        ? renderArtifactsHtml(m.meta.artifacts, m.id)
        : "";
      const sourcesHtml = (isAgent && m.meta?.sources?.length)
        ? renderSourcesHtml(m.meta.sources)
        : "";
      const uploadHtml = isUpload
        ? renderUploadCardInner(
          m.meta.document_id,
          uploadPreviewCache.get(m.meta.document_id),
          m.meta.file_name,
        )
        : "";
      const saveMdBtn = isAgent
        ? `<button type="button" class="btn btn-ghost btn-small chat-save-md" data-msg-id="${esc(m.id)}" title="Сохранить ответ как .md">Сохранить как MD</button>`
        : "";
      const modeBadge = isAgent && m.meta?.mode && m.meta.mode !== "dialog"
        ? `<span class="chat-mode-badge">${esc(AGENT_MODE_TRACE[m.meta.mode] || m.meta.mode)}</span>`
        : "";
      const bodyHtml = isUpload ? esc(m.body) : esc(m.body);
      return `
        <article class="chat-msg ${cls}">
          <div class="chat-msg-avatar" aria-hidden="true">${esc(avatar)}</div>
          <div class="chat-msg-content">
            <header>
              <strong>${esc(m.author_name)}</strong>
              ${!isUser && !isUpload ? `<span class="user-role-badge role-${esc(m.author_role)}">${esc(role.name_ru || m.author_role)}</span>` : ""}
              ${modeBadge}
              ${saveMdBtn}
              <span class="chat-msg-time">${esc(time)}</span>
            </header>
            ${traceHtml}
            ${reasoningHtml}
            <div class="chat-msg-body">${bodyHtml}</div>
            ${uploadHtml}
            ${sourcesHtml}
            ${artifactsHtml}
          </div>
        </article>`;
    }).join("");
    bindUploadCardEvents(el);
    el.querySelectorAll(".chat-save-md").forEach((btn) => {
      btn.addEventListener("click", () => {
        const msg = items.find((m) => m.id === btn.dataset.msgId);
        if (!msg) return;
        const stamp = msg.created_at ? new Date(msg.created_at).toISOString().slice(0, 10) : "chat";
        downloadTextAsMd(`mkg-chat-${stamp}.md`, buildChatMdExport(msg));
      });
    });
    el.querySelectorAll(".chat-source-link").forEach((btn) => {
      btn.addEventListener("click", () => {
        const docId = btn.dataset.docId;
        if (docId && window.MKG?.openDocWithMd) window.MKG.openDocWithMd(docId);
      });
    });
    mountMessageCharts(items);
    scrollChatToBottom(true);
    const lastAgent = [...items].reverse().find((m) => m.msg_type === "agent" && m.meta?.graph);
    if (lastAgent?.meta?.graph) {
      renderChatGraph(lastAgent.meta.graph, { animate: false });
    }
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

  async function postMessage(text, msgType = "user", authorName = null, authorId = null, meta = null) {
    await fetch(`${API}/chat/threads/${encodeURIComponent(activeThreadId)}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        author_id: authorId ?? currentUser.id,
        author_name: authorName ?? currentUser.display_name,
        author_role: currentUser.role_id,
        body: text,
        msg_type: msgType,
        meta: meta || {},
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
    const docIds = getMergedDocIds();
    const r = await fetch(`${API}/chat/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: query,
        role_id: currentUser.role_id,
        history,
        system_prompt: prompt || undefined,
        include_graph: true,
        include_artifacts: true,
        document_ids: docIds,
      }),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(parseApiError(data, "LLM недоступен"));
    return {
      text: data.reply || "",
      trace: data.trace || [],
      graph: data.graph || null,
      artifacts: data.artifacts || [],
      sources: data.sources || [],
    };
  }

  async function runAgentInChat(query) {
    const role = roleMeta(currentUser.role_id);
    const docIds = getMergedDocIds();
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
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(parseApiError(data, "AI недоступен"));
    return {
      text: formatAgentResult(data, query),
      trace: data.trace || [],
    };
  }

  function formatAgentResult(data, query) {
    const anomalyBlock = data.anomalies?.length
      ? `\n\nАномалии:\n${data.anomalies.map((a, i) => {
          const title = a.text || a.node_id || a.label || "узел";
          const reason = a.explanation || a.anomaly_reason || "";
          return `${i + 1}. ${title}${reason ? ` — ${reason}` : ""}`;
        }).join("\n")}`
      : "";
    return [
      data.summary || "",
      data.warnings?.length ? `\n⚠ ${data.warnings.join("\n")}` : "",
      data.hypotheses?.length
        ? `\n\nГипотезы:\n${data.hypotheses.map((h, i) => `${i + 1}. ${h.title || h.text || JSON.stringify(h)}`).join("\n")}`
        : "",
      data.recommendations?.length
        ? `\n\nРекомендации:\n${data.recommendations.map((x, i) => `${i + 1}. ${x.title || x.text || JSON.stringify(x)}`).join("\n")}`
        : "",
      anomalyBlock,
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
      const useAgent = selectedAgentMode && role.can_run_agents !== false;
      const tracePreview = useAgent
        ? (selectedAgentMode === "anomaly_mode" ? ANOMALY_TRACE_PREVIEW : AGENT_TRACE_PREVIEW)
        : DIALOG_TRACE_PREVIEW;
      showTyping(true, tracePreview);
      setChatGraphBuilding(true, useAgent ? "LangGraph: загрузка контекста…" : "Qdrant L3 → L4 → Neo4j…");
      try {
        let result;
        if (useAgent) {
          result = await runAgentInChat(text);
        } else {
          result = await runChatLLM(text, history);
        }
        if (result.graph) renderChatGraph(result.graph);
        await postMessage(result.text, "agent", "MKG AI", null, {
          trace: result.trace,
          mode: useAgent ? selectedAgentMode : "dialog",
          graph: result.graph || null,
          artifacts: result.artifacts || [],
          sources: result.sources || [],
        });
      } catch (e) {
        const msg = typeof e.message === "string" ? e.message : "AI недоступен";
        await postMessage(`⚠ ${msg}`, "system", "Система", null);
        updateChatGraphStats(null);
      } finally {
        showTyping(false);
        setChatGraphBuilding(false);
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
    $("chatAttachBtn")?.addEventListener("click", (e) => {
      e.preventDefault();
      $("chatFileInput")?.click();
    });
    $("chatFileInput")?.addEventListener("change", (e) => {
      const files = e.target?.files;
      if (files?.length) queueChatUpload(files);
    });
    $("chatUploadModeFull")?.addEventListener("click", () => {
      if (pendingUploadFiles) uploadChatFiles(pendingUploadFiles, "full");
    });
    $("chatUploadModeAnswers")?.addEventListener("click", () => {
      if (pendingUploadFiles) uploadChatFiles(pendingUploadFiles, "answers_only");
    });
    $("chatUploadModalCancel")?.addEventListener("click", hideChatUploadModal);
    $("chatUploadModalBackdrop")?.addEventListener("click", hideChatUploadModal);
    setupChatDragDrop();
    $("homeAgentRunBtn")?.addEventListener("click", runAgentQuery);
    $("homeAgentQuery")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); runAgentQuery(); }
    });
    bindRolePromptPanel();
    $("rolePromptSave")?.addEventListener("click", (e) => { e.preventDefault(); saveRolePrompt(); });
    $("rolePromptReset")?.addEventListener("click", (e) => { e.preventDefault(); resetRolePrompt(); });
    $("chatGraphToggle")?.addEventListener("click", () => toggleChatGraphPanel());
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
  window.MKG?.setPollUploadHook?.(pollUploadDoc);

  window.MKGAuth = {
    init,
    refreshChatsPage,
    requireIdentity,
    getCurrentUser: () => currentUser,
    getRole: () => roleMeta(currentUser?.role_id),
    applyPermissions,
  };
})();
