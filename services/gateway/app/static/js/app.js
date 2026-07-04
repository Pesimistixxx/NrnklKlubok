const API = "/api/v1";
const AGENT_API = "/api/v1/agents";

const $ = (id) => document.getElementById(id);

const els = {
  appRoot: $("appRoot"),
  mainArea: $("mainArea"),
  file: $("file"),
  drop: $("drop"),
  dropText: $("dropText"),
  pickBtn: $("pickBtn"),
  uploadBtn: $("uploadBtn"),
  uploadError: $("uploadError"),
  formatsHint: $("formatsHint"),
  classification: $("classification"),
  clearDbBtn: $("clearDbBtn"),
  docs: $("docs"),
  pageDocs: $("pageDocs"),
  pageGraphShell: $("pageGraphShell"),
  graphPanel: $("graphPanel"),
  pageQdrant: $("pageQdrant"),
  pageChats: $("pageChats"),
  pageSettings: $("pageSettings"),
  projectStageLine: null,
  viewAllGraphBtn: $("viewAllGraphBtn"),
  docPageBar: $("docPageBar"),
  docBackBtn: $("docBackBtn"),
  docPageTitle: $("docPageTitle"),
  docPageBadge: $("docPageBadge"),
  docPageMeta: $("docPageMeta"),
  docMetaGrid: $("docMetaGrid"),
  docPrimaryBtn: $("docPrimaryBtn"),
  docRebuildGraphBtn: $("docRebuildGraphBtn"),
  docReprocessBtn: $("docReprocessBtn"),
  docMdDownloadBtn: $("docMdDownloadBtn"),
  docMdInlineDownloadBtn: $("docMdInlineDownloadBtn"),
  docLogsBtn: $("docLogsBtn"),
  docNeo4jBtn: $("docNeo4jBtn"),
  docStopBtn: $("docStopBtn"),
  docMdPanel: $("docMdPanel"),
  docLogsPanel: $("docLogsPanel"),
  previewMdRender: $("previewMdRender"),
  previewMdSource: $("previewMdSource"),
  mdViewRenderBtn: $("mdViewRenderBtn"),
  mdViewSourceBtn: $("mdViewSourceBtn"),
  previewLogs: $("previewLogs"),
  logsPreview: $("previewLogs"),
  docListFilter: $("docListFilter"),
  graphPageHead: $("graphPageHead"),
  graphPageTitle: $("graphPageTitle"),
  graphPageLead: $("graphPageLead"),
  graphsEmpty: $("graphsEmpty"),
  graphsWorkspace: $("graphsWorkspace"),
  qdrantDocFilter: $("qdrantDocFilter"),
  qdrantSearchForm: $("qdrantSearchForm"),
  qdrantSearchQuery: $("qdrantSearchQuery"),
  qdrantSearchResults: $("qdrantSearchResults"),
  qdrantSearchMeta: $("qdrantSearchMeta"),
  qdrantPointsList: $("qdrantPointsList"),
  qdrantPointsCount: $("qdrantPointsCount"),
  qdrantClusterMap: $("qdrantClusterMap"),
  qdrantClusterCount: $("qdrantClusterCount"),
  qdrantIndexLog: $("qdrantIndexLog"),
  graphCanvas: $("graphCanvas"),
  graphCanvasWrap: $("graphCanvasWrap"),
  graphResizeHandle: $("graphResizeHandle"),
  graphNodeList: $("graphNodeList"),
  graphMapView: $("graphMapView"),
  graphRelsView: $("graphRelsView"),
  graphRelsList: $("graphRelsList"),
  graphRelsCount: $("graphRelsCount"),
  layerFilters: $("layerFilters"),
  crossLayerToggle: $("crossLayerToggle"),
  toggleNodeListBtn: $("toggleNodeListBtn"),
  viewMapBtn: $("viewMapBtn"),
  viewRelsBtn: $("viewRelsBtn"),
  originalGraphBtn: $("originalGraphBtn"),
  headerNeo4jBtn: $("headerNeo4jBtn"),
  l3EmbeddingStatus: $("l3EmbeddingStatus"),
  l3QdrantInfo: $("l3QdrantInfo"),
  l3Stats: $("l3Stats"),
  l3IndexBtn: $("l3IndexBtn"),
  l3IndexAllBtn: $("l3IndexAllBtn"),
  l4ClusterBtn: $("l4ClusterBtn"),
  graphCompactBtn: $("graphCompactBtn"),
  graphFullBtn: $("graphFullBtn"),
  llmModel: $("llmModel"),
  ocrModel: $("ocrModel"),
  embDocModel: $("embDocModel"),
  embQueryModel: $("embQueryModel"),
  saveConfigBtn: $("saveConfigBtn"),
  settingsSaveStatus: $("settingsSaveStatus"),
  diagBtn: $("diagBtn"),
  diagList: $("diagList"),
  liveExtract: $("liveExtract"),
  livePipeline: $("livePipeline"),
  liveStep: $("liveStep"),
  liveRels: $("liveRels"),
  docWorkHeader: $("docWorkHeader"),
  docWorkTitle: $("docWorkTitle"),
  docWorkBadge: $("docWorkBadge"),
  docWorkMeta: $("docWorkMeta"),
  docWorkTabJourney: $("docWorkTabJourney"),
  docWorkTabMd: $("docWorkTabMd"),
  docWorkTabGraph: $("docWorkTabGraph"),
  docJourneyPane: $("docJourneyPane"),
  docJourneyContent: $("docJourneyContent"),
  docMdPane: $("docMdPane"),
  docGraphPane: $("docGraphPane"),
  docMdInlineClean: $("docMdInlineClean"),
  docMdInlineMarked: $("docMdInlineMarked"),
  mdInlineCleanBtn: $("mdInlineCleanBtn"),
  mdInlineMarkedBtn: $("mdInlineMarkedBtn"),
  detailPanel: $("detailPanel"),
  detailBody: $("detailBody"),
  closeDetailBtn: $("closeDetailBtn"),
};

/** @type {HTMLElement|null} */
const logsPreview = els.previewLogs;

const LABEL_LAYER = {
  Material: "L1", Process: "L1", Equipment: "L1", ChemicalReagent: "L1", StandardMetric: "L1",
  Expert: "L2", Organization: "L2", Location: "L2", Timeline: "L2", Event: "L2", Facility: "L2", Document: "L2",
  TextParagraph: "L3", TextSection: "L3", LangContext: "L3", HeadingContext: "L3", DocumentText: "L3",
  ExperimentRun: "L4", TechStage: "L4", Measurement: "L4", Deviation: "L4", TrendVector: "L4",
  Formula: "L4", EnvironmentalCondition: "L4", Effect: "L4", Claim: "L4",
  SecurityRole: "L5", VerificationStatus: "L5", AuditTrail: "L5",
  TechnologySolution: "L6", EconomicIndicator: "L6", EnvironmentalIndicator: "L6",
};

const LAYER_COLOR = {
  L1: "#0288d1", L2: "#7b1fa2", L3: "#546e7a", L4: "#ef6c00", L5: "#c62828", L6: "#2e7d32", "L?": "#78909c",
};

const CROSS_LAYER_REL_TYPES = new Set(["DATA_SOURCE_FOR", "CONTEXT_FOR", "ABOUT"]);
const CROSS_LAYER_EDGE_COLOR = { color: "#ff9800", highlight: "#e65100" };
const L3_INTERNAL_REL_TYPES = new Set(["NEXT_PARAGRAPH", "TAGGED_WITH", "HAS_PARAGRAPH", "STRUCTURING"]);
const COMPACT_DOC_TEXT_ID = "__compact_doc_text__";
const MAX_COMPACT_PARAGRAPHS = 15;
const MAX_COMPACT_EDGES = 150;
const GRAPH_LABEL_MAX = 20;
const GRAPH_ALL_ID = "__all__";
const NEO4J_BROWSER_URL = "http://localhost:7474/browser/";

const DOC_PIPELINE = [
  { id: "upload", label: "Загрузка", short: "Файл" },
  { id: "ocr", label: "OCR / ingestion", short: "OCR" },
  { id: "md", label: "Markdown", short: "MD" },
  { id: "graph", label: "Extraction / граф", short: "Граф" },
  { id: "neo4j", label: "Neo4j", short: "Neo4j" },
  { id: "qdrant", label: "Индекс эмбеддингов L3 (Qdrant)", short: "L3" },
  { id: "l4", label: "HDBSCAN кластеризация L4", short: "L4" },
];

const JOURNEY_STAGES = [
  { id: "upload", title: "Загрузка файла", hint: "PDF, DOCX или другой формат принят в хранилище" },
  { id: "ocr", title: "OCR и ingestion", hint: "Распознавание текста, очистка, сборка Markdown" },
  { id: "md", title: "Markdown готов", hint: "Чистый MD и размеченный (L3 + узлы графа) — вкладка «Markdown», скачивание .md" },
  { id: "layers", title: "Извлечение слоёв L1–L6", hint: "LLM извлекает сущности, абзацы, факты, роли доступа…", isLayers: true },
  { id: "graph", title: "Граф знаний", hint: "Узлы и связи сохранены локально" },
  { id: "neo4j", title: "Neo4j", hint: "Синхронизация в графовую базу данных" },
  { id: "qdrant", title: "L3: индекс эмбеддингов (Qdrant)", hint: "TextParagraph → mkg_chunks, только семантический поиск (без HDBSCAN)" },
  { id: "l4", title: "L4: HDBSCAN кластеризация", hint: "Claim/Measurement → mkg_claims, cluster_id и is_anomaly для AI-поиска" },
];

/** Кнопки ↺ Перезапустить по этапам пайплайна */
const STAGE_RETRY = {
  ocr: { action: "reprocess", label: "↺ OCR", showOn: ["failed", "done"] },
  md: { action: "reprocess", label: "↺ OCR", showOn: ["done"] },
  layers: { action: "extract", label: "↺ Извлечение", showOn: ["failed", "done"] },
  graph: { action: "extract", label: "↺ Извлечение", showOn: ["failed", "done"] },
  neo4j: { action: "neo4j", label: "↺ Neo4j", showOn: ["failed", "done"] },
  qdrant: { action: "index", label: "↺ Индекс", showOn: ["failed", "done"] },
  l4: { action: "l4_cluster", label: "↺ HDBSCAN L4", showOn: ["failed", "done"] },
};

function isAnswersOnlyMode(doc) {
  return (doc?.processing_mode || "full") === "answers_only";
}

function shouldShowStageRetry(stageId, state, doc) {
  if (!doc || state === "active" || state === "pending" || state === "skipped") return false;
  const cfg = STAGE_RETRY[stageId];
  if (!cfg || !cfg.showOn.includes(state)) return false;
  if (isAnswersOnlyMode(doc) && ["layers", "graph", "neo4j", "l4"].includes(stageId)) return false;
  if (stageId === "md" && state !== "done") return false;
  if (stageId === "layers" && state === "done" && (doc.graph_nodes || 0) === 0) return false;
  if (stageId === "l4" && (doc.graph_nodes || 0) === 0) return false;
  return true;
}

function renderStageRetryBtn(docId, stageId, state, doc) {
  if (!shouldShowStageRetry(stageId, state, doc)) return "";
  const cfg = STAGE_RETRY[stageId];
  return `<button type="button" class="btn btn-ghost btn-small journey-retry-btn" data-retry-doc="${esc(docId)}" data-retry-action="${esc(cfg.action)}" data-retry-stage="${esc(stageId)}" title="Перезапустить этап">${esc(cfg.label)}</button>`;
}

function isL4Done(doc) {
  if (doc?.step === "l4_done") return true;
  if (doc?.step === "l4_cluster" || doc?.step === "l4_failed") return false;
  return doc?.l4_clusters != null;
}

function applyL4PipelineState(states, doc, { st, step, qdrant, nodes }) {
  if (isAnswersOnlyMode(doc)) {
    states.l4 = "skipped";
    return;
  }
  if (step === "l4_failed" || (st === "failed" && step === "l4_failed")) {
    states.l4 = "failed";
    return;
  }
  if (isL4Done(doc)) {
    states.l4 = "done";
    return;
  }
  if (states.qdrant === "done" && nodes > 0) {
    states.l4 = step === "l4_cluster" ? "active" : "active";
  } else if (states.qdrant === "done") {
    states.l4 = "pending";
  }
}

function getDocPipelineStates(doc) {
  const st = doc.status || "";
  const step = doc.step || "";
  const nodes = doc.graph_nodes || 0;
  const neo = doc.neo4j_synced === true;
  const docId = doc.id || doc.document_id;
  const qdrant = docId ? indexedDocsSet.has(docId) : false;
  const states = Object.fromEntries(DOC_PIPELINE.map((s) => [s.id, "pending"]));
  states.upload = "done";

  if (isAnswersOnlyMode(doc)) {
    states.ocr = ["uploaded", "processing"].includes(st) ? "active" : (st === "failed" && (step.includes("ingestion") || step === "ingestion_failed") ? "failed" : "done");
    states.md = states.ocr === "active" ? "pending" : (states.ocr === "failed" ? "pending" : "done");
    states.graph = "skipped";
    states.neo4j = "skipped";
    if (st === "failed" && (step === "index_failed" || step.includes("index"))) {
      states.qdrant = "failed";
    } else if (qdrant || (st === "loaded" && step === "answers_indexed")) {
      states.qdrant = "done";
    } else if (states.md === "done" && ["md_ready", "loaded"].includes(st)) {
      states.qdrant = "active";
    }
    applyL4PipelineState(states, doc, { st, step, qdrant, nodes: 0 });
    return states;
  }

  const markDoneThrough = (stageId) => {
    let found = false;
    for (const s of DOC_PIPELINE) {
      if (s.id === stageId) { found = true; continue; }
      if (!found) states[s.id] = "done";
    }
  };

  if (st === "failed") {
    markDoneThrough("upload");
    if (step.includes("ingestion") || step === "ingestion_failed") {
      states.ocr = "failed";
    } else if (step.includes("extraction") || step === "extraction_empty") {
      states.ocr = states.md = "done";
      states.graph = "failed";
    } else if (step === "neo4j_load") {
      states.ocr = states.md = states.graph = "done";
      states.neo4j = "failed";
    } else if (step === "l4_failed" || step === "l4_cluster") {
      states.ocr = states.md = states.graph = "done";
      states.neo4j = neo ? "done" : "failed";
      states.qdrant = qdrant ? "done" : "failed";
      states.l4 = step === "l4_failed" ? "failed" : "active";
    } else {
      states.graph = "failed";
    }
    applyL4PipelineState(states, doc, { st, step, qdrant, nodes });
    return states;
  }

  switch (st) {
    case "uploaded":
      states.ocr = "active";
      break;
    case "processing":
      states.ocr = "active";
      break;
    case "md_ready":
      states.ocr = states.md = "done";
      if (nodes > 0) {
        states.graph = "done";
        states.neo4j = neo ? "done" : "pending";
        states.qdrant = qdrant ? "done" : "pending";
      } else {
        states.graph = "active";
      }
      break;
    case "extracting":
      states.ocr = states.md = "done";
      if (step === "neo4j_load") {
        states.graph = "done";
        states.neo4j = "active";
      } else {
        states.graph = "active";
      }
      break;
    case "loaded":
      states.ocr = states.md = "done";
      states.graph = nodes > 0 ? "done" : "failed";
      states.neo4j = neo ? "done" : (nodes > 0 ? "active" : "pending");
      states.qdrant = qdrant ? "done" : (neo && nodes > 0 ? "active" : "pending");
      break;
    default:
      break;
  }
  applyL4PipelineState(states, doc, { st, step, qdrant, nodes });
  return states;
}

