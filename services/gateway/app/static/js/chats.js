/** Чат: роль + автоматический пайплайн агентов */
(function () {
  const API = "/api/v1";
  const SESSION_KEY = "mkg_user_session";
  const ROLE_PROMPT_OPEN_KEY = "mkg_role_prompt_open";
  const CHAT_GRAPH_OPEN_KEY = "mkg_chat_graph_open";
  const $ = (id) => document.getElementById(id);

  const FALLBACK_ROLES = [
    { id: "researcher", name_ru: "Исследователь", can_run_agents: true, can_upload: true, icon: "🔬", tagline: "Гипотезы и связи", capability_ru: "Синтез из графа MKG" },
    { id: "analyst", name_ru: "Аналитик", can_run_agents: true, can_upload: false, icon: "📊", tagline: "Паттерны в данных", capability_ru: "Qdrant + графики + L4-кластеры" },
    { id: "validator", name_ru: "Валидатор", can_run_agents: true, can_upload: false, icon: "✓", tagline: "Проверка фактов", capability_ru: "Аудит фактов и противоречий" },
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
  };

  let chartInstances = [];
  let chatGraphCollapsed = false;
  let chatGraphMaximized = false;
  let chatGraphWidthBeforeMax = null;
  let lastFullscreenGraph = null;
  let lastFullscreenTrace = null;
  let lastReplayableWalk = null;
  let graphReplayBusy = false;

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
  let lastMessagesFingerprint = "";
  let lastLoadedThreadId = null;
  const CHAT_SCROLL_THRESHOLD = 120;
  const GRAPH_WALK_UI_STEP_MS = window.MKGMiniGraph?.GRAPH_WALK_UI_STEP_MS || 700;
  const TYPEWRITER_MIN_MS = 8;
  const TYPEWRITER_MAX_MS = 16;

  let activeWalkCancel = null;
  let activeStreamPreview = null;

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

  function clearPendingComposeAttachments() {
    pendingComposeAttachments = null;
    renderPendingAttachmentsPreview();
  }

  function renderPendingAttachmentsPreview() {
    const el = $("chatPendingAttachments");
    if (!el) return;
    const pending = pendingComposeAttachments;
    if (!pending?.files?.length) {
      el.innerHTML = "";
      el.classList.add("hidden");
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
      userScrolledUp = !isChatNearBottom();
    }, { passive: true });
  }

  function messagesFingerprint(items) {
    return (items || []).map((m) =>
      `${m.id}:${m.created_at}:${(m.meta?.sources?.length || 0)}`,
    ).join("|");
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
    const chips = sources.map((s, i) => {
      const docId = s.document_id || "";
      const name = esc(s.file_name || docId.slice(-12) || "?");
      const layer = s.layer ? `<span class="chat-source-layer">${esc(s.layer)}</span>` : "";
      return `<span class="chat-source-chip-wrap">${layer}<button type="button" class="chat-source-chip" data-doc-id="${esc(docId)}" data-source-idx="${i}" title="Открыть Markdown документа">${name}</button></span>`;
    }).join("");
    const detailItems = sources.map((s) => {
      const docId = s.document_id || "";
      const name = esc(s.file_name || docId.slice(-12) || "?");
      const layer = s.layer ? `<span class="chat-source-layer">${esc(s.layer)}</span>` : "";
      const snippet = s.text
        ? `<div class="chat-source-snippet md-render-view">${renderChatMarkdown(String(s.text).slice(0, 800))}</div>`
        : "";
      return `<li><button type="button" class="chat-source-link" data-doc-id="${esc(docId)}" title="Открыть Markdown документа">${name}</button>${layer}${snippet ? `<br>${snippet}` : ""}</li>`;
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
      out.push({
        document_id: docId,
        file_name: item.file_name || docId.slice(-12),
        node_id: nodeId,
        label: item.label || "",
        layer: item.layer || "",
        score: Number(item.score) || 0,
        text: String(item.text || item.quote || "").slice(0, 500),
        md_url: `/api/v1/documents/${docId}/markdown`,
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
        });
      });
    });
    return out.slice(0, 8);
  }

  function replayPayloadFromMessage(msg) {
    if (!msg || msg.msg_type !== "agent" || !hasContextGraph(msg.meta)) return null;
    return {
      text: msg.body || "",
      graph: msg.meta.graph,
      trace: msg.meta.trace || [],
      layerResults: msg.meta.layer_results || msg.meta.graph?.layer_results || null,
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
      ? "Пройти по графу заново"
      : (graphReplayBusy ? "Обход графа…" : "Нет обхода для повтора");
  }

  async function replayLastGraphWalk() {
    if (!lastReplayableWalk?.graph?.nodes?.length || graphReplayBusy) return;
    graphReplayBusy = true;
    updateGraphReplayButton();
    try {
      if (activeWalkCancel) {
        activeWalkCancel();
        activeWalkCancel = null;
      }
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

  function canShowUpload(role) {
    if (!role) return true;
    if (role.id === "admin" || role.can_admin) return true;
    if (role.can_upload === true) return true;
    if (role.can_upload === false) return false;
    return ["admin", "researcher", "engineer"].includes(role.id);
  }

  function applyPermissions() {
    const roleId = currentUser?.role_id || selectedRoleId;
    if (!roleId) return;
    const role = roleMeta(roleId);
    const uploadPanel = document.getElementById("homeTabUpload");
    const uploadBtn = $("uploadBtn");
    const clearBtn = $("clearDbBtn");
    const homeRun = $("homeAgentRunBtn");
    const showUpload = canShowUpload(role);
    if (uploadPanel) {
      uploadPanel.classList.toggle("upload-hidden", !showUpload);
      uploadPanel.style.display = "";
    }
    if (uploadBtn) uploadBtn.disabled = !showUpload;
    if (clearBtn) clearBtn.style.display = role.can_admin ? "" : "none";
    if (homeRun) homeRun.disabled = role.can_run_agents === false;
    const chatAttach = $("chatAttachBtn");
    const chatHint = $("chatUploadHint");
    if (chatAttach) chatAttach.style.display = showUpload ? "" : "none";
    if (chatHint) chatHint.style.display = showUpload ? "" : "none";
    if (chatAttach) chatAttach.disabled = !showUpload;
    syncDocsUploadFallback();
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
    const sidebarEl = uploadPanel?.closest(".docs-sidebar");
    const sidebarWideEnough = !sidebarEl || sidebarEl.getBoundingClientRect().width >= 200;
    const sidebarVisible = uploadPanel
      && !uploadPanel.classList.contains("upload-hidden")
      && uploadPanel.offsetParent !== null
      && sidebarWideEnough;
    fallback.classList.toggle("hidden", !onDocs || sidebarVisible);
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

  const TRACE_LABELS = {
    chat_role: "Роль",
    chat_memory: "Память",
    qdrant_search: "Qdrant",
    qdrant_l3: "Qdrant L3",
    qdrant_l4_cluster: "L4 кластеры",
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
    orchestrator_init: "Старт",
    orchestrator_plan: "План слоёв",
    orchestrator_router: "Маршрутизатор",
    agent_loop_start: "Цикл агентов",
    agent_loop_round: "Раунд",
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

  const PIPELINE_SETUP_STEPS = new Set([
    "orchestrator_init", "orchestrator_plan", "agent_loop_start", "layer_loop_start",
    "chat_role", "chat_memory", "qdrant_l3", "qdrant_l4_cluster", "graph_walk_step",
    "graph_traversal", "retrieval_search", "graph_context_loader",
  ]);

  const PIPELINE_TAIL_STEPS = new Set([
    "discover_new_connections", "connection_gap_analyzer", "orchestrator_synthesize", "llm_compose",
  ]);

  function agentStepToLayer(step) {
    const m = /^l([1-6])_agent$/.exec(String(step || ""));
    return m ? `L${m[1]}` : null;
  }

  function agentIdToLayer(agentId) {
    const step = String(agentId || "");
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

  function buildPipelineModel(trace) {
    const setup = [];
    const tail = [];
    const roundMap = new Map();
    let currentRound = 0;
    let maxRounds = 4;
    let seq = 0;
    let dialogLayerBatch = null;
    const seenBusIds = new Set();

    const flushDialogLayers = () => {
      if (!dialogLayerBatch?.length) return;
      const r = dialogLayerBatch[0].round ?? 0;
      const bucket = ensureRound(r);
      bucket.items.push({
        kind: "layer_batch",
        round: r,
        agents: dialogLayerBatch.slice(),
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
        const busKey = m.id || `${m.from}|${m.to}|${m.type}|${m.round ?? roundNum}`;
        if (seenBusIds.has(busKey)) return;
        seenBusIds.add(busKey);
        ensureRound(m.round ?? roundNum ?? currentRound).items.push({
          kind: "bus",
          from: m.from,
          to: m.to,
          type: m.type,
          preview: m.preview,
          round: m.round ?? roundNum ?? currentRound,
          id: seq++,
        });
      });
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

      if (step === "orchestrator_router") {
        flushDialogLayers();
        currentRound = t.round ?? currentRound;
        ensureRound(currentRound).items.push({ kind: "router", ...t, id: seq++ });
        pushBusMessages(t.bus_preview, currentRound);
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
        ensureRound(currentRound).items.push(agentItem);
        pushBusMessages(t.bus_messages, currentRound);
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

    const rounds = [...roundMap.values()].sort((a, b) => a.round - b.round);
    const flatItems = [
      ...setup,
      ...rounds.flatMap((r) => r.items),
      ...tail,
    ];

    return { setup, rounds, tail, maxRounds, flatItems };
  }

  function pipelineItemState(item, { live, activeId }) {
    if (!live) return "done";
    if (item.id == null) return "pending";
    if (item.id < activeId) return "done";
    if (item.id === activeId) return "active";
    return "pending";
  }

  function renderPipelineAgentChip(item, state) {
    const layer = item.layer || agentStepToLayer(item.step) || "?";
    const skipped = item.skipped ? " skipped" : "";
    const layerCls = /^L[1-6]$/.test(layer) ? ` layer-${layer}` : "";
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

  function renderPipelineBusChip(item, state) {
    const fromLayer = agentIdToLayer(item.from) || item.from || "?";
    const toLayer = agentIdToLayer(item.to) || item.to || "?";
    const type = item.type ? ` · ${item.type}` : "";
    const title = `${fromLayer} → ${toLayer}${type}`;
    return `<span class="agent-pipeline-bus st-${state}" title="${esc(title)}"><span class="agent-pipeline-bus-icon" aria-hidden="true">⇄</span><span class="agent-pipeline-bus-label">Шина</span><span class="agent-pipeline-bus-route">${esc(fromLayer)}→${esc(toLayer)}</span></span>`;
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

  function renderAgentPipeline(traceOrModel, { live = false, activeId = -1 } = {}) {
    const model = traceOrModel?.flatItems ? traceOrModel : buildPipelineModel(traceOrModel);
    const opts = { live, activeId };
    if (!model.setup.length && !model.rounds.length && !model.tail.length) return "";

    const setupHtml = model.setup.length
      ? `<div class="agent-pipeline-setup">${model.setup.map((item) => renderPipelineSetupChip(item, pipelineItemState(item, opts))).join('<span class="agent-pipeline-link" aria-hidden="true">→</span>')}</div>`
      : "";

    const roundsHtml = model.rounds.length
      ? `<div class="agent-pipeline-rounds">${model.rounds.map((round) => {
        const maxR = model.maxRounds || "?";
        const track = joinPipelineTrack(round.items, opts);
        return `<div class="agent-pipeline-round" data-round="${round.round}">
          <div class="agent-pipeline-round-head"><span class="agent-pipeline-round-id">R${round.round}</span><span class="agent-pipeline-round-cap muted">/${maxR}</span></div>
          <div class="agent-pipeline-round-track">${track || '<span class="muted small">…</span>'}</div>
        </div>`;
      }).join("")}</div>`
      : "";

    const tailHtml = model.tail.length
      ? `<div class="agent-pipeline-tail">${model.tail.map((item) => renderPipelineTailChip(item, pipelineItemState(item, opts))).join('<span class="agent-pipeline-link" aria-hidden="true">→</span>')}</div>`
      : "";

    return `<div class="agent-pipeline${live ? " is-live" : ""}">${setupHtml}${roundsHtml}${tailHtml}</div>`;
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
      .filter((t) => /^l[1-6]_agent$/.test(t.step || ""))
      .map((t, i) => ({
        layer: t.layer || String(t.step || "").replace("_agent", "").toUpperCase(),
        loop_index: t.loop_index ?? i + 1,
        loop_total: t.loop_total ?? 6,
        loop_phase: t.loop_phase || "",
        round: t.round ?? null,
        max_rounds: t.max_rounds ?? null,
        node_count: t.node_count ?? 0,
        rel_count: t.rel_count ?? 0,
        situation: t.situation_evaluation || t.reasoning || "",
        agent_question: t.agent_question || "",
        bus_messages: t.bus_messages || [],
        skipped: !!t.skipped,
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

  function buildRoundModel(steps, loopMeta) {
    const byRound = new Map();
    for (const s of steps) {
      const r = s.round ?? 0;
      if (!byRound.has(r)) byRound.set(r, []);
      byRound.get(r).push(s);
    }
    const roundNums = [...byRound.keys()].sort((a, b) => a - b);
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
    const atFirst = defaultRound === roundNums[0];
    const atLast = defaultRound === roundNums[roundNums.length - 1];
    return `<div class="layer-round-nav" data-round="${defaultRound}" data-rounds="${roundNums.join(",")}" data-max="${maxR}">
      <button type="button" class="layer-round-btn layer-round-prev" aria-label="Предыдущий раунд"${atFirst ? " disabled" : ""}>◀</button>
      <span class="layer-round-indicator">раунд <span class="layer-round-current">${curHuman}</span>/<span class="layer-round-max">${maxR}</span></span>
      <button type="button" class="layer-round-btn layer-round-next" aria-label="Следующий раунд"${atLast ? " disabled" : ""}>▶</button>
    </div>`;
  }

  function setLayerRoundNav(detail, round) {
    const nav = detail?.querySelector(".layer-round-nav");
    if (!nav) return;
    const rounds = nav.dataset.rounds.split(",").map(Number);
    const maxR = Number(nav.dataset.max) || rounds.length;
    if (!rounds.includes(round)) return;
    nav.dataset.round = String(round);
    const curEl = nav.querySelector(".layer-round-current");
    if (curEl) curEl.textContent = String(round + 1);
    const maxEl = nav.querySelector(".layer-round-max");
    if (maxEl) maxEl.textContent = String(maxR);
    const idx = rounds.indexOf(round);
    const prevBtn = nav.querySelector(".layer-round-prev");
    const nextBtn = nav.querySelector(".layer-round-next");
    if (prevBtn) prevBtn.disabled = idx <= 0;
    if (nextBtn) nextBtn.disabled = idx >= rounds.length - 1;
    detail.querySelectorAll("[data-round]").forEach((el) => {
      if (el.classList.contains("layer-round-nav")) return;
      const r = Number(el.dataset.round);
      el.classList.toggle("is-round-hidden", r !== round);
    });
  }

  function renderAgentBusHtml(trace, round = null) {
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
    return `<details class="chat-agent-bus">
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
    const statusCls = s.skipped ? "layer-agent-skipped" : "layer-agent-active";
    const status = s.skipped ? "нет данных" : `${s.node_count} узл · ${s.rel_count} св`;
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

  function renderLayerAgentsHtml(trace, layerResults) {
    const steps = extractLayerAgentSteps(trace, layerResults);
    if (!steps.length) return "";
    const loopMeta = extractLoopMeta(trace);
    const roundModel = buildRoundModel(steps, loopMeta);
    const { defaultRound, roundNums } = roundModel;
    const flows = roundNums.map((r) => {
      const roundSteps = roundModel.byRound.get(r) || [];
      const flowMeta = { ...loopMeta, round: r, round_count: r + 1 };
      return `<div class="layer-loop-flow-panel${roundPanelCls(r, defaultRound)}" data-round="${r}">${renderLayerLoopFlowHtml(roundSteps, flowMeta)}</div>`;
    }).join("");
    const busPanels = roundNums.map((r) => {
      const bus = renderAgentBusHtml(trace, r);
      if (!bus) return "";
      return `<div class="layer-round-bus-panel${roundPanelCls(r, defaultRound)}" data-round="${r}">${bus}</div>`;
    }).join("");
    const rows = steps.map((s, i) => renderLayerAgentRow(s, i, defaultRound)).join("");
    const maxR = loopMeta.max_rounds || roundModel.maxR || "?";
    const nav = renderRoundNav(roundModel);
    return `<details class="chat-layer-agents">
      <summary>Агенты · гибкий цикл (до ${maxR} раундов)</summary>
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

  function resetThreadViewState() {
    if (activeWalkCancel) {
      activeWalkCancel();
      activeWalkCancel = null;
    }
    removeStreamPreview();
    clearAgentQuestions();
    hideTraceLive();
    showTyping(false);
    setChatGraphBuilding(false);
    lastFullscreenGraph = null;
    lastFullscreenTrace = null;
    setLastReplayableWalk(null);
    updateChatGraphStats(null);
    window.MKGMiniGraph?.destroy($("chatGraphCanvas"));
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
    const article = document.createElement("article");
    article.className = "chat-msg msg-agent chat-stream-preview";
    article.innerHTML = `
      <div class="chat-msg-avatar" aria-hidden="true">AI</div>
      <div class="chat-msg-content">
        <header>
          <strong>MKG AI</strong>
          <span class="user-role-badge role-${esc(role.id)}">${esc(role.name_ru || role.id)}</span>
          <span class="chat-mode-badge">Формирование ответа…</span>
        </header>
        <div class="chat-msg-body md-render-view"></div>
      </div>`;
    box.appendChild(article);
    activeStreamPreview = article;
    scrollChatToBottom(false);
    return article;
  }

  function updateStreamPreviewBody(text) {
    const preview = ensureStreamPreview();
    const body = preview?.querySelector(".chat-msg-body");
    if (body) body.innerHTML = renderChatMarkdown(sanitizeAgentAnswerBody(text));
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
      await sleep(Math.min(GRAPH_WALK_UI_STEP_MS * 0.42, 450));
    }

    if (walkPath.length && canvas) {
      if (activeWalkCancel) activeWalkCancel();
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
      await walkPromise;
      activeWalkCancel = null;
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

  function renderAgentMessageTrace(m) {
    const trace = m.meta?.trace;
    if (!trace?.length) return "";
    const graphMeta = m.meta?.graph;
    const layerResults = graphMeta?.layer_results || m.meta?.layer_results;
    const isOrchestrator = m.meta?.mode === "orchestrator_mode";
    const isDialog = !m.meta?.mode || m.meta.mode === "dialog";
    if (isOrchestrator) return renderOrchestratorTraceHtml(trace, layerResults);
    if (isDialog) return renderDialogTraceHtml(trace, graphMeta, layerResults);
    return `${renderLayerAgentsHtml(trace, layerResults)}${renderGraphWalkTimelineHtml(trace, graphMeta)}${renderReasoningChainHtml(trace)}`;
  }

  function renderOrchestratorTraceHtml(trace, layerResults) {
    return `${renderLayerAgentsHtml(trace, layerResults)}${renderGraphWalkTimelineHtml(trace, null)}${renderReasoningChainHtml(trace)}`;
  }

  function renderDialogTraceHtml(trace, graph, layerResults) {
    return `${renderLayerAgentsHtml(trace, layerResults)}${renderGraphWalkTimelineHtml(trace, graph)}${renderReasoningChainHtml(trace)}`;
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
    if (item.step === "orchestrator_router") {
      const nxt = item.next_agent || "?";
      const bus = item.bus_size ? ` · шина:${item.bus_size}` : "";
      return `${nxt}${bus}`;
    }
    if (item.step === "agent_loop_round") {
      return `→ раунд ${item.round}/${item.max_rounds || "?"}`;
    }
    if (item.step === "orchestrator_plan" && item.layers?.length) {
      return item.layers.join("→");
    }
    if (item.step === "graph_walk_step") {
      const rel = item.rel_type ? ` · ${item.rel_type}` : "";
      return `${item.label || item.node_id || ""}${rel}`.trim();
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
    if (/^l[1-6]_agent$/.test(step || "") && item.agent_question) {
      parts.push(String(item.agent_question));
    }
    if (item.rel_count != null) parts.push(`связей: ${item.rel_count}`);
    if (item.walk_step_count != null) parts.push(`шагов обхода: ${item.walk_step_count}`);
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

  function showTraceLive(previewSteps) {
    const el = $("chatTraceLive");
    if (!el || !previewSteps?.length) return;
    let idx = 0;
    clearInterval(traceLiveTimer);
    clearInterval(traceLivePollTimer);
    const steps = normalizePipelineTraceItems(previewSteps);
    const render = () => {
      const partial = steps.slice(0, idx + 1);
      const model = buildPipelineModel(partial);
      const activeId = model.flatItems.length ? model.flatItems[model.flatItems.length - 1].id : -1;
      el.innerHTML = renderAgentPipeline(model, { live: true, activeId });
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
    const el = $("chatTraceLive");
    if (!el || !trace?.length) return;
    const model = buildPipelineModel(trace);
    const activeId = model.flatItems.length ? model.flatItems[model.flatItems.length - 1].id : -1;
    el.innerHTML = renderAgentPipeline(model, { live: true, activeId });
  }

  function showTraceComplete(trace) {
    clearInterval(traceLiveTimer);
    traceLiveTimer = null;
    clearInterval(traceLivePollTimer);
    traceLivePollTimer = null;
    const el = $("chatTraceLive");
    if (!el || !trace?.length) return;
    el.innerHTML = renderAgentPipeline(trace, { live: false });
  }

  function hideTraceLive() {
    clearInterval(traceLiveTimer);
    traceLiveTimer = null;
    clearInterval(traceLivePollTimer);
    traceLivePollTimer = null;
    const el = $("chatTraceLive");
    if (el) el.innerHTML = "";
  }

  function setChatGraphBuilding(on, text = "Поиск в Qdrant…") {
    const el = $("chatGraphBuilding");
    const txt = $("chatGraphBuildingText");
    if (on) toggleChatGraphPanel(true);
    if (el) el.classList.toggle("hidden", !on);
    if (txt && text) txt.textContent = text;
  }

  function showMessageContextGraph(msg) {
    const graph = msg?.meta?.graph;
    if (!graph) return;
    lastFullscreenGraph = graph;
    lastFullscreenTrace = msg.meta?.trace || [];
    setLastReplayableWalk(replayPayloadFromMessage(msg));
    toggleChatGraphPanel(true);
    renderChatContextGraph(graph, {
      animate: true,
      walkPath: graph.walk_path || [],
    });
  }

  function hasContextGraph(meta) {
    const g = meta?.graph;
    return !!(g && (g.nodes?.length || g.relationships?.length || g.graph_walk_steps?.length));
  }

  function updateChatGraphStats(graph) {
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
        ? `${nodes} узл · ${rels} св${traverseCount ? ` · ${traverseCount} шаг.` : ""}`
        : "0 узлов";
    }
    const showEmpty = nodes === 0 || rels === 0;
    if (empty) empty.classList.toggle("hidden", !showEmpty);
    if (emptyMsg) {
      emptyMsg.textContent = nodes > 0 && rels === 0
        ? "Обход не нашёл связей"
        : "Нет данных MKG для этого запроса.";
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

  function renderChatContextGraph(graph, { animate = true, walkPath = [], skipHighlight = false } = {}) {
    const canvas = $("chatGraphCanvas");
    if (!canvas || chatGraphCollapsed) return;
    const safeGraph = normalizeChatGraph(graph);
    updateChatGraphStats(safeGraph);
    const nodes = safeGraph?.nodes?.length || 0;
    const rels = safeGraph?.relationships?.length || 0;
    if (!nodes || !rels) {
      window.MKGMiniGraph?.destroy(canvas);
      return;
    }
    const path = walkPath?.length ? walkPath : (safeGraph?.walk_path || []);
    try {
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
    if (safeNodes && safeRels) {
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
    if (lastFullscreenGraph?.nodes?.length) {
      openGraphFullscreenModal(lastFullscreenGraph, lastFullscreenTrace);
      return;
    }
    const layout = getChatGraphLayout();
    const btn = $("chatGraphExpand");
    const handle = $("chatGraphResizeHandle");
    if (!layout) return;

    if (chatGraphCollapsed && force !== false) toggleChatGraphPanel(true);

    chatGraphMaximized = force !== undefined ? force : !chatGraphMaximized;
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
    }
    if (persist) localStorage.setItem(CHAT_GRAPH_OPEN_KEY, open ? "true" : "false");
    requestAnimationFrame(() => refreshChatGraphViewport());
  }

  function initChatGraphPanel() {
    setChatGraphPanelOpen(localStorage.getItem(CHAT_GRAPH_OPEN_KEY) !== "false");
  }

  function toggleChatGraphPanel(force) {
    const open = force !== undefined ? force : !chatGraphCollapsed;
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
    const nearBottom = isChatNearBottom();
    if (!force && !nearBottom) return;
    const scroll = () => { box.scrollTop = box.scrollHeight; };
    scroll();
    requestAnimationFrame(() => {
      scroll();
      requestAnimationFrame(scroll);
    });
    userScrolledUp = false;
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
      scrollChatToBottom(false);
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
        await loadMessages(activeThreadId, { scroll: "force" });
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
        const nextId = btn.dataset.id;
        if (nextId === activeThreadId) return;
        activeThreadId = nextId;
        lastMessagesFingerprint = "";
        lastLoadedThreadId = null;
        userScrolledUp = false;
        resetThreadViewState();
        renderThreadList();
        loadMessages(activeThreadId, { scroll: "force", forceRender: true });
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
        lastMessagesFingerprint = "";
        lastLoadedThreadId = null;
        userScrolledUp = false;
        threadDocIds.delete(threadId);
        resetThreadViewState();
        if ($("chatActiveTitle")) $("chatActiveTitle").textContent = "Диалог";
        const msgEl = $("chatMessages");
        if (msgEl) msgEl.innerHTML = '<p class="chat-empty-hint">Напишите первое сообщение…</p>';
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
      syncThreadDocsFromMessages(items);
      const fp = messagesFingerprint(items);
      const threadChanged = threadId !== lastLoadedThreadId;
      const fingerprintChanged = fp !== lastMessagesFingerprint;
      if (!threadChanged && !fingerprintChanged && !options.forceRender) {
        const t = threads.find((x) => x.id === threadId);
        if ($("chatActiveTitle") && t) $("chatActiveTitle").textContent = t.title;
        return;
      }
      lastLoadedThreadId = threadId;
      lastMessagesFingerprint = fp;
      renderMessages(items, options);
      syncLastReplayableFromMessages(items);
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

  function renderMessages(items, options = {}) {
    const el = $("chatMessages");
    if (!el) return;
    bindChatScrollListener();
    const prevScrollTop = el.scrollTop;
    const wasNearBottom = isChatNearBottom();
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
      const userAttachments = isUser && (m.meta?.attachments || []).length
        ? m.meta.attachments
        : [];
      const cls = isUpload ? "msg-upload" : isAgent ? "msg-agent" : m.msg_type === "system" ? "msg-system" : "msg-user";
      const time = m.created_at ? new Date(m.created_at).toLocaleString("ru-RU", { hour: "2-digit", minute: "2-digit" }) : "";
      const avatarText = isAgent ? "AI" : isUser ? (role.name_ru || "?").slice(0, 1) : "·";
      const avatarHtml = isUpload
        ? ((window.MKG_ICONS && MKG_ICONS.paperclip(16)) || "↑")
        : esc(avatarText);
      const avatarCls = isUpload ? " chat-msg-avatar-icon" : "";
      const trace = m.meta?.trace;
      const traceHtml = (isAgent && trace?.length) ? renderAgentMessageTrace(m) : "";
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
        ? `<button type="button" class="btn btn-ghost btn-small chat-save-md" data-msg-id="${esc(m.id)}" title="Сохранить ответ как .md">Сохранить как MD</button>`
        : "";
      const graphBtn = (isAgent && hasContextGraph(m.meta))
        ? `<button type="button" class="btn btn-ghost btn-small chat-show-graph" data-msg-id="${esc(m.id)}" title="Показать граф обхода контекста">Показать граф обхода</button>`
        : "";
      const modeBadge = isAgent && m.meta?.mode && m.meta.mode !== "dialog"
        ? `<span class="chat-mode-badge">${esc(AGENT_MODE_TRACE[m.meta.mode] || m.meta.mode)}</span>`
        : "";
      const bodyHtml = isAgent
        ? `<div class="chat-msg-body md-render-view">${renderChatMarkdown(sanitizeAgentAnswerBody(m.body))}</div>`
        : `<div class="chat-msg-body">${esc(m.body)}</div>`;
      return `
        <article class="chat-msg ${cls}">
          <div class="chat-msg-avatar${avatarCls}" aria-hidden="true">${avatarHtml}</div>
          <div class="chat-msg-content">
            <header>
              <strong>${esc(m.author_name)}</strong>
              ${!isUser && !isUpload ? `<span class="user-role-badge role-${esc(m.author_role)}">${esc(role.name_ru || m.author_role)}</span>` : ""}
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
    const scrollPolicy = options.scroll || (wasNearBottom ? "bottom" : "restore");
    applyChatScrollPolicy(scrollPolicy, prevScrollTop);
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
      layer_results: data.layer_results || null,
    };
  }

  function detectPipelineMode(trace) {
    if ((trace || []).some((t) => String(t.step || "").startsWith("orchestrator"))) {
      return "orchestrator_mode";
    }
    const pipeline = (trace || []).find((t) => t.step === "chat_role")?.pipeline;
    return pipeline || "dialog";
  }

  async function sendChatMessage() {
    const input = $("chatMessageInput");
    let text = (input?.value || "").trim();
    const hasPending = pendingComposeAttachments?.files?.length;
    if (!text && !hasPending) return;
    const btn = $("chatSendBtn");
    const attachBtn = $("chatAttachBtn");
    if (btn) { btn.disabled = true; btn.textContent = "…"; }
    if (attachBtn) attachBtn.disabled = true;
    let history = [];
    let messageAttachments = [];
    try {
      if (!await requireIdentity()) return;
      if (!activeThreadId) {
        await createThread();
        if (!activeThreadId) return;
      }
      showChatUploadError("");

      if (hasPending) {
        const { files, processingMode } = pendingComposeAttachments;
        setChatGraphBuilding(true, "Загрузка и OCR прикреплённого файла…");
        try {
          const uploaded = await uploadFilesToServer(files, processingMode);
          if (!uploaded.length) return;
          clearPendingComposeAttachments();
          for (const item of uploaded) {
            addThreadDocId(activeThreadId, item.id);
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

      try {
        const mr = await fetch(`${API}/chat/threads/${encodeURIComponent(activeThreadId)}/messages`);
        if (mr.ok) {
          const md = await mr.json();
          history = buildHistory(md.items || []);
        }
      } catch { /* ignore */ }

      input.value = "";
      userScrolledUp = false;
      const docIds = getMergedDocIds();
      await postMessage(text, "user", null, null, {
        document_ids: docIds,
        attachments: messageAttachments.length ? messageAttachments : undefined,
      });
      await loadMessages(activeThreadId, { scroll: "force" });

      const role = roleMeta(currentUser.role_id);
      const usesOrchestrator = role.can_run_agents !== false;
      const tracePreview = usesOrchestrator ? AGENT_PIPELINE_STEPS : DIALOG_PIPELINE_STEPS;
      showTyping(true, tracePreview);
      setChatGraphBuilding(true, usesOrchestrator
        ? "Оркестратор: гибкий цикл агентов (шина)…"
        : "Qdrant L3+L4 → обход графа…");
      let result = null;
      try {
        result = await runChatLLM(text, history);
        if (result?.text) result.text = sanitizeAgentAnswerBody(result.text);
        if (result?.trace?.length) showTraceComplete(result.trace);

        if (result.graph) {
          lastFullscreenGraph = result.graph;
          lastFullscreenTrace = result.trace;
        }

        if (result?.graph?.nodes?.length) {
          setLastReplayableWalk({
            text: result.text,
            graph: result.graph,
            trace: result.trace,
            layerResults: result.layer_results,
          });
        }

        if (result.text) {
          if (result.graph?.nodes?.length) {
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

        await postMessage(result.text, "agent", "MKG AI", null, {
          trace: result.trace,
          mode: detectPipelineMode(result.trace),
          graph: result.graph || null,
          layer_results: result.layer_results || null,
          artifacts: result.artifacts || [],
          sources: result.sources || [],
        });
      } catch (e) {
        const raw = typeof e.message === "string" ? e.message : "AI недоступен";
        const msg = /Cannot add item|already exists/i.test(raw)
          ? "Ответ получен, но мини-граф не отобразился."
          : raw;
        await postMessage(`⚠ ${msg}`, "system", "Система", null);
        updateChatGraphStats(null);
      } finally {
        if (activeWalkCancel) {
          activeWalkCancel();
          activeWalkCancel = null;
        }
        removeStreamPreview();
        clearAgentQuestions();
        showTyping(false);
        setChatGraphBuilding(false);
        if (result?.graph?.nodes?.length) {
          toggleChatGraphPanel(true);
        }
      }

      await loadMessages(activeThreadId, { scroll: "bottom" });
      await loadThreads();
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = "Отправить"; }
      if (attachBtn) attachBtn.disabled = !canShowUpload(roleMeta(currentUser?.role_id));
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
    $("chatGraphToggle")?.addEventListener("click", () => toggleChatGraphPanel());
    $("chatGraphReplay")?.addEventListener("click", () => replayLastGraphWalk());
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
    $("chatMessages")?.addEventListener("click", (e) => {
      const btn = e.target.closest(".layer-round-prev, .layer-round-next");
      if (!btn || btn.disabled) return;
      e.preventDefault();
      const detail = btn.closest(".chat-layer-agents");
      const nav = detail?.querySelector(".layer-round-nav");
      if (!nav) return;
      const rounds = nav.dataset.rounds.split(",").map(Number);
      const cur = Number(nav.dataset.round);
      const idx = rounds.indexOf(cur);
      if (btn.classList.contains("layer-round-prev") && idx > 0) {
        setLayerRoundNav(detail, rounds[idx - 1]);
      } else if (btn.classList.contains("layer-round-next") && idx < rounds.length - 1) {
        setLayerRoundNav(detail, rounds[idx + 1]);
      }
    });
  }

  bindEvents();
  renderRoleCards();

  async function init() {
    await fetchRoles();
    const saved = loadSession();
    if (saved?.role_id) selectedRoleId = saved.role_id;
    await restoreSession();
    applyPermissions();
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
    canShowUpload,
    applyPermissions,
    syncDocsUploadFallback,
  };
})();
