/** Чат: роль + автоматический пайплайн агентов */
(function () {
  const API = "/api/v1";
  const SESSION_KEY = "mkg_user_session";
  const ROLE_PROMPT_OPEN_KEY = "mkg_role_prompt_open";
  const CHAT_GRAPH_OPEN_KEY = "mkg_chat_graph_open";
  const CHAT_SPEED_KEY = "mkg_chat_speed_mode";
  const CHAT_THREAD_SPEED_KEY = "mkg_chat_thread_speed";
  const CHAT_ACTIVE_THREAD_KEY = "mkg_chat_active_thread";
  const $ = (id) => document.getElementById(id);

  function tt(key, fallback = "") {
    const v = window.MKG?.t?.(key);
    return v && v !== key ? v : fallback;
  }

  function tf(key, vars, fallback = "") {
    let text = tt(key, fallback);
    if (vars && typeof text === "string") {
      Object.entries(vars).forEach(([k, v]) => {
        text = text.replaceAll(`{${k}}`, String(v));
      });
    }
    return text;
  }

  function roleDisplay(ro) {
    const id = ro?.id || "";
    return {
      name: tt(`role_${id}_name`, ro.name_ru || id),
      tagline: tt(`role_${id}_tagline`, ro.tagline || ro.description || ""),
      capability: tt(`role_${id}_capability`, ro.capability_ru || ro.description || ""),
      differs: ro.differs_from || "",
    };
  }

  function parseApiError(data, fallback = "AI недоступен") {
    const d = data?.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d[0]?.msg || fallback;
    if (data?.message && typeof data.message === "string") return data.message;
    return fallback;
  }

  function traceModeLabel(mode) {
    return tt(`agent_mode_${mode}`, AGENT_MODE_TRACE[mode] || mode);
  }

  function speedModeLabel(mode) {
    if (mode === "compare") return tt("chat_speed_compare", "Сравнение");
    if (mode === "direct") return tt("chat_speed_direct", "Прямой ответ");
    return mode === "fast" ? tt("chat_speed_fast", "Быстрый") : tt("chat_speed_full", "Подробный · с рассуждениями");
  }

  function chatLocale() {
    return window.MKG?.getUiLang?.() === "en" ? "en-US" : "ru-RU";
  }

  const FALLBACK_ROLES = [
    { id: "researcher", name_ru: "Исследователь", can_run_agents: true, can_upload: true, icon: "🔬", tagline: "Гипотезы и связи", capability_ru: "Синтез из графа MKG" },
    { id: "analyst", name_ru: "Аналитик", can_run_agents: true, can_upload: false, icon: "📊", tagline: "Паттерны в данных", capability_ru: "Qdrant + графики + L4-кластеры" },
    { id: "validator", name_ru: "Валидатор", can_run_agents: true, can_upload: false, icon: "✓", tagline: "Проверка фактов", capability_ru: "Аудит фактов и противоречий" },
    { id: "security", name_ru: "Безопасность", can_run_agents: false, can_upload: false, icon: "🔒", tagline: "Грифы и RBAC", capability_ru: "SecurityRole, классификация L5" },
    { id: "engineer", name_ru: "Инженер", can_run_agents: false, can_upload: true, icon: "🛠", tagline: "Пайплайн данных", capability_ru: "OCR → MD → Neo4j → Qdrant" },
    { id: "admin", name_ru: "Администратор", can_run_agents: true, can_upload: true, can_admin: true, icon: "⚙️", tagline: "Полный доступ", capability_ru: "Настройки и очистка" },
    { id: "viewer", name_ru: "Наблюдатель", can_run_agents: false, can_upload: false, icon: "👁", tagline: "Только просмотр", capability_ru: "Read-only" },
  ];

  const ROLE_ICONS = {
    admin: "⚙️", researcher: "🔬", engineer: "🛠", analyst: "📊",
    validator: "✓", security: "🔒", viewer: "👁",
  };

  const AGENT_MODE_TRACE = {
    orchestrator_mode: "Оркестратор L1–L6",
    hypothesis_mode: "Гипотезы",
    audit_mode: "Аудит",
    literature_review_mode: "Обзор",
    recommendation_mode: "Советы",
    anomaly_mode: "Аномалии",
    dialog: "Диалог",
    fast: "Быстрый",
    direct: "Прямой ответ",
  };

  const SPEED_MODE_LABELS = {
    fast: "Быстрый",
    full: "Подробный · с рассуждениями",
    compare: "Сравнение",
  };

  const threadSpeedModes = new Map();

  function loadThreadSpeedModes() {
    try {
      const raw = localStorage.getItem(CHAT_THREAD_SPEED_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        Object.entries(parsed).forEach(([tid, mode]) => {
          if (tid && (mode === "fast" || mode === "compare" || mode === "full")) {
            threadSpeedModes.set(tid, mode);
          }
        });
      }
    } catch { /* ignore */ }
  }

  function persistThreadSpeedModes() {
    try {
      localStorage.setItem(CHAT_THREAD_SPEED_KEY, JSON.stringify(Object.fromEntries(threadSpeedModes)));
    } catch { /* ignore */ }
  }

  loadThreadSpeedModes();

  function getChatSpeedMode(threadId = activeThreadId) {
    if (threadId && threadSpeedModes.has(threadId)) return threadSpeedModes.get(threadId);
    try {
      const v = localStorage.getItem(CHAT_SPEED_KEY);
      if (v === "fast") return "fast";
      if (v === "compare") return "compare";
      return "full";
    } catch {
      return "full";
    }
  }

  function setChatSpeedMode(mode, { threadId = activeThreadId, persistGlobal = true } = {}) {
    const next = mode === "fast" ? "fast" : mode === "compare" ? "compare" : "full";
    if (threadId) {
      threadSpeedModes.set(threadId, next);
      persistThreadSpeedModes();
    }
    if (persistGlobal) {
      try {
        localStorage.setItem(CHAT_SPEED_KEY, next);
      } catch { /* ignore */ }
    }
    if (!threadId || threadId === activeThreadId) syncChatSpeedToggleUi(next);
    return next;
  }

  function syncChatSpeedToggleUi(mode) {
    const root = $("chatSpeedToggle");
    if (!root) return;
    root.querySelectorAll(".chat-speed-pill[data-speed]").forEach((btn) => {
      const active = btn.dataset.speed === mode;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  let chartInstances = [];
  let chatGraphCollapsed = false;
  let chatGraphMaximized = false;
  let chatGraphWidthBeforeMax = null;
  let lastFullscreenGraph = null;
  let lastFullscreenTrace = null;
  let lastReplayableWalk = null;
  let graphReplayBusy = false;
  let liveAccumulatedGraph = null;
  let graphPollTimer = null;

  let roles = [...FALLBACK_ROLES];
  let currentUser = null;
  let threads = [];
  let activeThreadId = null;
  let selectedRoleId = null;
  const threadDocIds = new Map();
  const uploadPollers = new Map();
  const uploadPreviewCache = new Map();
  const TERMINAL_DOC_STATUSES = new Set(["loaded", "failed"]);
  let pollTimer = null;
  let rolePromptData = null;
  let pendingUploadFiles = null;
  /** Файлы, выбранные в compose и ожидающие отправки вместе с сообщением */
  let pendingComposeAttachments = null;
  let userScrolledUp = false;
  let chatScrollProgrammatic = false;
  let lastMessagesFingerprint = "";
  let lastLoadedThreadId = null;
  const CHAT_SCROLL_THRESHOLD = 120;
  const GRAPH_WALK_UI_STEP_MS = window.MKGMiniGraph?.GRAPH_WALK_UI_STEP_MS || 1300;
  const TYPEWRITER_MIN_MS = 8;
  const TYPEWRITER_MAX_MS = 16;

  let activeWalkCancel = null;
  let activeStreamPreview = null;
  let currentThreadMessages = [];
  let chatBusy = false;
  const CHAT_SEND_WATCHDOG_MS = 12 * 60 * 1000;

  function composeHasSendableContent() {
    const text = ($("chatMessageInput")?.value ?? "").trim();
    return !!text || !!(pendingComposeAttachments?.files?.length);
  }

  function isChatSending() {
    return chatBusy
      || !!activeStreamPreview?.isConnected
      || !$("chatTyping")?.classList.contains("hidden");
  }

  function syncComposeSendButton() {
    const btn = $("chatSendBtn");
    if (!btn) return;
    const canSend = composeHasSendableContent() && !isChatSending();
    btn.disabled = !canSend;
    btn.classList.toggle("disabled", !canSend);
    btn.setAttribute("aria-disabled", canSend ? "false" : "true");
  }

  function healOrphanChatBusyUi() {
    if (chatBusy) return;
    const typingVisible = $("chatTyping") && !$("chatTyping").classList.contains("hidden");
    if (typingVisible || activeStreamPreview?.isConnected) {
      showTyping(false);
      removeStreamPreview();
    }
    syncComposeSendButton();
  }

  function releaseChatComposeLock() {
    chatBusy = false;
    showTyping(false);
    removeStreamPreview();
    cancelActiveGraphWalk();
    setChatGraphBuilding(false);
    const btn = $("chatSendBtn");
    if (btn) btn.textContent = window.MKG?.t?.("chat_send") || "Отправить";
    const attachBtn = $("chatAttachBtn");
    if (attachBtn) attachBtn.disabled = !canShowUpload(roleMeta(currentUser?.role_id));
    syncComposeSendButton();
  }

  /** Выбранный раунд в блоке «Агенты · гибкий цикл» по id сообщения */
  const layerAgentsRoundByMsg = new Map();
  let layerRoundNavDelegated = false;

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
      (m.meta?.attachments || []).forEach((a) => {
        if (a.document_id) set.add(a.document_id);
      });
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
          <span class="icon-wrap" aria-hidden="true">${(window.MKG_ICONS && MKG_ICONS.paperclip(18)) || ""}</span>
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
        if (window.MKG.isDocIndexed(docId)) {
          window.MKG.showQdrantToast?.(`Документ «${data.file_name || docId}» проиндексирован в Qdrant.`, { ms: 5500 });
        }
      } else if (answersOnly && ["md_ready", "loaded"].includes(data.status) && !window.MKG.isDocIndexed(docId) && window.MKG.indexEmbeddings) {
        await window.MKG.indexEmbeddings(docId, { silent: true }).catch(() => {});
      } else if (data.status === "loaded" && answersOnly && window.MKG?.markDocIndexed && window.MKG.isDocIndexed(docId)) {
        window.MKG.markDocIndexed(docId);
      } else if (window.MKG?.isDocQdrantIndexed?.(data) && window.MKG?.markDocIndexed) {
        window.MKG.markDocIndexed(docId);
        if (TERMINAL_DOC_STATUSES.has(data.status) && data.step === "l4_done") {
          window.MKG.showQdrantToast?.(`«${data.file_name || docId}» — L3+L4 в Qdrant, кластеризация L4 готова.`, { ms: 6000 });
        }
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

  function clearPendingComposeAttachments() {
    pendingComposeAttachments = null;
    renderPendingAttachmentsPreview();
    syncComposeSendButton();
  }

  function renderPendingAttachmentsPreview() {
    const el = $("chatPendingAttachments");
    if (!el) return;
    const pending = pendingComposeAttachments;
    if (!pending?.files?.length) {
      el.innerHTML = "";
      el.classList.add("hidden");
      syncComposeSendButton();
      return;
    }
    const modeLabel = pending.processingMode === "answers_only"
      ? "только для ответов"
      : "полный пайплайн";
    const chips = pending.files.map((f, i) => `
      <span class="chat-pending-chip">
        <span class="icon-wrap" aria-hidden="true">${(window.MKG_ICONS && MKG_ICONS.paperclip(14)) || "📎"}</span>
        <span class="chat-pending-chip-name" title="${esc(f.name)}">${esc(f.name)}</span>
        <span class="chat-pending-chip-mode">${esc(modeLabel)}</span>
        <button type="button" class="chat-pending-chip-remove" data-pending-idx="${i}" title="Убрать" aria-label="Убрать файл">×</button>
      </span>`).join("");
    el.innerHTML = chips;
    el.classList.remove("hidden");
    syncComposeSendButton();
    el.querySelectorAll(".chat-pending-chip-remove").forEach((btn) => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.dataset.pendingIdx, 10);
        if (!pendingComposeAttachments?.files?.length) return;
        const next = pendingComposeAttachments.files.filter((_, j) => j !== idx);
        if (!next.length) {
          clearPendingComposeAttachments();
        } else {
          pendingComposeAttachments = { ...pendingComposeAttachments, files: next };
          renderPendingAttachmentsPreview();
        }
      });
    });
  }

  function confirmPendingComposeAttachments(processingMode) {
    const files = [...(pendingUploadFiles || [])].filter((f) => f && f.size > 0);
    if (!files.length) {
      hideChatUploadModal();
      return;
    }
    pendingComposeAttachments = {
      files,
      processingMode: processingMode === "answers_only" ? "answers_only" : "full",
    };
    hideChatUploadModal();
    renderPendingAttachmentsPreview();
    syncComposeSendButton();
    $("chatMessageInput")?.focus();
  }

  async function uploadFilesToServer(fileList, processingMode = "full") {
    const files = [...(fileList || [])].filter((f) => f && f.size > 0);
    if (!files.length) return [];
    if (!await requireIdentity()) return [];
    if (!activeThreadId) {
      await createThread();
      if (!activeThreadId) return [];
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
    return uploaded;
  }

  async function waitForDocsSearchable(docIds, processingMode, maxMs = 90000) {
    const searchable = new Set(["md_ready", "extracting", "loaded"]);
    const deadline = Date.now() + maxMs;
    while (Date.now() < deadline) {
      let ready = true;
      for (const docId of docIds) {
        try {
          const r = await fetch(`${API}/documents/${encodeURIComponent(docId)}/preview`);
          if (!r.ok) { ready = false; continue; }
          const data = await r.json();
          if (data.status === "failed") continue;
          if (!searchable.has(data.status)) {
            ready = false;
            continue;
          }
          if (data.status === "md_ready" && processingMode === "answers_only" && window.MKG?.indexEmbeddings) {
            await window.MKG.indexEmbeddings(docId, { silent: true }).catch(() => {});
          }
        } catch {
          ready = false;
        }
      }
      if (ready) return true;
      await sleep(1500);
    }
    return false;
  }

  function trackUploadedDocs(uploaded, processingMode) {
    for (const item of uploaded) {
      startUploadPoll(item.id);
      if (window.MKG?.trackPipelineDoc) window.MKG.trackPipelineDoc(item.id);
      if (window.MKG?.ensurePipeline) window.MKG.ensurePipeline(item.id).catch(() => {});
    }
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
    // Legacy entry: queue for compose send instead of immediate upload + orphan system message
    const files = [...(fileList || [])].filter((f) => f && f.size > 0);
    if (!files.length) return;
    pendingUploadFiles = files;
    confirmPendingComposeAttachments(processingMode);
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

  function renderChatMarkdown(text) {
    const fn = window.MKG?.renderMarkdownHtml;
    if (fn) return fn(text);
    return esc(text).replace(/\n/g, "<br>");
  }

  function sectionNodesHaveContent(nodes) {
    if (!nodes?.length) return false;
    const tmp = document.createElement("div");
    nodes.forEach((n) => tmp.appendChild(n.cloneNode(true)));
    return tmp.textContent.replace(/\s+/g, "").length > 0;
  }

  const SECTION_SHORT_LABELS = [
    [/^сводка/i, "Сводка"],
    [/^источники/i, "Источники"],
    [/^консенсус/i, "Консенсус"],
    [/^уверенность/i, "Уверенность"],
    [/^пробелы/i, "Пробелы"],
    [/^рекоменда/i, "Рекомендации"],
    [/^уточня/i, "Вопрос"],
  ];

  function sectionShortLabel(title) {
    const t = String(title || "").trim();
    for (const [re, label] of SECTION_SHORT_LABELS) {
      if (re.test(t)) return label;
    }
    return t.length > 22 ? `${t.slice(0, 20)}…` : t;
  }

  function truncatePlainText(text, maxChars = 280) {
    const s = String(text || "").replace(/\s+/g, " ").trim();
    if (s.length <= maxChars) return s;
    const cut = s.slice(0, maxChars);
    const lastDot = cut.lastIndexOf(". ");
    if (lastDot > maxChars * 0.45) return cut.slice(0, lastDot + 1);
    return `${cut.trimEnd()}…`;
  }

  function parseAnswerSectionsFromHtml(html) {
    if (!html || !/<h2\b/i.test(html)) return null;
    const tmp = document.createElement("div");
    tmp.innerHTML = html;
    const sections = [];
    let current = null;
    for (const node of [...tmp.childNodes]) {
      if (node.nodeType === 1 && node.tagName === "H2") {
        if (current) sections.push(current);
        current = { title: node.textContent.trim(), nodes: [] };
      } else if (current) {
        current.nodes.push(node);
      }
    }
    if (current) sections.push(current);
    return sections.filter((s) => sectionNodesHaveContent(s.nodes));
  }

  let answerSectionWalkTimer = null;

  function stopAnswerSectionWalk() {
    if (answerSectionWalkTimer) {
      clearTimeout(answerSectionWalkTimer);
      answerSectionWalkTimer = null;
    }
  }

  function activateAnswerSection(nav, idx) {
    if (!nav) return;
    const root = nav.closest(".chat-answer-plain");
    if (!root) return;
    nav.querySelectorAll(".chat-answer-section-pill:not(.chat-answer-section-collapse)").forEach((pill, i) => {
      pill.classList.toggle("active", i === idx);
      pill.setAttribute("aria-selected", i === idx ? "true" : "false");
    });
    root.querySelectorAll(".chat-answer-section").forEach((det, i) => {
      det.open = true;
      det.classList.toggle("is-active", i === idx);
    });
    const target = root.querySelector(`.chat-answer-section[data-section-idx="${idx}"]`);
    if (target) target.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function collapseAllAnswerSections(nav) {
    stopAnswerSectionWalk();
    const root = nav?.closest(".chat-answer-plain");
    if (!root) return;
    nav.querySelectorAll(".chat-answer-section-pill").forEach((pill) => {
      pill.classList.remove("active");
      pill.setAttribute("aria-selected", "false");
    });
    root.querySelectorAll(".chat-answer-section").forEach((det) => {
      det.open = false;
      det.classList.remove("is-active");
    });
  }

  function bindAnswerSectionNav(nav, { autoWalk = false } = {}) {
    if (!nav || nav.dataset.bound) return;
    nav.dataset.bound = "1";
    nav.querySelector(".chat-answer-section-collapse")?.addEventListener("click", (e) => {
      e.preventDefault();
      collapseAllAnswerSections(nav);
    });
    const pills = [...nav.querySelectorAll(".chat-answer-section-pill:not(.chat-answer-section-collapse)")];
    pills.forEach((pill, idx) => {
      pill.addEventListener("click", (e) => {
        e.preventDefault();
        stopAnswerSectionWalk();
        activateAnswerSection(nav, idx);
      });
    });
    if (autoWalk && pills.length > 1) {
      stopAnswerSectionWalk();
      let step = 0;
      const tick = () => {
        activateAnswerSection(nav, step);
        step += 1;
        if (step < pills.length) {
          answerSectionWalkTimer = setTimeout(tick, 2200);
        } else {
          answerSectionWalkTimer = null;
        }
      };
      answerSectionWalkTimer = setTimeout(tick, 600);
    }
  }

  /** Компактная сводка + навигация по ##-разделам + свёрнутые секции. */
  function wrapAnswerSectionsHtml(html) {
    if (!html || !/<h2\b/i.test(html)) return html;
    const sections = parseAnswerSectionsFromHtml(html);
    if (!sections?.length) return html;

    const summaryRe = /^(сводка|summary)$/i;
    let mainIdx = sections.findIndex((s) => summaryRe.test(s.title) && sectionNodesHaveContent(s.nodes));
    if (mainIdx < 0) mainIdx = sections.findIndex((s) => sectionNodesHaveContent(s.nodes));
    if (mainIdx < 0) return html;

    const mainSection = sections[mainIdx];
    const tmpMain = document.createElement("div");
    mainSection.nodes.forEach((n) => tmpMain.appendChild(n.cloneNode(true)));
    const summaryText = truncatePlainText(tmpMain.textContent || "");

    const out = document.createElement("div");
    out.className = "chat-answer-plain";

    if (sections.length >= 2) {
      const nav = document.createElement("nav");
      nav.className = "chat-answer-sections-nav";
      nav.setAttribute("role", "tablist");
      nav.setAttribute("aria-label", tt("chat_answer_sections", "Разделы ответа"));
      sections.forEach((sec, idx) => {
        const pill = document.createElement("button");
        pill.type = "button";
        pill.className = `chat-answer-section-pill${idx === mainIdx ? " active" : ""}`;
        pill.dataset.sectionIdx = String(idx);
        pill.setAttribute("role", "tab");
        pill.setAttribute("aria-selected", idx === mainIdx ? "true" : "false");
        pill.textContent = sectionShortLabel(sec.title);
        nav.appendChild(pill);
      });
      const collapseBtn = document.createElement("button");
      collapseBtn.type = "button";
      collapseBtn.className = "chat-answer-section-pill chat-answer-section-collapse";
      collapseBtn.textContent = tt("chat_answer_collapse_all", "Свернуть");
      collapseBtn.title = tt("chat_answer_collapse_all_hint", "Свернуть все разделы");
      nav.appendChild(collapseBtn);
      out.appendChild(nav);
    }

    const main = document.createElement("div");
    main.className = "chat-answer-main";
    const p = document.createElement("p");
    p.textContent = summaryText;
    main.appendChild(p);
    out.appendChild(main);

    const body = document.createElement("div");
    body.className = "chat-answer-sections";
    sections.forEach((sec, idx) => {
      const det = document.createElement("details");
      det.className = "chat-answer-section";
      det.dataset.sectionIdx = String(idx);
      det.open = true;
      const sum = document.createElement("summary");
      sum.className = "chat-answer-section-summary";
      const title = document.createElement("span");
      title.className = "chat-answer-section-title";
      title.textContent = sec.title;
      sum.appendChild(title);
      det.appendChild(sum);
      const secBody = document.createElement("div");
      secBody.className = "chat-answer-section-body md-render-view";
      sec.nodes.forEach((n) => secBody.appendChild(n.cloneNode(true)));
      det.appendChild(secBody);
      body.appendChild(det);
    });
    out.appendChild(body);
    return out.innerHTML;
  }

  function renderAgentAnswerHtml(text) {
    const clean = sanitizeAgentAnswerBody(text);
    const html = wrapAnswerSectionsHtml(renderChatMarkdown(clean));
    const enhance = window.MKG?.enhanceMarkdownTables || window.MKG?.enhanceComparisonTables;
    return typeof enhance === "function" ? enhance(html) : html;
  }

  /** Убрать внутренние предупреждения и метки шагов из текста ответа (только синтез для пользователя). */
  const INTERNAL_ANSWER_LINE = /^(?:⚠\s*)?(?:gap\s*analyzer|connection_gap_analyzer)\s*:/i;
  const INTERNAL_AGENT_STEP_LINE = /^(?:⚠\s*)?(?:orchestrator_|connection_|discover_|layer_loop_|l[1-6]_)[a-z0-9_]*\s*:/i;
  const EMPTY_WARNING_LINE = /^⚠\s*$/;

  function sanitizeAgentAnswerBody(text) {
    if (!text) return "";
    const lines = String(text).split(/\r?\n/);
    const kept = [];
    let inWarningBlock = false;
    for (const line of lines) {
      const t = line.trim();
      if (!t) {
        if (!inWarningBlock) kept.push("");
        continue;
      }
      if (INTERNAL_ANSWER_LINE.test(t) || INTERNAL_AGENT_STEP_LINE.test(t) || EMPTY_WARNING_LINE.test(t)) {
        inWarningBlock = true;
        continue;
      }
      if (inWarningBlock && /^⚠/.test(t)) continue;
      if (inWarningBlock && !/[а-яА-ЯёЁ]/.test(t) && /^[\w\s:.,!?-]+$/.test(t)) continue;
      inWarningBlock = false;
      kept.push(line);
    }
    return kept.join("\n").replace(/\n{3,}/g, "\n\n").trim();
  }

  function isChatNearBottom() {
    const box = $("chatMessages");
    if (!box) return true;
    return box.scrollHeight - box.scrollTop - box.clientHeight < CHAT_SCROLL_THRESHOLD;
  }

  function bindChatScrollListener() {
    const box = $("chatMessages");
    if (!box || box.dataset.scrollBound) return;
    box.dataset.scrollBound = "1";
    box.addEventListener("scroll", () => {
      if (chatScrollProgrammatic) return;
      userScrolledUp = !isChatNearBottom();
    }, { passive: true });
    box.addEventListener("wheel", () => {
      chatScrollProgrammatic = false;
    }, { passive: true });
    box.addEventListener("touchstart", () => {
      chatScrollProgrammatic = false;
    }, { passive: true });
  }

  function messagesFingerprint(items) {
    return (items || []).map((m) =>
      `${m.id}:${m.created_at}:${m.msg_type}:${(m.body || "").length}:${(m.meta?.graph?.nodes?.length || 0)}:${m.meta?.speed_mode || ""}:${(m.meta?.trace?.length || 0)}:${m.meta?.mode || ""}`,
    ).join("|");
  }

  function persistActiveThreadId(threadId) {
    try {
      if (threadId) localStorage.setItem(CHAT_ACTIVE_THREAD_KEY, threadId);
      else localStorage.removeItem(CHAT_ACTIVE_THREAD_KEY);
    } catch { /* ignore */ }
  }

  function loadPersistedActiveThreadId() {
    try {
      return localStorage.getItem(CHAT_ACTIVE_THREAD_KEY) || null;
    } catch {
      return null;
    }
  }

  function shouldOpenReasoningTrace(meta) {
    const speed = meta?.speed_mode || meta?.mode;
    return speed !== "fast" && speed !== "compare";
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

  function downloadJsonFile(filename, obj) {
    const blob = new Blob([JSON.stringify(obj, null, 2)], { type: "application/ld+json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename.endsWith(".json") ? filename : `${filename}.json`;
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

  function buildChatJsonLdExport(msg) {
    const role = roleMeta(msg.author_role);
    const sources = msg.meta?.sources || [];
    return {
      "@context": {
        "@vocab": "https://schema.org/",
        "mkg": "https://mkg.local/ontology#",
      },
      "@type": "Answer",
      "@id": `urn:mkg:chat:${msg.id || "answer"}`,
      "text": msg.body || "",
      "dateCreated": msg.created_at || new Date().toISOString(),
      "author": {
        "@type": "Person",
        "name": msg.author_name || role.name_ru || "MKG Assistant",
        "jobTitle": role.name_ru || msg.author_role,
      },
      "citation": sources.map((s, i) => ({
        "@type": "CreativeWork",
        "name": s.file_name || s.document_id || `source-${i + 1}`,
        "identifier": s.document_id || undefined,
        "description": s.text ? String(s.text).slice(0, 400) : undefined,
        "mkg:layer": s.layer || undefined,
      })),
      "isBasedOn": sources.map((s) => s.document_id).filter(Boolean),
    };
  }

  function openChatPrintView(msg) {
    const md = buildChatMdExport(msg);
    const bodyHtml = window.MKG?.renderMarkdownHtml
      ? window.MKG.renderMarkdownHtml(md)
      : `<pre>${esc(md)}</pre>`;
    const stamp = msg.created_at ? new Date(msg.created_at).toLocaleString("ru-RU") : "";
    const w = window.open("", "_blank", "noopener,noreferrer,width=900,height=720");
    if (!w) {
      showNotice("Разрешите всплывающие окна для печати/PDF", true);
      return;
    }
    w.document.write(`<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"/><title>MKG — ответ</title>
<style>
  body{font-family:Georgia,serif;max-width:720px;margin:2rem auto;line-height:1.55;color:#111}
  h1{font-size:1.25rem;font-weight:600} .meta{color:#666;font-size:.85rem;margin-bottom:1.5rem}
  @media print{ body{margin:1cm} }
</style></head><body>
<h1>Ответ MKG</h1>
<p class="meta">${esc(stamp)} · ${esc(msg.author_name || "")}</p>
<div class="content">${bodyHtml}</div>
<script>window.onload=function(){window.print();};<\/script>
</body></html>`);
    w.document.close();
  }

  function formatSourceReliability(conf) {
    if (conf == null || conf === "") return "";
    const n = Number(conf);
    if (!Number.isFinite(n)) return "";
    const pct = Math.round(n * 100);
    if (pct >= 85) return `высокая · ${pct}%`;
    if (pct >= 70) return `средняя · ${pct}%`;
    return `низкая · ${pct}%`;
  }

  function renderSourcesHtml(sources) {
    if (!sources?.length) return "";
    const chips = sources.map((s, i) => {
      const docId = s.document_id || "";
      const name = esc(s.file_name || docId.slice(-12) || "?");
      const layer = s.layer ? `<span class="chat-source-layer">${esc(s.layer)}</span>` : "";
      const rel = formatSourceReliability(s.extraction_confidence);
      const relBadge = rel ? `<span class="chat-source-reliability" title="extraction_confidence">${esc(rel)}</span>` : "";
      const date = s.source_date ? `<span class="chat-source-date">${esc(String(s.source_date))}</span>` : "";
      return `<span class="chat-source-chip-wrap">${layer}${relBadge}${date}<button type="button" class="chat-source-chip" data-doc-id="${esc(docId)}" data-source-idx="${i}" title="Открыть Markdown документа">${name}</button></span>`;
    }).join("");
    const detailItems = sources.map((s) => {
      const docId = s.document_id || "";
      const name = esc(s.file_name || docId.slice(-12) || "?");
      const layer = s.layer ? `<span class="chat-source-layer">${esc(s.layer)}</span>` : "";
      const rel = formatSourceReliability(s.extraction_confidence);
      const meta = [rel, s.source_date].filter(Boolean).map((x) => esc(String(x))).join(" · ");
      const metaLine = meta ? `<span class="chat-source-meta muted">${meta}</span><br>` : "";
      const snippet = s.text
        ? `<div class="chat-source-snippet md-render-view">${renderChatMarkdown(String(s.text).slice(0, 800))}</div>`
        : "";
      return `<li>${metaLine}<button type="button" class="chat-source-link" data-doc-id="${esc(docId)}" title="Открыть Markdown документа">${name}</button>${layer}${snippet ? `<br>${snippet}` : ""}</li>`;
    }).join("");
    const detailsBlock = sources.some((s) => s.text)
      ? `<details class="chat-sources-details">
          <summary>Подробнее об источниках (${sources.length})</summary>
          <ul>${detailItems}</ul>
        </details>`
      : "";
    return `<details class="chat-sources">
      <summary>Источники · ${sources.length}</summary>
      <div class="chat-sources-body">
        <div class="chat-source-chips">${chips}</div>
        ${detailsBlock}
      </div>
    </details>`;
  }

  function evidenceToSources(evidence, layerResults) {
    const seen = new Set();
    const out = [];
    const push = (item) => {
      const docId = String(item.document_id || item.doc_id || "").trim();
      if (!docId) return;
      const nodeId = String(item.node_id || "").trim();
      const key = `${docId}:${nodeId || item.text?.slice(0, 40) || ""}`;
      if (seen.has(key)) return;
      seen.add(key);
      const props = item.props || {};
      out.push({
        document_id: docId,
        file_name: item.file_name || docId.slice(-12),
        node_id: nodeId,
        label: item.label || "",
        layer: item.layer || "",
        score: Number(item.score) || 0,
        text: String(item.text || item.quote || "").slice(0, 500),
        md_url: `/api/v1/documents/${docId}/markdown`,
        extraction_confidence: item.extraction_confidence ?? props.extraction_confidence ?? props.confidence,
        source_date: item.source_date ?? props.publication_year ?? props.year ?? props.updated_at,
      });
    };
    (evidence || []).forEach((ev) => push({
      document_id: ev.doc_id || ev.document_id,
      node_id: ev.node_id,
      file_name: ev.file_name,
      label: ev.label,
      layer: ev.layer,
      score: ev.score,
      text: ev.text || ev.quote,
      props: ev.props || {},
    }));
    (layerResults || []).forEach((lr) => {
      (lr.nodes_found || []).forEach((n) => {
        const props = n.props || {};
        push({
          document_id: props._doc_id || props.document_id || props.source_doc_id,
          node_id: n.id,
          label: n.label,
          layer: lr.layer || props.layer,
          text: props.quote || props.raw_text_ru || props.name_ru || props.text,
          props,
        });
      });
    });
    return out.slice(0, 8);
  }

  function replayPayloadFromMessage(msg) {
    if (!msg || msg.msg_type !== "agent") return null;
    const graph = extractGraphFromTrace(
      msg.meta?.trace,
      msg.meta?.graph,
      msg.meta?.layer_results || msg.meta?.graph?.layer_results,
    ) || msg.meta?.graph;
    if (!graph?.nodes?.length && !graph?.relationships?.length && !graph?.graph_walk_steps?.length) return null;
    return {
      text: msg.body || "",
      graph,
      trace: msg.meta?.trace || [],
      layerResults: msg.meta?.layer_results || msg.meta?.graph?.layer_results || null,
    };
  }

  function setLastReplayableWalk(payload) {
    lastReplayableWalk = payload?.graph?.nodes?.length ? payload : null;
    updateGraphReplayButton();
  }

  function syncLastReplayableFromMessages(items) {
    const agents = (items || []).filter((m) => m.msg_type === "agent");
    for (let i = agents.length - 1; i >= 0; i -= 1) {
      const payload = replayPayloadFromMessage(agents[i]);
      if (payload) {
        setLastReplayableWalk(payload);
        return;
      }
    }
    setLastReplayableWalk(null);
  }

  function updateGraphReplayButton() {
    const btn = $("chatGraphReplay");
    if (!btn) return;
    const ok = !!(lastReplayableWalk?.graph?.nodes?.length) && !graphReplayBusy;
    btn.disabled = !ok;
    btn.classList.toggle("disabled", !ok);
    btn.title = ok
      ? tt("chat_graph_replay_ok", "Пройти по графу заново")
      : (graphReplayBusy ? tt("chat_graph_replay_busy", "Обход графа…") : tt("chat_graph_replay_none", "Нет обхода для повтора"));
    updateGraphStopButton();
  }

  function updateGraphStopButton() {
    const btn = $("chatGraphStop");
    if (!btn) return;
    const active = graphReplayBusy || !!activeWalkCancel || window.MKGMiniGraph?.isWalkActive?.();
    btn.disabled = !active;
    btn.classList.toggle("hidden", !active);
    btn.title = tt("chat_graph_stop", "Остановить обход графа");
  }

  function cancelActiveGraphWalk() {
    if (activeWalkCancel) {
      try { activeWalkCancel(); } catch { /* ignore */ }
      activeWalkCancel = null;
    }
    window.MKGMiniGraph?.stopWalk?.();
    updateGraphStopButton();
  }

  function stopGraphWalk() {
    cancelActiveGraphWalk();
    graphReplayBusy = false;
    updateGraphReplayButton();
  }

  async function replayLastGraphWalk() {
    if (!lastReplayableWalk?.graph?.nodes?.length || graphReplayBusy) return;
    graphReplayBusy = true;
    updateGraphReplayButton();
    try {
      cancelActiveGraphWalk();
      await replayAnswerWithWalk({ ...lastReplayableWalk, graphOnly: true });
    } catch (err) {
      console.warn("graph walk replay failed:", err);
    } finally {
      graphReplayBusy = false;
      updateGraphReplayButton();
    }
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
    badge.textContent = rolePromptData.is_custom
      ? tt("role_prompt_custom", "· изменён")
      : tt("role_prompt_default", "· по умолчанию");
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
      showNotice(tt("role_prompt_select_role", "Сначала выберите роль"), true);
      return;
    }
    const text = ($("rolePromptText")?.value || "").trim();
    if (!text) {
      showNotice(tt("role_prompt_empty", "Промпт не может быть пустым"), true);
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
        showNotice(data.detail || tt("role_prompt_save_failed", "Не удалось сохранить промпт"), true);
        return;
      }
      rolePromptData = data;
      updatePromptBadge();
      setRolePromptOpen(false);
      showNotice(tt("role_prompt_saved", "Промпт сохранён"));
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
        showNotice(data.detail || tt("role_prompt_reset_failed", "Не удалось сбросить"), true);
        return;
      }
      rolePromptData = data;
      if ($("rolePromptText")) $("rolePromptText").value = data.system_prompt || "";
      updatePromptBadge();
      setRolePromptOpen(false);
      showNotice(tt("role_prompt_reset_ok", "Промпт по умолчанию"));
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
      const disp = roleDisplay(ro);
      const tagline = disp.tagline;
      const diff = disp.differs ? ` title="${esc(disp.differs)}"` : "";
      return `<button type="button" class="role-card role-${esc(ro.id)}${active}" data-role="${esc(ro.id)}"${diff}>
        <span class="role-card-icon">${icon}</span>
        <span class="role-card-name">${esc(disp.name)}</span>
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
    const disp = roleDisplay(role);
    header.classList.remove("hidden");
    if (badge) {
      badge.className = `user-role-badge role-${esc(role.id)}`;
      badge.textContent = `${role.icon || ROLE_ICONS[role.id] || ""} ${disp.name || role.id}`.trim();
    }
    if (cap) {
      cap.textContent = disp.capability || "";
      cap.title = disp.differs || "";
    }
  }

  function canShowUpload(role) {
    if (!role) return true;
    if (role.id === "admin" || role.can_admin) return true;
    if (role.can_upload === true) return true;
    if (role.can_upload === false) return false;
    return ["admin", "researcher", "engineer"].includes(role.id);
  }

  function canDeleteDocument(role) {
    if (!role) return true;
    if (role.id === "admin" || role.can_admin) return true;
    if (role.can_upload === false) return false;
    return ["admin", "engineer", "researcher"].includes(role.id);
  }

  function applyPermissions() {
    const roleId = currentUser?.role_id || selectedRoleId;
    const role = roleId ? roleMeta(roleId) : null;
    const uploadPanel = document.getElementById("homeTabUpload");
    const uploadBtn = $("uploadBtn");
    const clearBtn = $("clearDbBtn");
    const homeRun = $("homeAgentRunBtn");
    const showUpload = role ? canShowUpload(role) : true;
    if (uploadPanel) {
      uploadPanel.classList.toggle("upload-hidden", !showUpload);
      uploadPanel.style.display = "";
    }
    if (uploadBtn) uploadBtn.disabled = !showUpload;
    if (typeof window.MKG?.syncDocWorkDeleteBtn === "function") {
      const sel = window.MKG?.selectedDoc;
      const doc = sel ? (window.MKG?.docsListCache || []).find((d) => d.id === sel) : null;
      window.MKG.syncDocWorkDeleteBtn(doc || null);
    }
    if (typeof window.MKG?.refreshDocsList === "function" && window.MKG?.currentPage === "docs") {
      window.MKG.refreshDocsList({ silent: true });
    }
    if (clearBtn) clearBtn.style.display = role.can_admin ? "" : "none";
    if (homeRun) homeRun.disabled = role.can_run_agents === false;
    const chatAttach = $("chatAttachBtn");
    const chatHint = $("chatUploadHint");
    if (chatAttach) chatAttach.style.display = showUpload ? "" : "none";
    if (chatHint) chatHint.style.display = showUpload ? "" : "none";
    if (chatAttach) chatAttach.disabled = !showUpload;
    syncDocsUploadFallback();
    syncComposeSendButton();
    if (typeof loadDataAccessSettings === "function") loadDataAccessSettings();
  }

  function syncDocsUploadFallback() {
    const fallback = document.getElementById("docUploadFallback");
    const uploadPanel = document.getElementById("homeTabUpload");
    if (!fallback) return;
    const roleId = currentUser?.role_id || selectedRoleId;
    const role = roleId ? roleMeta(roleId) : null;
    const showUpload = canShowUpload(role);
    if (!showUpload) {
      fallback.classList.add("hidden");
      return;
    }
    const onDocs = window.MKG?.currentPage === "docs";
    let sidebarVisible = false;
    if (uploadPanel && !uploadPanel.classList.contains("upload-hidden") && uploadPanel.offsetParent !== null) {
      const rect = uploadPanel.getBoundingClientRect();
      sidebarVisible = rect.height > 40 && rect.bottom > 80 && rect.top >= 0;
    }
    fallback.classList.toggle("hidden", !onDocs || sidebarVisible);
  }

  async function fetchRoles() {
    try {
      const r = await fetch(`${API}/roles`);
      if (!r.ok) {
        renderRoleCards();
        return;
      }
      const data = await r.json();
      if (Array.isArray(data.roles) && data.roles.length) {
        roles = data.roles;
      }
    } catch { /* fallback ok */ }
    renderRoleCards();
  }

  const TRACE_LABELS = {
    chat_role: "Роль",
    chat_memory: "Память",
    qdrant_search: "Qdrant",
    qdrant_l3: "Qdrant L3",
    qdrant_l4_cluster: "L4 кластеры",
    fast_retrieval: "Поиск L3+L4",
    graph_keyword_fallback: "Fallback граф/Neo4j",
    graph_traversal: "Обход (итог)",
    graph_walk_step: "Шаг графа",
    graph_sequential_walk: "Обход графа",
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
    direct_reply: "Прямой ответ",
    orchestrator_init: "Старт",
    orchestrator_plan: "План слоёв",
    orchestrator_router: "Маршрутизатор",
    agent_loop_start: "Цикл агентов",
    agent_loop_round: "Раунд",
    hrm_budget_sampled: "HRM бюджет",
    hrm_halt_decision: "HRM решение",
    layer_loop_start: "Цикл агентов",
    l1_agent: "L1 агент",
    l2_agent: "L2 агент",
    l3_agent: "L3 агент",
    l4_agent: "L4 агент",
    l5_agent: "L5 агент",
    l6_agent: "L6 агент",
    discover_new_connections: "Новые связи",
    connection_gap_analyzer: "Пробелы",
    orchestrator_synthesize: "Синтез LLM",
  };

  /** Live preview: flexible loop order (router → agent → bus), not L1→L6. */
  const AGENT_PIPELINE_STEPS = [
    { step: "orchestrator_init" },
    { step: "orchestrator_plan", layers: ["L4", "L3", "L1"] },
    { step: "agent_loop_start", round: 0, max_rounds: 3, planned_layers: ["L4", "L3", "L1"] },
    { step: "orchestrator_router", round: 0, next_agent: "l4_agent" },
    { step: "l4_agent", layer: "L4", round: 0, loop_index: 1 },
    { bus_messages: [{ from: "l4_agent", to: "l3_agent", type: "request_evidence", round: 0 }] },
    { step: "orchestrator_router", round: 0, next_agent: "l3_agent" },
    { step: "l3_agent", layer: "L3", round: 0, loop_index: 2 },
    { step: "orchestrator_router", round: 0, next_agent: "l1_agent" },
    { step: "l1_agent", layer: "L1", round: 0, loop_index: 3 },
    { step: "agent_loop_round", round: 1, max_rounds: 3 },
    { step: "orchestrator_router", round: 1, next_agent: "l5_agent" },
    { step: "l5_agent", layer: "L5", round: 1, loop_index: 1 },
    { step: "orchestrator_router", round: 1, next_agent: "discover_new_connections" },
    { step: "discover_new_connections" },
    { step: "connection_gap_analyzer" },
    { step: "orchestrator_synthesize" },
  ];

  const DIALOG_PIPELINE_STEPS = [
    { step: "chat_role" },
    { step: "chat_memory" },
    { step: "qdrant_l3" },
    { step: "qdrant_l4_cluster" },
    { step: "graph_walk_step" },
    { step: "graph_traversal" },
    { step: "l4_agent", layer: "L4", round: 0, loop_phase: "dialog_trace", node_count: 2 },
    { step: "l3_agent", layer: "L3", round: 0, loop_phase: "dialog_trace", node_count: 1 },
    { step: "l1_agent", layer: "L1", round: 0, loop_phase: "dialog_trace", skipped: true },
    { step: "discover_new_connections" },
    { step: "llm_compose" },
  ];

  const FAST_PIPELINE_STEPS = [
    { step: "fast_retrieval", pipeline: "fast", l3_hit_count: 0, l4_hit_count: 0, hit_count: 0 },
    { step: "graph_keyword_fallback", skipped: true, hit_count: 0, optional: true },
    { step: "llm_compose" },
  ];

  const DIRECT_PIPELINE_STEPS = [
    { step: "direct_reply", intent: "greeting", skipped_retrieval: true },
    { step: "llm_compose", pipeline: "direct" },
  ];

  const PIPELINE_SETUP_STEPS = new Set([
    "orchestrator_init", "orchestrator_plan", "agent_loop_start", "layer_loop_start",
    "chat_memory", "qdrant_l3", "qdrant_l4_cluster", "fast_retrieval",
    "graph_walk_step", "graph_traversal", "retrieval_search", "graph_context_loader",
    "graph_keyword_fallback", "direct_reply",
  ]);

  const PIPELINE_TAIL_STEPS = new Set([
    "discover_new_connections", "connection_gap_analyzer", "orchestrator_synthesize", "llm_compose",
  ]);

  function agentStepToLayer(step) {
    const s = String(step || "");
    if (/^anomaly_/.test(s)) return "L4";
    const m = /^l([1-6])_agent$/.exec(s);
    return m ? `L${m[1]}` : null;
  }

  function agentStepDisplayLabel(step) {
    const s = String(step || "");
    if (/^anomaly_/.test(s)) return traceStepLabel(s);
    return agentStepToLayer(s) || s;
  }

  function agentIdToLayer(agentId) {
    const step = String(agentId || "");
    if (/^anomaly_/.test(step) || step === "anomaly_mode" || step === "anomaly_mode_builder") return "L4";
    if (/^l[1-6]_agent$/i.test(step)) return agentStepToLayer(step);
    const raw = step.replace(/_agent$/i, "").toUpperCase();
    return /^L[1-6]$/.test(raw) ? raw : null;
  }

  function normalizePipelineTraceItems(items) {
    return (items || []).map((item, i) => {
      if (typeof item === "string") return { step: item, _pid: i };
      if (item.bus_messages && !item.step) {
        return { step: "__bus__", bus_messages: item.bus_messages, _pid: i };
      }
      return { ...item, _pid: item._pid ?? i };
    });
  }

  const PIPELINE_MAX_CHIPS_PER_ROUND = 12;
  const pipelineExpandedRounds = new Set();
  const pipelineRenderCache = new Map();
  let pipelineScopeSeq = 0;

  function nextPipelineScopeId(prefix = "pipe") {
    pipelineScopeSeq += 1;
    return `${prefix}-${pipelineScopeSeq}`;
  }

  function pipelineRoundKey(scopeId, round) {
    return `${scopeId}:${round}`;
  }

  function isPipelineRoundExpanded(scopeId, round) {
    return pipelineExpandedRounds.has(pipelineRoundKey(scopeId, round));
  }

  function togglePipelineRoundExpanded(scopeId, round) {
    const key = pipelineRoundKey(scopeId, round);
    if (pipelineExpandedRounds.has(key)) pipelineExpandedRounds.delete(key);
    else pipelineExpandedRounds.add(key);
  }

  function registerPipelineRender(scopeId, model, { live = false, activeId = -1 } = {}) {
    pipelineRenderCache.set(scopeId, { model, live, activeId });
  }

  function refreshPipelineScope(scopeId) {
    const cached = pipelineRenderCache.get(scopeId);
    if (!cached) return;
    const el = document.querySelector(`.agent-pipeline[data-pipeline-id="${scopeId}"]`);
    if (!el) return;
    el.outerHTML = renderAgentPipeline(cached.model, {
      live: cached.live,
      activeId: cached.activeId,
      scopeId,
    });
  }

  function pipelineBusChipKey(m, roundNum) {
    const fromLayer = pipelineBusEndpoint(m.from);
    const toLayer = pipelineBusEndpoint(m.to);
    const round = m.round ?? roundNum ?? 0;
    return `${round}|${fromLayer}|${toLayer}|${m.type || ""}`;
  }

  function pipelineBusEndpoint(ep) {
    const raw = String(ep || "").toLowerCase();
    if (!raw || raw === "broadcast") return "broadcast";
    return agentIdToLayer(raw) || raw;
  }

  function pipelineBusEndpointLabel(ep) {
    if (!ep || String(ep).toLowerCase() === "broadcast") return "all";
    return agentIdToLayer(ep) || ep;
  }

  function pipelineAgentChipKey(item) {
    const step = item.step || "";
    if (/^anomaly_/.test(step)) return `anomaly:${step}:${item.round ?? 0}`;
    const layer = item.layer || agentStepToLayer(step) || "";
    return `${item.round ?? 0}|${layer}|${item.skipped ? 1 : 0}`;
  }

  function capPipelineRoundItems(items, max = PIPELINE_MAX_CHIPS_PER_ROUND) {
    if (!items?.length || items.length <= max) return { items: items || [], overflow: 0 };
    return { items: items.slice(0, max), overflow: items.length - max };
  }

  function pipelineModelFingerprint(model, { live = false, activeId = -1, scopeId = "default" } = {}) {
    const parts = [`live:${live ? 1 : 0}`, `active:${activeId}`];
    model.setup.forEach((item) => parts.push(`s:${item.step}`));
    model.rounds.forEach((round) => {
      parts.push(`r:${round.round}`);
      if (round.overflow) parts.push(`ov:${round.overflow}`);
      if (isPipelineRoundExpanded(scopeId, round.round)) parts.push(`exp:${round.round}`);
      round.items.forEach((item) => {
        if (item.kind === "agent") {
          parts.push(`a:${pipelineAgentChipKey(item)}`);
        } else if (item.kind === "bus") {
          parts.push(`b:${pipelineBusChipKey(item, item.round)}:${item.count || 1}`);
        } else if (item.kind === "layer_batch") {
          item.agents.forEach((a) => parts.push(`lb:${pipelineAgentChipKey(a)}`));
        } else if (item.kind === "router") {
          parts.push(`rt:${item.next_agent || ""}`);
        } else {
          parts.push(`${item.kind}:${item.step || item.id || ""}`);
        }
      });
    });
    model.tail.forEach((item) => parts.push(`t:${item.step}`));
    return parts.join("|");
  }

  function inferTracePipelineKind(trace) {
    const items = trace || [];
    if (items.some((raw) => {
      const step = typeof raw === "string" ? raw : raw.step;
      return step === "agent_loop_start" || step === "layer_loop_start"
        || String(step || "").startsWith("orchestrator");
    })) return "orchestrator";
    if (items.some((raw) => {
      const t = typeof raw === "string" ? { step: raw } : raw;
      return t.pipeline === "fast" || t.step === "fast_retrieval" || t.speed_mode === "fast";
    })) return "fast";
    return "dialog";
  }

  function buildPipelineModel(trace) {
    const pipelineKind = inferTracePipelineKind(trace);
    const setup = [];
    const tail = [];
    const roundMap = new Map();
    let currentRound = 0;
    let maxRounds = 4;
    let seq = 0;
    let dialogLayerBatch = null;
    const seenBusKeys = new Map();
    const seenAgentKeys = new Set();
    const seenRouterKeys = new Set();

    const flushDialogLayers = () => {
      if (!dialogLayerBatch?.length) return;
      const r = dialogLayerBatch[0].round ?? 0;
      const agents = [];
      const batchSeen = new Set();
      dialogLayerBatch.forEach((a) => {
        const k = pipelineAgentChipKey(a);
        if (batchSeen.has(k)) return;
        batchSeen.add(k);
        agents.push(a);
      });
      const bucket = ensureRound(r);
      bucket.items.push({
        kind: "layer_batch",
        round: r,
        agents,
        id: seq++,
      });
      dialogLayerBatch = null;
    };

    const ensureRound = (roundNum) => {
      const r = Number.isFinite(roundNum) ? roundNum : 0;
      if (!roundMap.has(r)) roundMap.set(r, { round: r, items: [] });
      return roundMap.get(r);
    };

    const pushBusMessages = (messages, roundNum) => {
      (messages || []).forEach((m) => {
        const round = m.round ?? roundNum ?? currentRound;
        const busKey = pipelineBusChipKey(m, round);
        const existing = seenBusKeys.get(busKey);
        if (existing) {
          existing.count = (existing.count || 1) + 1;
          return;
        }
        const item = {
          kind: "bus",
          from: m.from,
          to: m.to,
          type: m.type,
          preview: m.preview,
          round,
          count: 1,
          id: seq++,
        };
        seenBusKeys.set(busKey, item);
        ensureRound(round).items.push(item);
      });
    };

    const pushAgentItem = (agentItem) => {
      const agentKey = pipelineAgentChipKey(agentItem);
      if (seenAgentKeys.has(agentKey)) return false;
      seenAgentKeys.add(agentKey);
      ensureRound(agentItem.round ?? currentRound).items.push(agentItem);
      return true;
    };

    (trace || []).forEach((raw) => {
      const t = typeof raw === "string" ? { step: raw } : raw;
      const step = t.step || "";

      if (step === "agent_loop_start" || step === "layer_loop_start") {
        flushDialogLayers();
        currentRound = t.round ?? 0;
        maxRounds = t.max_rounds ?? maxRounds;
        if (t.loop_phase === "dialog_trace") {
          dialogLayerBatch = [];
        } else {
          ensureRound(currentRound).items.push({ kind: "loop_start", ...t, id: seq++ });
        }
        return;
      }

      if (PIPELINE_SETUP_STEPS.has(step)) {
        flushDialogLayers();
        if (pipelineKind === "orchestrator" && (step === "chat_role" || step === "chat_memory")) {
          return;
        }
        if (pipelineKind === "fast" && (step === "chat_role" || step === "chat_memory")) {
          return;
        }
        if (pipelineKind === "direct" && (step === "chat_role" || step === "chat_memory")) {
          return;
        }
        if (pipelineKind === "fast" && step === "graph_keyword_fallback" && t.skipped) {
          return;
        }
        setup.push({ kind: "setup", step, data: t, id: seq++ });
        return;
      }

      if (step === "chat_role") {
        flushDialogLayers();
        if (pipelineKind === "orchestrator" || pipelineKind === "direct") return;
        setup.push({ kind: "setup", step, data: t, id: seq++ });
        return;
      }

      if (step === "agent_loop_round") {
        flushDialogLayers();
        currentRound = t.round ?? currentRound + 1;
        maxRounds = t.max_rounds ?? maxRounds;
        ensureRound(currentRound).items.push({ kind: "round_marker", ...t, id: seq++ });
        return;
      }

      if (step === "hrm_budget_sampled") {
        flushDialogLayers();
        maxRounds = t.sampled_budget ?? t.hard_cap ?? maxRounds;
        setup.push({ kind: "setup", step, data: t, id: seq++ });
        return;
      }

      if (step === "hrm_halt_decision") {
        flushDialogLayers();
        currentRound = t.round ?? currentRound;
        ensureRound(currentRound).items.push({ kind: "hrm", step, ...t, data: t, id: seq++ });
        return;
      }

      if (step === "orchestrator_router") {
        flushDialogLayers();
        currentRound = t.round ?? currentRound;
        const routerKey = `${currentRound}|${t.next_agent || ""}`;
        if (!seenRouterKeys.has(routerKey)) {
          seenRouterKeys.add(routerKey);
          ensureRound(currentRound).items.push({ kind: "router", ...t, id: seq++ });
        }
        return;
      }

      if (/^l[1-6]_agent$/.test(step)) {
        const agentItem = {
          kind: "agent",
          step,
          layer: t.layer || agentStepToLayer(step),
          round: t.round ?? currentRound,
          skipped: !!t.skipped,
          loop_index: t.loop_index,
          id: seq++,
          data: t,
        };
        if (t.loop_phase === "dialog_trace" && dialogLayerBatch) {
          dialogLayerBatch.push(agentItem);
          return;
        }
        flushDialogLayers();
        currentRound = agentItem.round;
        pushAgentItem(agentItem);
        pushBusMessages(t.bus_messages, currentRound);
        return;
      }

      if (/^anomaly_/.test(step)) {
        flushDialogLayers();
        const agentItem = {
          kind: "agent",
          step,
          layer: t.layer || "L4",
          agent_kind: "anomaly",
          round: t.round ?? currentRound,
          skipped: false,
          id: seq++,
          data: t,
        };
        pushAgentItem(agentItem);
        return;
      }

      if (step === "__bus__" || (t.bus_messages && !step)) {
        flushDialogLayers();
        pushBusMessages(t.bus_messages, currentRound);
        return;
      }

      if (PIPELINE_TAIL_STEPS.has(step)) {
        flushDialogLayers();
        tail.push({ kind: "tail", step, data: t, id: seq++ });
        return;
      }
    });

    flushDialogLayers();

    for (let r = 0; r < maxRounds; r += 1) {
      ensureRound(r);
    }

    const rounds = [...roundMap.values()]
      .sort((a, b) => a.round - b.round)
      .map((round) => {
        const capped = capPipelineRoundItems(round.items);
        return {
          round: round.round,
          items: capped.items,
          allItems: round.items,
          overflow: capped.overflow,
        };
      });
    const flatItems = [
      ...setup.slice(0, 8),
      ...rounds.flatMap((r) => r.items),
      ...tail.slice(0, 6),
    ];

    return { setup: setup.slice(0, 8), rounds, tail: tail.slice(0, 6), maxRounds, flatItems };
  }

  function pipelineItemState(item, { live, activeId }) {
    if (!live) return "done";
    if (item.id == null) return "pending";
    if (item.id < activeId) return "done";
    if (item.id === activeId) return "active";
    return "pending";
  }

  function renderPipelineAgentChip(item, state) {
    const isAnomaly = item.agent_kind === "anomaly" || /^anomaly_/.test(item.step || "");
    const layer = isAnomaly ? agentStepDisplayLabel(item.step) : (item.layer || agentStepToLayer(item.step) || "?");
    const skipped = item.skipped ? " skipped" : "";
    const layerCls = isAnomaly ? " layer-L4 anomaly-agent" : (/^L[1-6]$/.test(item.layer || "") ? ` layer-${item.layer}` : "");
    const detail = item.data ? traceStepDetail(item.data) : "";
    const title = detail ? `${layer} · ${detail}` : layer;
    const roundTag = item.round != null ? `<span class="agent-pipeline-round-tag">R${item.round}</span>` : "";
    return `<span class="agent-pipeline-agent${layerCls}${skipped} st-${state}" title="${esc(title)}">${roundTag}<span class="agent-pipeline-agent-label">${esc(layer)}</span></span>`;
  }

  function renderPipelineRouterChip(item, state) {
    const nxt = item.next_agent || "?";
    const layer = agentIdToLayer(nxt);
    const label = layer || traceStepLabel(nxt);
    return `<span class="agent-pipeline-router st-${state}" title="маршрутизатор → ${esc(label)}">↪ ${esc(label)}</span>`;
  }

  function renderPipelineHrmChip(item, state) {
    const halt = item.decision === "halt";
    const icon = halt ? "⏹" : "↻";
    const word = halt ? "стоп" : "ещё цикл";
    const gain = item.marginal_gain != null ? ` +${item.marginal_gain}` : "";
    const conf = item.confidence != null ? ` · ${Math.round(item.confidence * 100)}%` : "";
    const budget = item.sampled_budget != null ? ` · бюджет ${(item.round ?? 0) + 1}/${item.sampled_budget}` : "";
    const title = `HRM: ${word}${gain ? ` · прирост${gain}` : ""}${conf}${budget}${item.reason ? ` · ${item.reason}` : ""}${item.source ? ` [${item.source}]` : ""}`;
    return `<span class="agent-pipeline-hrm st-${state}${halt ? " hrm-halt" : " hrm-continue"}" title="${esc(title)}">${icon} HRM ${esc(word)}${esc(gain)}</span>`;
  }

  function renderPipelineBusChip(item, state) {
    const fromLayer = pipelineBusEndpointLabel(item.from);
    const toLayer = pipelineBusEndpointLabel(item.to);
    const type = item.type ? ` · ${item.type}` : "";
    const count = item.count > 1 ? ` ×${item.count}` : "";
    const title = `${fromLayer} → ${toLayer}${type}${count}`;
    return `<span class="agent-pipeline-bus st-${state}" title="${esc(title)}"><span class="agent-pipeline-bus-icon" aria-hidden="true">⇄</span><span class="agent-pipeline-bus-label">Шина</span><span class="agent-pipeline-bus-route">${esc(fromLayer)}→${esc(toLayer)}</span>${item.count > 1 ? `<span class="agent-pipeline-bus-count">×${item.count}</span>` : ""}</span>`;
  }

  function renderPipelineOverflowChip(count, scopeId, round) {
    const expandLabel = tt("expand_stages", "Развернуть");
    const title = tf("pipeline_overflow_title", { count }, `Ещё ${count} шагов · ${expandLabel}`);
    return `<button type="button" class="agent-pipeline-overflow agent-pipeline-expand muted" data-pipeline-scope="${esc(scopeId)}" data-round="${round}" title="${esc(title)}" aria-label="${esc(expandLabel)}">+${count}</button>`;
  }

  function renderPipelineCollapseBtn(scopeId, round) {
    const label = tt("collapse_stages", "Свернуть");
    return `<button type="button" class="agent-pipeline-expand agent-pipeline-collapse muted" data-pipeline-scope="${esc(scopeId)}" data-round="${round}" title="${esc(label)}" aria-label="${esc(label)}">${esc(label)}</button>`;
  }

  function renderPipelineSetupChip(item, state) {
    const label = traceStepLabel(item.step);
    const detail = item.data ? traceStepDetail(item.data) : "";
    return `<span class="agent-pipeline-setup-chip st-${state}" title="${esc(detail || label)}">${esc(label)}${detail ? `<span class="agent-pipeline-meta">${esc(detail)}</span>` : ""}</span>`;
  }

  function renderPipelineTailChip(item, state) {
    const label = traceStepLabel(item.step);
    const detail = item.data ? traceStepDetail(item.data) : "";
    return `<span class="agent-pipeline-tail-chip st-${state}" title="${esc(detail || label)}">${esc(label)}</span>`;
  }

  function joinPipelineTrack(items, opts) {
    const parts = [];
    items.forEach((item, i) => {
      let html = "";
      if (item.kind === "agent") html = renderPipelineAgentChip(item, pipelineItemState(item, opts));
      else if (item.kind === "router") html = renderPipelineRouterChip(item, pipelineItemState(item, opts));
      else if (item.kind === "bus") html = renderPipelineBusChip(item, pipelineItemState(item, opts));
      else if (item.kind === "layer_batch") {
        html = item.agents.map((a) => renderPipelineAgentChip(a, pipelineItemState(a, opts))).join("");
      } else if (item.kind === "loop_start" || item.kind === "round_marker") {
        html = `<span class="agent-pipeline-round-start st-${pipelineItemState(item, opts)}">●</span>`;
      } else if (item.kind === "hrm") {
        html = renderPipelineHrmChip(item, pipelineItemState(item, opts));
      }
      if (!html) return;
      if (parts.length) {
        const prev = items[i - 1];
        const arrowCls = item.kind === "bus" || prev?.kind === "bus"
          ? "agent-pipeline-link bus"
          : "agent-pipeline-link";
        parts.push(`<span class="${arrowCls}" aria-hidden="true">${item.kind === "bus" ? "⇄" : "→"}</span>`);
      }
      parts.push(html);
    });
    return parts.join("");
  }

  function renderAgentPipeline(traceOrModel, { live = false, activeId = -1, scopeId = "default" } = {}) {
    const model = traceOrModel?.flatItems ? traceOrModel : buildPipelineModel(traceOrModel);
    const opts = { live, activeId };
    if (!model.setup.length && !model.rounds.length && !model.tail.length) return "";

    registerPipelineRender(scopeId, model, { live, activeId });

    const setupHtml = model.setup.length
      ? `<div class="agent-pipeline-setup">${model.setup.map((item) => renderPipelineSetupChip(item, pipelineItemState(item, opts))).join('<span class="agent-pipeline-link" aria-hidden="true">→</span>')}</div>`
      : "";

    const roundsHtml = model.rounds.length
      ? `<div class="agent-pipeline-rounds">${model.rounds.map((round) => {
        const maxR = model.maxRounds || "?";
        const expanded = isPipelineRoundExpanded(scopeId, round.round);
        const displayItems = expanded && round.allItems ? round.allItems : round.items;
        const track = joinPipelineTrack(displayItems, opts);
        const overflow = !expanded && round.overflow
          ? renderPipelineOverflowChip(round.overflow, scopeId, round.round)
          : "";
        const collapseBtn = expanded && round.overflow
          ? renderPipelineCollapseBtn(scopeId, round.round)
          : "";
        const roundCls = expanded ? " agent-bus-expanded" : "";
        return `<div class="agent-pipeline-round${roundCls}" data-round="${round.round}">
          <div class="agent-pipeline-round-head"><span class="agent-pipeline-round-id">R${round.round}</span><span class="agent-pipeline-round-cap muted">/${maxR}</span></div>
          <div class="agent-pipeline-round-track">${track || '<span class="muted small">…</span>'}${overflow}${collapseBtn}</div>
        </div>`;
      }).join("")}</div>`
      : "";

    const tailHtml = model.tail.length
      ? `<div class="agent-pipeline-tail">${model.tail.map((item) => renderPipelineTailChip(item, pipelineItemState(item, opts))).join('<span class="agent-pipeline-link" aria-hidden="true">→</span>')}</div>`
      : "";

    return `<div class="agent-pipeline${live ? " is-live" : ""}" data-pipeline-id="${esc(scopeId)}">${setupHtml}${roundsHtml}${tailHtml}</div>`;
  }

  function inferAgentQuestion(ws) {
    const label = ws.label || ws.node_id || "?";
    const snippet = String(ws.snippet || "").slice(0, 50);
    const name = snippet || label;
    if (ws.action === "seed_load") return `С чего начать: что известно о «${name}»?`;
    if (ws.rel_type) {
      const rel = String(ws.rel_type).replace(/_/g, " ");
      return `Как «${name}» (${label}) связан через ${rel}?`;
    }
    return `Что можно узнать о ${label}: «${name}»?`;
  }

  function extractWalkSteps(trace, graph) {
    const fromTrace = (trace || []).filter((t) => t.step === "graph_walk_step");
    const fromGraph = graph?.graph_walk_steps || [];
    const raw = fromTrace.length ? fromTrace : fromGraph;
    return raw.map((ws) => ({
      ...ws,
      agent_question: ws.agent_question || inferAgentQuestion(ws),
    }));
  }

  function extractBusMessages(trace) {
    const msgs = [];
    (trace || []).forEach((t) => {
      const bus = t.bus_messages || t.bus_preview || [];
      bus.forEach((m) => {
        msgs.push({
          ...m,
          step: t.step,
          round: m.round ?? t.round ?? null,
        });
      });
    });
    return msgs;
  }

  function extractLoopMeta(trace) {
    const start = (trace || []).find((t) => t.step === "agent_loop_start" || t.step === "layer_loop_start");
    const rounds = (trace || []).filter((t) => t.step === "agent_loop_round");
    const routers = (trace || []).filter((t) => t.step === "orchestrator_router");
    return {
      round: start?.round ?? 0,
      max_rounds: start?.max_rounds ?? 4,
      round_count: rounds.length + 1,
      last_router: routers[routers.length - 1] || null,
      planned_layers: start?.planned_layers || [],
    };
  }

  function extractLayerAgentSteps(trace, layerResults) {
    const fromTrace = (trace || [])
      .filter((t) => /^l[1-6]_agent$/.test(t.step || "") || t.step === "anomaly_mode_builder")
      .map((t, i) => ({
        step: t.step,
        layer: /^anomaly_/.test(t.step || "") ? agentStepDisplayLabel(t.step) : (t.layer || String(t.step || "").replace("_agent", "").toUpperCase()),
        loop_index: t.loop_index ?? i + 1,
        loop_total: t.loop_total ?? 6,
        loop_phase: t.loop_phase || "",
        round: t.round ?? null,
        max_rounds: t.max_rounds ?? null,
        node_count: t.node_count ?? t.anomaly_count ?? 0,
        rel_count: t.rel_count ?? 0,
        situation: t.situation_evaluation || t.reasoning || "",
        agent_question: t.agent_question || "",
        bus_messages: t.bus_messages || [],
        skipped: !!t.skipped,
        agent_kind: /^anomaly_/.test(t.step || "") ? "anomaly" : "",
      }));
    if (fromTrace.length) return fromTrace;
    return (layerResults || []).map((lr, i) => ({
      layer: lr.layer || "?",
      loop_index: i + 1,
      loop_total: 6,
      loop_phase: "layer_results",
      round: null,
      node_count: lr.nodes_found?.length ?? lr.node_count ?? 0,
      rel_count: lr.edges_found?.length ?? lr.rel_count ?? 0,
      situation: lr.situation_evaluation || lr.reasoning_step || "",
      agent_question: lr.agent_question || "",
      bus_messages: [],
      skipped: !(lr.nodes_found?.length || lr.node_count),
    }));
  }

  function collectTraceRoundNums(trace, loopMeta) {
    const nums = new Set();
    (trace || []).forEach((t) => {
      if (t.round == null) return;
      if (
        t.step === "agent_loop_round"
        || t.step === "agent_loop_start"
        || t.step === "layer_loop_start"
        || t.step === "orchestrator_router"
        || /^l[1-6]_agent$/.test(t.step || "")
        || /^anomaly_/.test(t.step || "")
      ) {
        nums.add(Number(t.round));
      }
    });
    const countFromMeta = loopMeta?.round_count ?? 0;
    if (countFromMeta > 1) {
      for (let i = 0; i < countFromMeta; i += 1) nums.add(i);
    } else if (!nums.size && countFromMeta === 1) {
      nums.add(0);
    }
    if (!nums.size) nums.add(0);
    return [...nums].sort((a, b) => a - b);
  }

  function buildRoundModel(steps, loopMeta, trace) {
    const byRound = new Map();
    for (const s of steps) {
      const r = s.round ?? 0;
      if (!byRound.has(r)) byRound.set(r, []);
      byRound.get(r).push(s);
    }
    const roundNums = collectTraceRoundNums(trace, loopMeta);
    for (const r of roundNums) {
      if (!byRound.has(r)) byRound.set(r, []);
    }
    const maxR = loopMeta?.max_rounds ?? (roundNums.length ? Math.max(...roundNums) + 1 : 1);
    const defaultRound = roundNums[0] ?? 0;
    return { byRound, roundNums, maxR, defaultRound };
  }

  function roundPanelCls(round, activeRound) {
    return round === activeRound ? "" : " is-round-hidden";
  }

  function renderRoundNav(roundModel) {
    const { roundNums, maxR, defaultRound } = roundModel;
    if (roundNums.length <= 1 && maxR <= 1) return "";
    const curHuman = defaultRound + 1;
    const idx = roundNums.indexOf(defaultRound);
    const atFirst = idx <= 0;
    const atLast = idx >= roundNums.length - 1;
    return `<div class="layer-round-nav" data-round="${defaultRound}" data-rounds="${roundNums.join(",")}" data-max="${maxR}">
      <button type="button" class="layer-round-btn layer-round-prev" aria-label="Предыдущий раунд"${atFirst ? " disabled" : ""}>◀</button>
      <span class="layer-round-indicator">раунд <span class="layer-round-current">${curHuman}</span>/<span class="layer-round-max">${maxR}</span></span>
      <button type="button" class="layer-round-btn layer-round-next" aria-label="Следующий раунд"${atLast ? " disabled" : ""}>▶</button>
    </div>`;
  }

  function setLayerRoundNav(detailsEl, round) {
    const nav = detailsEl?.querySelector(".layer-round-nav");
    if (!nav) return;
    const rounds = nav.dataset.rounds.split(",").map(Number);
    const maxR = Number(nav.dataset.max) || rounds.length;
    if (!rounds.includes(round)) return;
    nav.dataset.round = String(round);
    detailsEl.dataset.selectedRound = String(round);
    const curEl = nav.querySelector(".layer-round-current");
    if (curEl) curEl.textContent = String(round + 1);
    const maxEl = nav.querySelector(".layer-round-max");
    if (maxEl) maxEl.textContent = String(maxR);
    const idx = rounds.indexOf(round);
    const prevBtn = nav.querySelector(".layer-round-prev");
    const nextBtn = nav.querySelector(".layer-round-next");
    if (prevBtn) prevBtn.disabled = idx <= 0;
    if (nextBtn) nextBtn.disabled = idx >= rounds.length - 1;
    detailsEl.querySelectorAll("[data-round]").forEach((el) => {
      if (el.classList.contains("layer-round-nav")) return;
      const r = Number(el.dataset.round);
      el.classList.toggle("is-round-hidden", r !== round);
    });
  }

  function handleLayerRoundNavClick(e) {
    const target = e.target instanceof Element ? e.target : e.target?.parentElement;
    const btn = target?.closest?.(".layer-round-prev, .layer-round-next");
    if (!btn || btn.disabled) return;
    e.preventDefault();
    e.stopPropagation();
    const detailsEl = btn.closest(".chat-layer-agents");
    const nav = detailsEl?.querySelector(".layer-round-nav");
    if (!nav) return;
    const rounds = nav.dataset.rounds.split(",").map(Number);
    const cur = Number(nav.dataset.round);
    const idx = rounds.indexOf(cur);
    if (btn.classList.contains("layer-round-prev") && idx > 0) {
      setLayerRoundNav(detailsEl, rounds[idx - 1]);
    } else if (btn.classList.contains("layer-round-next") && idx < rounds.length - 1) {
      setLayerRoundNav(detailsEl, rounds[idx + 1]);
    }
  }

  function ensureLayerRoundNavDelegation() {
    const root = $("chatMessages");
    if (!root || layerRoundNavDelegated) return;
    layerRoundNavDelegated = true;
    root.addEventListener("click", handleLayerRoundNavClick);
  }

  function captureLayerAgentsUiState(container) {
    const state = new Map();
    container?.querySelectorAll(".chat-layer-agents[data-msg-id]").forEach((det) => {
      const nav = det.querySelector(".layer-round-nav");
      const roundRaw = nav?.dataset.round ?? det.dataset.selectedRound;
      const round = roundRaw != null && roundRaw !== "" ? Number(roundRaw) : null;
      if (round != null) layerAgentsRoundByMsg.set(det.dataset.msgId, round);
      state.set(det.dataset.msgId, {
        open: det.open,
        round,
      });
    });
    return state;
  }

  function restoreLayerAgentsUiState(container, state) {
    if (!container || !state?.size) return;
    container.querySelectorAll(".chat-layer-agents[data-msg-id]").forEach((det) => {
      const saved = state.get(det.dataset.msgId);
      if (!saved) return;
      if (saved.open) det.open = true;
      if (saved.round != null && det.querySelector(".layer-round-nav")) {
        setLayerRoundNav(det, saved.round);
      }
    });
  }

  function renderAgentBusHtml(trace, round = null, { open = false } = {}) {
    let msgs = extractBusMessages(trace);
    if (round != null) msgs = msgs.filter((m) => m.round === round);
    if (!msgs.length) return "";
    const rows = msgs.map((m) => {
      const preview = m.preview ? `<span class="agent-bus-preview">${esc(m.preview)}</span>` : "";
      const round = m.round != null ? `<span class="agent-bus-round">R${m.round}</span>` : "";
      return `<li class="agent-bus-row">
        ${round}<span class="agent-bus-route">${esc(m.from || "?")} → ${esc(m.to || "?")}</span>
        <span class="agent-bus-type muted">${esc(m.type || "")}</span>
        ${preview}
      </li>`;
    }).join("");
    const openAttr = open ? " open" : "";
    return `<details class="chat-agent-bus"${openAttr}>
      <summary>Шина агентов · ${msgs.length} сообщ.</summary>
      <ul class="agent-bus-list">${rows}</ul>
    </details>`;
  }

  function renderLayerLoopFlowHtml(steps, loopMeta) {
    if (!steps.length) return "";
    const meta = loopMeta || {};
    const roundBadge = meta.max_rounds
      ? `<span class="layer-loop-round-badge">раунд ${meta.round_count || 1}/${meta.max_rounds}</span>`
      : "";
    const chips = steps.map((s, i) => {
      const num = s.loop_index || i + 1;
      const cls = s.skipped ? "layer-loop-step skipped" : "layer-loop-step done";
      const roundTag = s.round != null ? ` R${s.round}` : "";
      const phase = s.loop_phase === "refinement" ? " · уточн." : s.loop_phase === "flexible_bus" ? "" : "";
      return `<span class="${cls}" title="шаг ${num} · ${esc(s.layer)}${roundTag}${phase}">
        <span class="layer-loop-num">${esc(s.layer)}</span>${roundTag ? `<span class="layer-loop-round">${roundTag.trim()}</span>` : ""}
      </span>`;
    }).join('<span class="layer-loop-arrow" aria-hidden="true">·</span>');
    return `<div class="layer-loop-flow" aria-label="Гибкий цикл агентов">${roundBadge}${chips}</div>`;
  }

  function renderLayerAgentRow(s, i, activeRound) {
    const num = s.loop_index || i + 1;
    const round = s.round ?? 0;
    const isAnomaly = s.agent_kind === "anomaly" || /^anomaly_/.test(s.step || "");
    const statusCls = s.skipped ? "layer-agent-skipped" : (isAnomaly ? "layer-agent-anomaly" : "layer-agent-active");
    const status = s.skipped
      ? (isAnomaly ? "нет аномалий" : "нет данных")
      : (isAnomaly ? `${s.node_count} аном.` : `${s.node_count} узл · ${s.rel_count} св`);
    const situation = s.situation
      ? `<span class="layer-agent-situation">${esc(s.situation)}</span>`
      : "";
    const question = s.agent_question
      ? `<span class="graph-walk-agent-q">${esc(s.agent_question)}</span>`
      : "";
    const phaseHint = s.loop_phase === "refinement"
      ? '<span class="layer-loop-phase-tag">уточнение</span>'
      : "";
    const roundHint = s.round != null ? `<span class="layer-loop-phase-tag">R${s.round}</span>` : "";
    const busHint = (s.bus_messages || []).length
      ? `<span class="agent-bus-inline muted">шина: ${s.bus_messages.length}</span>`
      : "";
    const hiddenCls = roundPanelCls(round, activeRound);
    return `<li class="layer-agent-row ${statusCls}${hiddenCls}" data-round="${round}">
      <span class="layer-agent-id" title="шаг ${num}">${esc(s.layer)}</span>
      <div class="layer-agent-body">
        <strong>${esc(s.layer)}${roundHint ? ` ${roundHint}` : ""}${phaseHint ? ` ${phaseHint}` : ""}</strong>
        <span class="layer-agent-status muted">${esc(status)}${busHint ? ` · ${busHint}` : ""}</span>
        ${situation}
        ${question}
      </div>
    </li>`;
  }

  function renderLayerAgentsHtml(trace, layerResults, selectedRound = null, msgId = null, { open = false } = {}) {
    const steps = extractLayerAgentSteps(trace, layerResults);
    if (!steps.length) return "";
    const loopMeta = extractLoopMeta(trace);
    const roundModel = buildRoundModel(steps, loopMeta, trace);
    const { roundNums, maxR } = roundModel;
    const defaultRound = selectedRound != null && roundNums.includes(selectedRound)
      ? selectedRound
      : roundModel.defaultRound;
    const flows = roundNums.map((r) => {
      const roundSteps = roundModel.byRound.get(r) || [];
      const flowMeta = { ...loopMeta, round: r, round_count: r + 1 };
      return `<div class="layer-loop-flow-panel${roundPanelCls(r, defaultRound)}" data-round="${r}">${renderLayerLoopFlowHtml(roundSteps, flowMeta)}</div>`;
    }).join("");
    const busPanels = roundNums.map((r) => {
      const bus = renderAgentBusHtml(trace, r, { open });
      if (!bus) return "";
      return `<div class="layer-round-bus-panel${roundPanelCls(r, defaultRound)}" data-round="${r}">${bus}</div>`;
    }).join("");
    const rows = steps.map((s, i) => renderLayerAgentRow(s, i, defaultRound)).join("");
    const maxLabel = loopMeta.max_rounds || maxR || "?";
    const navModel = { ...roundModel, defaultRound };
    const nav = renderRoundNav(navModel);
    const msgAttr = msgId ? ` data-msg-id="${esc(msgId)}"` : "";
    const openAttr = open ? " open" : "";
    return `<details class="chat-layer-agents" data-selected-round="${defaultRound}"${msgAttr}${openAttr}>
      <summary>Агенты · гибкий цикл (до ${maxLabel} раундов)</summary>
      ${nav}
      ${flows}
      ${busPanels}
      <ul class="layer-agent-list">${rows}</ul>
    </details>`;
  }

  function extractLayerQuestions(trace) {
    return (trace || [])
      .filter((t) => /^l[1-6]_agent$/.test(t.step || "") && t.agent_question)
      .map((t) => ({ layer: t.layer, question: t.agent_question }));
  }

  function showAgentQuestion(text) {
    const el = $("chatAgentQuestions");
    if (!el || !text) return;
    el.innerHTML = `<p class="chat-agent-question">${esc(text)}</p>`;
    scrollChatToBottom(false);
  }

  function clearAgentQuestions() {
    const el = $("chatAgentQuestions");
    if (el) el.innerHTML = "";
  }

  function resetThreadViewState({ clearGraph = true } = {}) {
    cancelActiveGraphWalk();
    stopAnswerSectionWalk();
    removeStreamPreview();
    clearAgentQuestions();
    hideTraceLive();
    showTyping(false);
    setChatGraphBuilding(false);
    stopGraphPoll();
    syncComposeSendButton();
    if (clearGraph) {
      lastFullscreenGraph = null;
      lastFullscreenTrace = null;
      liveAccumulatedGraph = null;
      setLastReplayableWalk(null);
      updateChatGraphStats(null);
      window.MKGMiniGraph?.destroy($("chatGraphCanvas"));
    }
  }

  function findLastAgentMessage(items) {
    const list = items || [];
    for (let i = list.length - 1; i >= 0; i -= 1) {
      if (list[i].msg_type === "agent") return list[i];
    }
    return null;
  }

  function restoreThreadUiFromMessages(items) {
    const lastAgent = findLastAgentMessage(items);
    if (lastAgent?.meta?.speed_mode) {
      setChatSpeedMode(lastAgent.meta.speed_mode, { persistGlobal: false });
    }
    if (chatBusy) return;
    if (lastAgent?.meta?.trace?.length) {
      showTraceComplete(lastAgent.meta.trace);
    } else {
      hideTraceLive();
    }
  }

  function removeStreamPreview() {
    if (activeStreamPreview?.parentNode) {
      activeStreamPreview.remove();
    }
    activeStreamPreview = null;
  }

  function ensureStreamPreview() {
    if (activeStreamPreview?.isConnected) return activeStreamPreview;
    const box = $("chatMessages");
    if (!box) return null;
    const role = roleMeta(currentUser?.role_id);
    const disp = roleDisplay(role);
    const article = document.createElement("article");
    article.className = "chat-msg msg-agent chat-stream-preview";
    article.innerHTML = `
      <div class="chat-msg-avatar" aria-hidden="true">AI</div>
      <div class="chat-msg-content">
        <header>
          <strong>MKG AI</strong>
          <span class="user-role-badge role-${esc(role.id)}">${esc(disp.name || role.id)}</span>
          <span class="chat-mode-badge">Формирование ответа…</span>
        </header>
        <div class="chat-stream-trace" id="chatStreamTrace"></div>
        <div class="chat-msg-body md-render-view"></div>
      </div>`;
    box.appendChild(article);
    activeStreamPreview = article;
    scrollChatToBottom(false);
    return article;
  }

  function mountCompletedTraceInPreview(trace) {
    if (!trace?.length) return;
    const preview = ensureStreamPreview();
    const slot = preview?.querySelector(".chat-stream-trace");
    if (!slot) return;
    const scopeId = nextPipelineScopeId("preview");
    const model = buildPipelineModel(trace);
    const pipeline = renderAgentPipeline(model, { live: false, activeId: -1, scopeId });
    slot.innerHTML = pipeline
      ? `<details class="chat-agent-pipeline-trace"><summary>${esc(tt("chat_pipeline", "Пайплайн"))}</summary>${pipeline}</details>`
      : "";
    scrollChatToBottom(false);
  }

  function updateStreamPreviewBody(text) {
    const preview = ensureStreamPreview();
    const body = preview?.querySelector(".chat-msg-body");
    if (body) body.innerHTML = renderAgentAnswerHtml(text);
    scrollChatToBottom(false);
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async function typewriterReveal(fullText, { totalMs = 2400, chunkMs = TYPEWRITER_MAX_MS, prefix = "" } = {}) {
    const text = String(fullText || "");
    if (!text && !prefix) return;
    ensureStreamPreview();
    const step = Math.max(1, Math.ceil(text.length / Math.max(1, Math.floor(totalMs / chunkMs))));
    for (let i = step; i <= text.length; i += step) {
      updateStreamPreviewBody(prefix + text.slice(0, i));
      await sleep(chunkMs);
    }
    updateStreamPreviewBody(prefix + text);
  }

  async function replayAnswerWithWalk({ text, graph, trace, layerResults, graphOnly = false } = {}) {
    const walkSteps = extractWalkSteps(trace, graph);
    const walkPath = (graph?.walk_path?.length ? graph.walk_path : walkSteps).map((s) => ({
      node_id: s.node_id,
      from_id: s.from_id,
      rel_type: s.rel_type,
      hop: s.hop,
      action: s.action,
      agent_question: s.agent_question,
    }));
    const layerQuestions = extractLayerQuestions(trace);
    const fullText = sanitizeAgentAnswerBody(String(text || ""));
    const stepCount = Math.max(walkPath.length, layerQuestions.length, 1);
    const totalWalkMs = stepCount * GRAPH_WALK_UI_STEP_MS;
    let revealedChars = 0;

    toggleChatGraphPanel(true);

    if (!graphOnly && fullText) ensureStreamPreview();

    const canvas = $("chatGraphCanvas");
    if (graph?.nodes?.length) {
      renderChatContextGraph(graph, { animate: true, walkPath: [], skipHighlight: true });
    }

    for (const lq of layerQuestions) {
      showAgentQuestion(lq.question);
      await sleep(Math.min(GRAPH_WALK_UI_STEP_MS * 0.45, 580));
    }

    if (walkPath.length && canvas) {
      cancelActiveGraphWalk();
      graphReplayBusy = true;
      updateGraphReplayButton();
      const walkPromise = window.MKGMiniGraph?.highlightWalkPath(canvas, walkPath, {
        intervalMs: GRAPH_WALK_UI_STEP_MS,
        onStep: (step, idx) => {
          const ws = walkSteps[idx] || step;
          const q = ws.agent_question || step.agent_question;
          if (q) showAgentQuestion(q);
          if (graphOnly || !fullText) return;
          const target = Math.floor(((idx + 1) / walkPath.length) * fullText.length);
          revealedChars = Math.max(revealedChars, target);
          updateStreamPreviewBody(fullText.slice(0, revealedChars));
        },
      });
      activeWalkCancel = walkPromise?.cancel || null;
      updateGraphStopButton();
      await walkPromise;
      activeWalkCancel = null;
      graphReplayBusy = false;
      updateGraphReplayButton();
    } else if (fullText && !graphOnly) {
      await typewriterReveal(fullText, { totalMs: totalWalkMs });
      return;
    }

    if (graphOnly || !fullText) return;

    ensureStreamPreview();
    if (revealedChars < fullText.length) {
      const prefix = fullText.slice(0, revealedChars);
      await typewriterReveal(fullText.slice(revealedChars), {
        totalMs: Math.max(500, totalWalkMs * 0.25),
        prefix,
      });
      updateStreamPreviewBody(fullText);
    } else {
      updateStreamPreviewBody(fullText);
    }
  }

  async function replayAnswerOnly(text) {
    const clean = sanitizeAgentAnswerBody(text);
    if (!clean) return;
    await typewriterReveal(clean, { totalMs: Math.max(900, clean.length * TYPEWRITER_MIN_MS) });
  }

  function graphWalkStepIcon(action) {
    return action === "seed_load" ? "★" : "→";
  }

  function graphWalkStepTitle(ws) {
    const order = ws.order ?? "?";
    const label = ws.label || ws.node_id || "?";
    if (ws.action === "seed_load") {
      return `Шаг ${order}: seed · ${label}`;
    }
    const rel = ws.rel_type ? ` · ${ws.rel_type}` : "";
    const fromLabel = ws.from_id ? `${ws.from_id.slice(-10)}` : "?";
    return `Шаг ${order}: ${fromLabel}${rel} → ${label}`;
  }

  function renderGraphWalkTimelineHtml(trace, graph) {
    const walkSteps = (trace || []).filter((t) => t.step === "graph_walk_step");
    const fromGraph = graph?.graph_walk_steps || [];
    const steps = walkSteps.length ? walkSteps : fromGraph;
    if (!steps.length) return "";
    const rows = steps.map((ws) => {
      const icon = graphWalkStepIcon(ws.action);
      const title = graphWalkStepTitle(ws);
      const snippet = ws.snippet ? `<span class="graph-walk-snippet">${esc(ws.snippet)}</span>` : "";
      const agentQ = ws.agent_question
        ? `<span class="graph-walk-agent-q">${esc(ws.agent_question)}</span>`
        : "";
      const meta = [
        ws.hop != null ? `hop ${ws.hop}` : "",
        ws.node_id ? esc(String(ws.node_id).slice(-16)) : "",
        ws.source || "",
      ].filter(Boolean).join(" · ");
      return `<li class="graph-walk-step graph-walk-${esc(ws.action || "traverse")}" data-node-id="${esc(ws.node_id || "")}">
        <span class="graph-walk-icon" aria-hidden="true">${icon}</span>
        <div class="graph-walk-body">
          <strong>${esc(title)}</strong>
          ${agentQ}
          ${snippet}
          <span class="graph-walk-meta muted">${esc(meta)}</span>
        </div>
      </li>`;
    }).join("");
    return `<details class="graph-walk-timeline">
      <summary>Обход графа · ${steps.length} шагов</summary>
      <ol class="graph-walk-steps">${rows}</ol>
    </details>`;
  }

  function renderAgentMessageTrace(m, layerUiState = null) {
    const trace = m.meta?.trace;
    if (!trace?.length) return "";
    const msgId = m.id || null;
    const selectedRound = layerUiState?.round ?? (msgId ? layerAgentsRoundByMsg.get(msgId) : null) ?? null;
    const openTrace = shouldOpenReasoningTrace(m.meta);
    if (m.meta?.speed_mode === "fast" || m.meta?.mode === "fast") {
      return renderFastTraceHtml(trace, m.meta?.timing_ms);
    }
    const graphMeta = m.meta?.graph;
    const layerResults = graphMeta?.layer_results || m.meta?.layer_results;
    const isOrchestrator = m.meta?.mode === "orchestrator_mode";
    const isDialog = !m.meta?.mode || m.meta.mode === "dialog";
    if (isOrchestrator) return renderOrchestratorTraceHtml(trace, layerResults, selectedRound, msgId, { open: openTrace });
    if (isDialog) return renderDialogTraceHtml(trace, graphMeta, layerResults, selectedRound, msgId, { open: openTrace });
    return `${renderLayerAgentsHtml(trace, layerResults, selectedRound, msgId, { open: openTrace })}${renderGraphWalkTimelineHtml(trace, graphMeta)}${renderReasoningChainHtml(trace, { open: openTrace })}`;
  }

  function renderFastTraceHtml(trace, timingMs) {
    const rows = (trace || []).map((t) => {
      const label = TRACE_LABELS[t.step] || t.step || "?";
      const extra = [];
      if (t.hit_count != null) extra.push(`${t.hit_count} хит.`);
      if (t.elapsed_ms != null) extra.push(`${t.elapsed_ms} мс`);
      const suffix = extra.length ? ` · ${extra.join(" · ")}` : "";
      return `<li>${esc(label)}${esc(suffix)}</li>`;
    }).join("");
    const total = timingMs != null ? ` · ${timingMs} мс` : "";
    return `<details class="chat-trace-fast">
      <summary>Trace (быстрый)${esc(total)}</summary>
      <ul>${rows}</ul>
    </details>`;
  }

  function renderOrchestratorTraceHtml(trace, layerResults, selectedRound = null, msgId = null, { open = false } = {}) {
    const scopeId = msgId ? `msg-${msgId}` : nextPipelineScopeId("msg");
    const model = trace?.flatItems ? trace : buildPipelineModel(trace);
    const pipeline = renderAgentPipeline(model, { live: false, activeId: -1, scopeId });
    const openAttr = open ? " open" : "";
    const pipelineHtml = pipeline
      ? `<details class="chat-agent-pipeline-trace"${openAttr}>
          <summary>${esc(tt("chat_pipeline", "Пайплайн агентов"))}</summary>
          ${pipeline}
        </details>`
      : "";
    return `${pipelineHtml}${renderLayerAgentsHtml(trace, layerResults, selectedRound, msgId, { open })}${renderGraphWalkTimelineHtml(trace, null)}${renderReasoningChainHtml(trace, { open })}`;
  }

  function renderDialogTraceHtml(trace, graph, layerResults, selectedRound = null, msgId = null, { open = false } = {}) {
    const hasAnomaly = (trace || []).some((t) => /^anomaly_/.test(t.step || ""));
    const scopeId = msgId ? `msg-${msgId}` : nextPipelineScopeId("dlg");
    const pipelineModel = hasAnomaly ? buildPipelineModel(trace) : null;
    const openAttr = open ? " open" : "";
    const pipelineHtml = pipelineModel?.flatItems?.length
      ? `<details class="chat-agent-pipeline-trace"${openAttr}>
          <summary>${esc(tt("chat_pipeline", "Пайплайн агентов"))}</summary>
          ${renderAgentPipeline(pipelineModel, { live: false, activeId: -1, scopeId })}
        </details>`
      : "";
    return `${pipelineHtml}${renderLayerAgentsHtml(trace, layerResults, selectedRound, msgId, { open })}${renderGraphWalkTimelineHtml(trace, graph)}${renderReasoningChainHtml(trace, { open })}`;
  }

  const AGENT_TRACE_PREVIEW = [
    "capabilities_check", "llm_scope_planner", "document_selector",
    "retrieval_search", "graph_sequential_walk", "graph_context_loader", "evidence_collector",
    "llm_evidence_analyzer", "final_report_builder",
  ];

  const ANOMALY_TRACE_PREVIEW = [
    "capabilities_check", "llm_scope_planner", "document_selector",
    "anomaly_seed_loader", "anomaly_graph_walker", "anomaly_qdrant_refine",
    "graph_sequential_walk", "graph_context_loader", "evidence_collector", "llm_evidence_analyzer",
    "anomaly_mode_builder", "final_report_builder",
  ];

  function traceStepLabel(step) {
    return tt(`trace_${step}`, TRACE_LABELS[step] || step.replace(/_/g, " "));
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
    if (item.step === "chat_memory") {
      const trunc = item.truncated ? " · сжато" : "";
      return `${item.turn_count ?? 0} реплик${trunc}`;
    }
    if (item.step === "chat_role") return item.name_ru || item.role_id || "";
    if (item.step === "graph_traversal" || item.step === "graph_context_loader") {
      if (item.skipped) return item.reason === "no_index" ? "нет данных" : "пропуск";
      const fb = item.fallback ? " · fallback" : "";
      const walk = item.walk_step_count != null ? ` · ${item.walk_step_count} шагов` : "";
      return `${item.node_count ?? 0} узл.${walk}${fb}`;
    }
    if (item.step === "discover_new_connections") {
      const parts = [`+${item.total_discoveries ?? 0} связей`];
      if (item.cross_layer) parts.push(`XL:${item.cross_layer}`);
      if (item.cross_document) parts.push(`XD:${item.cross_document}`);
      return parts.join(" · ");
    }
    if (/^l[1-6]_agent$/.test(item.step || "")) {
      if (item.skipped) return item.reason === "not_in_plan" ? "не в плане" : "пропуск";
      const round = item.round != null ? `R${item.round} · ` : "";
      const phase = item.loop_phase === "refinement" ? " · уточнение" : "";
      const sit = item.situation_evaluation ? String(item.situation_evaluation).slice(0, 72) : "";
      if (sit) return `${round}${sit}${phase}`;
      return `${round}${item.node_count ?? 0} узл · ${item.rel_count ?? 0} св`;
    }
    if (item.step === "layer_loop_start" || item.step === "agent_loop_start") {
      const layers = item.planned_layers?.length ? item.planned_layers.join(" · ") : "L1–L6";
      const r = item.round != null ? `R${item.round}` : "";
      const mr = item.max_rounds ? `/${item.max_rounds}` : "";
      return `гибкий цикл ${r}${mr} · ${layers}`;
    }
    if (item.step === "fast_retrieval") {
      const l3 = item.l3_hit_count ?? item.hit_count ?? 0;
      const l4 = item.l4_hit_count ?? 0;
      const clusters = item.cluster_hit_count ?? 0;
      const parts = [`L3:${l3}`, `L4:${l4}`];
      if (clusters) parts.push(`кл:${clusters}`);
      if (item.indexed_total != null) parts.push(`idx:${item.indexed_total}`);
      if (item.warning) parts.push(String(item.warning));
      return parts.join(" · ");
    }
    if (item.step === "graph_keyword_fallback") {
      return `${item.hit_count ?? 0} хитов · ${item.source || "fallback"}`;
    }
    if (item.step === "orchestrator_router") {
      const nxt = item.next_agent || "?";
      const bus = item.bus_size ? ` · шина:${item.bus_size}` : "";
      return `${nxt}${bus}`;
    }
    if (item.step === "agent_loop_round") {
      return `→ раунд ${item.round}/${item.max_rounds || "?"}`;
    }
    if (item.step === "hrm_budget_sampled") {
      return `бюджет ${item.sampled_budget ?? "?"} (мин ${item.min_rounds ?? "?"} / макс ${item.hard_cap ?? "?"}) · ${item.mode || "adaptive"}`;
    }
    if (item.step === "hrm_halt_decision") {
      const word = item.decision === "halt" ? "стоп" : "ещё цикл";
      const parts = [word];
      if (item.marginal_gain != null) parts.push(`прирост +${item.marginal_gain}`);
      if (item.confidence != null) parts.push(`${Math.round(item.confidence * 100)}%`);
      if (item.source) parts.push(item.source);
      return parts.join(" · ");
    }
    if (item.step === "orchestrator_plan" && item.layers?.length) {
      return item.layers.join("→");
    }
    if (item.step === "graph_walk_step") {
      const rel = item.rel_type ? ` · ${item.rel_type}` : "";
      return `${item.label || item.node_id || ""}${rel}`.trim();
    }
    if (item.step === "anomaly_mode_builder" || item.step === "anomaly_seed_loader") {
      if (item.anomaly_count != null) return `${item.anomaly_count} аном.`;
      if (item.hit_count != null) return `${item.hit_count} хитов`;
    }
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
    if (item.walk_step_count != null) parts.push(`шагов обхода: ${item.walk_step_count}`);
    if (item.node_count != null) parts.push(`узлов: ${item.node_count}`);
    if (item.node_id && item.step === "graph_walk_step") {
      parts.push(`${item.label || ""} · ${item.node_id}`);
      if (item.rel_type) parts.push(`связь: ${item.rel_type}`);
      if (item.agent_question) parts.push(String(item.agent_question));
      if (item.snippet) parts.push(String(item.snippet).slice(0, 80));
    }
    if (/^l[1-6]_agent$/.test(step || "") && item.situation_evaluation) {
      parts.push(String(item.situation_evaluation));
    }
    if (/^anomaly_/.test(step || "") && item.situation_evaluation) {
      parts.push(String(item.situation_evaluation));
    }
    if (/^anomaly_/.test(step || "") && item.skipped) {
      parts.push("аномалий не обнаружено");
    }
    if (/^l[1-6]_agent$/.test(step || "") && item.agent_question) {
      parts.push(String(item.agent_question));
    }
    if (item.rel_count != null) parts.push(`связей: ${item.rel_count}`);
    if (item.walk_step_count != null) parts.push(`шагов обхода: ${item.walk_step_count}`);
    if (item.source) parts.push(`источник: ${item.source}`);
    if (item.warning) parts.push(String(item.warning));
    if (item.anomaly_count != null && item.anomaly_count > 0) {
      parts.push(`аномалии: ${item.anomaly_count}`);
    }
    if (item.fallback) parts.push("режим fallback (без Qdrant-хитов)");
    if (item.collection) parts.push(`коллекция: ${item.collection}`);
    if (item.indexed_total != null) parts.push(`индекс: ${item.indexed_total} точек`);
    if (item.error) parts.push(`ошибка: ${item.error}`);
    if (item.elapsed_ms != null) parts.push(`${item.elapsed_ms} ms`);
    return parts.length ? parts.join(" · ") : traceStepLabel(step);
  }

  function renderReasoningChainHtml(trace, { open = false } = {}) {
    if (!trace?.length) return "";
    const rows = trace.map((item) => {
      const step = typeof item === "string" ? item : item.step;
      const label = traceStepLabel(step);
      const detail = traceStepReasoningDetail(item);
      return `<li><strong>${esc(label)}</strong><span class="chat-reasoning-detail">${esc(detail)}</span></li>`;
    }).join("");
    const openAttr = open ? " open" : "";
    return `<details class="chat-reasoning-chain"${openAttr}>
      <summary>Цепочка рассуждений · ${trace.length} шагов</summary>
      <ol class="chat-reasoning-steps">${rows}</ol>
    </details>`;
  }

  function renderAgentTraceHtml(trace, { live = false, activeIdx = -1 } = {}) {
    const model = buildPipelineModel(trace);
    const activeId = live && activeIdx >= 0 && model.flatItems[activeIdx]
      ? model.flatItems[activeIdx].id
      : (live ? activeIdx : -1);
    return renderAgentPipeline(model, { live, activeId });
  }

  let traceLiveTimer = null;
  let traceLivePollTimer = null;
  let traceLiveFingerprint = "";

  function paintTraceLive(model, { live = false, activeId = -1 } = {}) {
    const el = $("chatTraceLive");
    if (!el) return;
    const scopeId = "chatTraceLive";
    const fp = pipelineModelFingerprint(model, { live, activeId, scopeId });
    if (fp === traceLiveFingerprint) return;
    traceLiveFingerprint = fp;
    el.innerHTML = renderAgentPipeline(model, { live, activeId, scopeId });
  }

  function handlePipelineExpandClick(e) {
    const btn = e.target.closest(".agent-pipeline-expand");
    if (!btn) return;
    e.preventDefault();
    e.stopPropagation();
    const scopeId = btn.dataset.pipelineScope;
    const round = parseInt(btn.dataset.round, 10);
    if (!scopeId || !Number.isFinite(round)) return;
    togglePipelineRoundExpanded(scopeId, round);
    if (scopeId === "chatTraceLive") traceLiveFingerprint = "";
    refreshPipelineScope(scopeId);
  }

  function showTraceLive(previewSteps) {
    const el = $("chatTraceLive");
    if (!el || !previewSteps?.length) return;
    let idx = 0;
    clearInterval(traceLiveTimer);
    clearInterval(traceLivePollTimer);
    traceLiveFingerprint = "";
    const steps = normalizePipelineTraceItems(previewSteps);
    const render = () => {
      const partial = steps.slice(0, idx + 1);
      const model = buildPipelineModel(partial);
      const activeId = model.flatItems.length ? model.flatItems[model.flatItems.length - 1].id : -1;
      paintTraceLive(model, { live: true, activeId });
    };
    render();
    traceLiveTimer = setInterval(() => {
      if (idx < steps.length - 1) {
        idx += 1;
        render();
      } else {
        clearInterval(traceLiveTimer);
        traceLiveTimer = null;
      }
    }, 420);
  }

  function updateTraceLiveFromPoll(trace) {
    if (!trace?.length) return;
    clearInterval(traceLiveTimer);
    traceLiveTimer = null;
    const model = buildPipelineModel(trace);
    const activeId = model.flatItems.length ? model.flatItems[model.flatItems.length - 1].id : -1;
    paintTraceLive(model, { live: true, activeId });
  }

  function showTraceComplete(trace) {
    clearInterval(traceLiveTimer);
    traceLiveTimer = null;
    clearInterval(traceLivePollTimer);
    traceLivePollTimer = null;
    if (!trace?.length) return;
    const model = buildPipelineModel(trace);
    traceLiveFingerprint = "";
    paintTraceLive(model, { live: false, activeId: -1 });
  }

  function hideTraceLive() {
    clearInterval(traceLiveTimer);
    traceLiveTimer = null;
    clearInterval(traceLivePollTimer);
    traceLivePollTimer = null;
    traceLiveFingerprint = "";
    const el = $("chatTraceLive");
    if (el) el.innerHTML = "";
  }

  function setChatGraphBuilding(on, text = "Сбор графа…") {
    const el = $("chatGraphBuilding");
    const txt = $("chatGraphBuildingText");
    const empty = $("chatGraphEmpty");
    if (on) toggleChatGraphPanel(true);
    if (el) el.classList.toggle("hidden", !on);
    if (txt && text) txt.textContent = text;
    if (empty && on) empty.classList.add("hidden");
  }

  function extractGraphFromTrace(trace, graph, layerResults) {
    let snap = graph && graph.nodes?.length ? { ...graph } : null;
    for (const t of trace || []) {
      const gs = t.graph_snapshot;
      if (gs?.nodes?.length) {
        snap = snap
          ? (window.MKGMiniGraph?.mergeGraphs?.(snap, gs) || gs)
          : gs;
      }
    }
    if (!snap?.nodes?.length && layerResults?.length) {
      const nodes = [];
      const relationships = [];
      for (const lr of layerResults) {
        (lr.nodes_found || []).forEach((n) => nodes.push(n));
        (lr.edges_found || []).forEach((r) => relationships.push(r));
      }
      if (nodes.length) {
        snap = window.MKGMiniGraph?.normalizeGraph?.({ nodes, relationships }) || { nodes, relationships };
      }
    }
    return snap;
  }

  const GRAPH_META_MAX_NODES = 64;
  const GRAPH_META_MAX_RELS = 128;
  const GRAPH_META_MAX_WALK = 48;
  const GRAPH_META_MAX_PROP = 400;

  function trimGraphProps(props, maxLen = GRAPH_META_MAX_PROP) {
    if (!props || typeof props !== "object") return {};
    const keys = ["raw_text_ru", "quote", "text", "name_ru", "title_ru", "description", "snippet", "summary", "content"];
    const out = {};
    Object.entries(props).forEach(([key, val]) => {
      if (typeof val === "string" && keys.includes(key)) {
        out[key] = val.length > maxLen ? `${val.slice(0, maxLen - 1)}…` : val;
      } else if (typeof val === "string" || typeof val === "number" || typeof val === "boolean" || val == null) {
        out[key] = val;
      }
    });
    return out;
  }

  function trimGraphForMeta(graph) {
    if (!graph) return null;
    const nodes = (graph.nodes || []).slice(0, GRAPH_META_MAX_NODES).map((node) => ({
      id: String(node.id || ""),
      label: String(node.label || "?").slice(0, 160),
      props: trimGraphProps(node.props || {}),
    })).filter((n) => n.id);
    const nodeIds = new Set(nodes.map((n) => n.id));
    const relationships = (graph.relationships || []).slice(0, GRAPH_META_MAX_RELS).flatMap((rel) => {
      const from = String(rel.from || rel.from_ || "");
      const to = String(rel.to || "");
      if (!from || !to || !nodeIds.has(from) || !nodeIds.has(to)) return [];
      return [{
        type: String(rel.type || "").slice(0, 80),
        from,
        to,
        props: trimGraphProps(rel.props || {}, 240),
      }];
    });
    const walkSteps = (graph.graph_walk_steps || []).slice(0, GRAPH_META_MAX_WALK).map((step) => ({
      ...step,
      snippet: step.snippet ? String(step.snippet).slice(0, GRAPH_META_MAX_PROP) : step.snippet,
      agent_question: step.agent_question ? String(step.agent_question).slice(0, GRAPH_META_MAX_PROP) : step.agent_question,
    }));
    const walkPath = (graph.walk_path || walkSteps).slice(0, GRAPH_META_MAX_WALK).map((step) => ({
      node_id: step.node_id,
      from_id: step.from_id,
      to_id: step.to_id,
      rel_type: step.rel_type,
      label: step.label,
    })).filter((s) => s.node_id);
    if (!nodes.length && !relationships.length && !walkSteps.length) return null;
    return {
      nodes,
      relationships,
      graph_walk_steps: walkSteps,
      walk_path: walkPath,
      seed_count: graph.seed_count ?? nodes.length,
      document_ids: (graph.document_ids || []).slice(0, 24),
    };
  }

  function prepareGraphForMeta(graph, trace, layerResults) {
    const merged = extractGraphFromTrace(trace, graph, layerResults) || graph;
    if (!merged) return null;
    let safe = normalizeChatGraph(merged);
    if (!safe.graph_walk_steps?.length) {
      const steps = extractWalkSteps(trace, safe);
      if (steps.length) safe = { ...safe, graph_walk_steps: steps };
    }
    if (!safe.walk_path?.length && safe.graph_walk_steps?.length) {
      safe = {
        ...safe,
        walk_path: safe.graph_walk_steps.map((s) => ({
          node_id: s.node_id,
          from_id: s.from_id,
          to_id: s.to_id,
          rel_type: s.rel_type,
          label: s.label,
        })).filter((s) => s.node_id),
      };
    }
    return trimGraphForMeta(safe);
  }

  function findLastGraphMessage(items) {
    const list = items || [];
    if (!list.length) return null;
    for (let i = list.length - 1; i >= 0; i -= 1) {
      if (list[i].msg_type === "agent" && hasContextGraph(list[i].meta)) return list[i];
    }
    return null;
  }

  function resetChatGraphForNewQuestion() {
    cancelActiveGraphWalk();
    removeStreamPreview();
    lastFullscreenGraph = null;
    lastFullscreenTrace = null;
    liveAccumulatedGraph = null;
    graphReplayBusy = false;
    stopGraphPoll();
    setLastReplayableWalk(null);
    window.MKGMiniGraph?.destroy($("chatGraphCanvas"));
    updateChatGraphStats(null);
    toggleChatGraphPanel(true);
    updateGraphReplayButton();
  }

  function isGraphPanelEmpty() {
    const canvas = $("chatGraphCanvas");
    const empty = $("chatGraphEmpty");
    if (!canvas) return true;
    if (empty && !empty.classList.contains("hidden")) return true;
    return !(lastFullscreenGraph?.nodes?.length || liveAccumulatedGraph?.nodes?.length);
  }

  function restoreGraphPanelFromMessages(items, { force = false } = {}) {
    if (chatBusy && !force) return;
    const msg = findLastGraphMessage(items);
    if (!msg) {
      if (!chatBusy || force) {
        updateChatGraphStats(null);
        window.MKGMiniGraph?.destroy($("chatGraphCanvas"));
        setLastReplayableWalk(null);
      }
      return;
    }
    const payload = replayPayloadFromMessage(msg);
    const graph = payload?.graph;
    const hasGraph = graph?.nodes?.length || graph?.relationships?.length || graph?.graph_walk_steps?.length;
    if (!hasGraph) return;
    lastFullscreenGraph = graph;
    lastFullscreenTrace = payload.trace || [];
    setLastReplayableWalk(payload);
    toggleChatGraphPanel(true);
    if (graph.nodes?.length) {
      renderChatContextGraph(graph, {
        animate: false,
        walkPath: graph.walk_path || [],
        skipHighlight: false,
      });
    } else {
      updateChatGraphStats(normalizeChatGraph(graph), { building: false });
    }
  }

  function restoreGraphPanelIfNeeded(items) {
    if (chatBusy || !isGraphPanelEmpty()) return;
    restoreGraphPanelFromMessages(items);
  }

  function applyLiveGraphUpdate(graph, trace, layerResults) {
    const current = (graph?.nodes?.length
      ? normalizeChatGraph(graph)
      : extractGraphFromTrace([], graph, layerResults));
    if (!current?.nodes?.length) return;
    liveAccumulatedGraph = current;
    renderChatContextGraph(liveAccumulatedGraph, {
      animate: false,
      skipHighlight: true,
      building: true,
    });
  }

  function stopGraphPoll() {
    if (graphPollTimer) {
      clearInterval(graphPollTimer);
      graphPollTimer = null;
    }
  }

  function showMessageContextGraph(msg) {
    const graph = extractGraphFromTrace(
      msg?.meta?.trace,
      msg?.meta?.graph,
      msg?.meta?.layer_results,
    ) || msg?.meta?.graph;
    if (!graph) return;
    cancelActiveGraphWalk();
    liveAccumulatedGraph = normalizeChatGraph(graph);
    lastFullscreenGraph = liveAccumulatedGraph;
    lastFullscreenTrace = msg.meta?.trace || [];
    setLastReplayableWalk(replayPayloadFromMessage(msg));
    toggleChatGraphPanel(true);
    renderChatContextGraph(liveAccumulatedGraph, {
      animate: true,
      walkPath: liveAccumulatedGraph.walk_path || [],
    });
  }

  function hasContextGraph(meta) {
    const g = extractGraphFromTrace(meta?.trace, meta?.graph, meta?.layer_results);
    return !!(g && (g.nodes?.length || g.relationships?.length || g.graph_walk_steps?.length));
  }

  function updateChatGraphStats(graph, { building = false } = {}) {
    const stats = $("chatGraphStats");
    const empty = $("chatGraphEmpty");
    const emptyMsg = $("chatGraphEmptyMsg");
    const canvas = $("chatGraphCanvas");
    const nodes = graph?.nodes?.length || 0;
    const rels = graph?.relationships?.length || 0;
    const walkSteps = graph?.graph_walk_steps || [];
    const traverseCount = walkSteps.filter((s) => s.action === "traverse").length;
    if (stats) {
      stats.textContent = nodes
        ? (traverseCount
          ? tf("chat_graph_stats_walk", { nodes, rels, steps: traverseCount })
          : tf("chat_graph_stats", { nodes, rels }))
        : (building ? "…" : tt("chat_graph_stats_zero", "0 узлов"));
    }
    const showEmpty = !building && nodes === 0;
    if (empty) empty.classList.toggle("hidden", !showEmpty);
    if (emptyMsg && showEmpty) {
      emptyMsg.textContent = tt("chat_graph_empty", "Нет данных MKG для этого запроса.");
    }
    if (canvas) canvas.classList.toggle("hidden", showEmpty);
  }

  function normalizeChatGraph(graph) {
    return window.MKGMiniGraph?.normalizeGraph?.(graph || {}) || graph || {};
  }

  function showChatGraphRenderWarning(message) {
    const empty = $("chatGraphEmpty");
    const emptyMsg = $("chatGraphEmptyMsg");
    const canvas = $("chatGraphCanvas");
    if (emptyMsg) emptyMsg.textContent = message || "Не удалось отобразить граф контекста.";
    if (empty) empty.classList.remove("hidden");
    if (canvas) canvas.classList.add("hidden");
  }

  function mergeChatContextGraph(graph, { building = false, animate = true } = {}) {
    const canvas = $("chatGraphCanvas");
    if (!canvas || chatGraphCollapsed) return;
    const safeGraph = normalizeChatGraph(graph);
    updateChatGraphStats(safeGraph, { building });
    if (!safeGraph?.nodes?.length) return;
    try {
      return window.MKGMiniGraph?.mergeInto?.(canvas, safeGraph, { animate }) ||
        window.MKGMiniGraph?.render(canvas, safeGraph, { animate });
    } catch (err) {
      console.warn("chat context graph merge failed:", err);
      return null;
    }
  }

  function renderChatContextGraph(graph, { animate = true, walkPath = [], skipHighlight = false, building = false } = {}) {
    const canvas = $("chatGraphCanvas");
    if (!canvas || chatGraphCollapsed) return;
    const safeGraph = normalizeChatGraph(graph);
    updateChatGraphStats(safeGraph, { building });
    const nodes = safeGraph?.nodes?.length || 0;
    if (!nodes) {
      window.MKGMiniGraph?.destroy(canvas);
      return;
    }
    const path = walkPath?.length ? walkPath : (safeGraph?.walk_path || []);
    try {
      window.MKGMiniGraph?.destroy(canvas);
      const network = window.MKGMiniGraph?.render(canvas, safeGraph, { animate });
      if (!skipHighlight && path?.length) {
        window.MKGMiniGraph?.highlightWalkPath(canvas, path);
      }
      return network;
    } catch (err) {
      console.warn("chat context graph render failed:", err);
      window.MKGMiniGraph?.destroy(canvas);
      showChatGraphRenderWarning("Граф контекста недоступен — ответ в чате сохранён.");
      return null;
    }
  }

  function renderChatGraph(graph, opts) {
    return renderChatContextGraph(graph, opts);
  }

  function getChatGraphLayout() {
    return document.querySelector(".chats-layout-with-graph");
  }

  function getChatGraphMinWidth() {
    return 260;
  }

  function getChatGraphMaxWidth() {
    return Math.min(920, Math.round(window.innerWidth * 0.72));
  }

  function applyChatGraphWidth(w) {
    const layout = getChatGraphLayout();
    if (!layout) return w;
    const clamped = Math.max(getChatGraphMinWidth(), Math.min(getChatGraphMaxWidth(), w));
    layout.style.setProperty("--chat-graph-w", `${clamped}px`);
    return clamped;
  }

  function refreshChatGraphViewport() {
    const canvas = $("chatGraphCanvas");
    window.MKGMiniGraph?.refreshViewport?.(canvas);
  }

  function closeGraphFullscreenModal() {
    const modal = $("graphFullscreenModal");
    if (modal) modal.classList.add("hidden");
    window.MKGMiniGraph?.destroy($("graphFullscreenCanvas"));
  }

  function openGraphFullscreenModal(graph, trace) {
    const modal = $("graphFullscreenModal");
    const canvas = $("graphFullscreenCanvas");
    const stats = $("graphFullscreenStats");
    const traceBody = $("graphFullscreenTraceBody");
    if (!modal || !canvas) return;
    lastFullscreenGraph = graph;
    lastFullscreenTrace = trace;
    modal.classList.remove("hidden");
    const nodes = graph?.nodes?.length || 0;
    const rels = graph?.relationships?.length || 0;
    if (stats) stats.textContent = `${nodes} узл · ${rels} св`;
    if (traceBody) {
      const isOrch = (trace || []).some((t) => String(t.step || "").startsWith("orchestrator") || /^l[1-6]_agent$/.test(t.step));
      traceBody.innerHTML = isOrch
        ? renderOrchestratorTraceHtml(trace, graph?.layer_results)
        : (renderDialogTraceHtml(trace, graph, graph?.layer_results) || renderReasoningChainHtml(trace) || '<p class="muted small">Нет trace</p>');
    }
    window.MKGMiniGraph?.destroy(canvas);
    const safeGraph = normalizeChatGraph(graph);
    const safeNodes = safeGraph?.nodes?.length || 0;
    const safeRels = safeGraph?.relationships?.length || 0;
    if (safeNodes) {
      try {
        const network = window.MKGMiniGraph?.render(canvas, safeGraph, { animate: false });
        setTimeout(() => {
          network?.fit({ animation: { duration: 300, easingFunction: "easeInOutQuad" } });
          network?.setOptions({ physics: { enabled: false } });
        }, 80);
      } catch (err) {
        console.warn("fullscreen graph render failed:", err);
        canvas.innerHTML = '<p class="muted small" style="padding:24px">Не удалось отобразить граф</p>';
      }
    } else {
      canvas.innerHTML = '<p class="muted small" style="padding:24px">Нет данных графа</p>';
    }
  }

  function initChatGraphResize() {
    const handle = $("chatGraphResizeHandle");
    const layout = getChatGraphLayout();
    if (!handle || !layout) return;

    const saved = localStorage.getItem("mkg_chat_graph_w");
    const parsed = saved ? parseInt(saved, 10) : 320;
    applyChatGraphWidth(Number.isFinite(parsed) ? parsed : 320);

    let startX = 0;
    let startW = 0;

    const onMove = (e) => {
      applyChatGraphWidth(startW + (e.clientX - startX));
      refreshChatGraphViewport();
    };

    const onUp = () => {
      document.body.classList.remove("mkg-resizing-col");
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      const w = parseInt(layout.style.getPropertyValue("--chat-graph-w") || "320", 10);
      localStorage.setItem("mkg_chat_graph_w", String(w));
    };

    handle.addEventListener("mousedown", (e) => {
      if (chatGraphCollapsed || chatGraphMaximized) return;
      e.preventDefault();
      startX = e.clientX;
      startW = parseInt(layout.style.getPropertyValue("--chat-graph-w") || "320", 10);
      document.body.classList.add("mkg-resizing-col");
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    });
  }

  function toggleChatGraphMaximized(force) {
    const nextMaximized = force !== undefined ? force : !chatGraphMaximized;
    // Fullscreen modal only when expanding inline panel — never when collapsing/un-maximizing.
    if (nextMaximized && lastFullscreenGraph?.nodes?.length) {
      openGraphFullscreenModal(lastFullscreenGraph, lastFullscreenTrace);
      return;
    }
    const layout = getChatGraphLayout();
    const btn = $("chatGraphExpand");
    const handle = $("chatGraphResizeHandle");
    if (!layout) return;

    if (chatGraphCollapsed && nextMaximized) toggleChatGraphPanel(true);

    chatGraphMaximized = nextMaximized;
    layout.classList.toggle("chat-graph-maximized", chatGraphMaximized);

    if (btn) {
      btn.title = chatGraphMaximized ? "Свернуть граф" : "Развернуть граф";
      btn.setAttribute("aria-label", chatGraphMaximized ? "Свернуть" : "Развернуть");
      btn.classList.toggle("active", chatGraphMaximized);
    }
    if (handle) handle.style.display = chatGraphMaximized ? "none" : "";

    if (chatGraphMaximized) {
      chatGraphWidthBeforeMax = parseInt(layout.style.getPropertyValue("--chat-graph-w") || "320", 10);
      applyChatGraphWidth(getChatGraphMaxWidth());
    } else if (chatGraphWidthBeforeMax != null) {
      applyChatGraphWidth(chatGraphWidthBeforeMax);
      localStorage.setItem("mkg_chat_graph_w", String(chatGraphWidthBeforeMax));
    }

    requestAnimationFrame(() => refreshChatGraphViewport());
  }

  function setChatGraphPanelOpen(open, persist) {
    const panel = $("chatGraphPanel");
    const btn = $("chatGraphToggle");
    if (!panel) return;
    chatGraphCollapsed = !open;
    panel.classList.toggle("collapsed", chatGraphCollapsed);
    if (chatGraphCollapsed && chatGraphMaximized) toggleChatGraphMaximized(false);
    if (btn) {
      btn.textContent = chatGraphCollapsed ? "‹" : "›";
      btn.title = chatGraphCollapsed ? "Развернуть панель" : "Свернуть панель";
      btn.setAttribute("aria-label", chatGraphCollapsed ? "Развернуть панель" : "Свернуть панель");
    }
    if (persist) localStorage.setItem(CHAT_GRAPH_OPEN_KEY, open ? "true" : "false");
    requestAnimationFrame(() => refreshChatGraphViewport());
  }

  function initChatGraphPanel() {
    setChatGraphPanelOpen(localStorage.getItem(CHAT_GRAPH_OPEN_KEY) !== "false");
  }

  function toggleChatGraphPanel(force) {
    // Toggle: open panel → collapse (open=false); collapsed strip → expand (open=true).
    const open = force !== undefined ? force : chatGraphCollapsed;
    setChatGraphPanelOpen(open, force === undefined);
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
    if (!force && userScrolledUp) return;
    if (!force && !isChatNearBottom()) return;
    chatScrollProgrammatic = true;
    const scroll = () => { box.scrollTop = box.scrollHeight; };
    scroll();
    requestAnimationFrame(() => {
      scroll();
      requestAnimationFrame(() => {
        scroll();
        chatScrollProgrammatic = false;
        if (isChatNearBottom()) userScrolledUp = false;
      });
    });
  }

  function applyChatScrollPolicy(policy, prevScrollTop) {
    const box = $("chatMessages");
    if (!box) return;
    if (policy === "force") {
      scrollChatToBottom(true);
    } else if (policy === "bottom") {
      scrollChatToBottom(false);
    } else if (policy === "restore" && prevScrollTop != null) {
      box.scrollTop = prevScrollTop;
    }
  }

  function showTyping(on, previewSteps = null) {
    const el = $("chatTyping");
    if (!el) return;
    el.classList.toggle("hidden", !on);
    if (on) {
      showTraceLive(previewSteps);
      if (!userScrolledUp) scrollChatToBottom(false);
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
        const savedId = loadPersistedActiveThreadId();
        const pick = savedId && threads.some((t) => t.id === savedId) ? savedId : threads[0].id;
        activeThreadId = pick;
        persistActiveThreadId(activeThreadId);
        await loadMessages(activeThreadId, { scroll: "force", forceRender: true });
      }
    } catch { /* ignore */ }
  }

  function renderThreadList() {
    const el = $("chatThreadList");
    if (!el) return;
    if (!threads.length) {
      el.innerHTML = `<p class="muted small">${esc(tt("chat_no_threads", "Нет чатов"))}</p>`;
      return;
    }
    const delTitle = tt("chat_delete_thread", "Удалить чат");
    el.innerHTML = threads.map((t) => `
      <div class="chats-thread-row${t.id === activeThreadId ? " active" : ""}" data-id="${esc(t.id)}">
        <button type="button" class="chats-thread-select" data-id="${esc(t.id)}">
          <span class="chats-thread-title">${esc(t.title)}</span>
          <span class="muted chats-thread-meta">${t.message_count || 0}</span>
        </button>
        <button type="button" class="chats-thread-delete" data-id="${esc(t.id)}" title="${esc(delTitle)}" aria-label="${esc(delTitle)}"><span aria-hidden="true">×</span></button>
      </div>`).join("");
    el.querySelectorAll(".chats-thread-select").forEach((btn) => {
      btn.addEventListener("click", () => {
        switchThread(btn.dataset.id);
      });
    });
    el.querySelectorAll(".chats-thread-delete").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        deleteThread(btn.dataset.id);
      });
    });
  }

  async function switchThread(nextId) {
    if (!nextId || nextId === activeThreadId) return;
    if (chatBusy) releaseChatComposeLock();
    else healOrphanChatBusyUi();
    activeThreadId = nextId;
    persistActiveThreadId(activeThreadId);
    lastMessagesFingerprint = "";
    lastLoadedThreadId = null;
    userScrolledUp = false;
    resetThreadViewState({ clearGraph: true });
    renderThreadList();
    const t = threads.find((x) => x.id === nextId);
    if ($("chatActiveTitle") && t) $("chatActiveTitle").textContent = t.title;
    await loadMessages(nextId, { scroll: "force", forceRender: true, threadSwitch: true });
  }

  async function deleteThread(threadId) {
    if (!threadId) return;
    if (!confirm(tt("chat_delete_confirm", "Удалить этот чат? Сообщения будут удалены безвозвратно."))) return;
    try {
      const r = await fetch(`${API}/chat/threads/${encodeURIComponent(threadId)}`, { method: "DELETE" });
      if (!r.ok) {
        const data = await r.json().catch(() => ({}));
        showNotice(data.detail || "Не удалось удалить чат", true);
        return;
      }
      if (activeThreadId === threadId) {
        activeThreadId = null;
        persistActiveThreadId(null);
        lastMessagesFingerprint = "";
        lastLoadedThreadId = null;
        userScrolledUp = false;
        threadDocIds.delete(threadId);
        resetThreadViewState();
        if ($("chatActiveTitle")) $("chatActiveTitle").textContent = tt("chat_dialog", "Диалог");
        const msgEl = $("chatMessages");
        if (msgEl) msgEl.innerHTML = `<p class="chat-empty-hint">${esc(tt("chat_empty_new", "Напишите первое сообщение…"))}</p>`;
      }
      await loadThreads();
      if (!activeThreadId && threads.length) {
        activeThreadId = threads[0].id;
        await loadMessages(activeThreadId, { scroll: "force" });
      }
    } catch (e) {
      showNotice(e.message || "Ошибка сети", true);
    }
  }

  async function loadMessages(threadId, options = {}) {
    if (!threadId) return;
    try {
      const r = await fetch(`${API}/chat/threads/${encodeURIComponent(threadId)}/messages`);
      if (!r.ok) return;
      const data = await r.json();
      const items = data.items || [];
      if (threadId !== activeThreadId) return;
      syncThreadDocsFromMessages(items);
      const fp = messagesFingerprint(items);
      const threadChanged = threadId !== lastLoadedThreadId;
      const fingerprintChanged = fp !== lastMessagesFingerprint;
      const forceRender = !!options.forceRender || !!options.threadSwitch;
      if (!threadChanged && !fingerprintChanged && !forceRender) {
        const t = threads.find((x) => x.id === threadId);
        if ($("chatActiveTitle") && t) $("chatActiveTitle").textContent = t.title;
        restoreGraphPanelIfNeeded(items);
        return;
      }
      if (chatBusy && !forceRender) {
        const t = threads.find((x) => x.id === threadId);
        if ($("chatActiveTitle") && t) $("chatActiveTitle").textContent = t.title;
        return;
      }
      lastLoadedThreadId = threadId;
      lastMessagesFingerprint = fp;
      currentThreadMessages = items;
      renderMessages(items, options);
      syncLastReplayableFromMessages(items);
      restoreThreadUiFromMessages(items);
      restoreGraphPanelFromMessages(items, { force: forceRender });
      items.forEach((m) => {
        if (m.meta?.kind === "upload" && m.meta?.document_id) {
          const st = uploadPreviewCache.get(m.meta.document_id)?.status;
          if (!st || !TERMINAL_DOC_STATUSES.has(st)) startUploadPoll(m.meta.document_id);
        }
        (m.meta?.attachments || []).forEach((a) => {
          if (!a.document_id) return;
          const st = uploadPreviewCache.get(a.document_id)?.status;
          if (!st || !TERMINAL_DOC_STATUSES.has(st)) startUploadPoll(a.document_id);
        });
      });
      const t = threads.find((x) => x.id === threadId);
      if ($("chatActiveTitle") && t) $("chatActiveTitle").textContent = t.title;
    } catch { /* ignore */ }
  }

  function buildHistory(items) {
    return (items || [])
      .filter((m) => m.msg_type === "user" || m.msg_type === "agent")
      .slice(-16)
      .map((m) => ({
        role: m.msg_type === "agent" ? "assistant" : "user",
        content: m.body,
      }));
  }

  function buildHistoryThrough(items, msgId) {
    const idx = (items || []).findIndex((m) => m.id === msgId);
    if (idx < 0) return buildHistory(items);
    return buildHistory(items.slice(0, idx + 1));
  }

  function buildHistoryBeforeMessage(items, msgId) {
    const idx = (items || []).findIndex((m) => m.id === msgId);
    if (idx <= 0) return [];
    return buildHistory(items.slice(0, idx));
  }

  function findPrecedingUserMessage(items, agentMsgId) {
    const idx = (items || []).findIndex((m) => m.id === agentMsgId);
    if (idx <= 0) return null;
    for (let i = idx - 1; i >= 0; i--) {
      if (items[i].msg_type === "user") return items[i];
    }
    return null;
  }

  function findFollowingMessages(items, msgId) {
    const idx = (items || []).findIndex((m) => m.id === msgId);
    if (idx < 0) return [];
    return items.slice(idx + 1);
  }

  async function apiDeleteMessage(msgId, { cascade = false, after = false, reload = true } = {}) {
    if (!activeThreadId || !msgId) return false;
    let qs = "";
    if (cascade) qs = "?cascade=following";
    else if (after) qs = "?cascade=after";
    const r = await fetch(
      `${API}/chat/threads/${encodeURIComponent(activeThreadId)}/messages/${encodeURIComponent(msgId)}${qs}`,
      { method: "DELETE" },
    );
    if (!r.ok) {
      const data = await r.json().catch(() => ({}));
      showNotice(parseApiError(data, "Не удалось удалить сообщение"), true);
      return false;
    }
    lastMessagesFingerprint = "";
    if (reload) {
      await loadMessages(activeThreadId, { scroll: "restore", forceRender: true });
      await loadThreads();
    }
    return true;
  }

  function isChatBusy() {
    return isChatSending();
  }

  function renderAgentMsgActionsHtml(msgId) {
    const busy = isChatBusy();
    const dis = busy ? ' disabled aria-disabled="true"' : "";
    return `<div class="chat-msg-actions${busy ? " is-busy" : ""}">
            <button type="button" class="chat-msg-action" data-action="explain" data-msg-id="${esc(msgId)}"${dis}>${esc(tt("action_explain", "Пояснить"))}</button>
            <button type="button" class="chat-msg-action" data-action="expand" data-msg-id="${esc(msgId)}"${dis}>${esc(tt("action_expand", "Дополнить"))}</button>
            <button type="button" class="chat-msg-action" data-action="regenerate" data-msg-id="${esc(msgId)}"${dis}>${esc(tt("action_regenerate", "Обновить"))}</button>
            <button type="button" class="chat-msg-action" data-action="delete" data-msg-id="${esc(msgId)}"${dis}>${esc(tt("action_delete", "Удалить"))}</button>
          </div>`;
  }

  function bindChatMsgActionsDelegation() {
    const el = $("chatMessages");
    if (!el || el.dataset.msgActionsBound) return;
    el.dataset.msgActionsBound = "1";
    el.addEventListener("click", async (e) => {
      const btn = e.target.closest(".chat-msg-action");
      if (!btn) return;
      const msgId = btn.dataset.msgId;
      const action = btn.dataset.action;
      if (!msgId || !action || chatBusy || btn.disabled) return;
      if (action === "explain") {
        sendChatMessage({ explain: true, targetAgentMsgId: msgId });
      } else if (action === "expand") {
        sendChatMessage({ expand: true, targetAgentMsgId: msgId });
      } else if (action === "regenerate") {
        sendChatMessage({ regenerate: true, targetAgentMsgId: msgId });
      } else if (action === "delete") {
        const cascade = btn.dataset.cascade === "following";
        await apiDeleteMessage(msgId, { cascade });
      }
    });
  }

  function renderMessages(items, options = {}) {
    const el = $("chatMessages");
    if (!el) return;
    bindChatScrollListener();
    const prevScrollTop = el.scrollTop;
    const wasNearBottom = isChatNearBottom();
    destroyMessageCharts();
    const layerAgentsState = captureLayerAgentsUiState(el);
    if (!items.length) {
      el.innerHTML = `<p class="chat-empty-hint">${esc(tt("chat_empty_first", "Выберите роль и напишите первое сообщение — AI ответит в режиме «Диалог»."))}</p>`;
      updateChatGraphStats(null);
      window.MKGMiniGraph?.destroy($("chatGraphCanvas"));
      return;
    }
    el.innerHTML = items.map((m) => {
      const role = roleMeta(m.author_role);
      const isUser = m.msg_type === "user";
      const isAgent = m.msg_type === "agent";
      const isUpload = m.msg_type === "system" && m.meta?.kind === "upload";
      const userAttachments = isUser && (m.meta?.attachments || []).length
        ? m.meta.attachments
        : [];
      const cls = isUpload ? "msg-upload" : isAgent ? "msg-agent" : m.msg_type === "system" ? "msg-system" : "msg-user";
      const time = m.created_at ? new Date(m.created_at).toLocaleString(chatLocale(), { hour: "2-digit", minute: "2-digit" }) : "";
      const disp = roleDisplay(role);
      const avatarText = isAgent ? "AI" : isUser ? (disp.name || "?").slice(0, 1) : "·";
      const avatarHtml = isUpload
        ? ((window.MKG_ICONS && MKG_ICONS.paperclip(16)) || "↑")
        : esc(avatarText);
      const avatarCls = isUpload ? " chat-msg-avatar-icon" : "";
      const trace = m.meta?.trace;
      const traceHtml = (isAgent && trace?.length) ? renderAgentMessageTrace(m, layerAgentsState.get(m.id)) : "";
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
        : userAttachments.length
          ? userAttachments.map((a) => renderUploadCardInner(
            a.document_id,
            uploadPreviewCache.get(a.document_id),
            a.file_name,
          )).join("")
          : "";
      const saveMdBtn = isAgent
        ? `<button type="button" class="btn btn-ghost btn-small chat-save-md" data-msg-id="${esc(m.id)}" title="Сохранить ответ как .md">MD</button>
           <button type="button" class="btn btn-ghost btn-small chat-save-jsonld" data-msg-id="${esc(m.id)}" title="Скачать JSON-LD">JSON-LD</button>
           <button type="button" class="btn btn-ghost btn-small chat-save-print" data-msg-id="${esc(m.id)}" title="Печать / PDF">PDF</button>`
        : "";
      const graphBtn = (isAgent && hasContextGraph(m.meta))
        ? `<button type="button" class="btn btn-ghost btn-small chat-show-graph" data-msg-id="${esc(m.id)}" title="${esc(tt("chat_show_graph", "Показать граф обхода"))}">${esc(tt("chat_show_graph", "Показать граф обхода"))}</button>`
        : "";
      const modeBadge = isAgent && m.meta?.mode
        && !["dialog", "fast", "orchestrator_mode"].includes(m.meta.mode)
        ? `<span class="chat-mode-badge">${esc(traceModeLabel(m.meta.mode))}</span>`
        : "";
      const speedBadge = isAgent && m.meta?.speed_mode
        ? `<span class="chat-mode-badge chat-speed-${esc(m.meta.speed_mode)}">${esc(speedModeLabel(m.meta.speed_mode))}</span>`
        : "";
      const bodyHtml = isAgent
        ? `<div class="chat-msg-body md-render-view">${renderAgentAnswerHtml(m.body)}</div>`
        : `<div class="chat-msg-body">${esc(m.body)}</div>`;
      const showMsgActions = (isAgent || isUser) && !isUpload;
      let actionsHtml = "";
      if (showMsgActions && isAgent) {
        actionsHtml = renderAgentMsgActionsHtml(m.id);
      } else if (showMsgActions && isUser) {
        const delLabel = tt("action_delete", "Удалить");
        actionsHtml = `<div class="chat-msg-actions">
            <button type="button" class="chat-msg-action" data-action="delete" data-msg-id="${esc(m.id)}" data-cascade="following">${esc(delLabel)}</button>
          </div>`;
      }
      return `
        <article class="chat-msg ${cls}" data-msg-id="${esc(m.id)}">
          <div class="chat-msg-avatar${avatarCls}" aria-hidden="true">${avatarHtml}</div>
          <div class="chat-msg-content">
            <header>
              <strong>${esc(m.author_name)}</strong>
              ${!isUser && !isUpload ? `<span class="user-role-badge role-${esc(m.author_role)}">${esc(disp.name || m.author_role)}</span>` : ""}
              ${speedBadge}
              ${modeBadge}
              ${saveMdBtn}
              ${graphBtn}
              <span class="chat-msg-time">${esc(time)}</span>
            </header>
            ${traceHtml}
            ${bodyHtml}
            ${sourcesHtml}
            ${uploadHtml}
            ${artifactsHtml}
            ${actionsHtml}
          </div>
        </article>`;
    }).join("");
    restoreLayerAgentsUiState(el, layerAgentsState);
    bindUploadCardEvents(el);
    el.querySelectorAll(".chat-save-md").forEach((btn) => {
      btn.addEventListener("click", () => {
        const msg = items.find((m) => m.id === btn.dataset.msgId);
        if (!msg) return;
        const stamp = msg.created_at ? new Date(msg.created_at).toISOString().slice(0, 10) : "chat";
        downloadTextAsMd(`mkg-chat-${stamp}.md`, buildChatMdExport(msg));
      });
    });
    el.querySelectorAll(".chat-save-jsonld").forEach((btn) => {
      btn.addEventListener("click", () => {
        const msg = items.find((m) => m.id === btn.dataset.msgId);
        if (!msg) return;
        const stamp = msg.created_at ? new Date(msg.created_at).toISOString().slice(0, 10) : "chat";
        downloadJsonFile(`mkg-chat-${stamp}.jsonld`, buildChatJsonLdExport(msg));
      });
    });
    el.querySelectorAll(".chat-save-print").forEach((btn) => {
      btn.addEventListener("click", () => {
        const msg = items.find((m) => m.id === btn.dataset.msgId);
        if (msg) openChatPrintView(msg);
      });
    });
    el.querySelectorAll(".chat-show-graph").forEach((btn) => {
      btn.addEventListener("click", () => {
        const msg = items.find((m) => m.id === btn.dataset.msgId);
        if (msg) showMessageContextGraph(msg);
      });
    });
    el.querySelectorAll(".chat-source-link, .chat-source-chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        const docId = btn.dataset.docId;
        if (docId && window.MKG?.openDocWithMd) window.MKG.openDocWithMd(docId);
      });
    });
    mountMessageCharts(items);
    el.querySelectorAll(".chat-answer-sections-nav").forEach((nav) => {
      bindAnswerSectionNav(nav);
    });
    const scrollPolicy = options.scroll || (wasNearBottom ? "bottom" : "restore");
    applyChatScrollPolicy(scrollPolicy, prevScrollTop);
  }

  async function createThread() {
    const btn = $("chatNewBtn");
    const prev = btn?.textContent;
    if (btn) { btn.disabled = true; btn.textContent = "…"; }
    try {
      if (!await requireIdentity()) return;
      const r = await fetch(`${API}/chat/threads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "Новый чат", kind: "team", created_by: currentUser.id }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        showNotice(data.detail || "Не удалось создать чат", true);
        return;
      }
      activeThreadId = data.id;
      persistActiveThreadId(activeThreadId);
      lastMessagesFingerprint = "";
      lastLoadedThreadId = null;
      userScrolledUp = false;
      threadDocIds.set(activeThreadId, new Set());
      clearPendingComposeAttachments();
      resetThreadViewState();
      if ($("chatActiveTitle")) $("chatActiveTitle").textContent = data.title;
      renderMessages([], { scroll: "force" });
      await loadThreads();
      await loadMessages(activeThreadId, { scroll: "force", forceRender: true });
      $("chatMessageInput")?.focus();
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = prev; }
    }
  }

  async function postMessage(text, msgType = "user", authorName = null, authorId = null, meta = null, threadId = activeThreadId) {
    if (!threadId) return false;
    const r = await fetch(`${API}/chat/threads/${encodeURIComponent(threadId)}/messages`, {
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
    if (!r.ok) {
      const data = await r.json().catch(() => ({}));
      console.warn("postMessage failed:", parseApiError(data, "Не удалось сохранить сообщение"));
    }
    return r.ok;
  }

  function isWeakOrchestratorReply(text) {
    const t = String(text || "").trim();
    if (!t) return true;
    if (/^Найдено \d+ узлов и \d+ связей по слоям MKG\.\s*$/.test(t)) return true;
    if (t === "Недостаточно данных из графа для ответа.") return true;
    return !/##\s/.test(t) && t.length < 120;
  }

  function orchestratorResultText(res) {
    return String(res?.summary || res?.final_report || "").trim();
  }

  async function runChatLLMOrchestratorAsync(query, history, docIds) {
    const r = await fetch(`${API}/agents-service/run/async`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        mode: "orchestrator_mode",
        user_role: currentUser.role_id,
        doc_ids: docIds?.length ? docIds : undefined,
        history,
        limit: 5,
        speed_mode: "full",
      }),
    });
    const startData = await r.json().catch(() => ({}));
    if (!r.ok) {
      if (r.status === 404 || r.status === 503) {
        return runChatLLM(query, history, { usesOrchestrator: false, docIds });
      }
      throw new Error(parseApiError(startData, "Оркестратор недоступен"));
    }
    const runId = startData.run_id;
    if (!runId) throw new Error("Не получен run_id оркестратора");

    liveAccumulatedGraph = null;
    window.MKGMiniGraph?.destroy($("chatGraphCanvas"));
    const pollMs = 420;
    const maxWaitMs = 600000;
    const t0 = Date.now();

    const pollOnce = async () => {
      const sr = await fetch(`${API}/agents-service/run/${encodeURIComponent(runId)}`);
      const status = await sr.json().catch(() => ({}));
      if (!sr.ok) throw new Error(parseApiError(status, "Ошибка опроса оркестратора"));
      if (status.trace?.length) {
        updateTraceLiveFromPoll(status.trace);
        applyLiveGraphUpdate(status.graph, status.trace, status.layer_results);
        const lastStep = status.trace[status.trace.length - 1];
        if (lastStep?.layer) {
          setChatGraphBuilding(true, `Сбор графа… ${lastStep.layer} · ${lastStep.node_count ?? 0} узл.`);
        } else if (lastStep?.step === "discover_new_connections") {
          setChatGraphBuilding(true, `Сбор графа… новые связи · ${lastStep.node_count ?? 0} узл.`);
        }
      }
      return status;
    };

    while (Date.now() - t0 < maxWaitMs) {
      const status = await pollOnce();
      if (status.status === "complete" && status.result) {
        const res = status.result;
        const trace = [{ step: "chat_role", pipeline: "orchestrator_mode", elapsed_ms: 0 }, ...(res.trace || [])];
        return {
          text: res.summary || "",
          trace,
          graph: res.graph ? normalizeChatGraph(res.graph) : liveAccumulatedGraph,
          artifacts: [],
          sources: sourcesFromAgentResult(res),
          layer_results: res.layer_results || null,
          speed_mode: "full",
          timing_ms: res.elapsed_ms || 0,
        };
      }
      if (status.status === "error") {
        throw new Error(status.error || "Оркестратор завершился с ошибкой");
      }
      await sleep(pollMs);
    }
    throw new Error("Превышено время ожидания оркестратора");
  }

  function sourcesFromAgentResult(res) {
    const out = [];
    const seen = new Set();
    for (const lr of res.layer_results || []) {
      for (const n of lr.nodes_found || []) {
        const props = n.props || {};
        const docId = props._doc_id || props.document_id;
        const key = `${docId}|${n.id}`;
        if (seen.has(key)) continue;
        seen.add(key);
        if (docId) {
          out.push({
            document_id: docId,
            node_id: n.id,
            label: n.label,
            layer: lr.layer,
            text: props.quote || props.raw_text_ru || props.name_ru || "",
          });
        }
      }
    }
    return out.slice(0, 8);
  }

  async function runChatLLM(query, history, { usesOrchestrator = false, docIds = [] } = {}) {
    if (usesOrchestrator) {
      return runChatLLMOrchestratorAsync(query, history, docIds);
    }
    const prompt = (rolePromptData?.system_prompt || $("rolePromptText")?.value || "").trim();
    const docIdsMerged = docIds?.length ? docIds : getMergedDocIds();
    const speedMode = getChatSpeedMode();
    const r = await fetch(`${API}/chat/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: query,
        role_id: currentUser.role_id,
        history,
        system_prompt: prompt || undefined,
        include_graph: speedMode !== "fast",
        include_artifacts: speedMode !== "fast",
        document_ids: docIdsMerged,
        speed_mode: speedMode,
        ui_lang: window.MKG?.getUiLang?.() || "ru",
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
      layer_results: data.layer_results || null,
      speed_mode: data.speed_mode || speedMode,
      timing_ms: data.timing_ms || 0,
    };
  }

  function detectPipelineMode(trace, speedMode) {
    if (speedMode === "fast") return "fast";
    if (speedMode === "compare") return "compare";
    if ((trace || []).some((t) => String(t.step || "").startsWith("orchestrator"))) {
      return "orchestrator_mode";
    }
    const pipeline = (trace || []).find((t) => t.step === "chat_role")?.pipeline;
    return pipeline || "dialog";
  }

  function onChatComposeSubmit(e) {
    e?.preventDefault?.();
    if (!composeHasSendableContent() || isChatSending()) return;
    sendChatMessage();
  }

  async function sendChatMessage(forcedOptions = null) {
    if (isChatSending()) return;
    const opts = forcedOptions || {};
    const fromInput = !forcedOptions;
    const input = $("chatMessageInput");
    const draftText = fromInput ? (input?.value ?? "") : "";
    let text = opts.text ?? draftText.trim();
    const hasPending = fromInput && pendingComposeAttachments?.files?.length;
    if (!text && !hasPending && !opts.explain && !opts.regenerate && !opts.expand) return;

    const isNewQuestion = !opts.explain && !opts.regenerate && !opts.expand;
    let skipUserPost = !!opts.skipUserPost;
    let prefetchedHistory = null;

    if (opts.explain && opts.targetAgentMsgId) {
      text = "Поясни подробнее предыдущий ответ простым языком";
      prefetchedHistory = buildHistoryThrough(currentThreadMessages, opts.targetAgentMsgId);
    } else if (opts.expand && opts.targetAgentMsgId) {
      text = tt("action_expand_prompt", "Дополни предыдущий ответ: раскрой детали, добавь примеры и контекст, сохрани структуру");
      prefetchedHistory = buildHistoryThrough(currentThreadMessages, opts.targetAgentMsgId);
    } else if (opts.regenerate && opts.targetAgentMsgId) {
      const userMsg = findPrecedingUserMessage(currentThreadMessages, opts.targetAgentMsgId);
      if (!userMsg?.body) {
        showNotice("Не найден вопрос для обновления", true);
        return;
      }
      text = userMsg.body;
      prefetchedHistory = buildHistoryBeforeMessage(currentThreadMessages, userMsg.id);
      skipUserPost = true;
      await apiDeleteMessage(opts.targetAgentMsgId, { reload: false });
      await loadMessages(activeThreadId, { scroll: "restore", forceRender: true });
    }

    if (isNewQuestion || opts.regenerate) {
      resetChatGraphForNewQuestion();
    }

    const btn = $("chatSendBtn");
    const attachBtn = $("chatAttachBtn");
    if (btn) btn.textContent = "…";
    if (attachBtn) attachBtn.disabled = true;
    chatBusy = true;
    syncComposeSendButton();
    let history = prefetchedHistory || [];
    let messageAttachments = [];
    let sendThreadId = activeThreadId;
    let userPosted = false;
    let sendWatchdog = setTimeout(() => {
      if (!chatBusy) return;
      console.warn("MKG chat: send watchdog released stuck busy state");
      releaseChatComposeLock();
    }, CHAT_SEND_WATCHDOG_MS);
    try {
      if (!await requireIdentity()) return;
      if (!activeThreadId) {
        await createThread();
        if (!activeThreadId) return;
      }
      sendThreadId = activeThreadId;
      showChatUploadError("");

      if (hasPending) {
        const { files, processingMode } = pendingComposeAttachments;
        setChatGraphBuilding(true, "Загрузка и OCR прикреплённого файла…");
        try {
          const uploaded = await uploadFilesToServer(files, processingMode);
          if (!uploaded.length) return;
          clearPendingComposeAttachments();
          for (const item of uploaded) {
            addThreadDocId(sendThreadId, item.id);
            messageAttachments.push({
              kind: "upload",
              document_id: item.id,
              file_name: item.name,
              processing_mode: processingMode,
            });
          }
          trackUploadedDocs(uploaded, processingMode);
          await waitForDocsSearchable(uploaded.map((u) => u.id), processingMode);
          if (!text) {
            text = uploaded.length === 1
              ? `Вопрос по документу «${uploaded[0].name}»`
              : `Вопрос по документам (${uploaded.length})`;
          }
        } catch (e) {
          showChatUploadError(e.message || "Ошибка загрузки");
          return;
        } finally {
          setChatGraphBuilding(false);
        }
      }

      if (!prefetchedHistory) {
        try {
          const mr = await fetch(`${API}/chat/threads/${encodeURIComponent(sendThreadId)}/messages`);
          if (mr.ok) {
            const md = await mr.json();
            history = buildHistory(md.items || []);
          }
        } catch { /* ignore */ }
      }

      userScrolledUp = false;
      const docIds = getThreadDocIds(sendThreadId);
      const sel = window.MKG?.selectedDoc;
      if (sel && !docIds.includes(sel)) docIds.push(sel);
      if (!skipUserPost) {
        const posted = await postMessage(text, "user", null, null, {
          document_ids: docIds,
          attachments: messageAttachments.length ? messageAttachments : undefined,
        }, sendThreadId);
        if (!posted) {
          if (fromInput && input) input.value = draftText;
          showNotice("Не удалось отправить сообщение", true);
          return;
        }
        userPosted = true;
        if (fromInput && input) input.value = "";
        await loadThreads();
        if (activeThreadId === sendThreadId) {
          const activeThread = threads.find((x) => x.id === sendThreadId);
          if ($("chatActiveTitle") && activeThread) $("chatActiveTitle").textContent = activeThread.title;
          await loadMessages(sendThreadId, { scroll: "force" });
        }
      } else if (activeThreadId === sendThreadId) {
        await loadMessages(sendThreadId, { scroll: "force", forceRender: true });
      }

      const role = roleMeta(currentUser.role_id);
      const speedMode = getChatSpeedMode(sendThreadId);
      const isFast = speedMode === "fast";
      const usesOrchestrator = !isFast && role.can_run_agents !== false;
      const tracePreview = isFast
        ? FAST_PIPELINE_STEPS
        : usesOrchestrator
          ? AGENT_PIPELINE_STEPS
          : DIALOG_PIPELINE_STEPS;
      showTyping(true, tracePreview);
      if (!isFast) {
        setChatGraphBuilding(true, usesOrchestrator
          ? "Сбор графа… оркестратор"
          : "Сбор графа… Qdrant → обход");
      }
      let result = null;
      try {
        result = await runChatLLM(text, history, { usesOrchestrator, docIds });
        if (result?.text) result.text = sanitizeAgentAnswerBody(result.text);
        showTyping(false);
        if (result?.trace?.length) {
          mountCompletedTraceInPreview(result.trace);
        }

        if (!isFast && result?.graph?.nodes?.length) {
          lastFullscreenGraph = normalizeChatGraph(result.graph);
          liveAccumulatedGraph = lastFullscreenGraph;
          lastFullscreenTrace = result.trace;
        }

        if (!isFast && result?.graph?.nodes?.length) {
          setLastReplayableWalk({
            text: result.text,
            graph: result.graph,
            trace: result.trace,
            layerResults: result.layer_results,
          });
        }

        if (result.text) {
          if (!isFast && result.graph?.nodes?.length) {
            setChatGraphBuilding(false);
            try {
              await replayAnswerWithWalk({
                text: result.text,
                graph: result.graph,
                trace: result.trace,
                layerResults: result.layer_results,
              });
            } catch (graphErr) {
              console.warn("chat walk replay failed:", graphErr);
              await replayAnswerOnly(result.text);
            }
          } else {
            await replayAnswerOnly(result.text);
          }
        }

        const graphMeta = isFast ? null : prepareGraphForMeta(result.graph, result.trace, result.layer_results);
        await postMessage(result.text, "agent", "MKG AI", null, {
          trace: result.trace,
          mode: detectPipelineMode(result.trace, result.speed_mode),
          speed_mode: result.speed_mode || speedMode,
          timing_ms: result.timing_ms,
          graph: graphMeta,
          layer_results: isFast ? null : (result.layer_results || null),
          artifacts: isFast ? [] : (result.artifacts || []),
          sources: result.sources || [],
          ...(opts.regenerate ? { regenerated: true } : {}),
          ...(opts.explain ? { explained: true } : {}),
          ...(opts.expand ? { expanded: true } : {}),
        }, sendThreadId);
      } catch (e) {
        const raw = typeof e.message === "string" ? e.message : "AI недоступен";
        const msg = /Cannot add item|already exists/i.test(raw)
          ? "Ответ получен, но мини-граф не отобразился."
          : raw;
        await postMessage(`⚠ ${msg}`, "system", "Система", null, null, sendThreadId);
        updateChatGraphStats(null);
      } finally {
        cancelActiveGraphWalk();
        stopAnswerSectionWalk();
        removeStreamPreview();
        clearAgentQuestions();
        hideTraceLive();
        showTyping(false);
        setChatGraphBuilding(false);
        if (result?.graph?.nodes?.length) {
          updateChatGraphStats(normalizeChatGraph(result.graph), { building: false });
          toggleChatGraphPanel(true);
        } else if (!isFast) {
          updateChatGraphStats(null, { building: false });
        }
      }

      if (activeThreadId === sendThreadId) {
        await loadMessages(sendThreadId, {
          scroll: "bottom",
          sectionWalk: !!result?.text,
          forceRender: true,
        });
        await loadThreads();
      }
    } catch (e) {
      if (fromInput && !userPosted && input) input.value = draftText;
      if (!userPosted) showNotice(e?.message || "Не удалось отправить сообщение", true);
    } finally {
      clearTimeout(sendWatchdog);
      chatBusy = false;
      if (btn) btn.textContent = window.MKG?.t?.("chat_send") || "Отправить";
      if (attachBtn) attachBtn.disabled = !canShowUpload(roleMeta(currentUser?.role_id));
      syncComposeSendButton();
    }
  }

  async function runAgentQuery() {
    const query = ($("homeAgentQuery")?.value || "").trim();
    if (!query) return;
    window.MKG?.switchPage?.("chats");
    $("chatMessageInput").value = query;
    await sendChatMessage();
    const out = $("homeAgentResult");
    if (out) out.textContent = "Ответ в чате ↑";
  }

  async function refreshChatsPage() {
    await restoreSession();
    renderRoleCards();
    await loadThreads();
    if (activeThreadId) {
      await loadMessages(activeThreadId, { scroll: "restore", forceRender: true });
    }
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(() => {
      if (window.MKG?.currentPage === "chats" && activeThreadId) {
        loadMessages(activeThreadId);
        loadThreads();
      }
    }, 4000);
    healOrphanChatBusyUi();
  }

  function bindEvents() {
    syncChatSpeedToggleUi(getChatSpeedMode());
    $("chatSpeedToggle")?.querySelectorAll(".chat-speed-pill[data-speed]").forEach((btn) => {
      btn.addEventListener("click", () => setChatSpeedMode(btn.dataset.speed));
    });
    $("chatNewBtn")?.addEventListener("click", (e) => { e.preventDefault(); createThread(); });
    $("chatsCompose")?.addEventListener("submit", onChatComposeSubmit);
    $("chatMessageInput")?.addEventListener("input", syncComposeSendButton);
    $("chatMessageInput")?.addEventListener("keydown", (e) => {
      if (e.key !== "Enter" || e.shiftKey || e.isComposing) return;
      e.preventDefault();
      if (!composeHasSendableContent() || isChatSending()) return;
      sendChatMessage();
    });
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") healOrphanChatBusyUi();
    });
    syncComposeSendButton();
    $("chatAttachBtn")?.addEventListener("click", (e) => {
      e.preventDefault();
      $("chatFileInput")?.click();
    });
    $("chatFileInput")?.addEventListener("change", (e) => {
      const files = e.target?.files;
      if (files?.length) queueChatUpload(files);
    });
    $("chatUploadModeFull")?.addEventListener("click", () => {
      if (pendingUploadFiles) confirmPendingComposeAttachments("full");
    });
    $("chatUploadModeAnswers")?.addEventListener("click", () => {
      if (pendingUploadFiles) confirmPendingComposeAttachments("answers_only");
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
    $("chatGraphToggle")?.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      toggleChatGraphPanel();
    });
    $("chatGraphReplay")?.addEventListener("click", () => replayLastGraphWalk());
    $("chatGraphStop")?.addEventListener("click", () => stopGraphWalk());
    $("chatGraphExpand")?.addEventListener("click", () => toggleChatGraphMaximized());
    $("graphFullscreenClose")?.addEventListener("click", closeGraphFullscreenModal);
    $("graphFullscreenBackdrop")?.addEventListener("click", closeGraphFullscreenModal);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeGraphFullscreenModal();
    });
    initChatGraphResize();
    initChatGraphPanel();
    updateGraphReplayButton();
    $("chatAgentsDocLink")?.addEventListener("click", (e) => {
      e.preventDefault();
      window.MKG?.openDocGuide?.("layer-agents");
    });
    document.addEventListener("click", handlePipelineExpandClick);
    ensureLayerRoundNavDelegation();
  }

  renderRoleCards();

  try {
    bindEvents();
  } catch (err) {
    console.error("MKG chat bindEvents error:", err);
  }

  async function init() {
    await fetchRoles();
    const saved = loadSession();
    if (saved?.role_id) selectedRoleId = saved.role_id;
    await restoreSession();
    applyPermissions();
    updateChatGraphStats(null);
    await refreshChatsPage();
  }

  window.MKGAuth = {
    init,
    refreshChatsPage,
    requireIdentity,
    getCurrentUser: () => currentUser,
    getRole: () => roleMeta(currentUser?.role_id),
    getActiveThreadId: () => activeThreadId,
    canShowUpload,
    canDeleteDocument: () => canDeleteDocument(roleMeta(currentUser?.role_id || selectedRoleId)),
    applyPermissions,
    syncDocsUploadFallback,
  };

  init();
  window.MKG?.setPollUploadHook?.(pollUploadDoc);

  if (window.MKG) {
    window.MKG.onLangChange = () => {
      renderRoleCards();
      updateRoleHeader();
      updatePromptBadge();
      renderThreadList();
      updateGraphReplayButton();
      syncChatSpeedToggleUi(getChatSpeedMode());
      syncComposeSendButton();
      if (currentThreadMessages?.length) {
        renderMessages(currentThreadMessages, { scroll: "restore" });
      } else {
        const msgEl = $("chatMessages");
        if (msgEl) renderMessages([], {});
      }
      const graph = liveAccumulatedGraph || lastReplayableWalk?.graph;
      updateChatGraphStats(graph ? normalizeChatGraph(graph) : null);
      window.MKG?.onAppLangChange?.();
    };
  }
})();