function renderDocPipelineHtml(doc, { compact = true, showRetry = true } = {}) {
  const states = getDocPipelineStates(doc);
  const docId = doc.id || doc.document_id;
  const chips = DOC_PIPELINE.map((s, i) => {
    const state = states[s.id] || "pending";
    const label = compact ? s.short : s.label;
    const stepHint = doc.step && state === "active" ? (STEP_RU[doc.step] || doc.step) : "";
    const title = stepHint ? `${s.label} · ${stepHint}` : s.label;
    const retry = showRetry && docId && shouldShowStageRetry(s.id, state, doc)
      ? `<button type="button" class="doc-pipe-retry" data-retry-doc="${esc(docId)}" data-retry-action="${esc(STAGE_RETRY[s.id]?.action || "")}" data-retry-stage="${esc(s.id)}" title="Перезапустить">${esc(STAGE_RETRY[s.id]?.label || "↺")}</button>`
      : "";
    return `<span class="doc-pipe-step ${state}" title="${esc(title)}">${esc(label)}${retry}</span>`;
  });
  const joined = [];
  chips.forEach((chip, i) => {
    joined.push(chip);
    if (i < chips.length - 1) joined.push('<span class="doc-pipe-arrow">→</span>');
  });
  return `<div class="doc-pipeline">${joined.join("")}</div>`;
}

function getLayersJourneyState(doc, layers) {
  if (isAnswersOnlyMode(doc)) return "skipped";
  const st = doc?.status || "";
  const nodes = doc?.graph_nodes || 0;
  const pipe = getDocPipelineStates(doc);
  if (st === "failed" && pipe.graph === "failed") return "failed";
  if (pipe.graph === "done" || (st === "loaded" && nodes > 0)) return "done";
  if (st === "extracting") return "active";
  if (st === "md_ready" && nodes === 0) return "active";
  if (layers?.some((l) => l.status === "running")) return "active";
  if (layers?.some((l) => l.status === "done" || l.status === "partial")) return "active";
  if (pipe.md === "done") return "pending";
  return "pending";
}

function journeyMarkerIcon(state) {
  if (state === "done") return "✓";
  if (state === "failed") return "!";
  if (state === "skipped") return "—";
  if (state === "active") return "●";
  return "○";
}

function renderJourneyLayerGrid(layers) {
  if (!layers?.length) {
    return '<p class="muted">Слои появятся при запуске извлечения графа.</p>';
  }
  return `<div class="journey-layer-grid">${layers.map((l) => `
    <div class="journey-layer st-${l.status}" title="${esc(l.title)}">
      <span class="jl-id l-${l.id}">${esc(l.id)}</span>
      <span class="jl-title">${esc(l.title)}</span>
      <span class="jl-stat">${esc(LAYER_STATUS_RU[l.status] || l.status)} · ${l.nodes} узл · ${l.relationships} св</span>
    </div>`).join("")}</div>`;
}

function renderJourneyRecentRels(rels) {
  if (!rels?.length) return "";
  const chips = rels.slice(-8).map((rel) =>
    `<span class="rel-chip rel-chip-${esc(rel.layer || "L?")}" title="${esc(rel.type)}"><span class="rel-from">${esc(rel.from_short)}</span><b>${esc(rel.type)}</b><span class="rel-to">${esc(rel.to_short)}</span></span>`,
  ).join("");
  return `<div class="journey-recent-rels"><h6>Последние связи</h6>${chips}</div>`;
}

function renderDocJourneyHtml(doc, layerPayload) {
  if (!doc) {
    return '<p class="muted doc-work-empty">Выберите документ слева или загрузите новый файл.</p>';
  }
  const docId = doc.id || doc.document_id;
  const states = getDocPipelineStates(doc);
  const layers = layerPayload?.layers || [];
  const layersState = getLayersJourneyState(doc, layers);
  const stepHint = doc.step ? (STEP_RU[doc.step] || doc.step) : "";
  const showLayerBlock = ["md_ready", "extracting", "loaded", "failed"].includes(doc.status);

  const steps = JOURNEY_STAGES.map((stage) => {
    let state = states[stage.id] || "pending";
    if (stage.isLayers) state = layersState;
    if (stage.id === "graph" && isAnswersOnlyMode(doc)) state = "skipped";
    if (stage.id === "neo4j" && isAnswersOnlyMode(doc)) state = "skipped";
    if (stage.id === "l4" && isAnswersOnlyMode(doc)) state = "skipped";
    let detail = "";
    if (state === "active" && stepHint && (stage.id === "ocr" || stage.id === "layers" || stage.id === "graph" || stage.id === "neo4j" || stage.id === "l4")) {
      detail = `<div class="journey-step-detail">${esc(stepHint)}</div>`;
    } else if (stage.id === "upload" && doc.size_bytes) {
      detail = `<div class="journey-step-detail">${esc(formatBytes(doc.size_bytes))} · ${esc(formatDateTime(doc.upload_date))}</div>`;
    } else if (stage.id === "md" && state === "done") {
      detail = '<div class="journey-step-detail">Вкладка «Markdown»: без разметки / с L3-маркерами · «Скачать .md»</div>';
    } else if (stage.id === "graph" && state === "done" && doc.graph_nodes) {
      detail = `<div class="journey-step-detail">${doc.graph_nodes} узлов · ${doc.graph_relationships || 0} связей</div>`;
    } else if (stage.id === "neo4j" && doc.neo4j_synced) {
      detail = '<div class="journey-step-detail">Синхронизировано с Neo4j</div>';
    } else if (stage.id === "qdrant" && docId && indexedDocsSet.has(docId)) {
      detail = '<div class="journey-step-detail">L3 TextParagraph проиндексированы в mkg_chunks</div>';
    } else if (stage.id === "l4" && isL4Done(doc)) {
      const clusters = doc.l4_clusters ?? 0;
      const anomalies = doc.l4_anomalies ?? 0;
      const clustered = doc.l4_clustered ?? 0;
      detail = `<div class="journey-step-detail">${clustered} точек · ${clusters} кластеров · ${anomalies} аномалий</div>`;
    } else if (stage.id === "l4" && doc.l4_error) {
      detail = `<div class="journey-step-detail">${esc(doc.l4_error)}</div>`;
    } else if (state === "failed" && doc.error) {
      detail = `<div class="journey-step-detail">${esc(doc.error)}</div>`;
    }

    const layerBlock = stage.isLayers && showLayerBlock
      ? `<div class="journey-layer-block"><h5>Слои L1–L6</h5>${renderJourneyLayerGrid(layers)}${doc.status === "extracting" ? renderJourneyRecentRels(layerPayload?.recent_relationships) : ""}</div>`
      : "";

    return `
      <div class="journey-step ${state}">
        <div class="journey-marker">${journeyMarkerIcon(state)}</div>
        <div class="journey-body">
          <div class="journey-step-head">
            <h4>${esc(stage.title)}</h4>
            ${renderStageRetryBtn(docId, stage.id, state, doc)}
          </div>
          <p class="muted">${state === "skipped" ? "Пропущено (режим «только для ответов»)" : esc(stage.hint)}</p>
          ${detail}
          ${layerBlock}
        </div>
      </div>`;
  });

  return `<div class="doc-journey-timeline">${steps.join("")}</div>`;
}

let docWorkTab = "journey";
let docWorkTabManual = false;
let layerJourneyCache = null;
let layerJourneyDocId = null;

async function refreshDocJourney(docId) {
  if (!docId || !els.docJourneyContent) return null;
  let layerPayload = null;
  const doc = docsListCache.find((d) => d.id === docId);
  const needLayers = doc && ["md_ready", "extracting", "loaded", "failed"].includes(doc.status);
  if (needLayers) {
    try {
      const r = await fetch(`${API}/documents/${encodeURIComponent(docId)}/pipeline/layers`);
      if (r.ok) {
        layerPayload = await r.json();
        layerJourneyCache = layerPayload;
        layerJourneyDocId = docId;
      }
    } catch { /* ignore */ }
  } else {
    layerJourneyCache = null;
    layerJourneyDocId = null;
  }
  return layerPayload;
}

function updateDocWorkHeader(doc) {
  const show = isInlineGraphPage() && graphScope === "doc" && doc;
  els.docWorkHeader?.classList.toggle("hidden", !show);
  if (!show || !doc) return;
  const label = statusLabel(doc);
  if (els.docWorkTitle) els.docWorkTitle.textContent = doc.file_name || doc.document_id || doc.id;
  if (els.docWorkBadge) {
    els.docWorkBadge.textContent = label.text;
    els.docWorkBadge.className = `badge ${label.cls}`;
  }
  if (els.docWorkMeta) {
    const step = doc.step ? stepLabel(doc.step) : "";
    els.docWorkMeta.textContent = step ? `Шаг: ${step}` : "";
  }
  const isAll = graphScope === "all";
  els.docWorkTabJourney?.classList.toggle("hidden", isAll);
  els.docWorkTabMd?.classList.toggle("hidden", isAll);
}

function syncDocWorkTabUI(tab) {
  if (!["journey", "md", "graph"].includes(tab)) tab = "journey";
  document.querySelectorAll(".doc-work-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });
  els.docJourneyPane?.classList.toggle("active", tab === "journey");
  els.docMdPane?.classList.toggle("active", tab === "md");
  els.docGraphPane?.classList.toggle("active", tab === "graph");
}

function setDocWorkTab(tab, { manual = false } = {}) {
  if (!["journey", "md", "graph"].includes(tab)) tab = "journey";
  if (manual) docWorkTabManual = true;
  docWorkTab = tab;
  syncDocWorkTabUI(tab);
  if (tab === "graph") {
    refreshGraphViewport();
    const docId = graphScope === "all" ? GRAPH_ALL_ID : (graphViewDocId || selectedDoc || pickGraphDocId());
    if (docId && isGraphHostPage()) loadGraph(docId);
  }
}

function maybeAutoDocWorkTab(doc, prevStatus) {
  if (!isInlineGraphPage() || graphScope !== "doc" || !doc) return;
  if (docWorkTabManual && docWorkTab === "graph") return;
  if (prevStatus === "processing" && doc.status === "md_ready") {
    setDocWorkTab("md");
    docWorkTabManual = false;
    return;
  }
  if (ACTIVE_DOC_STATUSES.has(doc.status)) {
    setDocWorkTab("journey");
    return;
  }
  if (doc.status === "loaded" && (doc.graph_nodes || 0) > 0 && !docWorkTabManual) {
    setDocWorkTab("graph");
  }
}

async function updateDocWorkArea(doc, previewData) {
  if (!isInlineGraphPage()) return;
  const data = previewData || doc;
  updateDocWorkHeader(data);
  if (!data || graphScope !== "doc") {
    if (els.docJourneyContent) {
      els.docJourneyContent.innerHTML = renderDocJourneyHtml(null);
    }
    return;
  }
  const docId = data.id || data.document_id;
  let layerPayload = layerJourneyDocId === docId ? layerJourneyCache : null;
  if (["md_ready", "extracting", "loaded", "failed"].includes(data.status)) {
    layerPayload = await refreshDocJourney(docId) || layerPayload;
  }
  if (els.docJourneyContent) {
    els.docJourneyContent.innerHTML = renderDocJourneyHtml(data, layerPayload);
    bindRetryButtons(els.docJourneyContent);
  }
  syncDocWorkTabUI(docWorkTab);
}

function updateDocPipelinePanel(doc) {
  updateDocWorkArea(doc);
}

const STEP_RU = {
  ingestion: "OCR / ingestion",
  reprocess: "повтор OCR",
  extraction: "извлечение",
  layer_L3: "текст L3",
  layer_L5: "доступ L5",
  layer_L2_L6: "контекст и ТЭП",
  layer_L2: "контекст L2",
  layer_L6: "ТЭП L6",
  layer_L1_L4: "сущности и факты",
  neo4j_load: "загрузка Neo4j",
  extraction_failed: "ошибка extraction",
  ingestion_failed: "ошибка ingestion",
  index_failed: "ошибка индексации",
  answers_indexed: "индекс для чата",
  qdrant_index: "индекс эмбеддингов L3",
  l4_cluster: "HDBSCAN L4",
  l4_done: "кластеризация L4 готова",
  l4_failed: "ошибка L4",
  cancelling: "остановка",
  extraction_cancelled: "остановлено",
  extraction_empty: "пустой граф",
};

const LAYER_STATUS_RU = {
  pending: "ожид.",
  running: "идёт",
  done: "готово",
  partial: "частично",
  empty: "пусто",
  failed: "ошибка",
};

let selectedDoc = null;
let currentPage = "chats";
let graphScope = "doc";
let docPanelMode = null;
let docListFilterText = "";
let graphNodeListVisible = false;
let lastQdrantIndexLog = "";
let markdownClean = "";
let markdownMarked = "";
let mdViewMode = "clean";
const ACTIVE_DOC_STATUSES = new Set(["uploaded", "processing", "extracting"]);
/** Документы, ожидающие автозапуск extraction после ingestion */
const pipelineQueue = new Set();
let graphLayerFilter = "all";
let showCrossLayerOnly = false;
let graphDensityMode = "compact";
let graphViewMode = "map";
let graphData = { nodes: [], relationships: [] };
let visNetwork = null;
let visNodesDataSet = null;
let visEdgesDataSet = null;
let lastGraphRenderKey = "";
let lastGraphDataKey = "";
let lastGraphDocId = null;
let graphPhysicsStable = false;
let embeddingStatusCache = null;
let graphViewDocId = null;
let graphVisible = false;
let docsListCache = [];
let selectedFiles = [];
let docStatusCache = new Map();
let indexedDocsSet = new Set(JSON.parse(localStorage.getItem("mkg_indexed_docs") || "[]"));
let lastLogsDocId = null;
let lastLogsKey = "";
let docGraphCountCache = new Map();
const GRAPH_CONTENT_HASH_LIMIT = 12000;

let nodeFieldHints = {};

async function loadNodeFieldHints() {
  try {
    const r = await fetch(`${API}/ontology/node-fields`);
    if (r.ok) nodeFieldHints = await r.json();
  } catch { /* ignore */ }
}

function propHasValue(v) {
  if (v === null || v === undefined) return false;
  if (typeof v === "string") return v.trim().length > 0;
  if (Array.isArray(v)) return v.length > 0;
  if (typeof v === "object") return Object.keys(v).length > 0;
  return true;
}

function formatPropValue(v) {
  if (!propHasValue(v)) return '<span class="prop-empty-val">— не задано</span>';
  if (Array.isArray(v)) {
    return v.map((x) => `<span class="prop-tag">${esc(String(x))}</span>`).join(" ");
  }
  if (typeof v === "object") {
    return `<pre class="prop-json">${esc(JSON.stringify(v, null, 2))}</pre>`;
  }
  const s = String(v);
  if (s.length > 400) return `<div class="prop-long">${esc(s)}</div>`;
  return esc(s);
}

function renderNodePropsSection(label, props) {
  const hints = nodeFieldHints[label] || [];
  const skip = new Set(["id"]);
  const actualKeys = Object.keys(props || {}).filter((k) => !skip.has(k) && propHasValue(props[k]));
  const ordered = [];
  hints.forEach((k) => { if (!skip.has(k) && !ordered.includes(k)) ordered.push(k); });
  actualKeys.forEach((k) => { if (!ordered.includes(k)) ordered.push(k); });

  if (!ordered.length) {
    return '<p class="muted">Нет свойств в payload узла</p>';
  }

  let expectedFilled = 0;
  const hintSet = new Set(hints);
  const rows = ordered.map((key) => {
    const has = propHasValue(props[key]);
    const expected = hintSet.has(key);
    if (expected && has) expectedFilled += 1;
    let rowCls = "prop-row";
    if (has && expected) rowCls += " prop-ok";
    else if (has && !expected) rowCls += " prop-extra";
    else if (!has && expected) rowCls += " prop-missing";
    else rowCls += " prop-empty";
    const badge = expected
      ? (has ? '<span class="prop-badge ok">✓</span>' : '<span class="prop-badge miss">ожидается</span>')
      : (has ? '<span class="prop-badge extra">+</span>' : "");
    return `<div class="${rowCls}"><dt>${esc(key)} ${badge}</dt><dd>${formatPropValue(props[key])}</dd></div>`;
  }).join("");

  const hintCount = hints.filter((k) => !skip.has(k)).length;
  const summary = hintCount
    ? `<p class="detail-props-summary">Заполнено <b>${expectedFilled}/${hintCount}</b> ожидаемых · всего полей <b>${actualKeys.length}</b></p>`
    : `<p class="detail-props-summary">Полей в узле: <b>${actualKeys.length}</b> (схема для ${esc(label)} не задана)</p>`;

  return `${summary}<dl class="detail-props detail-props-full">${rows}</dl>`;
}

function renderRelBlock(rels, direction) {
  if (!rels.length) return '<p class="muted">—</p>';
  return rels.map((r) => {
    const other = direction === "in" ? (r.from || r.from_) : r.to;
    const arrow = direction === "in"
      ? `${esc(other)} → <b>${esc(r.type)}</b>`
      : `<b>${esc(r.type)}</b> → ${esc(r.to)}`;
    const rp = r.props || {};
    const rpKeys = Object.keys(rp).filter((k) => propHasValue(rp[k]));
    const rpHtml = rpKeys.length
      ? `<div class="detail-rel-props">${rpKeys.map((k) => `<span><i>${esc(k)}</i>: ${esc(typeof rp[k] === "object" ? JSON.stringify(rp[k]) : rp[k])}</span>`).join(" · ")}</div>`
      : "";
    return `<div class="detail-rel-item">${arrow}${rpHtml}</div>`;
  }).join("");
}

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
}

function showBox(el, msg) {
  if (!el) return;
  if (!msg) {
    el.style.display = "none";
    el.textContent = "";
    return;
  }
  el.style.display = "block";
  el.textContent = msg;
}

function pickFiles(fileList) {
  selectedFiles = Array.from(fileList || []);
  if (!selectedFiles.length) {
    if (els.uploadBtn) els.uploadBtn.disabled = true;
    return;
  }
  showBox(els.uploadError, "");
  const names = selectedFiles.map((f) => f.name).slice(0, 2).join(", ");
  const more = selectedFiles.length > 2 ? ` +${selectedFiles.length - 2}` : "";
  const totalKb = selectedFiles.reduce((s, f) => s + f.size, 0) / 1024;
  if (els.dropText) {
    els.dropText.innerHTML = `<b>${selectedFiles.length} файл(ов)</b><br><span class="muted">${esc(names)}${esc(more)} · ${totalKb.toFixed(1)} КБ</span>`;
  }
  if (els.uploadBtn) els.uploadBtn.disabled = false;
}

function resetDropZone() {
  selectedFiles = [];
  if (els.file) els.file.value = "";
  if (els.dropText) {
    els.dropText.innerHTML = 'Перетащите файл или нажмите<br><span class="muted">PDF · DOCX · XLSX · MD · TXT</span>';
  }
  if (els.uploadBtn) els.uploadBtn.disabled = true;
}

function openFilePicker() {
  if (!els.file) return;
  els.file.value = "";
  els.file.click();
}

async function loadFormats() {
  if (!els.formatsHint) return;
  try {
    const r = await fetch(`${API}/formats`);
    if (!r.ok) return;
    const f = await r.json();
    els.formatsHint.textContent = `${f.extensions.join(" · ")} · до ${(f.max_size_bytes / (1024 * 1024)).toFixed(0)} МБ`;
  } catch {
    els.formatsHint.textContent = "PDF, DOCX, XLSX, MD, TXT…";
  }
}

async function uploadFiles() {
  if (!selectedFiles.length || !els.uploadBtn) return;
  els.uploadBtn.disabled = true;
  els.uploadBtn.textContent = "Загрузка…";
  showBox(els.uploadError, "");
  const fd = new FormData();
  const useBatch = selectedFiles.length > 1;
  if (useBatch) {
    selectedFiles.forEach((f) => fd.append("files", f));
  } else {
    fd.append("file", selectedFiles[0]);
  }
  fd.append("classification", els.classification?.value || "открытый");
  let ok = false;
  const uploadedIds = [];
  try {
    const url = useBatch ? `${API}/documents/batch` : `${API}/documents`;
    const r = await fetch(url, { method: "POST", body: fd });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Ошибка загрузки");
    ok = true;
    if (useBatch) {
      const items = (data.items || []).filter((x) => x.document);
      const bad = (data.items || []).filter((x) => x.error);
      if (bad.length) showBox(els.uploadError, bad.map((x) => `${x.file_name}: ${x.error}`).join("\n"));
      items.forEach((x) => {
        if (x.document?.id) {
          uploadedIds.push(x.document.id);
          pipelineQueue.add(x.document.id);
        }
      });
      if (items.length) {
        switchPage("docs");
        await openDoc(items[0].document.id, { keepPage: true, showGraph: true });
      }
    } else {
      uploadedIds.push(data.id);
      pipelineQueue.add(data.id);
      switchPage("docs");
      await openDoc(data.id, { keepPage: true, showGraph: true });
    }
    resetDropZone();
    await renderDocsList();
    for (const id of uploadedIds) {
      ensurePipeline(id).catch(() => {});
    }
  } catch (e) {
    showBox(els.uploadError, e.message);
    if (selectedFiles.length) els.uploadBtn.disabled = false;
  } finally {
    els.uploadBtn.textContent = "Загрузить и обработать";
    if (!ok && selectedFiles.length) els.uploadBtn.disabled = false;
    renderDocsList();
  }
}

async function ensurePipeline(docId) {
  if (!docId || !pipelineQueue.has(docId)) return;
  try {
    const r = await fetch(`${API}/documents/${encodeURIComponent(docId)}/preview`);
    if (!r.ok) return;
    const data = await r.json();
    const st = data.status;
    if (st === "uploaded" || st === "processing") return;
    if (st === "md_ready" && !(data.graph_nodes > 0)) {
      if (data.processing_mode === "answers_only") {
        if (!indexedDocsSet.has(docId)) {
          await fetch(`${API}/documents/${encodeURIComponent(docId)}/index`, { method: "POST" });
          indexedDocsSet.add(docId);
          saveIndexedDocs();
        }
        pipelineQueue.delete(docId);
        return;
      }
      await fetch(`${API}/documents/${encodeURIComponent(docId)}/submit`, { method: "POST" });
      return;
    }
    if (st === "loaded" || st === "md_ready" || st === "failed") {
      const needsL4 = data.processing_mode !== "answers_only" && (data.graph_nodes > 0);
      const l4Ready = !needsL4 || isL4Done(data) || data.step === "l4_failed";
      if (l4Ready) pipelineQueue.delete(docId);
    }
  } catch { /* retry on next poll */ }
}

async function retryPipelineStage(docId, action, btn) {
  if (!docId || !action) return;
  const prev = btn?.textContent;
  if (btn) { btn.disabled = true; if (prev) btn.textContent = "…"; }
  try {
    let url = "";
    if (action === "reprocess") url = `${API}/documents/${encodeURIComponent(docId)}/reprocess`;
    else if (action === "extract") url = `${API}/documents/${encodeURIComponent(docId)}/submit`;
    else if (action === "neo4j") url = `${API}/documents/${encodeURIComponent(docId)}/neo4j-sync`;
    else if (action === "index") url = `${API}/documents/${encodeURIComponent(docId)}/index`;
    else if (action === "l4_cluster") url = `${API}/documents/${encodeURIComponent(docId)}/l4-cluster`;
    else return;
    const r = await fetch(url, { method: "POST" });
    if (!r.ok) {
      const data = await r.json().catch(() => ({}));
      throw new Error(data.detail || "Ошибка перезапуска");
    }
    if (action === "index") {
      const data = await r.json();
      if ((data.indexed ?? 0) > 0 || !data.error) {
        indexedDocsSet.add(docId);
        saveIndexedDocs();
      }
    }
    if (action === "l4_cluster") {
      const data = await r.json();
      if (data.l4_clustered > 0 || data.step === "l4_done" || data.clusters != null) {
        indexedDocsSet.add(docId);
        saveIndexedDocs();
      }
    }
    pipelineQueue.add(docId);
    if (docId === selectedDoc) await openDoc(docId, { keepPage: true });
    else await renderDocsList();
    document.querySelectorAll(`[data-upload-doc="${CSS.escape(docId)}"]`).forEach(() => {
      pollUploadDocExternal?.(docId);
    });
  } catch (e) {
    if (btn) btn.title = e.message || "Ошибка";
  } finally {
    if (btn) { btn.disabled = false; if (prev) btn.textContent = prev; }
  }
}

let pollUploadDocExternal = null;

function bindRetryButtons(root = document) {
  root.querySelectorAll("[data-retry-action]").forEach((btn) => {
    if (btn.dataset.retryBound) return;
    btn.dataset.retryBound = "1";
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      retryPipelineStage(btn.dataset.retryDoc, btn.dataset.retryAction, btn);
    });
  });
}

function setPreview(el, text, isEmpty) {
  el.textContent = text;
  el.classList.toggle("empty", !!isEmpty);
}

function stepLabel(step) {
  if (!step) return "извлечение";
  const m = String(step).match(/^layer_L1_L4_(\d+)\/(\d+)$/);
  if (m) return `факты ${m[1]}/${m[2]}`;
  return STEP_RU[step] || step;
}

function formatBytes(n) {
  const v = Number(n);
  if (!Number.isFinite(v) || v <= 0) return "—";
  if (v < 1024) return `${v} Б`;
  if (v < 1024 * 1024) return `${(v / 1024).toFixed(1)} КБ`;
  return `${(v / (1024 * 1024)).toFixed(2)} МБ`;
}

function formatDateTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString("ru-RU");
}

function renderDocMetadata(data) {
  if (!els.docMetaGrid || !data || graphScope === "all") {
    els.docMetaGrid?.classList.add("hidden");
    return;
  }
  const rows = [
    ["Тип", data.doc_type || "—"],
    ["MIME", data.mime_type || "—"],
    ["Классификация", data.classification || "—"],
    ["Организация", data.organization || "—"],
    ["Язык", data.lang || "—"],
    ["Размер", formatBytes(data.size_bytes)],
    ["Загружен", formatDateTime(data.upload_date)],
    ["SHA-256", data.hash_sum ? `${data.hash_sum.slice(0, 12)}…` : "—"],
    ["Шаг", data.step ? (STEP_RU[data.step] || data.step) : "—"],
  ];
  els.docMetaGrid.innerHTML = rows.map(
    ([label, value]) => `<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`,
  ).join("");
  els.docMetaGrid.classList.remove("hidden");
}

function applyMarkdownFromPreview(data) {
  if (!data) return;
  if (data.markdown && data.markdown.trim()) {
    setMarkdownViews(data.markdown, data.markdown_marked || data.markdown, false);
    return;
  }
  const stepHint = data.step ? ` · ${STEP_RU[data.step] || data.step}` : "";
  if (data.status === "processing") {
    setMarkdownViews(`OCR → Markdown${stepHint}…`, "", true);
  } else if (data.status === "uploaded") {
    setMarkdownViews("В очереди на обработку…", "", true);
  } else if (data.status === "extracting") {
    setMarkdownViews(`Извлечение графа${stepHint}…`, "", true);
  } else if (data.status === "failed") {
    setMarkdownViews(data.error ? `Ошибка: ${data.error}` : "Ошибка обработки.", "", true);
  } else if (data.status === "md_ready" || data.status === "loaded") {
    setMarkdownViews("Markdown пуст или ещё не сохранён.", "", true);
  } else {
    setMarkdownViews("Ожидание worker…", "", true);
  }
}

async function reloadGraphForDoc(docId, { silent = false } = {}) {
  if (!docId) return;
  try {
    const gr = await fetch(`${API}/graph/documents/${encodeURIComponent(docId)}`);
    if (!gr.ok) return;
    const g = await gr.json();
    const rels = (g.relationships || []).map((rel) => ({
      type: rel.type,
      from: rel.from || rel.from_,
      to: rel.to,
      props: rel.props || {},
    }));
    const nodes = g.nodes || [];
    const newKey = graphContentKey(nodes, rels);
    if (newKey === lastGraphDataKey && docId === lastGraphDocId) return;
    graphData = { nodes, relationships: rels };
    lastGraphDataKey = newKey;
    lastGraphDocId = docId;
    updateCrossLayerStat();
    updatePreviewMeta(docId);
    if (graphVisible) renderGraphViews({ skipLayerFilters: silent });
  } catch {
    if (!silent) { /* ignore */ }
  }
}

async function applyPreviewUpdate(data, opts = {}) {
  if (!data) return;
  const docId = data.document_id || data.id || selectedDoc;
  const prevStatus = docStatusCache.get(docId);

  updateExtractControls(data.status, data.step);
  updateDocPageBar(data);
  renderDocMetadata(data);
  applyMarkdownFromPreview(data);

  docStatusCache.set(docId, data.status);
  maybeAutoDocWorkTab(data, prevStatus);

  const graphCount = data.graph_nodes || 0;
  const prevGraphCount = docGraphCountCache.get(docId) || 0;
  const hadGraph = graphData.nodes.length > 0;
  const graphCountChanged = graphCount !== prevGraphCount;
  docGraphCountCache.set(docId, graphCount);
  if (graphCount > 0 && (graphCountChanged || !hadGraph || opts.forceGraph)) {
    await reloadGraphForDoc(docId, { silent: true });
  } else if (graphCount === 0 && hadGraph && data.status === "extracting") {
    graphData = { nodes: [], relationships: [] };
    updateCrossLayerStat();
    updatePreviewMeta(docId);
  }

  if (docPanelMode === "logs" && ACTIVE_DOC_STATUSES.has(data.status)) {
    loadLogs(docId, { silent: true });
  }
  if (data.status === "extracting" && (currentPage === "doc" || currentPage === "graphAll" || isInlineGraphPage())) {
    refreshLiveExtract(docId);
  }

  const finishedExtract =
    prevStatus === "extracting"
    && (data.status === "loaded" || data.status === "md_ready")
    && graphCount > 0;
  if (finishedExtract) autoIndexAfterExtraction(docId);

  if (
    (prevStatus === "processing" || prevStatus === "uploaded")
    && data.status === "md_ready"
    && (currentPage === "doc" || isInlineGraphPage())
    && graphScope === "doc"
  ) {
    docPanelMode = "md";
    els.docMdPanel?.classList.remove("hidden");
    els.docMdBtn?.classList.add("active");
    if (isInlineGraphPage()) setDocWorkTab("md");
  }

  if (isInlineGraphPage()) {
    await updateDocWorkArea(data, data);
  }
}

function stripMdComments(text) {
  return String(text || "").replace(/<!--[\s\S]*?-->/g, "");
}

function renderMarkdownHtml(text) {
  const src = stripMdComments(text || "").slice(0, 120000);
  if (!src.trim()) return "";
  if (window.marked?.parse) {
    return window.marked.parse(src, { breaks: true, gfm: true });
  }
  return esc(src).replace(/\n/g, "<br>");
}

function setMdViewMode(mode) {
  mdViewMode = mode === "marked" ? "marked" : "clean";
  els.mdViewRenderBtn?.classList.toggle("active", mdViewMode === "clean");
  els.mdViewSourceBtn?.classList.toggle("active", mdViewMode === "marked");
  els.mdInlineCleanBtn?.classList.toggle("active", mdViewMode === "clean");
  els.mdInlineMarkedBtn?.classList.toggle("active", mdViewMode === "marked");
  els.previewMdRender?.classList.toggle("hidden", mdViewMode !== "clean");
  els.previewMdSource?.classList.toggle("hidden", mdViewMode !== "marked");
  els.docMdInlineClean?.classList.toggle("hidden", mdViewMode !== "clean");
  els.docMdInlineMarked?.classList.toggle("hidden", mdViewMode !== "marked");
}

function updateMarkdownPreview(isEmpty) {
  const renderEl = els.previewMdRender;
  const sourceEl = els.previewMdSource;
  const inlineClean = els.docMdInlineClean;
  const inlineMarked = els.docMdInlineMarked;

  const emptyText = markdownClean || "—";
  const cleanHtml = isEmpty || !markdownClean.trim()
    ? esc(emptyText)
    : renderMarkdownHtml(markdownClean);
  const markedText = isEmpty || !(markdownMarked || markdownClean).trim()
    ? emptyText
    : (markdownMarked || markdownClean).slice(0, 120000);

  if (renderEl) {
    renderEl.innerHTML = cleanHtml;
    renderEl.className = `preview md-panel doc-md-panel md-render-view${isEmpty || !markdownClean.trim() ? " empty" : ""}`;
  }
  if (sourceEl) {
    sourceEl.textContent = markedText;
    sourceEl.className = `preview md-panel doc-md-panel md-source-view hidden${isEmpty ? " empty" : ""}`;
  }
  if (inlineClean) {
    inlineClean.innerHTML = cleanHtml;
    inlineClean.className = `preview md-panel doc-md-inline md-clean-view${isEmpty || !markdownClean.trim() ? " empty" : ""}`;
  }
  if (inlineMarked) {
    inlineMarked.textContent = markedText;
    inlineMarked.className = `preview md-panel doc-md-inline md-marked-view hidden${isEmpty ? " empty" : ""}`;
  }
  setMdViewMode(mdViewMode);
}

function setMarkdownViews(clean, marked, isEmpty) {
  markdownClean = clean || "";
  markdownMarked = marked || clean || "";
  updateMarkdownPreview(isEmpty);
}

function downloadDocumentMd(variant) {
  if (!selectedDoc) return;
  const v = variant || (mdViewMode === "marked" ? "marked" : "clean");
  const url = `${API}/documents/${encodeURIComponent(selectedDoc)}/markdown?variant=${v}&download=1`;
  const a = document.createElement("a");
  a.href = url;
  a.rel = "noopener";
  a.click();
}

async function openDocWithMd(docId) {
  if (!docId) return;
  await openDoc(docId, { switchTo: "doc" });
  docPanelMode = "md";
  els.docMdPanel?.classList.remove("hidden");
  els.docLogsPanel?.classList.add("hidden");
  els.docMdBtn?.classList.add("active");
  els.docLogsBtn?.classList.remove("active");
  setDocWorkTab("md", { manual: true });
}

function layerOf(label) {
  return LABEL_LAYER[label] || "L?";
}

function nodeLayerMap() {
  const m = new Map();
  graphData.nodes.forEach((n) => m.set(n.id, layerOf(n.label)));
  return m;
}

function relEndpoints(rel) {
  return { from: rel.from || rel.from_, to: rel.to };
}

function isCrossLayerRel(rel, layerMap) {
  const { from, to } = relEndpoints(rel);
  if (CROSS_LAYER_REL_TYPES.has(rel.type)) return true;
  const lf = layerMap.get(from);
  const lt = layerMap.get(to);
  return !!(lf && lt && lf !== lt);
}

function countCrossLayerRels() {
  const layerMap = nodeLayerMap();
  return graphData.relationships.filter((r) => isCrossLayerRel(r, layerMap)).length;
}

function updateCrossLayerStat() {
  countCrossLayerRels();
}

function updatePreviewMeta(docId) {
  if (!els.docPageMeta) return;
  const nodes = graphData?.nodes?.length || 0;
  const rels = graphData?.relationships?.length || 0;
  const cross = countCrossLayerRels();
  const ready = indexedDocsSet.has(docId);
  els.docPageMeta.textContent = `${nodes} узл · ${rels} св · ${cross} межсл. · Qdrant: ${ready ? "да" : "нет"}`;
}

function updateSearchBadge(docId) {
  updatePreviewMeta(docId);
}

function formatEmbeddingStatus(data) {
  if (!data) return "Эмбеддинги: недоступны";
  const chunks = data.collections?.mkg_chunks?.points ?? 0;
  const claims = data.collections?.mkg_claims?.points ?? 0;
  const ok = data.yandex_configured ? "настроен" : "не настроен";
  return `Yandex (${ok}) → Qdrant · chunks ${chunks} · claims ${claims}`;
}

function formatQdrantInfo(data) {
  if (!data) return "";
  const lines = [
    `Qdrant: ${data.qdrant_url}`,
    `Размер вектора: ${data.vector_size}`,
    `Yandex: ${data.yandex_configured ? "ключ настроен" : "ключ не задан"}`,
  ];
  Object.entries(data.collections || {}).forEach(([name, c]) => {
    lines.push(`${name}: ${c.points} точек — ${c.purpose}`);
  });
  return lines.join("\n");
}

function saveIndexedDocs() {
  localStorage.setItem("mkg_indexed_docs", JSON.stringify([...indexedDocsSet]));
}

function countL3Nodes(nodes) {
  const counts = { TextParagraph: 0, HeadingContext: 0, LangContext: 0, TableMatrix: 0, SynonymMap: 0, other: 0 };
  (nodes || []).forEach((n) => {
    const label = n.label || "";
    if (label in counts) counts[label] += 1;
    else if (layerOf(label) === "L3") counts.other += 1;
  });
  return counts;
}

function renderL3Stats() {
  if (!els.l3Stats) return;
  if (!selectedDoc || !graphData?.nodes?.length) {
    els.l3Stats.innerHTML = '<p class="muted">Постройте граф документа — здесь появится статистика L3.</p>';
    return;
  }
  const c = countL3Nodes(graphData.nodes);
  const cross = countCrossLayerRels();
  const indexed = indexedDocsSet.has(selectedDoc);
  els.l3Stats.innerHTML = `
    <div class="l3-stat"><span class="l3-stat-val">${c.TextParagraph}</span><span class="l3-stat-label">TextParagraph</span></div>
    <div class="l3-stat"><span class="l3-stat-val">${c.HeadingContext}</span><span class="l3-stat-label">HeadingContext</span></div>
    <div class="l3-stat"><span class="l3-stat-val">${c.LangContext}</span><span class="l3-stat-label">LangContext</span></div>
    <div class="l3-stat"><span class="l3-stat-val">${cross}</span><span class="l3-stat-label">межсл. связей</span></div>
    <div class="l3-stat"><span class="l3-stat-val">${indexed ? "да" : "нет"}</span><span class="l3-stat-label">в Qdrant</span></div>`;
}

function populateGraphDocFilter(items) {
  const list = items || docsListCache;
  const docOpts = list.length
    ? list.map((d) => `<option value="${esc(d.id)}" ${d.id === selectedDoc ? "selected" : ""}>${esc(d.file_name || d.id)}</option>`).join("")
    : "";
  if (els.qdrantDocFilter) {
    els.qdrantDocFilter.innerHTML = docOpts || '<option value="">—</option>';
  }
}

async function refreshEmbeddingStatus() {
  try {
    const r = await fetch(`${AGENT_API}/embeddings/status`);
    if (!r.ok) return;
    embeddingStatusCache = await r.json();
    const line = formatEmbeddingStatus(embeddingStatusCache);
    if (els.l3EmbeddingStatus) els.l3EmbeddingStatus.textContent = line;
    if (els.l3QdrantInfo) els.l3QdrantInfo.textContent = formatQdrantInfo(embeddingStatusCache);
  } catch {
    const line = "Эмбеддинги: сервис недоступен";
    if (els.l3EmbeddingStatus) els.l3EmbeddingStatus.textContent = line;
    if (els.l3QdrantInfo) els.l3QdrantInfo.textContent = "";
  }
  renderL3Stats();
  if (currentPage === "qdrant" && selectedDoc) loadQdrantPoints(selectedDoc);
}

async function indexEmbeddings(docId = selectedDoc, opts = {}) {
  const { silent = false, btn = els.l3IndexBtn } = opts;
  if (!docId) return null;
  let prev = "";
  if (btn) {
    btn.disabled = true;
    prev = btn.textContent;
    btn.textContent = "Индексация…";
  }
  try {
    const r = await fetch(
      `${AGENT_API}/documents/${encodeURIComponent(docId)}/embeddings/index`,
      { method: "POST" },
    );
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Ошибка индексации");
    if ((data.indexed ?? 0) > 0 || !data.error) {
      indexedDocsSet.add(docId);
      saveIndexedDocs();
    }
    if (docId === selectedDoc) updateSearchBadge(docId);
    if (!silent) appendQdrantLog(`Индексация: +${data.indexed ?? 0}, пропущено ${data.skipped ?? 0}`);
    await refreshEmbeddingStatus();
    await loadQdrantPoints(docId);
    return data;
  } catch (e) {
    if (!silent) appendQdrantLog(`Ошибка: ${e.message}`, true);
    return null;
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = prev;
    }
  }
}

async function autoIndexAfterExtraction(docId) {
  if (!docId || indexedDocsSet.has(docId)) return;
  await indexEmbeddings(docId, { silent: true });
}

async function indexAllEmbeddings() {
  const btn = els.l3IndexAllBtn;
  if (!docsListCache.length) return;
  btn.disabled = true;
  const prev = btn.textContent;
  btn.textContent = "Индексация…";
  try {
    for (const d of docsListCache) {
      if ((d.graph_nodes || 0) === 0) continue;
      await indexEmbeddings(d.id, { silent: true, btn: null });
    }
    await refreshEmbeddingStatus();
    appendQdrantLog("Индексация всех документов завершена");
  } catch (e) {
    appendQdrantLog(e.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = prev;
  }
}

async function runSearch(query, targetEl = els.qdrantSearchResults) {
  if (!selectedDoc || !query?.trim() || !targetEl) return;
  targetEl.innerHTML = '<p class="muted">Поиск…</p>';
  try {
    const r = await fetch(
      `${AGENT_API}/documents/${encodeURIComponent(selectedDoc)}/search`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim(), limit: 15, mode: "auto", index_if_missing: true }),
      },
    );
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Ошибка поиска");
    if (data.index?.indexed > 0) {
      indexedDocsSet.add(selectedDoc);
      saveIndexedDocs();
      updateSearchBadge(selectedDoc);
      await refreshEmbeddingStatus();
    }
    if (els.qdrantSearchMeta) {
      els.qdrantSearchMeta.textContent = `Режим: ${data.mode} · ${data.hits?.length ?? 0} результатов`;
    }
    renderSearchHits(data.hits || [], targetEl, { showDoc: false });
  } catch (e) {
    targetEl.innerHTML = `<p class="muted">${esc(e.message)}</p>`;
  }
}

function renderSearchHits(hits, targetEl, opts = {}) {
  if (!targetEl) return;
  if (!hits.length) {
    targetEl.innerHTML = '<p class="muted">Ничего не найдено.</p>';
    return;
  }
  const docName = (docId) => {
    const d = docsListCache.find((x) => x.id === docId);
    return d?.file_name || docId;
  };
  targetEl.innerHTML = hits.map((hit) => `
    <article class="search-hit" data-node-id="${esc(hit.node_id)}" data-doc-id="${esc(hit.document_id || selectedDoc || "")}">
      <div class="search-hit-head">
        ${opts.showDoc && hit.document_id ? `<span class="search-hit-doc">${esc(docName(hit.document_id))}</span>` : ""}
        <span class="search-hit-layer" style="background:${LAYER_COLOR[hit.layer] || LAYER_COLOR["L?"]}">${esc(hit.layer)}</span>
        <span class="search-hit-label">${esc(hit.label)}</span>
        <span class="search-hit-score">${hit.score != null ? (hit.score <= 1 ? `${(hit.score * 100).toFixed(0)}%` : hit.score.toFixed(2)) : "—"}</span>
        <span class="search-hit-mode muted">${esc((hit.retrieval_factors || []).join("+") || hit.mode || "")}</span>
        ${hit.cluster_id != null ? `<span class="search-hit-cluster muted">c${esc(String(hit.cluster_id))}</span>` : ""}
        ${hit.is_anomaly ? '<span class="search-hit-anomaly muted">anomaly</span>' : ""}
      </div>
      <p class="search-hit-text">${esc(hit.text || "—")}</p>
      <code class="search-hit-id">${esc(hit.node_id)}</code>
    </article>`).join("");
  targetEl.querySelectorAll(".search-hit").forEach((el) => {
    el.addEventListener("click", async () => {
      const docId = el.dataset.docId;
      if (docId && docId !== selectedDoc) {
        await openDoc(docId, { switchTo: "doc" });
      }
      const node = graphData.nodes.find((n) => n.id === el.dataset.nodeId);
      if (node) openDetailPanel(node);
      else {
        els.detailBody.innerHTML = `<p class="muted">Узел ${esc(el.dataset.nodeId)} — откройте граф документа.</p>`;
        els.detailPanel.classList.remove("hidden");
        els.appRoot.classList.add("has-detail");
      }
    });
  });
}

function appendQdrantLog(msg, isErr = false) {
  if (!els.qdrantIndexLog) return;
  const ts = new Date().toLocaleTimeString("ru-RU");
  const line = `[${ts}] ${msg}`;
  lastQdrantIndexLog = `${line}\n${lastQdrantIndexLog}`.slice(0, 4000);
  els.qdrantIndexLog.innerHTML = lastQdrantIndexLog.split("\n").filter(Boolean)
    .map((l) => `<div class="qdrant-log-line${isErr ? " err" : ""}">${esc(l)}</div>`).join("");
}

async function loadQdrantPoints(docId = selectedDoc) {
  if (!docId || !els.qdrantPointsList) return;
  try {
    const r = await fetch(`${AGENT_API}/documents/${encodeURIComponent(docId)}/embeddings/points?limit=200`);
    if (!r.ok) {
      els.qdrantPointsList.innerHTML = '<p class="muted">Точки недоступны (индексируйте документ).</p>';
      if (els.qdrantPointsCount) els.qdrantPointsCount.textContent = "(0)";
      return;
    }
    const data = await r.json();
    if (els.qdrantPointsCount) els.qdrantPointsCount.textContent = `(${data.total})`;
    if (!data.points?.length) {
      els.qdrantPointsList.innerHTML = '<p class="muted">Нет точек в Qdrant для этого документа.</p>';
      return;
    }
    els.qdrantPointsList.innerHTML = data.points.map((p) => `
      <div class="qdrant-point-row">
        <span class="qp-layer" style="background:${LAYER_COLOR[p.layer] || LAYER_COLOR["L?"]}">${esc(p.layer || "?")}</span>
        <span class="qp-label">${esc(p.label || "?")}</span>
        <code class="qp-id">${esc(p.node_id || p.point_id)}</code>
        <span class="qp-coll muted">${esc(p.collection)}</span>
        <p class="qp-text">${esc(p.text || "")}</p>
      </div>`).join("");
  } catch {
    els.qdrantPointsList.innerHTML = '<p class="muted">Ошибка загрузки точек Qdrant.</p>';
  }
}

async function loadProjectStage() {
  let stage = "MVP";
  let label = "ingestion, extraction, Neo4j, Qdrant";
  try {
    const r = await fetch(`${AGENT_API}/capabilities`);
    if (r.ok) {
      const data = await r.json();
      stage = data.project_stage || stage;
      label = data.stage_label_ru || label;
    }
  } catch { /* ignore */ }
  if (els.projectStageLine) {
    els.projectStageLine.textContent = `Этап: ${label} (${stage}) — карта знаний R&D`;
  }
}

function renderLivePipeline(layers) {
  if (!els.livePipeline) return;
  if (!layers?.length) {
    els.livePipeline.innerHTML = "";
    return;
  }
  els.livePipeline.innerHTML = layers.map((l) =>
    `<span class="lp-mini-badge l-${l.id} st-${l.status}" title="${esc(l.title)} — ${LAYER_STATUS_RU[l.status] || l.status} · ${l.nodes} узл · ${l.relationships} св">${esc(l.id)}</span>`,
  ).join("");
}

function renderLiveRels(rels) {
  if (!rels?.length) {
    els.liveRels.innerHTML = '<span class="muted">Связи появятся по мере извлечения…</span>';
    return;
  }
  const grouped = {};
  rels.forEach((rel) => {
    const layer = rel.layer || "L?";
    if (!grouped[layer]) grouped[layer] = [];
    grouped[layer].push(rel);
  });
  const order = ["L1", "L2", "L3", "L4", "L5", "L6", "L?"];
  els.liveRels.innerHTML = order
    .filter((l) => grouped[l]?.length)
    .map((layer) => {
      const chips = grouped[layer].map((rel) =>
        `<span class="rel-chip rel-chip-${layer}" title="${esc(rel.type)}"><span class="rel-from">${esc(rel.from_short)}</span><b>${esc(rel.type)}</b><span class="rel-to">${esc(rel.to_short)}</span></span>`,
      ).join("");
      return `<div class="live-rel-group"><span class="lp-mini-badge l-${layer}">${layer}</span>${chips}</div>`;
    }).join("");
}

async function refreshLiveExtract(docId) {
  if (!els.liveExtract || !docId) return;
  try {
    const r = await fetch(`${API}/documents/${encodeURIComponent(docId)}/pipeline/layers`);
    if (!r.ok) return;
    const data = await r.json();
    const step = stepLabel(data.step);
    els.liveStep.textContent = `${data.total_nodes || 0} узл · ${data.total_relationships || 0} св · ${step}`;
    renderLivePipeline(data.layers || []);
    renderLiveRels(data.recent_relationships || []);
  } catch { /* ignore */ }
}

function setLiveExtractVisible(show) {
  const visible = show && (currentPage === "doc" || currentPage === "graphAll");
  if (els.liveExtract) els.liveExtract.classList.toggle("hidden", !visible);
}

function isGraphHostPage(page = currentPage) {
  return page === "docs" || page === "doc" || page === "graphAll";
}

function isInlineGraphPage(page = currentPage) {
  return page === "docs";
}

function docsWithGraph(items) {
  return (items || docsListCache).filter((d) => (d.graph_nodes || 0) > 0);
}

function pickGraphDocId() {
  if (selectedDoc && docsListCache.some((d) => d.id === selectedDoc && (d.graph_nodes || 0) > 0)) {
    return selectedDoc;
  }
  const withGraph = docsWithGraph();
  return withGraph[0]?.id || selectedDoc || null;
}

function updateGraphScopeUI() {
  const isAll = graphScope === "all";
  els.pageGraphShell?.classList.toggle("graph-scope-all", isAll);
  if (isAll) {
    docPanelMode = null;
    els.docMdPanel?.classList.add("hidden");
    els.docLogsPanel?.classList.add("hidden");
    els.docMetaGrid?.classList.add("hidden");
    els.docMdBtn?.classList.remove("active");
    els.docLogsBtn?.classList.remove("active");
    setLiveExtractVisible(false);
  }
}

function updateGraphVisibility() {
  const isDocPage = currentPage === "doc" || currentPage === "graphAll";
  const isInlineGraph = isInlineGraphPage();
  const isDocDetail = graphScope === "doc" && !graphVisible && isDocPage;
  const showGraphArea = isInlineGraph || (isDocPage && (graphScope === "all" || graphVisible));

  els.graphPanel?.classList.toggle("hidden", !showGraphArea);
  els.pageGraphShell?.classList.toggle("doc-detail-only", isDocPage && isDocDetail);
  els.graphPageHead?.classList.toggle("hidden", !showGraphArea || (isDocPage && isDocDetail) || (isInlineGraph && graphScope === "doc"));
  els.docWorkHeader?.classList.toggle("hidden", !isInlineGraph || graphScope !== "doc" || !selectedDoc);

  if (isInlineGraph && graphScope === "doc") {
    syncDocWorkTabUI(docWorkTab);
  } else if (isInlineGraph && graphScope === "all") {
    syncDocWorkTabUI("graph");
  }

  if (!isGraphHostPage()) return;

  const withGraph = docsWithGraph();
  const hasGraph = graphScope === "all"
    ? withGraph.length > 0
    : withGraph.some((d) => d.id === selectedDoc);

  els.graphsEmpty?.classList.toggle("hidden", !showGraphArea || hasGraph);
  els.graphsWorkspace?.classList.toggle("hidden", !showGraphArea || !hasGraph);

  const emptyMsg = els.graphsEmpty?.querySelector("p");
  if (emptyMsg) {
    emptyMsg.textContent = graphScope === "all"
      ? "Нет документов с графом. Загрузите файл на вкладке «Документы» — пайплайн запустится автоматически."
      : "Граф строится… или загрузите документ и дождитесь обработки.";
  }
}

function updateGraphsPageState() {
  updateGraphVisibility();
  if (graphScope === "doc" && !graphVisible && !isInlineGraphPage()) return;

  const withGraph = docsWithGraph();
  const hasGraph = graphScope === "all"
    ? withGraph.length > 0
    : withGraph.some((d) => d.id === selectedDoc);

  if (isGraphHostPage() && (hasGraph || graphScope === "all" || isInlineGraphPage())) {
    const docId = graphScope === "all" ? GRAPH_ALL_ID : (graphViewDocId || selectedDoc || pickGraphDocId());
    if (docId) {
      graphViewDocId = docId;
      loadGraph(docId);
    }
  }
}

function renderDocCard(d) {
  const st = statusLabel(d);
  const typeHint = d.doc_type ? ` · ${d.doc_type}` : "";
  const isLive = ["uploaded", "processing", "extracting"].includes(d.status);
  return `
    <div class="doc ${selectedDoc === d.id ? "active" : ""} ${isLive ? "doc-live" : ""}" data-id="${esc(d.id)}" role="button">
      <div class="doc-name">${esc(d.file_name)}</div>
      <div class="doc-meta">${formatBytes(d.size_bytes)}${esc(typeHint)} · ${formatDateTime(d.upload_date)}</div>
      ${renderDocPipelineHtml(d)}
      <span class="badge ${st.cls}">${esc(st.text)}</span>
    </div>`;
}

function bindDocCards(container) {
  bindRetryButtons(container);
  container?.querySelectorAll(".doc").forEach((el) => {
    el.addEventListener("click", () => {
      const id = el.dataset.id;
      docWorkTabManual = false;
      docWorkTab = "journey";
      if (currentPage === "docs") {
        openDoc(id, { keepPage: true, showGraph: true });
        graphScope = "doc";
        updateGraphsPageState();
        refreshGraphViewport();
        renderDocsList();
        return;
      }
      openDoc(id, { switchTo: "doc" });
    });
  });
}

async function loadQdrantClusterMap() {
  if (!els.qdrantClusterMap) return;
  try {
    const r = await fetch(`${AGENT_API}/embeddings/points/all?limit=500`);
    if (!r.ok) {
      els.qdrantClusterMap.innerHTML = '<p class="muted">Точки недоступны</p>';
      return;
    }
    const data = await r.json();
    const points = data.points || [];
    if (els.qdrantClusterCount) els.qdrantClusterCount.textContent = `(${points.length})`;
    if (!points.length) {
      els.qdrantClusterMap.innerHTML = '<p class="muted">Нет точек — проиндексируйте документы</p>';
      return;
    }
    const l4Points = points.filter((p) => p.layer === "L4");
    const byCluster = {};
    l4Points.forEach((p) => {
      const cid = p.cluster_id != null ? p.cluster_id : (p.is_anomaly ? -1 : "none");
      const key = String(cid);
      if (!byCluster[key]) byCluster[key] = [];
      byCluster[key].push(p);
    });
    const clusterKeys = Object.keys(byCluster).sort((a, b) => {
      if (a === "none") return 1;
      if (b === "none") return -1;
      return Number(a) - Number(b);
    });
    if (!clusterKeys.length || (clusterKeys.length === 1 && clusterKeys[0] === "none")) {
      const byLayer = {};
      points.forEach((p) => {
        const layer = p.layer || "L?";
        if (!byLayer[layer]) byLayer[layer] = [];
        byLayer[layer].push(p);
      });
      els.qdrantClusterMap.innerHTML = Object.entries(byLayer).map(([layer, pts]) => `
        <div class="qdrant-cluster-group">
          <div class="qdrant-cluster-head">
            <span class="qp-layer" style="background:${LAYER_COLOR[layer] || LAYER_COLOR["L?"]}">${esc(layer)}</span>
            <span class="muted">${pts.length} точек · запустите HDBSCAN</span>
          </div>
          <div class="qdrant-cluster-dots">
            ${pts.map((p) => `<span class="qdrant-dot" title="${esc(p.text || p.node_id || "")}" style="background:${LAYER_COLOR[layer] || LAYER_COLOR["L?"]}"></span>`).join("")}
          </div>
        </div>`).join("");
      return;
    }
    els.qdrantClusterMap.innerHTML = clusterKeys.map((key) => {
      const pts = byCluster[key];
      const isAnomaly = key === "-1";
      const label = key === "none" ? "без кластера" : (isAnomaly ? `аномалии (${pts.length})` : `кластер ${key}`);
      const color = isAnomaly ? "#c62828" : (LAYER_COLOR.L4 || "#ef6c00");
      return `
      <div class="qdrant-cluster-group">
        <div class="qdrant-cluster-head">
          <span class="qp-layer" style="background:${color}">${esc(label)}</span>
          <span class="muted">${pts.length} L4-точек</span>
        </div>
        <div class="qdrant-cluster-dots">
          ${pts.map((p) => `<span class="qdrant-dot ${p.is_anomaly ? "qdrant-dot-anomaly" : ""}" title="${esc(p.text || p.neo4j_node_id || p.node_id || "")}" style="background:${color}"></span>`).join("")}
        </div>
      </div>`;
    }).join("");
  } catch {
    els.qdrantClusterMap.innerHTML = '<p class="muted">Ошибка загрузки карты точек</p>';
  }
}

async function runL4Clustering() {
  const docParam = selectedDoc ? `?document_id=${encodeURIComponent(selectedDoc)}` : "";
  if (els.qdrantIndexLog) {
    els.qdrantIndexLog.textContent = "HDBSCAN L4…";
  }
  try {
    const r = await fetch(`${AGENT_API}/analytics/l4-cluster${docParam}`, { method: "POST" });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Ошибка кластеризации");
    if (els.qdrantIndexLog) {
      els.qdrantIndexLog.textContent = `L4: ${data.clustered || 0} точек, ${data.clusters || 0} кластеров, ${data.anomalies || 0} аномалий`;
    }
    await loadQdrantClusterMap();
    if (selectedDoc && graphVisible) await loadGraph(selectedDoc, { silent: true });
  } catch (e) {
    if (els.qdrantIndexLog) els.qdrantIndexLog.textContent = `Ошибка: ${e.message}`;
  }
}

function viewAllGraph() {
  graphScope = "all";
  graphDensityMode = "full";
  graphVisible = true;
  graphViewDocId = GRAPH_ALL_ID;
  docWorkTabManual = true;
  if (!isGraphHostPage()) {
    switchPage("docs");
    return;
  }
  updateGraphScopeUI();
  updateDensityToggleUI();
  setDocWorkTab("graph");
  updateGraphsPageState();
  refreshGraphViewport();
}

function openNeo4jBrowser() {
  window.open(NEO4J_BROWSER_URL, "_blank", "noopener,noreferrer");
}

function resetGraphFilters() {
  graphLayerFilter = "all";
  showCrossLayerOnly = false;
  graphDensityMode = "full";
  if (els.crossLayerToggle) els.crossLayerToggle.classList.remove("active");
  updateDensityToggleUI();
  graphViewMode = "map";
  if (els.viewMapBtn) els.viewMapBtn.classList.add("active");
  if (els.viewRelsBtn) els.viewRelsBtn.classList.remove("active");
  if (els.graphMapView) els.graphMapView.classList.remove("hidden");
  if (els.graphCanvasWrap) els.graphCanvasWrap.classList.remove("hidden");
  if (els.graphRelsView) els.graphRelsView.classList.add("hidden");
  resetGraphNetwork();
  renderGraphViews();
}

function updateDensityToggleUI() {
  els.graphCanvas?.classList.toggle("graph-compact", graphDensityMode === "compact");
  els.graphCompactBtn?.classList.toggle("active", graphDensityMode === "compact");
  els.graphFullBtn?.classList.toggle("active", graphDensityMode === "full");
  if (els.graphPageTitle) {
    if (graphScope === "all") {
      els.graphPageTitle.textContent = "Полный граф всех документов";
    } else {
      els.graphPageTitle.textContent = graphDensityMode === "compact" ? "Граф документа (компактный)" : "Граф документа (полный)";
    }
  }
  if (els.graphPageLead) {
    if (graphScope === "all") {
      els.graphPageLead.textContent = "Объединённая карта всех документов с графом. Узлы перетаскиваются.";
    } else {
      els.graphPageLead.textContent = graphDensityMode === "compact"
        ? "Сущности и межслойные связи. Узлы перетаскиваются."
        : "Все узлы L3, включая абзацы. Узлы перетаскиваются.";
    }
  }
}

function setGraphDensityMode(mode) {
  if (graphDensityMode === mode) return;
  graphDensityMode = mode;
  updateDensityToggleUI();
  resetGraphNetwork();
  renderGraphViews();
}

function setGraphViewMode(mode) {
  graphViewMode = mode;
  const isMap = mode === "map";
  els.viewMapBtn?.classList.toggle("active", isMap);
  els.viewRelsBtn?.classList.toggle("active", !isMap);
  els.graphCanvasWrap?.classList.toggle("hidden", !isMap);
  els.graphMapView?.classList.toggle("hidden", !isMap);
  els.graphRelsView?.classList.toggle("hidden", isMap);
  if (!isMap) renderAllRelationshipsList();
  if (isMap) refreshGraphViewport();
}

function updateExtractControls(status, step) {
  const extracting = status === "extracting";
  const cancelling = extracting && step === "cancelling";
  if (els.docPrimaryBtn) els.docPrimaryBtn.disabled = extracting;
  if (els.docStopBtn) {
    els.docStopBtn.classList.toggle("hidden", !extracting || cancelling);
    els.docStopBtn.disabled = cancelling;
    els.docStopBtn.textContent = cancelling ? "Останавливаем…" : "Стоп";
  }
  setLiveExtractVisible(extracting && !cancelling);
  if (extracting && selectedDoc) refreshLiveExtract(selectedDoc);
  if (selectedDoc) {
    const cached = docsListCache.find((d) => d.id === selectedDoc);
    if (cached) {
      updateDocPrimaryBtn(cached);
      updateDocRebuildBtn(cached);
    }
  }
}

function toggleDocPanel(mode) {
  docPanelMode = docPanelMode === mode ? null : mode;
  els.docMdPanel?.classList.toggle("hidden", docPanelMode !== "md");
  els.docLogsPanel?.classList.toggle("hidden", docPanelMode !== "logs");
  els.docMdBtn?.classList.toggle("active", docPanelMode === "md");
  els.docLogsBtn?.classList.toggle("active", docPanelMode === "logs");
  if (docPanelMode === "logs" && selectedDoc) loadLogs(selectedDoc, { force: true });
}

function updateDocRebuildBtn(data) {
  if (!els.docRebuildGraphBtn || !data) return;
  const busy = data.status === "extracting" || data.status === "processing";
  const hasGraph = (data.graph_nodes || 0) > 0;
  const canRebuild = graphScope !== "all" && (
    data.status === "failed"
    || data.status === "loaded"
    || (hasGraph && ["md_ready", "loaded"].includes(data.status))
  );
  els.docRebuildGraphBtn.classList.toggle("hidden", !canRebuild);
  els.docRebuildGraphBtn.disabled = busy;
  els.docRebuildGraphBtn.textContent = hasGraph ? "↺ Перестроить связи" : "↺ Построить связи";
}

function updateDocPrimaryBtn(data) {
  if (!els.docPrimaryBtn || !data) return;
  const hasGraph = (data.graph_nodes || 0) > 0;
  const extracting = data.status === "extracting";
  if (graphScope === "all") {
    els.docPrimaryBtn.textContent = "Обновить карту";
    els.docPrimaryBtn.dataset.action = "refresh";
    els.docPrimaryBtn.disabled = false;
    return;
  }
  if (hasGraph) {
    els.docPrimaryBtn.textContent = "Посмотреть граф";
    els.docPrimaryBtn.dataset.action = "view";
    els.docPrimaryBtn.disabled = false;
  } else {
    els.docPrimaryBtn.textContent = extracting ? "Извлечение…" : "Построить граф";
    els.docPrimaryBtn.dataset.action = "build";
    els.docPrimaryBtn.disabled = extracting;
  }
}

function updateDocPageBar(data) {
  if (!data) return;
  const label = statusLabel(data);
  if (graphScope === "all") {
    if (els.docPageTitle) els.docPageTitle.textContent = "Все документы — полный граф";
    if (els.docPageBadge) {
      els.docPageBadge.textContent = `${graphData.nodes?.length || 0} узл.`;
      els.docPageBadge.className = "badge s-loaded";
    }
    if (els.docPageMeta) {
      els.docPageMeta.textContent = `${graphData.relationships?.length || 0} связей · объединённый граф`;
    }
    updateDocPrimaryBtn(data);
    return;
  }
  if (els.docPageTitle) {
    els.docPageTitle.textContent = data.file_name || data.document_id || data.id;
  }
  if (els.docPageBadge) {
    els.docPageBadge.textContent = label.text;
    els.docPageBadge.className = `badge ${label.cls}`;
  }
  updatePreviewMeta(data.document_id || data.id);
  updateDocPrimaryBtn(data);
  updateDocRebuildBtn(data);
  if (currentPage === "docs") {
    const cached = docsListCache.find((x) => x.id === (data.document_id || data.id));
    updateDocWorkArea(cached || data);
  }
}

function statusLabel(doc) {
  const nodes = doc.graph_nodes || 0;
  const synced = doc.neo4j_synced === true;
  const stepRu = doc.step ? (STEP_RU[doc.step] || doc.step) : "";
  const stepSuffix = stepRu ? ` · ${stepRu}` : "";
  if (doc.status === "extracting" && doc.step === "cancelling") {
    return { text: "остановка…", cls: "s-processing s-live" };
  }
  switch (doc.status) {
    case "uploaded": return { text: `в очереди${stepSuffix}`, cls: "s-uploaded s-live" };
    case "processing": return { text: `OCR и очистка${stepSuffix}`, cls: "s-processing s-live" };
    case "extracting": return { text: `извлечение${stepSuffix}`, cls: "s-extracting s-live" };
    case "failed": return { text: "ошибка", cls: "s-failed" };
    case "loaded":
      if (nodes > 0 && synced) return { text: `в Neo4j · ${nodes} узл.`, cls: "s-loaded" };
      if (nodes > 0) return { text: `граф локально · ${nodes} узл.`, cls: "s-md_ready" };
      return { text: "граф пуст", cls: "s-failed" };
    case "md_ready":
      if (nodes > 0) return { text: `MD + граф · ${nodes} узл.`, cls: "s-md_ready" };
      return { text: "MD готов", cls: "s-md_ready" };
    default: return { text: doc.status, cls: "s-uploaded" };
  }
}

function shortNodeLabel(node) {
  const props = node.props || {};
  const name = props.name_ru || props.name_en || props.name || props.title || props.quote;
  if (typeof name === "string" && name.length) {
    return name.length > 28 ? `${name.slice(0, 28)}…` : name;
  }
  const id = String(node.id || "");
  const tail = id.includes(":") ? id.split(":").pop() : id;
  return tail.length > 24 ? `${tail.slice(0, 24)}…` : tail;
}

function shortGraphLabel(node) {
  const type = node.label || "?";
  const id = String(node.id || "");
  const tail = id.includes(":") ? id.split(":").pop() : id;
  const shortId = tail.length > 8 ? `${tail.slice(0, 8)}…` : tail;
  const text = `${type} ${shortId}`;
  return text.length > GRAPH_LABEL_MAX ? `${text.slice(0, GRAPH_LABEL_MAX - 1)}…` : text;
}

function relKey(rel) {
  const { from, to } = relEndpoints(rel);
  return `${from}|${rel.type}|${to}`;
}

function dedupeRels(rels) {
  const seen = new Set();
  return rels.filter((r) => {
    const k = relKey(r);
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
}

function edgePriority(rel, layerMap) {
  const cross = isCrossLayerRel(rel, layerMap);
  if (cross) return 0;
  const { from, to } = relEndpoints(rel);
  const lf = layerMap.get(from);
  const lt = layerMap.get(to);
  if (lf && lt && lf !== "L3" && lt !== "L3") return 1;
  if (lf !== "L3" || lt !== "L3") return 2;
  return 3;
}

function limitEdges(rels, layerMap, max) {
  if (rels.length <= max) return rels;
  const sorted = [...rels].sort((a, b) => edgePriority(a, layerMap) - edgePriority(b, layerMap));
  return sorted.slice(0, max);
}

function applyCompactGraphFilter(nodes, rels) {
  const layerMap = new Map();
  nodes.forEach((n) => layerMap.set(n.id, layerOf(n.label)));

  rels = rels.filter((r) => !L3_INTERNAL_REL_TYPES.has(r.type));

  const paragraphs = nodes.filter((n) => n.label === "TextParagraph");
  const nonParagraphL3 = nodes.filter((n) => layerOf(n.label) === "L3" && n.label !== "TextParagraph");
  const entityNodes = nodes.filter((n) => layerOf(n.label) !== "L3");
  const paraIds = new Set(paragraphs.map((p) => p.id));

  if (paragraphs.length > MAX_COMPACT_PARAGRAPHS) {
    const superNode = {
      id: COMPACT_DOC_TEXT_ID,
      label: "DocumentText",
      props: { name_ru: `Текст документа (${paragraphs.length} абз.)` },
      _collapsed: true,
      _collapsedCount: paragraphs.length,
    };
    rels = rels.map((r) => {
      const from = r.from || r.from_;
      const to = r.to;
      return {
        ...r,
        from: paraIds.has(from) ? COMPACT_DOC_TEXT_ID : from,
        from_: paraIds.has(from) ? COMPACT_DOC_TEXT_ID : from,
        to: paraIds.has(to) ? COMPACT_DOC_TEXT_ID : to,
      };
    });
    rels = dedupeRels(rels);
    nodes = [...entityNodes, ...nonParagraphL3, superNode];
  } else if (paragraphs.length > 0) {
    const scored = paragraphs.map((p) => {
      const score = rels.filter((r) => {
        const { from, to } = relEndpoints(r);
        return (from === p.id || to === p.id) && isCrossLayerRel(r, layerMap);
      }).length;
      return { node: p, score };
    });
    scored.sort((a, b) => b.score - a.score);
    const keepIds = new Set(scored.slice(0, MAX_COMPACT_PARAGRAPHS).map((s) => s.node.id));
    nodes = [...entityNodes, ...nonParagraphL3, ...paragraphs.filter((p) => keepIds.has(p.id))];
    rels = rels.filter((r) => {
      const { from, to } = relEndpoints(r);
      return (!paraIds.has(from) || keepIds.has(from)) && (!paraIds.has(to) || keepIds.has(to));
    });
  } else {
    nodes = [...entityNodes, ...nonParagraphL3];
  }

  nodes.forEach((n) => layerMap.set(n.id, layerOf(n.label)));
  rels = limitSuperNodeFan(rels, layerMap);
  rels = limitEdges(rels, layerMap, MAX_COMPACT_EDGES);
  return { nodes, rels };
}

function limitSuperNodeFan(rels, layerMap, max = 18) {
  const fromSuper = rels.filter((r) => (r.from || r.from_) === COMPACT_DOC_TEXT_ID);
  if (fromSuper.length <= max) return rels;
  const rest = rels.filter((r) => (r.from || r.from_) !== COMPACT_DOC_TEXT_ID);
  return [...rest, ...limitEdges(fromSuper, layerMap, max)];
}

function filteredGraph() {
  const layerMap = nodeLayerMap();
  let nodes = [...graphData.nodes];
  let rels = [...graphData.relationships];

  if (showCrossLayerOnly) {
    rels = rels.filter((r) => isCrossLayerRel(r, layerMap));
    const ids = new Set();
    rels.forEach((r) => {
      const { from, to } = relEndpoints(r);
      ids.add(from);
      ids.add(to);
    });
    nodes = nodes.filter((n) => ids.has(n.id));
    return { nodes, rels };
  }

  if (graphLayerFilter !== "all") {
    const primary = nodes.filter((n) => layerOf(n.label) === graphLayerFilter);
    const keepIds = new Set(primary.map((n) => n.id));
    rels.forEach((r) => {
      const { from, to } = relEndpoints(r);
      if (keepIds.has(from) || keepIds.has(to)) {
        keepIds.add(from);
        keepIds.add(to);
      }
    });
    nodes = nodes.filter((n) => keepIds.has(n.id));
    rels = rels.filter((r) => {
      const { from, to } = relEndpoints(r);
      return keepIds.has(from) && keepIds.has(to);
    });
  }

  if (graphDensityMode === "compact") {
    return applyCompactGraphFilter(nodes, rels);
  }

  return { nodes, rels };
}

function switchPage(page) {
  if (!page) return;
  if (page === "graphs" || page === "fullgraph") page = "doc";
  if (page === "search" || page === "home") page = "docs";
  currentPage = page;
  const isGraphView = page === "doc" || page === "graphAll";
  const isDocsArea = page === "docs" || isGraphView;
  const isInlineGraph = isInlineGraphPage(page);
  els.pageDocs?.classList.toggle("hidden", page !== "docs");
  els.pageGraphShell?.classList.toggle("hidden", !isGraphView);
  els.pageQdrant?.classList.toggle("hidden", page !== "qdrant");
  els.pageChats?.classList.toggle("hidden", page !== "chats");
  els.pageSettings?.classList.toggle("hidden", page !== "settings");
  els.pageDocs?.classList.toggle("page-docs-graph", page === "docs");
  els.mainArea?.classList.toggle("layout-docs-graph", page === "docs");
  document.querySelectorAll(".page-nav-link").forEach((link) => {
    const p = link.dataset.page;
    link.classList.toggle("active", p === page || (p === "docs" && isDocsArea));
  });

  if (page === "docs") {
    graphVisible = true;
    if (graphScope !== "all") {
      graphScope = selectedDoc && docsWithGraph().some((d) => d.id === selectedDoc) ? "doc" : "all";
      graphViewDocId = graphScope === "all" ? GRAPH_ALL_ID : (selectedDoc || pickGraphDocId());
    }
  } else if (page !== "doc" && page !== "graphAll") {
    if (graphScope === "all") graphScope = "doc";
  }

  if (isGraphView) {
    graphScope = page === "graphAll" ? "all" : graphScope;
    if (graphScope === "all") {
      graphDensityMode = "full";
      graphViewDocId = GRAPH_ALL_ID;
      graphVisible = true;
    }
    updateGraphScopeUI();
    updateDensityToggleUI();
    if (graphScope === "doc" && selectedDoc) {
      graphViewDocId = selectedDoc;
    }
    updateGraphsPageState();
    if (graphVisible || graphScope === "all") refreshGraphViewport();
    if (graphScope === "all") {
      updateDocPageBar({ file_name: "Все документы", id: GRAPH_ALL_ID, graph_nodes: graphData.nodes.length });
    } else if (selectedDoc) {
      const cached = docsListCache.find((d) => d.id === selectedDoc);
      if (cached) updateDocPageBar(cached);
    }
  } else if (isInlineGraph) {
    updateGraphScopeUI();
    updateDensityToggleUI();
    updateGraphsPageState();
    refreshGraphViewport();
  } else {
    updateGraphScopeUI();
    updateGraphVisibility();
  }
  if (page === "docs") loadDocuments();
  else {
    updateDocWorkArea(null);
    if (page !== "docs") els.docWorkHeader?.classList.add("hidden");
  }
  if (page === "qdrant") {
    if (els.qdrantDocFilter && selectedDoc) els.qdrantDocFilter.value = selectedDoc;
    refreshEmbeddingStatus();
    renderL3Stats();
    loadQdrantClusterMap();
    if (selectedDoc) loadQdrantPoints(selectedDoc);
  }
  if (page === "chats") window.MKGAuth?.refreshChatsPage();
}

window.MKG = {
  get selectedDoc() { return selectedDoc; },
  get currentPage() { return currentPage; },
  switchPage,
  openDocWithMd,
  downloadDocumentMd,
  renderDocPipelineHtml,
  getDocPipelineStates,
  formatLogEntry,
  ensurePipeline,
  indexEmbeddings,
  isDocIndexed: (docId) => indexedDocsSet.has(docId),
  markDocIndexed: (docId) => { indexedDocsSet.add(docId); saveIndexedDocs(); },
  trackPipelineDoc(docId) { if (docId) pipelineQueue.add(docId); },
  retryPipelineStage,
  bindRetryButtons,
  setPollUploadHook(fn) { pollUploadDocExternal = fn; },
};

function closeDetailPanel() {
  els.detailPanel.classList.add("hidden");
  els.appRoot.classList.remove("has-detail");
}

function openDetailPanel(node) {
  if (!node) return;
  if (node._collapsed) {
    els.detailBody.innerHTML = `
      <span class="detail-layer" style="background:${LAYER_COLOR.L3}">L3 · Текст документа</span>
      <div class="detail-id">${esc(node.id)}</div>
      <p class="muted">Свернуто <b>${node._collapsedCount || "?"}</b> абзацев TextParagraph. Переключите «Полный» в панели графа.</p>`;
    els.detailPanel.classList.remove("hidden");
    els.appRoot.classList.add("has-detail");
    return;
  }
  const layer = layerOf(node.label);
  const props = node.props || {};
  const incoming = graphData.relationships.filter((r) => r.to === node.id);
  const outgoing = graphData.relationships.filter((r) => (r.from || r.from_) === node.id);
  const propsHtml = renderNodePropsSection(node.label, props);
  const clusterBadge = props.cluster_id != null
    ? `<span class="detail-badge">кластер ${esc(String(props.cluster_id))}</span>`
    : "";
  const anomalyBadge = props.is_anomaly
    ? `<span class="detail-badge detail-badge-warn">аномалия</span>`
    : "";

  els.detailBody.innerHTML = `
    <span class="detail-layer" style="background:${LAYER_COLOR[layer] || LAYER_COLOR["L?"]}">${esc(layer)} · ${esc(node.label)}</span>
    <div class="detail-id">${esc(node.id)} ${clusterBadge}${anomalyBadge}</div>
    <section class="detail-section">
      <h4 class="detail-section-title">Метаданные узла</h4>
      ${propsHtml}
    </section>
    <section class="detail-section detail-rels">
      <h4 class="detail-section-title">Входящие (${incoming.length})</h4>
      ${renderRelBlock(incoming, "in")}
      <h4 class="detail-section-title">Исходящие (${outgoing.length})</h4>
      ${renderRelBlock(outgoing, "out")}
    </section>`;

  els.detailPanel.classList.remove("hidden");
  els.appRoot.classList.add("has-detail");
  document.querySelectorAll(".graph-node-item, .entity-card").forEach((el) => {
    el.classList.toggle("active", el.dataset.id === node.id);
  });
}

function renderLayerFilters() {
  const counts = { all: graphData.nodes.length };
  graphData.nodes.forEach((n) => {
    const l = layerOf(n.label);
    counts[l] = (counts[l] || 0) + 1;
  });
  const layers = ["all", "L1", "L2", "L3", "L4", "L5", "L6"];
  els.layerFilters.innerHTML = layers
    .filter((l) => l === "all" || counts[l])
    .map((l) => {
      const label = l === "all" ? `Все (${counts.all})` : `${l} (${counts[l] || 0})`;
      return `<button type="button" class="layer-chip ${graphLayerFilter === l ? "active" : ""}" data-layer="${l}">${label}</button>`;
    }).join("");
  els.layerFilters.querySelectorAll(".layer-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      graphLayerFilter = btn.dataset.layer;
      showCrossLayerOnly = false;
      if (els.crossLayerToggle) els.crossLayerToggle.classList.remove("active");
      renderGraphViews();
    });
  });
  if (els.crossLayerToggle) {
    els.crossLayerToggle.classList.toggle("active", showCrossLayerOnly);
  }
}

function renderGraphNodeList(nodes) {
  if (!nodes.length) {
    els.graphNodeList.innerHTML = '<div class="muted" style="padding:12px">Нет узлов</div>';
    return;
  }
  els.graphNodeList.innerHTML = nodes.slice(0, 200).map((n) => `
    <button type="button" class="graph-node-item" data-id="${esc(n.id)}">
      <div class="gn-label">${esc(n.label)}</div>
      <div class="gn-id">${esc(shortNodeLabel(n))}</div>
      <div class="gn-layer">${esc(layerOf(n.label))}</div>
    </button>`).join("");
  els.graphNodeList.querySelectorAll(".graph-node-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const node = graphData.nodes.find((n) => n.id === btn.dataset.id);
      openDetailPanel(node);
      if (visNetwork) visNetwork.selectNodes([node.id]);
    });
  });
}

function renderAllRelationshipsList() {
  const layerMap = nodeLayerMap();
  const nodeById = Object.fromEntries(graphData.nodes.map((n) => [n.id, n]));
  const rels = graphData.relationships;
  if (els.graphRelsCount) {
    const cross = rels.filter((r) => isCrossLayerRel(r, layerMap)).length;
    els.graphRelsCount.textContent = `${rels.length} связей · ${cross} межслойных`;
  }
  if (!rels.length) {
    els.graphRelsList.innerHTML = '<div class="muted">Нет связей</div>';
    return;
  }
  els.graphRelsList.innerHTML = rels.map((r) => {
    const { from, to } = relEndpoints(r);
    const cross = isCrossLayerRel(r, layerMap);
    const fromNode = nodeById[from];
    const toNode = nodeById[to];
    const fromLayer = fromNode ? layerOf(fromNode.label) : "?";
    const toLayer = toNode ? layerOf(toNode.label) : "?";
    return `
      <div class="rel-row ${cross ? "rel-cross-layer" : ""}" data-from="${esc(from)}" data-to="${esc(to)}">
        <span class="rel-from" data-id="${esc(from)}">${esc(shortNodeLabel(fromNode || { id: from }))}<small>${fromLayer}</small></span>
        <span class="rel-type">${esc(r.type)}</span>
        <span class="rel-to" data-id="${esc(to)}">${esc(shortNodeLabel(toNode || { id: to }))}<small>${toLayer}</small></span>
      </div>`;
  }).join("");
  els.graphRelsList.querySelectorAll(".rel-from, .rel-to").forEach((el) => {
    el.addEventListener("click", () => {
      const node = nodeById[el.dataset.id];
      if (node) openDetailPanel(node);
    });
  });
}

function graphDataKey(nodes, rels) {
  return `${nodes.length}|${rels.length}|${nodes.map((n) => n.id).sort().join(",")}`;
}

function graphContentKey(nodes, rels) {
  const propSig = nodes.map((n) => {
    const p = n.props || {};
    const keys = Object.keys(p).sort();
    return `${n.id}:${keys.map((k) => `${k}=${String(p[k]).slice(0, 24)}`).join("|")}`;
  }).join(";");
  return `${graphDataKey(nodes, rels)}|${propSig.slice(0, GRAPH_CONTENT_HASH_LIMIT)}`;
}

function graphViewKey(nodes, rels) {
  return `${graphLayerFilter}|${showCrossLayerOnly}|${graphDensityMode}|${graphViewMode}|${graphDataKey(nodes, rels)}`;
}

function resetGraphNetwork() {
  if (visNetwork) {
    visNetwork.destroy();
    visNetwork = null;
  }
  visNodesDataSet = null;
  visEdgesDataSet = null;
  lastGraphRenderKey = "";
  graphPhysicsStable = false;
}

function freezeGraphPhysics() {
  if (!visNetwork || graphPhysicsStable) return;
  visNetwork.setOptions({ physics: { enabled: false } });
  graphPhysicsStable = true;
}

function nodeHierarchicalLevel(label) {
  const layer = layerOf(label);
  if (layer === "L2" || layer === "L6") return 0;
  if (layer === "L1" || layer === "L4" || layer === "L5") return 1;
  if (layer === "L3") return 2;
  return 1;
}

function getVisNetworkOptions(nodeCount) {
  const compact = graphDensityMode === "compact";
  const interaction = {
    hover: true,
    tooltipDelay: 120,
    navigationButtons: true,
    keyboard: true,
    zoomView: true,
    dragView: true,
    dragNodes: true,
  };
  if (compact) {
    return {
      physics: {
        enabled: true,
        stabilization: { iterations: 55, fit: true, updateInterval: 20 },
        barnesHut: {
          gravitationalConstant: -1100,
          centralGravity: 0.1,
          springLength: 190,
          springConstant: 0.018,
          damping: 0.22,
          avoidOverlap: 0.4,
        },
        maxVelocity: 5,
        minVelocity: 0.04,
      },
      interaction,
    };
  }
  return {
    physics: {
      enabled: true,
      stabilization: { iterations: 80, fit: true, updateInterval: 25 },
      barnesHut: {
        gravitationalConstant: -3000,
        centralGravity: 0.2,
        springLength: 140,
        springConstant: 0.04,
        damping: 0.12,
        avoidOverlap: 0.15,
      },
    },
    interaction,
    layout: { improvedLayout: nodeCount < 80 },
  };
}

function buildVisGraphItems(nodes, rels) {
  const layerMap = new Map();
  nodes.forEach((n) => layerMap.set(n.id, layerOf(n.label)));
  const compact = graphDensityMode === "compact";
  const visNodes = nodes.map((n) => {
    const item = {
      id: n.id,
      label: shortGraphLabel(n),
      title: `${n.label}: ${n.id}`,
      color: {
        background: LAYER_COLOR[layerOf(n.label)] || LAYER_COLOR["L?"],
        border: "#fff",
        highlight: { background: "#01579b", border: "#fff" },
      },
      font: { color: "#fff", size: compact ? 9 : 11, face: "Inter, sans-serif" },
      shape: n._collapsed ? "ellipse" : "box",
      margin: compact ? 4 : 8,
      widthConstraint: compact ? { maximum: 90 } : undefined,
    };
    if (compact) item.level = nodeHierarchicalLevel(n.label);
    return item;
  });
  const edgeLimit = compact ? MAX_COMPACT_EDGES : 500;
  const visEdges = rels.slice(0, edgeLimit).map((r, i) => {
    const cross = isCrossLayerRel(r, layerMap);
    const showLabel = !compact && (cross || rels.length < 25);
    return {
      id: `e${i}`,
      from: r.from || r.from_,
      to: r.to,
      label: showLabel ? r.type : undefined,
      title: r.type,
      arrows: { to: { enabled: true, scaleFactor: compact ? 0.45 : 0.6 } },
      font: { size: 8, align: "middle", strokeWidth: 0, color: cross ? "#e65100" : "#546e7a" },
      color: cross
        ? { color: "rgba(255,152,0,0.55)", highlight: "#e65100" }
        : { color: "rgba(144,202,249,0.7)", highlight: "#0288d1" },
      width: cross ? (compact ? 1.2 : 2) : 0.8,
      smooth: { type: "dynamic", roundness: compact ? 0.35 : 0.5 },
      dashes: cross ? false : undefined,
    };
  });
  return { visNodes, visEdges };
}

function syncVisGraphData(visNodes, visEdges) {
  if (!visNodesDataSet || !visEdgesDataSet) return;
  const nodeIds = new Set(visNodes.map((n) => n.id));
  const edgeIds = new Set(visEdges.map((e) => e.id));
  const staleNodes = visNodesDataSet.getIds().filter((id) => !nodeIds.has(id));
  const staleEdges = visEdgesDataSet.getIds().filter((id) => !edgeIds.has(id));
  if (staleNodes.length) visNodesDataSet.remove(staleNodes);
  if (staleEdges.length) visEdgesDataSet.remove(staleEdges);
  visNodesDataSet.update(visNodes);
  visEdgesDataSet.update(visEdges);
}

function refreshGraphViewport() {
  if (!visNetwork) return;
  requestAnimationFrame(() => visNetwork.redraw());
}

function renderGraphMap(nodes, rels) {
  if (typeof vis === "undefined") {
    els.graphCanvas.innerHTML = '<div class="muted" style="padding:20px">vis-network не загрузился</div>';
    return;
  }
  updateDensityToggleUI();
  const renderKey = graphViewKey(nodes, rels);
  const { visNodes, visEdges } = buildVisGraphItems(nodes, rels);

  if (visNetwork && visNodesDataSet && lastGraphRenderKey === renderKey) {
    return;
  }

  if (visNetwork && visNodesDataSet) {
    const prevDensity = lastGraphRenderKey.split("|")[2];
    if (prevDensity && prevDensity !== graphDensityMode) {
      resetGraphNetwork();
    } else {
      syncVisGraphData(visNodes, visEdges);
      lastGraphRenderKey = renderKey;
      if (graphPhysicsStable) refreshGraphViewport();
      return;
    }
  }

  resetGraphNetwork();
  els.graphCanvas.innerHTML = "";
  updateDensityToggleUI();
  visNodesDataSet = new vis.DataSet(visNodes);
  visEdgesDataSet = new vis.DataSet(visEdges);
  visNetwork = new vis.Network(
    els.graphCanvas,
    { nodes: visNodesDataSet, edges: visEdgesDataSet },
    getVisNetworkOptions(nodes.length),
  );
  visNetwork.on("click", (params) => {
    if (!params.nodes.length) return;
    const nodeId = params.nodes[0];
    const node = nodes.find((n) => n.id === nodeId) || graphData.nodes.find((n) => n.id === nodeId);
    openDetailPanel(node);
  });
  if (graphDensityMode === "compact") {
    graphPhysicsStable = false;
    const onCompactStable = () => {
      visNetwork?.fit({ animation: { duration: 280, easingFunction: "easeInOutQuad" } });
      visNetwork?.setOptions({
        physics: {
          enabled: true,
          barnesHut: {
            gravitationalConstant: -450,
            centralGravity: 0.06,
            springLength: 200,
            springConstant: 0.01,
            damping: 0.32,
            avoidOverlap: 0.25,
          },
          maxVelocity: 2.5,
          minVelocity: 0.02,
        },
      });
    };
    visNetwork.once("stabilizationIterationsDone", onCompactStable);
    visNetwork.once("stabilized", onCompactStable);
  } else {
    const onStable = () => {
      freezeGraphPhysics();
      visNetwork.fit({ animation: { duration: 300, easingFunction: "easeInOutQuad" } });
    };
    visNetwork.once("stabilizationIterationsDone", onStable);
    visNetwork.once("stabilized", () => freezeGraphPhysics());
  }
  lastGraphRenderKey = renderKey;
}

function renderGraphViews(opts = {}) {
  const skipLayerFilters = opts.skipLayerFilters === true;
  if (!skipLayerFilters) renderLayerFilters();
  updateCrossLayerStat();
  const { nodes, rels } = filteredGraph();
  renderGraphNodeList(nodes);
  if (graphViewMode === "rels") {
    renderAllRelationshipsList();
  } else {
    renderGraphMap(nodes, rels);
  }
  renderL3Stats();
}

function initGraphResize() {
  const handle = els.graphResizeHandle;
  const wrap = els.graphCanvasWrap;
  if (!handle || !wrap) return;
  const saved = localStorage.getItem("mkg_graph_h");
  if (saved) wrap.style.height = `${saved}px`;
  let startY = 0;
  let startH = 0;
  const onMove = (e) => {
    const h = Math.max(220, Math.min(window.innerHeight * 0.78, startH + (e.clientY - startY)));
    wrap.style.height = `${h}px`;
    refreshGraphViewport();
  };
  const onUp = () => {
    localStorage.setItem("mkg_graph_h", String(wrap.offsetHeight));
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("mouseup", onUp);
  };
  handle.addEventListener("mousedown", (e) => {
    e.preventDefault();
    startY = e.clientY;
    startH = wrap.offsetHeight;
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  });
}

function toggleGraphNodeList() {
  graphNodeListVisible = !graphNodeListVisible;
  els.graphMapView?.classList.toggle("graph-node-list-hidden", !graphNodeListVisible);
  els.toggleNodeListBtn?.classList.toggle("active", graphNodeListVisible);
}

function fillModelSelect(selectEl, models, labels, current) {
  if (!selectEl) return;
  selectEl.innerHTML = models.map((m) => {
    const label = labels?.[m] || m;
    return `<option value="${esc(m)}" ${m === current ? "selected" : ""}>${esc(label)}</option>`;
  }).join("");
}

async function loadConfig() {
  try {
    const r = await fetch(`${API}/config/models`);
    if (!r.ok) return;
    const cfg = await r.json();
    fillModelSelect(els.llmModel, cfg.llm_models, null, cfg.llm_model);
    fillModelSelect(els.ocrModel, cfg.ocr_models, cfg.ocr_model_labels, cfg.ocr_model);
    fillModelSelect(els.embDocModel, cfg.emb_doc_models, cfg.emb_model_labels, cfg.emb_doc_model);
    fillModelSelect(els.embQueryModel, cfg.emb_query_models, cfg.emb_model_labels, cfg.emb_query_model);
  } catch { /* ignore */ }
}

async function saveConfig() {
  els.saveConfigBtn.disabled = true;
  if (els.settingsSaveStatus) els.settingsSaveStatus.textContent = "Сохранение…";
  try {
    const r = await fetch(`${API}/config/models`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        llm_model: els.llmModel.value,
        ocr_model: els.ocrModel.value,
        emb_doc_model: els.embDocModel.value,
        emb_query_model: els.embQueryModel.value,
      }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "ошибка сохранения");
    if (els.settingsSaveStatus) els.settingsSaveStatus.textContent = "Сохранено";
    setTimeout(() => {
      if (els.settingsSaveStatus) els.settingsSaveStatus.textContent = "";
    }, 2500);
    await refreshEmbeddingStatus();
  } catch (e) {
    if (els.settingsSaveStatus) els.settingsSaveStatus.textContent = e.message;
  } finally {
    els.saveConfigBtn.disabled = false;
  }
}

async function clearDatabase() {
  if (!window.confirm("Удалить все документы, Markdown, графы, логи и Neo4j?")) return;
  els.clearDbBtn.disabled = true;
  try {
    const r = await fetch(`${API}/admin/clear?confirm=true`, { method: "POST" });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Ошибка очистки");
    selectedDoc = null;
    graphViewDocId = null;
    graphVisible = false;
    lastGraphDocId = null;
    lastGraphDataKey = "";
    lastLogsDocId = null;
    lastLogsKey = "";
    resetGraphNetwork();
    indexedDocsSet.clear();
    saveIndexedDocs();
    docStatusCache.clear();
    switchPage("docs");
    docPanelMode = null;
    els.docMdPanel?.classList.add("hidden");
    els.docLogsPanel?.classList.add("hidden");
    closeDetailPanel();
    await renderDocsList();
  } catch (e) {
    appendQdrantLog(e.message, true);
  } finally {
    els.clearDbBtn.disabled = false;
  }
}

async function runDiagnostics() {
  els.diagBtn.disabled = true;
  els.diagList.innerHTML = '<div class="muted">Проверка…</div>';
  try {
    const r = await fetch(`${API}/diagnostics`);
    const data = await r.json();
    els.diagList.innerHTML = (data.checks || []).map((c) => `
      <div class="diag-item">
        <span>${esc(c.name)}</span>
        <span class="${c.ok ? "diag-ok" : "diag-fail"}">${c.ok ? "OK" : "FAIL"} · ${c.latency_ms} ms</span>
      </div>
      ${!c.ok && c.error ? `<div class="diag-error">${esc(c.error)}</div>` : ""}
      ${c.ok && c.detail ? `<div class="muted">${esc(c.detail)}</div>` : ""}`).join("") + (data.yandex_key_hint ? `<div class="muted" style="margin-top:8px">${esc(data.yandex_key_hint)}</div>` : "");
  } catch {
    els.diagList.innerHTML = '<div class="muted">Диагностика недоступна</div>';
  } finally {
    els.diagBtn.disabled = false;
  }
}

function formatUsage(u) {
  if (!u || typeof u !== "object") return "";
  const inT = u.input_tokens ?? "—";
  const outT = u.output_tokens ?? "—";
  const cacheT = u.cached_tokens ?? 0;
  const hit = u.cache_hit ? " · кэш" : "";
  return `in ${inT} · out ${outT} · cached ${cacheT}${hit}`;
}

function logsDataKey(items) {
  if (!items?.length) return "0";
  const last = items[items.length - 1];
  return `${items.length}|${last.ts || ""}|${last.kind || ""}`;
}

function hasOpenLogDetails() {
  return !!els.logsPreview?.querySelector(".log-details[open]");
}

function captureOpenLogDetails() {
  const open = [];
  els.logsPreview?.querySelectorAll(".log-entry").forEach((entry, idx) => {
    entry.querySelectorAll(".log-details[open]").forEach((det) => {
      const summary = det.querySelector("summary")?.textContent?.trim() || "";
      open.push(`${idx}:${summary}`);
    });
  });
  return open;
}

function restoreOpenLogDetails(keys) {
  if (!keys?.length) return;
  const entries = els.logsPreview?.querySelectorAll(".log-entry");
  keys.forEach((key) => {
    const sep = key.indexOf(":");
    const idx = Number(key.slice(0, sep));
    const summary = key.slice(sep + 1);
    const entry = entries?.[idx];
    if (!entry) return;
    entry.querySelectorAll(".log-details").forEach((det) => {
      const s = det.querySelector("summary")?.textContent?.trim() || "";
      if (s === summary) det.open = true;
    });
  });
}

function formatLogEntry(item) {
  const ts = item.ts ? new Date(item.ts).toLocaleString("ru-RU") : "—";
  const model = item.model || item.request?.model || item.request?.auto_reason || "";
  const usage = item.usage || item.response?.usage;
  const usageLine = formatUsage(usage);
  const cacheHit = item.response?.cache_hit || item.cache_hit;
  const req = item.request ? JSON.stringify(item.request, null, 2) : "—";
  const resp = item.error
    ? item.error
    : (item.response ? JSON.stringify(item.response, null, 2) : "—");
  return `<div class="log-entry">
    <div class="log-head">
      <span class="log-kind">${esc(item.kind || "?")}</span>
      <span class="log-ts">${esc(ts)}</span>
      ${usageLine ? `<span class="log-tokens">${esc(usageLine)}</span>` : ""}
      ${cacheHit ? `<span class="log-cache">кэш hit</span>` : ""}
    </div>
    ${model ? `<div class="log-model">${esc(model)}</div>` : ""}
    <details class="log-details"><summary>тело запроса</summary><pre>${esc(req)}</pre></details>
    <details class="log-details"><summary>${item.error ? "ошибка" : "ответ"}</summary><pre>${esc(resp)}</pre></details>
  </div>`;
}

async function loadGraph(docId, opts = {}) {
  const silent = opts.silent === true;
  const docChanged = docId !== lastGraphDocId;
  if (docChanged) {
    resetGraphNetwork();
    lastGraphDocId = docId;
    lastGraphDataKey = "";
  }
  if (graphViewMode === "map" && !silent && !visNetwork) {
    els.graphCanvas.innerHTML = '<div class="muted" style="padding:20px">Загрузка графа…</div>';
  }
  if (!silent) els.graphNodeList.innerHTML = "";
  try {
    const url = docId === GRAPH_ALL_ID
      ? `${API}/graph/all`
      : `${API}/graph/documents/${encodeURIComponent(docId)}`;
    const r = await fetch(url);
    if (!r.ok) {
      graphData = { nodes: [], relationships: [] };
      lastGraphDataKey = "";
      if (graphViewMode === "map" && !visNetwork) {
        els.graphCanvas.innerHTML = '<div class="muted" style="padding:20px">Граф ещё не сформирован. Нажмите «Построить граф».</div>';
      }
      renderGraphViews();
      return;
    }
    const g = await r.json();
    const rels = (g.relationships || []).map((rel) => ({
      type: rel.type,
      from: rel.from || rel.from_,
      to: rel.to,
      props: rel.props || {},
    }));
    const nodes = g.nodes || [];
    const newKey = graphContentKey(nodes, rels);
    const dataChanged = newKey !== lastGraphDataKey || docChanged;
    graphData = { nodes, relationships: rels };
    lastGraphDataKey = newKey;
    if (!dataChanged) {
      updateCrossLayerStat();
      if (!silent) renderGraphViews();
      return;
    }
    renderGraphViews({ skipLayerFilters: silent });
    if (docId === GRAPH_ALL_ID) {
      updateDocPageBar({ file_name: "Все документы", id: GRAPH_ALL_ID, graph_nodes: nodes.length });
    } else if (docId === selectedDoc) {
      const cached = docsListCache.find((d) => d.id === selectedDoc);
      if (cached) updateDocPageBar(cached);
    }
  } catch {
    graphData = { nodes: [], relationships: [] };
    lastGraphDataKey = "";
    if (graphViewMode === "map" && !visNetwork) {
      els.graphCanvas.innerHTML = '<div class="muted" style="padding:20px">Ошибка загрузки графа</div>';
    }
  }
}

async function loadLogs(docId, opts = {}) {
  const force = opts.force === true;
  const silent = opts.silent === true;
  const prevKey = lastLogsKey;
  const prevCount = prevKey === "0" ? 0 : Number(prevKey.split("|")[0]) || 0;
  const sameDoc = docId === lastLogsDocId;

  if (!force && sameDoc && hasOpenLogDetails()) {
    // defer DOM wipe while user reads expanded entries; still fetch to detect new logs
  } else if (!silent && (!sameDoc || !lastLogsKey)) {
    els.logsPreview.innerHTML = '<div class="muted">Загрузка…</div>';
    els.logsPreview.classList.add("empty");
  }
  try {
    const r = await fetch(`${API}/documents/${encodeURIComponent(docId)}/logs?limit=100`);
    if (!r.ok) {
      lastLogsKey = "";
      lastLogsDocId = docId;
      setPreview(els.logsPreview, "Логи недоступны", true);
      return;
    }
    const data = await r.json();
    const items = (data.items || []).filter((item) => !item.doc_id || item.doc_id === docId);
    const key = logsDataKey(items);
    if (!force && sameDoc && key === lastLogsKey) return;

    if (!items.length) {
      lastLogsKey = key;
      lastLogsDocId = docId;
      const hint = selectedDoc === docId ? "Пока нет записей. Логи появятся во время OCR и извлечения." : "—";
      setPreview(els.logsPreview, hint, true);
      return;
    }

    if (!force && sameDoc && hasOpenLogDetails() && items.length > prevCount) {
      const newItems = items.slice(prevCount);
      if (newItems.length) {
        els.logsPreview.insertAdjacentHTML("beforeend", newItems.map(formatLogEntry).join(""));
        els.logsPreview.classList.remove("empty");
      }
      lastLogsKey = key;
      lastLogsDocId = docId;
      return;
    }

    const openKeys = captureOpenLogDetails();
    els.logsPreview.innerHTML = items.map(formatLogEntry).join("");
    els.logsPreview.classList.remove("empty");
    restoreOpenLogDetails(openKeys);
    lastLogsKey = key;
    lastLogsDocId = docId;
  } catch {
    if (!silent) setPreview(els.logsPreview, "Ошибка загрузки логов", true);
  }
}

async function rebuildGraphConnections() {
  if (!selectedDoc) return;
  if (!window.confirm(
    "Перестроить связи и узлы графа заново?\n\n"
    + "Будет запущено повторное извлечение из Markdown. Текущий граф заменится новым результатом.",
  )) return;
  await submitToGraph();
}

async function submitToGraph() {
  if (!selectedDoc) return;
  if (els.docPrimaryBtn) els.docPrimaryBtn.disabled = true;
  await fetch(`${API}/documents/${encodeURIComponent(selectedDoc)}/submit`, { method: "POST" });
  await openDoc(selectedDoc, { switchTo: "doc" });
  if (els.docPrimaryBtn) els.docPrimaryBtn.disabled = false;
}

function viewGraph() {
  if (!selectedDoc) return;
  graphScope = "doc";
  graphVisible = true;
  if (currentPage !== "doc" && currentPage !== "graphAll") {
    switchPage("doc");
  } else {
    updateGraphsPageState();
    refreshGraphViewport();
  }
}

async function openDoc(id, opts = {}) {
  selectedDoc = id;
  graphViewDocId = id;
  graphScope = "doc";
  docWorkTabManual = false;
  docWorkTab = "journey";
  if (opts.showGraph === true) {
    graphVisible = true;
    docWorkTab = "journey";
  } else if (opts.switchTo) graphVisible = false;
  closeDetailPanel();
  if (opts.switchTo) {
    switchPage(opts.switchTo);
  }
  const p = await fetch(`${API}/documents/${encodeURIComponent(id)}/preview`);
  if (!p.ok) return;
  const data = await p.json();

  updateGraphScopeUI();
  await applyPreviewUpdate(data, { clearError: true, forceGraph: true });
  refreshEmbeddingStatus();
  updateSearchBadge(id);
  populateGraphDocFilter(docsListCache);
  if (docPanelMode === "logs") loadLogs(id, { force: true });
  updateGraphsPageState();
  if (currentPage === "docs") renderDocsList();
  if (currentPage === "qdrant") {
    loadQdrantPoints(id);
    loadQdrantClusterMap();
  }
}

function docNeedsLivePreview(cur, prevStatus) {
  if (!cur || !selectedDoc || cur.id !== selectedDoc) return false;
  if (ACTIVE_DOC_STATUSES.has(cur.status)) return true;
  if (cur.status !== prevStatus) return true;
  if (
    (currentPage === "doc" || currentPage === "graphAll")
    && (cur.graph_nodes || 0) > 0
    && graphData.nodes.length === 0
  ) return true;
  return false;
}

async function pollSelectedDocumentPreview() {
  if (!selectedDoc || graphScope === "all") return;
  const cur = docsListCache.find((x) => x.id === selectedDoc);
  const prevStatus = docStatusCache.get(selectedDoc);
  if (!docNeedsLivePreview(cur, prevStatus)) return;
  try {
    const prev = await fetch(`${API}/documents/${encodeURIComponent(selectedDoc)}/preview`);
    if (!prev.ok) return;
    const p = await prev.json();
    await applyPreviewUpdate(p, {
      forceGraph: p.status === "loaded" || p.status === "md_ready",
    });
  } catch { /* ignore */ }
}

async function loadDocuments() {
  return renderDocsList();
}

async function renderDocsList() {
  if (!els.docs) return;
  try {
    const r = await fetch(`${API}/documents?page=1&page_size=50`);
    if (!r.ok) {
      els.docs.innerHTML = '<div class="muted">Не удалось загрузить список документов</div>';
      return;
    }
    const data = await r.json();
    docsListCache = data.items || [];
    populateGraphDocFilter(docsListCache);
    updateGraphsPageState();
    if (!data.items?.length) {
      els.docs.innerHTML = '<div class="muted">Пока нет документов — загрузите файл выше</div>';
      return;
    }
    const q = docListFilterText.trim().toLowerCase();
    const filtered = q
      ? data.items.filter((d) => (d.file_name || d.id || "").toLowerCase().includes(q))
      : data.items;
    if (!filtered.length) {
      els.docs.innerHTML = '<div class="muted">Нет документов по фильтру</div>';
      return;
    }
    els.docs.innerHTML = filtered.map(renderDocCard).join("");
    bindDocCards(els.docs);
    const sel = docsListCache.find((x) => x.id === selectedDoc);
    updateDocWorkArea(sel || null);
    await pollSelectedDocumentPreview();
    for (const id of [...pipelineQueue]) {
      await ensurePipeline(id);
    }
  } catch (e) {
    els.docs.innerHTML = `<div class="muted">Ошибка загрузки: ${esc(e.message)}</div>`;
  }
}

function bindNavigation() {
  document.querySelectorAll(".page-nav-link").forEach((link) => {
    link.addEventListener("click", () => switchPage(link.dataset.page));
  });
}

function bindEvents() {
  els.file?.addEventListener("change", (e) => pickFiles(e.target.files));
  els.pickBtn?.addEventListener("click", (e) => { e.stopPropagation(); openFilePicker(); });
  els.drop?.addEventListener("click", (e) => {
    if (e.target.closest(".upload-actions")) return;
    openFilePicker();
  });
  els.drop?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openFilePicker(); }
  });
  els.drop?.addEventListener("dragover", (e) => { e.preventDefault(); els.drop.classList.add("over"); });
  els.drop?.addEventListener("dragleave", () => els.drop.classList.remove("over"));
  els.drop?.addEventListener("drop", (e) => {
    e.preventDefault();
    els.drop.classList.remove("over");
    pickFiles(e.dataTransfer.files);
  });
  els.uploadBtn?.addEventListener("click", (e) => { e.stopPropagation(); uploadFiles(); });
  els.saveConfigBtn?.addEventListener("click", saveConfig);
  els.clearDbBtn?.addEventListener("click", clearDatabase);
  els.diagBtn?.addEventListener("click", runDiagnostics);
  els.l3IndexBtn?.addEventListener("click", () => indexEmbeddings(selectedDoc));
  els.l3IndexAllBtn?.addEventListener("click", indexAllEmbeddings);
  els.l4ClusterBtn?.addEventListener("click", runL4Clustering);
  els.qdrantDocFilter?.addEventListener("change", () => {
    openDoc(els.qdrantDocFilter.value, { keepPage: true });
    loadQdrantPoints(selectedDoc);
  });
  els.qdrantSearchForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    runSearch(els.qdrantSearchQuery?.value, els.qdrantSearchResults);
  });
  els.docListFilter?.addEventListener("input", (e) => {
    docListFilterText = e.target.value;
    renderDocsList();
  });
  els.viewAllGraphBtn?.addEventListener("click", viewAllGraph);
  els.docBackBtn?.addEventListener("click", () => switchPage("docs"));
  els.docPrimaryBtn?.addEventListener("click", () => {
    const action = els.docPrimaryBtn?.dataset.action;
    if (action === "view" || action === "refresh") {
      graphVisible = true;
      if (graphScope === "all") {
        updateGraphVisibility();
        loadGraph(GRAPH_ALL_ID);
        refreshGraphViewport();
      } else {
        viewGraph();
      }
    } else submitToGraph();
  });
  els.docRebuildGraphBtn?.addEventListener("click", rebuildGraphConnections);
  els.docReprocessBtn?.addEventListener("click", async () => {
    if (!selectedDoc) return;
    await fetch(`${API}/documents/${encodeURIComponent(selectedDoc)}/reprocess`, { method: "POST" });
    await openDoc(selectedDoc, { keepPage: true });
  });
  els.docMdBtn?.addEventListener("click", () => toggleDocPanel("md"));
  els.docLogsBtn?.addEventListener("click", () => toggleDocPanel("logs"));
  els.mdViewRenderBtn?.addEventListener("click", () => setMdViewMode("clean"));
  els.mdViewSourceBtn?.addEventListener("click", () => setMdViewMode("marked"));
  els.mdInlineCleanBtn?.addEventListener("click", () => setMdViewMode("clean"));
  els.mdInlineMarkedBtn?.addEventListener("click", () => setMdViewMode("marked"));
  els.docMdDownloadBtn?.addEventListener("click", () => downloadDocumentMd());
  els.docMdInlineDownloadBtn?.addEventListener("click", () => downloadDocumentMd());
  document.querySelectorAll(".doc-work-tab").forEach((btn) => {
    btn.addEventListener("click", () => setDocWorkTab(btn.dataset.tab, { manual: true }));
  });
  els.docNeo4jBtn?.addEventListener("click", openNeo4jBrowser);
  els.docStopBtn?.addEventListener("click", async () => {
    if (!selectedDoc) return;
    await fetch(`${API}/documents/${encodeURIComponent(selectedDoc)}/cancel-extraction`, { method: "POST" });
    await openDoc(selectedDoc, { keepPage: true });
  });
  els.graphCompactBtn?.addEventListener("click", () => setGraphDensityMode("compact"));
  els.graphFullBtn?.addEventListener("click", () => setGraphDensityMode("full"));
  els.closeDetailBtn?.addEventListener("click", closeDetailPanel);
  els.crossLayerToggle?.addEventListener("click", () => {
    showCrossLayerOnly = !showCrossLayerOnly;
    if (showCrossLayerOnly) graphLayerFilter = "all";
    renderGraphViews();
  });
  els.toggleNodeListBtn?.addEventListener("click", toggleGraphNodeList);
  els.viewMapBtn?.addEventListener("click", () => setGraphViewMode("map"));
  els.viewRelsBtn?.addEventListener("click", () => setGraphViewMode("rels"));
  els.originalGraphBtn?.addEventListener("click", resetGraphFilters);
  els.headerNeo4jBtn?.addEventListener("click", openNeo4jBrowser);
  initGraphResize();
}

function boot() {
  if (window.marked?.setOptions) {
    window.marked.setOptions({ breaks: true, gfm: true });
  }
  switchPage("chats");
  bindNavigation();
  try {
    bindEvents();
  } catch (err) {
    console.error("MKG UI init error:", err);
  }
  updateDensityToggleUI();
  els.appRoot?.classList.add("js-ready");
  loadFormats();
  loadNodeFieldHints();
  loadConfig();
  loadProjectStage();
  refreshEmbeddingStatus();
  renderDocsList();
  setInterval(renderDocsList, 1500);
  setInterval(refreshEmbeddingStatus, 30000);
  window.MKGAuth?.init();
}

boot();
