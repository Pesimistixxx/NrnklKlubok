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
  pageGuide: $("pageGuide"),
  pageSettings: $("pageSettings"),
  docSectionTabs: $("docSectionTabs"),
  guideContent: $("guideContent"),
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
  previewMdRaw: $("previewMdRaw"),
  previewMdSource: $("previewMdSource"),
  mdViewCleanBtn: $("mdViewCleanBtn"),
  mdViewRawBtn: $("mdViewRawBtn"),
  mdViewMarkedBtn: $("mdViewMarkedBtn"),
  previewLogs: $("previewLogs"),
  logsPreview: $("previewLogs"),
  docListFilter: $("docListFilter"),
  graphPageHead: $("graphPageHead"),
  graphPageTitle: $("graphPageTitle"),
  graphPageLead: $("graphPageLead"),
  graphsEmpty: $("graphsEmpty"),
  graphsWorkspace: $("graphsWorkspace"),
  qdrantSearchForm: $("qdrantSearchForm"),
  qdrantSearchQuery: $("qdrantSearchQuery"),
  qdrantSearchResults: $("qdrantSearchResults"),
  qdrantSearchMeta: $("qdrantSearchMeta"),
  qdrantPointsList: $("qdrantPointsList"),
  qdrantPointsCount: $("qdrantPointsCount"),
  qdrantClusterMap: $("qdrantClusterMap"),
  qdrantClusterCount: $("qdrantClusterCount"),
  qdrantVizCanvas: $("qdrantVizCanvas"),
  qdrantVizLegend: $("qdrantVizLegend"),
  qdrantVizMeta: $("qdrantVizMeta"),
  qdrantVizPlaceholder: $("qdrantVizPlaceholder"),
  qdrantVizEmptyState: $("qdrantVizEmptyState"),
  qdrantClusterCards: $("qdrantClusterCards"),
  qdrantToast: $("qdrantToast"),
  qdrantIndexLog: $("qdrantIndexLog"),
  graphCanvas: $("graphCanvas"),
  graphCanvasWrap: $("graphCanvasWrap"),
  graphResizeHandle: $("graphResizeHandle"),
  graphToolbarShell: $("graphToolbarShell"),
  graphToolbarToggle: $("graphToolbarToggle"),
  graphNodeList: $("graphNodeList"),
  graphMapView: $("graphMapView"),
  graphRelsView: $("graphRelsView"),
  graphRelsList: $("graphRelsList"),
  graphRelsCount: $("graphRelsCount"),
  layerFilters: $("layerFilters"),
  crossLayerToggle: $("crossLayerToggle"),
  connectionFormationBtn: $("connectionFormationBtn"),
  connectionFormationTimeline: $("connectionFormationTimeline"),
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
  graphClusterLegend: $("graphClusterLegend"),
  graphCompactBtn: $("graphCompactBtn"),
  graphFullBtn: $("graphFullBtn"),
  graphFilterSearch: $("graphFilterSearch"),
  graphEntityTypeChecks: $("graphEntityTypeChecks"),
  graphFilterGeography: $("graphFilterGeography"),
  graphFilterPracticeRegion: $("graphFilterPracticeRegion"),
  graphFilterNumericMin: $("graphFilterNumericMin"),
  graphFilterNumericMax: $("graphFilterNumericMax"),
  graphFilterNumericParam: $("graphFilterNumericParam"),
  graphFilterYearMin: $("graphFilterYearMin"),
  graphFilterYearMax: $("graphFilterYearMax"),
  graphFilterYearLabel: $("graphFilterYearLabel"),
  graphFilterConfidence: $("graphFilterConfidence"),
  graphFilterMaterial: $("graphFilterMaterial"),
  graphFilterProcess: $("graphFilterProcess"),
  graphDocTypeChecks: $("graphDocTypeChecks"),
  graphRelationTypeChecks: $("graphRelationTypeChecks"),
  graphFilterLanguage: $("graphFilterLanguage"),
  graphFilterParamMin: $("graphFilterParamMin"),
  graphFilterParamMax: $("graphFilterParamMax"),
  graphFilterContradictions: $("graphFilterContradictions"),
  graphFilterGaps: $("graphFilterGaps"),
  graphFilterApplyBtn: $("graphFilterApplyBtn"),
  graphFilterResetBtn: $("graphFilterResetBtn"),
  graphFilterStatus: $("graphFilterStatus"),
  qdrantSearchKeyword: $("qdrantSearchKeyword"),
  qdrantFilterChips: $("qdrantFilterChips"),
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
  docUploadFallback: $("docUploadFallback"),
  docUploadFallbackBtn: $("docUploadFallbackBtn"),
  docJourneyPane: $("docJourneyPane"),
  docJourneyContent: $("docJourneyContent"),
  docMdPane: $("docMdPane"),
  docGraphPane: $("docGraphPane"),
  docMdInlineClean: $("docMdInlineClean"),
  docMdInlineRaw: $("docMdInlineRaw"),
  docMdInlineMarked: $("docMdInlineMarked"),
  mdInlineCleanBtn: $("mdInlineCleanBtn"),
  mdInlineRawBtn: $("mdInlineRawBtn"),
  mdInlineMarkedBtn: $("mdInlineMarkedBtn"),
  detailPanel: $("detailPanel"),
  detailTitle: $("detailTitle"),
  detailBody: $("detailBody"),
  closeDetailBtn: $("closeDetailBtn"),
  graphCompareBtn: $("graphCompareBtn"),
  graphComparePanel: $("graphComparePanel"),
  graphCompareSelected: $("graphCompareSelected"),
  graphCompareClearBtn: $("graphCompareClearBtn"),
  graphCompareRefreshBtn: $("graphCompareRefreshBtn"),
  graphCompareTableWrap: $("graphCompareTableWrap"),
  dashboardCards: $("dashboardCards"),
  dashboardDomains: $("dashboardDomains"),
  dashboardRiskList: $("dashboardRiskList"),
  dashboardRefreshBtn: $("dashboardRefreshBtn"),
  topicWatchlistInput: $("topicWatchlistInput"),
  topicWatchlistSaveBtn: $("topicWatchlistSaveBtn"),
  topicWatchlistStatus: $("topicWatchlistStatus"),
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

const QDRANT_VIZ_L3_COLOR = "#0288d1";
const QDRANT_VIZ_L4_COLOR = "#ef6c00";
const QDRANT_VIZ_ANOMALY_COLOR = "#c62828";
const QDRANT_CLUSTER_PALETTE = [
  "#ef6c00", "#7b1fa2", "#1565c0", "#2e7d32", "#00838f",
  "#6a1b9a", "#558b2f", "#ad1457", "#4527a0", "#fb8c00",
  "#5d4037", "#00695c", "#c2185b", "#283593", "#827717",
];

/** @type {import("chart.js").Chart|null} */
let qdrantVizChart = null;
/** @type {Array<Record<string, unknown>>} */
let qdrantVizPoints = [];
/** @type {Array<{id:number,name:string,color:string,count:number}>} */
let qdrantVizClusters = [];
/** @type {Array<object>} */
let qdrantVizRegions = [];
/** @type {object|null} */
let qdrantClusteringContext = null;
/** @type {boolean} */
let qdrantClusterAutoPending = false;
/** @type {boolean} */
let qdrantClusterAutoDone = false;

function clusterColor(clusterId) {
  return QDRANT_CLUSTER_PALETTE[Math.abs(Number(clusterId)) % QDRANT_CLUSTER_PALETTE.length];
}

function convexHull2D(points) {
  if (points.length < 3) return points.slice();
  const pts = [...points].sort((a, b) => a.x - b.x || a.y - b.y);
  const cross = (o, a, b) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
  const lower = [];
  for (const p of pts) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop();
    lower.push(p);
  }
  const upper = [];
  for (let i = pts.length - 1; i >= 0; i -= 1) {
    const p = pts[i];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop();
    upper.push(p);
  }
  upper.pop();
  lower.pop();
  return lower.concat(upper);
}

function buildQdrantClusterRegions(points, clusterMeta) {
  const byCluster = new Map();
  points.forEach((p) => {
    if (p.layer !== "L4" || p.cluster_id == null || Number(p.cluster_id) < 0) return;
    const cid = Number(p.cluster_id);
    if (!byCluster.has(cid)) byCluster.set(cid, []);
    byCluster.get(cid).push({ x: p.x, y: p.y });
  });
  const metaById = new Map((clusterMeta || []).map((c) => [Number(c.id), c]));
  const regions = [];
  byCluster.forEach((coords, cid) => {
    if (!coords.length) return;
    const color = metaById.get(cid)?.color || clusterColor(cid);
    const label = metaById.get(cid)?.name || `Кластер ${cid}`;
    if (coords.length >= 3) {
      regions.push({
        type: "hull",
        clusterId: cid,
        points: convexHull2D(coords),
        fill: `${color}33`,
        stroke: color,
        label,
      });
      return;
    }
    const cx = coords.reduce((s, p) => s + p.x, 0) / coords.length;
    const cy = coords.reduce((s, p) => s + p.y, 0) / coords.length;
    let rx = 0.06;
    let ry = 0.04;
    if (coords.length === 2) {
      const dx = coords[1].x - coords[0].x;
      const dy = coords[1].y - coords[0].y;
      const dist = Math.hypot(dx, dy);
      rx = Math.max(dist / 2 + 0.04, 0.05);
      ry = Math.max(dist * 0.35, 0.04);
    }
    regions.push({
      type: "ellipse",
      clusterId: cid,
      cx,
      cy,
      rx,
      ry,
      fill: `${color}33`,
      stroke: color,
      label,
    });
  });
  return regions;
}

/** @deprecated use buildQdrantClusterRegions */
function buildQdrantClusterHulls(points, clusterMeta) {
  return buildQdrantClusterRegions(points, clusterMeta);
}

const qdrantHullPlugin = {
  id: "qdrantClusterHulls",
  afterDatasetsDraw(chart, _args, opts) {
    const regions = opts?.hulls || opts?.regions;
    if (!regions?.length) return;
    const { ctx } = chart;
    const xScale = chart.scales.x;
    const yScale = chart.scales.y;
    const drawLabel = (label, cx, cy, stroke) => {
      if (!label) return;
      const px = xScale.getPixelForValue(cx);
      const py = yScale.getPixelForValue(cy);
      ctx.font = "600 11px Inter, system-ui, sans-serif";
      ctx.fillStyle = stroke;
      ctx.strokeStyle = "rgba(255,255,255,0.92)";
      ctx.lineWidth = 3;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      const txt = label.length > 36 ? `${label.slice(0, 34)}…` : label;
      ctx.strokeText(txt, px, py);
      ctx.fillText(txt, px, py);
    };
    ctx.save();
    regions.forEach((region) => {
      ctx.fillStyle = region.fill;
      ctx.strokeStyle = region.stroke;
      ctx.lineWidth = 2;
      ctx.globalAlpha = 0.88;
      if (region.type === "ellipse") {
        const px = xScale.getPixelForValue(region.cx);
        const py = yScale.getPixelForValue(region.cy);
        const rx = Math.abs(xScale.getPixelForValue(region.cx + region.rx) - px);
        const ry = Math.abs(yScale.getPixelForValue(region.cy + region.ry) - py);
        ctx.beginPath();
        ctx.ellipse(px, py, Math.max(rx, 8), Math.max(ry, 8), 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
        drawLabel(region.label, region.cx, region.cy, region.stroke);
      } else {
        const pts = region.points;
        if (!pts || pts.length < 3) return;
        ctx.beginPath();
        ctx.moveTo(xScale.getPixelForValue(pts[0].x), yScale.getPixelForValue(pts[0].y));
        for (let i = 1; i < pts.length; i += 1) {
          ctx.lineTo(xScale.getPixelForValue(pts[i].x), yScale.getPixelForValue(pts[i].y));
        }
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
        const cx = pts.reduce((s, p) => s + p.x, 0) / pts.length;
        const cy = pts.reduce((s, p) => s + p.y, 0) / pts.length;
        drawLabel(region.label, cx, cy, region.stroke);
      }
      ctx.globalAlpha = 1;
    });
    ctx.restore();
  },
};

if (typeof Chart !== "undefined" && Chart.register) {
  Chart.register(qdrantHullPlugin);
}

const CROSS_LAYER_REL_TYPES = new Set(["DATA_SOURCE_FOR", "CONTEXT_FOR", "ABOUT"]);
const CROSS_LAYER_EDGE_COLOR = { color: "#ff9800", highlight: "#e65100" };
const ENTITY_LABELS = new Set(["Material", "Process", "Equipment", "ChemicalReagent", "Organization", "Person", "Expert", "Facility"]);
const FORMATION_LAYERS = ["L1", "L2", "L3", "L4", "L5", "L6"];
const FORMATION_LAYER_LABELS = {
  L1: "Сущности L1",
  L2: "Контекст L2",
  L3: "Текст L3",
  L4: "Факты L4",
  L5: "Доступ L5",
  L6: "Решения L6",
};
const FORMATION_STEP_MS = 1400;
const L3_INTERNAL_REL_TYPES = new Set(["NEXT_PARAGRAPH", "TAGGED_WITH", "HAS_PARAGRAPH", "STRUCTURING"]);
const COMPACT_DOC_TEXT_ID = "__compact_doc_text__";
const MAX_COMPACT_PARAGRAPHS = 15;
const MAX_COMPACT_EDGES = 150;
const GRAPH_LABEL_MAX = 20;
const GRAPH_ALL_ID = "__all__";
const NEO4J_BROWSER_URL = "http://localhost:7474/browser/";
const GRAPH_ADV_FILTERS_SESSION_KEY = "mkg_graph_adv_filters";

const ENTITY_TYPE_FILTERS = [
  { id: "material", label: "Материал", labels: ["Material"] },
  { id: "process", label: "Процесс", labels: ["Process"] },
  { id: "equipment", label: "Оборудование", labels: ["Equipment"] },
  { id: "property", label: "Свойство", labels: ["Property"] },
  { id: "experiment", label: "Эксперимент", labels: ["ExperimentRun"] },
  { id: "publication", label: "Публикация", labels: ["Document"] },
  { id: "expert", label: "Эксперт", labels: ["Expert"] },
  { id: "object", label: "Объект", labels: ["Organization", "Location", "Facility"] },
];
const ALL_ENTITY_FILTER_IDS = ENTITY_TYPE_FILTERS.map((e) => e.id);
const ENTITY_LABELS_BY_FILTER_ID = Object.fromEntries(
  ENTITY_TYPE_FILTERS.map((e) => [e.id, new Set(e.labels)]),
);
const CONTRADICTION_REL_TYPES = new Set([
  "FOUND_ANOMALY", "BASE_FOR_CONFLICT", "RESOLVED_BY", "FIXED_IN", "LINKED_GAP",
]);
const CONTRADICTION_NODE_LABELS = new Set(["Contradiction"]);
const GAP_NODE_LABELS = new Set(["KnowledgeGap"]);
const GAP_REL_TYPES = new Set(["DETECTED_MISSING", "LINKED_GAP"]);

const DOC_CATEGORY_FILTERS = [
  { id: "patent", label: "Патент" },
  { id: "article", label: "Статья" },
  { id: "report", label: "Отчёт" },
  { id: "handbook", label: "Справочник" },
];
const ALL_DOC_CATEGORY_IDS = DOC_CATEGORY_FILTERS.map((d) => d.id);

const RELATION_TYPE_FILTERS = [
  { id: "USES_MAT", label: "Материал (USED_FOR)" },
  { id: "OPERATES_PROC", label: "Процесс" },
  { id: "SHOWED_EFFECT", label: "Эффект (SHOWED_EFFECT)" },
  { id: "AUTHORED", label: "Автор (EXPERT_IN)" },
  { id: "PRODUCED_MEASURE", label: "Измерение" },
  { id: "ASSERTED_BY", label: "Утверждение" },
  { id: "DERIVED_FROM", label: "Выведено из" },
  { id: "CONTEXT_FOR", label: "Контекст" },
  { id: "DATA_SOURCE_FOR", label: "Источник данных" },
];
const ALL_RELATION_FILTER_IDS = RELATION_TYPE_FILTERS.map((r) => r.id);

const SYNONYM_PAIRS = [
  ["электроэкстракция", "electrowinning"],
  ["пвп", "fluidized bed furnace"],
  ["fluidized bed", "пвп"],
];

function defaultGraphAdvancedFilters() {
  return {
    active: false,
    searchText: "",
    entityTypes: [...ALL_ENTITY_FILTER_IDS],
    docCategories: [...ALL_DOC_CATEGORY_IDS],
    relationTypes: [...ALL_RELATION_FILTER_IDS],
    geography: "",
    practiceRegion: "",
    yearMin: 1990,
    yearMax: 2026,
    minConfidence: 0,
    materialKeyword: "",
    processKeyword: "",
    language: "both",
    numericMin: "",
    numericMax: "",
    numericParam: "",
    showContradictions: false,
    showGaps: false,
  };
}

function defaultQdrantPostFilters() {
  return { docTypes: [], layers: [], minConfidence: 0 };
}

const DOC_PIPELINE = [
  { id: "upload", label: "Загрузка", short: "Файл" },
  { id: "ocr", label: "OCR / ingestion", short: "OCR" },
  { id: "md", label: "Markdown", short: "MD" },
  { id: "graph", label: "Extraction / граф", short: "Граф" },
  { id: "neo4j", label: "Neo4j", short: "Neo4j" },
  { id: "qdrant", label: "L3+L4 индекс (Qdrant)", short: "L3+L4" },
  { id: "l4", label: "Глобальная кластеризация L4", short: "L4" },
];

const JOURNEY_STAGES = [
  { id: "upload", title: "Загрузка файла", hint: "PDF, DOCX или другой формат принят в хранилище" },
  { id: "ocr", title: "OCR и ingestion", hint: "Распознавание текста, очистка, сборка Markdown" },
  { id: "md", title: "Markdown готов", hint: "Чистый MD и размеченный (L3 + узлы графа) — вкладка «Markdown», скачивание .md" },
  { id: "layers", title: "Извлечение слоёв L1–L6", hint: "LLM извлекает сущности, абзацы, факты, роли доступа…", isLayers: true },
  { id: "graph", title: "Граф знаний", hint: "Узлы и связи сохранены локально" },
  { id: "neo4j", title: "Neo4j", hint: "Синхронизация в графовую базу данных" },
  { id: "qdrant", title: "L3+L4: индекс эмбеддингов (Qdrant)", hint: "TextParagraph → mkg_chunks; Claim/Measurement/… → mkg_claims" },
  { id: "l4", title: "L4: глобальная HDBSCAN-кластеризация", hint: "Claim/Measurement → mkg_claims, cluster_id и is_anomaly по всему корпусу" },
];

/** Кнопки ↺ Перезапустить по этапам пайплайна */
const STAGE_RETRY = {
  ocr: { action: "reprocess", label: "↺ OCR", showOn: ["failed", "done"] },
  md: { action: "reprocess", label: "↺ OCR", showOn: ["done"] },
  layers: { action: "extract", label: "↺ Извлечение", showOn: ["failed", "done"] },
  graph: { action: "extract", label: "↺ Извлечение", showOn: ["failed", "done"] },
  neo4j: { action: "neo4j", label: "↺ Neo4j", showOn: ["failed", "done"] },
  qdrant: { action: "index", label: "↺ Индекс", showOn: ["failed", "done"] },
  l4: { action: "l4_cluster", label: "↺ Глоб. L4", showOn: ["failed", "done"] },
};

function isAnswersOnlyMode(doc) {
  return (doc?.processing_mode || "full") === "answers_only";
}

function isDocPipelineBusy(doc) {
  return doc && ["uploaded", "processing", "extracting"].includes(doc.status);
}

function needsFullGraphBuild(doc) {
  if (!doc || graphScope === "all") return false;
  return (doc.graph_nodes || 0) === 0 && !isDocPipelineBusy(doc);
}

const FULL_PIPELINE_STEPS = [
  { id: "ocr", label: "OCR и Markdown" },
  { id: "layers", label: "Извлечение слоёв L1–L6" },
  { id: "graph", label: "Граф знаний (узлы и связи)" },
  { id: "neo4j", label: "Синхронизация Neo4j" },
  { id: "qdrant", label: "Индекс L3+L4 в Qdrant" },
  { id: "l4", label: "Глобальная кластеризация L4" },
];

function renderFullPipelineStepsHtml(doc) {
  if (!doc) return "";
  const states = getDocPipelineStates(doc);
  const layersState = getLayersJourneyState(doc, null);
  return FULL_PIPELINE_STEPS.map((s) => {
    let state = states[s.id] || "pending";
    if (s.id === "layers") state = layersState;
    if (isAnswersOnlyMode(doc) && ["layers", "graph", "neo4j", "l4"].includes(s.id)) state = "skipped";
    return `<li class="${state}">${esc(s.label)}</li>`;
  }).join("");
}

function renderAnswersOnlyBanner(doc) {
  if (!doc || !isAnswersOnlyMode(doc) || isDocPipelineBusy(doc)) return "";
  const docId = doc.id || doc.document_id;
  const busy = doc.status === "extracting";
  return `<div class="pipeline-answers-banner">
    <p><strong>Документ загружен только для чата</strong> — слои L1–L6, граф и Neo4j не строились. Для карты знаний запустите полный пайплайн.</p>
    <button type="button" class="btn btn-primary btn-small" data-full-pipeline-doc="${esc(docId)}" ${busy ? "disabled" : ""}>↺ Построить полный граф</button>
  </div>`;
}

function isDocQdrantIndexed(doc) {
  if (!doc) return false;
  const docId = doc.id || doc.document_id;
  if (docId && indexedDocsSet.has(docId)) return true;
  const step = doc.step || "";
  if (step === "l4_done" || step === "answers_indexed") return true;
  return false;
}

function isQdrantIndexingInProgress(doc) {
  if (!doc) return false;
  const step = doc.step || "";
  return step === "qdrant_index" || step === "l4_cluster";
}

function docNeedsQdrantIndex(doc) {
  if (!doc || isDocQdrantIndexed(doc) || isQdrantIndexingInProgress(doc)) return false;
  if (isAnswersOnlyMode(doc)) {
    return ["md_ready", "loaded"].includes(doc.status);
  }
  return doc.status === "loaded" && (doc.graph_nodes || 0) > 0;
}

function renderQdrantPendingBanner(doc) {
  if (!docNeedsQdrantIndex(doc)) return "";
  const docId = doc.id || doc.document_id;
  const answersOnly = isAnswersOnlyMode(doc);
  const msg = answersOnly
    ? "Markdown готов — проиндексируйте фрагменты в Qdrant для семантического поиска в чате."
    : "Граф построен — индекс L3+L4 в Qdrant ещё не создан (или индексация прервалась).";
  return `<div class="pipeline-qdrant-banner">
    <p><strong>Индексировать в Qdrant?</strong> ${esc(msg)}</p>
    <button type="button" class="btn btn-primary btn-small" data-qdrant-index-doc="${esc(docId)}">⚡ Индексировать в Qdrant</button>
    <button type="button" class="btn btn-ghost btn-small" data-open-qdrant-tab>Открыть Qdrant</button>
  </div>`;
}

function bindQdrantPendingBanner(root = document) {
  root?.querySelectorAll("[data-qdrant-index-doc]").forEach((btn) => {
    if (btn.dataset.qdrantBannerBound) return;
    btn.dataset.qdrantBannerBound = "1";
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const docId = btn.dataset.qdrantIndexDoc;
      btn.disabled = true;
      indexEmbeddings(docId, { silent: false }).finally(() => {
        btn.disabled = false;
      });
    });
  });
  root?.querySelectorAll("[data-open-qdrant-tab]").forEach((btn) => {
    if (btn.dataset.qdrantTabBound) return;
    btn.dataset.qdrantTabBound = "1";
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      switchPage("qdrant");
    });
  });
}

const qdrantNotifyShown = new Set();

function notifyQdrantIndexed(docId, doc) {
  if (!docId || qdrantNotifyShown.has(docId)) return;
  qdrantNotifyShown.add(docId);
  const name = doc?.file_name || docId;
  const msg = isAnswersOnlyMode(doc)
    ? `«${name}» — фрагменты в Qdrant (режим чата)`
    : `«${name}» — документ в Qdrant (L3+L4)`;
  showQdrantToast(`${msg}. Откройте вкладку Qdrant для карты.`, { ms: 6500 });
  if (docId === selectedDoc) {
    refreshDocJourney(docId).catch(() => {});
    updateSearchBadge(docId);
  }
}

async function handleDocQdrantState(data, prevData) {
  const docId = data.document_id || data.id;
  if (!docId) return;

  if (isDocQdrantIndexed(data)) {
    if (!indexedDocsSet.has(docId)) {
      indexedDocsSet.add(docId);
      saveIndexedDocs();
    }
    if (prevData && !isDocQdrantIndexed(prevData)) {
      notifyQdrantIndexed(docId, data);
    }
    return;
  }

  if (isQdrantIndexingInProgress(data)) return;

  if (docNeedsQdrantIndex(data)) {
    await autoIndexAfterExtraction(docId, data);
  }
}

function updateGraphEmptyState(doc) {
  if (!els.graphsEmpty) return;
  const showArea = !els.graphsEmpty.classList.contains("hidden");
  if (!showArea) return;

  const data = doc || (graphScope === "doc" && selectedDoc
    ? docsListCache.find((d) => d.id === selectedDoc)
    : null);

  if (graphScope === "all") {
    if (els.graphEmptyTitle) els.graphEmptyTitle.textContent = "Нет документов с графом";
    if (els.graphEmptyDesc) {
      els.graphEmptyDesc.textContent = "Загрузите файл на вкладке «Документы» — полный пайплайн (OCR → граф → Neo4j → Qdrant) запустится автоматически.";
    }
    if (els.graphEmptySteps) els.graphEmptySteps.innerHTML = "";
    els.graphEmptyActionBtn?.classList.add("hidden");
    return;
  }

  if (!data) {
    if (els.graphEmptyTitle) els.graphEmptyTitle.textContent = "Граф ещё не построен";
    if (els.graphEmptyDesc) {
      els.graphEmptyDesc.textContent = "Выберите документ слева или загрузите файл.";
    }
    if (els.graphEmptySteps) els.graphEmptySteps.innerHTML = "";
    els.graphEmptyActionBtn?.classList.add("hidden");
    return;
  }

  const busy = isDocPipelineBusy(data);
  const answersOnly = isAnswersOnlyMode(data);

  if (answersOnly && needsFullGraphBuild(data)) {
    if (els.graphEmptyTitle) els.graphEmptyTitle.textContent = "Граф не построен";
    if (els.graphEmptyDesc) {
      els.graphEmptyDesc.textContent = "Документ загружен в режиме «только для ответов» — слои и Neo4j не строились. Нажмите кнопку ниже для полной обработки.";
    }
  } else if (needsFullGraphBuild(data)) {
    if (els.graphEmptyTitle) els.graphEmptyTitle.textContent = "Граф ещё не построен";
    if (els.graphEmptyDesc) {
      els.graphEmptyDesc.textContent = busy
        ? "Идёт обработка — граф появится после извлечения слоёв L1–L6."
        : "Markdown готов. Запустите извлечение, чтобы построить граф знаний.";
    }
  } else if (busy) {
    if (els.graphEmptyTitle) els.graphEmptyTitle.textContent = "Граф строится…";
    if (els.graphEmptyDesc) els.graphEmptyDesc.textContent = "Дождитесь завершения текущего этапа пайплайна.";
  }

  if (els.graphEmptySteps) {
    els.graphEmptySteps.innerHTML = renderFullPipelineStepsHtml(data);
  }

  const showAction = needsFullGraphBuild(data) && !busy;
  if (els.graphEmptyActionBtn) {
    els.graphEmptyActionBtn.classList.toggle("hidden", !showAction);
    els.graphEmptyActionBtn.textContent = answersOnly ? "↺ Построить полный граф" : "Построить граф";
    els.graphEmptyActionBtn.disabled = busy;
    els.graphEmptyActionBtn.dataset.docId = data.id || data.document_id || "";
  }
}

async function startFullPipeline(docId, btn) {
  if (!docId) return;
  const prev = btn?.textContent;
  if (btn) { btn.disabled = true; btn.textContent = "Запуск…"; }
  try {
    const r = await fetch(`${API}/documents/${encodeURIComponent(docId)}/reprocess-full`, { method: "POST" });
    if (!r.ok) {
      const data = await r.json().catch(() => ({}));
      throw new Error(data.detail || "Ошибка запуска");
    }
    pipelineQueue.add(docId);
    if (docId === selectedDoc) await openDoc(docId, { keepPage: true });
    else await renderDocsList();
  } catch (e) {
    if (btn) btn.title = e.message || "Ошибка";
    showBox(els.uploadError, e.message || "Не удалось запустить полный пайплайн");
  } finally {
    if (btn) { btn.disabled = false; if (prev) btn.textContent = prev; }
  }
}

function bindFullPipelineButtons(root = document) {
  root.querySelectorAll("[data-full-pipeline-doc]").forEach((btn) => {
    if (btn.dataset.fullPipelineBound) return;
    btn.dataset.fullPipelineBound = "1";
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      startFullPipeline(btn.dataset.fullPipelineDoc, btn);
    });
  });
}

function shouldShowStageRetry(stageId, state, doc) {
  if (!doc || state === "active" || state === "pending") return false;
  if (isAnswersOnlyMode(doc) && stageId === "graph" && state === "skipped") return true;
  if (state === "skipped") return false;
  const cfg = STAGE_RETRY[stageId];
  if (!cfg || !cfg.showOn.includes(state)) return false;
  if (isAnswersOnlyMode(doc) && ["layers", "neo4j", "l4"].includes(stageId)) return false;
  if (stageId === "md" && state !== "done") return false;
  if (stageId === "layers" && state === "done" && (doc.graph_nodes || 0) === 0) return false;
  if (stageId === "l4" && (doc.graph_nodes || 0) === 0) return false;
  return true;
}

function renderStageRetryBtn(docId, stageId, state, doc) {
  if (isAnswersOnlyMode(doc) && stageId === "graph" && state === "skipped") {
    return `<button type="button" class="btn btn-ghost btn-small journey-retry-btn" data-retry-doc="${esc(docId)}" data-retry-action="full" data-retry-stage="${esc(stageId)}" title="Полный пайплайн">↺ Полная обработка</button>`;
  }
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
  const qdrant = isDocQdrantIndexed(doc);
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
      if (isQdrantIndexingInProgress(doc)) {
        states.qdrant = "active";
      } else {
        states.qdrant = qdrant ? "done" : (neo && nodes > 0 ? "active" : "pending");
      }
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
    const retryAction = (isAnswersOnlyMode(doc) && s.id === "graph" && state === "skipped")
      ? "full"
      : (STAGE_RETRY[s.id]?.action || "");
    const retryLabel = retryAction === "full" ? "↺" : (STAGE_RETRY[s.id]?.label || "↺");
    const showGraphFull = isAnswersOnlyMode(doc) && s.id === "graph" && state === "skipped";
    const retry = showRetry && docId && (shouldShowStageRetry(s.id, state, doc) || showGraphFull)
      ? `<button type="button" class="doc-pipe-retry" data-retry-doc="${esc(docId)}" data-retry-action="${esc(retryAction)}" data-retry-stage="${esc(s.id)}" title="${showGraphFull ? "Полная обработка" : "Перезапустить"}">${esc(retryLabel)}</button>`
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

function renderRelChip(rel, { docId = null } = {}) {
  const layer = rel.layer || "L?";
  const from = rel.from || rel.from_ || "";
  const to = rel.to || "";
  const clickable = !!(from && to && rel.type);
  const docAttr = docId ? ` data-doc-id="${esc(docId)}"` : "";
  const clickCls = clickable ? " rel-chip-clickable" : "";
  const tag = clickable ? "button" : "span";
  const typeAttr = clickable ? ' type="button"' : "";
  return `<${tag}${typeAttr} class="rel-chip rel-chip-${esc(layer)}${clickCls}"${docAttr}${clickable ? ` data-from="${esc(from)}" data-to="${esc(to)}" data-type="${esc(rel.type)}"` : ""} title="${esc(rel.type)}"><span class="rel-from">${esc(rel.from_short)}</span><b>${esc(rel.type)}</b><span class="rel-to">${esc(rel.to_short)}</span></${tag}>`;
}

function renderJourneyRecentRels(rels, docId = null) {
  if (!rels?.length) return "";
  const chips = rels.slice(-8).map((rel) => renderRelChip(rel, { docId })).join("");
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
      ? `<div class="journey-layer-block"><h5>Слои L1–L6</h5>${renderJourneyLayerGrid(layers)}${doc.status === "extracting" ? renderJourneyRecentRels(layerPayload?.recent_relationships, docId) : ""}</div>`
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

  return `<div class="doc-journey-timeline">${renderAnswersOnlyBanner(doc)}${renderQdrantPendingBanner(doc)}${steps.join("")}</div>`;
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
  const isAll = graphScope === "all";
  const show = isInlineGraphPage() && (isAll || (graphScope === "doc" && doc));
  els.docWorkHeader?.classList.toggle("hidden", !show);
  if (!show) {
    window.MKGAuth?.syncDocsUploadFallback?.();
    return;
  }
  if (isAll) {
    if (els.docWorkTitle) els.docWorkTitle.textContent = "Все документы";
    if (els.docWorkBadge) {
      els.docWorkBadge.textContent = "граф";
      els.docWorkBadge.className = "badge s-search-ready";
    }
    if (els.docWorkMeta) {
      const n = docsWithGraph().length;
      els.docWorkMeta.textContent = n ? `${n} док. с графом` : "";
    }
  } else if (doc) {
    const label = statusLabel(doc);
    if (els.docWorkTitle) {
      const modeBadge = isAnswersOnlyMode(doc)
        ? ' <span class="doc-mode-badge">только чат</span>'
        : "";
      els.docWorkTitle.innerHTML = `${esc(doc.file_name || doc.document_id || doc.id)}${modeBadge}`;
    }
    if (els.docWorkBadge) {
      els.docWorkBadge.textContent = label.text;
      els.docWorkBadge.className = `badge ${label.cls}`;
    }
    if (els.docWorkMeta) {
      const step = doc.step ? stepLabel(doc.step) : "";
      els.docWorkMeta.textContent = step ? `Шаг: ${step}` : "";
    }
  }
  els.docWorkTabJourney?.classList.toggle("hidden", isAll);
  els.docWorkTabMd?.classList.toggle("hidden", isAll);
  window.MKGAuth?.syncDocsUploadFallback?.();
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

function setDocWorkTab(tab, { manual = false, skipGraphLoad = false } = {}) {
  if (!["journey", "md", "graph"].includes(tab)) tab = "journey";
  if (manual) docWorkTabManual = true;
  docWorkTab = tab;
  syncDocWorkTabUI(tab);
  if (tab === "graph" && !skipGraphLoad) {
    refreshGraphViewport({ fit: true, force: true });
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
    bindFullPipelineButtons(els.docJourneyContent);
    bindQdrantPendingBanner(els.docJourneyContent);
    bindRelChipClicks(els.docJourneyContent, docId);
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
  qdrant_index: "индекс L3+L4 в Qdrant",
  l4_cluster: "глобальная кластеризация L4",
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
let markdownRaw = "";
let markdownMarked = "";
let mdViewMode = "clean";
const ACTIVE_DOC_STATUSES = new Set(["uploaded", "processing", "extracting"]);
/** Документы, ожидающие автозапуск extraction после ingestion */
const pipelineQueue = new Set();
let graphLayerFilter = "all";
let highlightCrossLayer = false;
let graphAdvancedFilters = defaultGraphAdvancedFilters();
let lastQdrantSearchHits = [];
let qdrantPostFilters = defaultQdrantPostFilters();
let connectionFormationMode = false;
let connectionFormationStep = 0;
let connectionFormationTimer = null;
let multiDocCountByNodeId = new Map();
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
let graphViewsRenderTimer = null;
let graphViewportTimer = null;
const GRAPH_FILTER_DEBOUNCE_MS = 320;
const GRAPH_VIEWPORT_DEBOUNCE_MS = 320;
let embeddingStatusCache = null;
let graphViewDocId = null;
let graphVisible = false;
let docsListCache = [];
const WATCHLIST_STORAGE_KEY = "mkg_topic_watchlist";
const KNOWN_DOCS_STORAGE_KEY = "mkg_known_doc_ids";
const COMPARE_ENTITY_LABELS = new Set(["Process", "Material"]);
/** @type {Set<string>} */
let compareSelectedNodeIds = new Set();
let graphComparePanelOpen = false;
let docsTotalCount = 0;
let docsListFetchSeq = 0;
let docsListLoaded = false;
let selectedFiles = [];
let docStatusCache = new Map();
let indexedDocsSet = new Set(JSON.parse(localStorage.getItem("mkg_indexed_docs") || "[]"));
let lastLogsDocId = null;
let lastLogsKey = "";
let docGraphCountCache = new Map();
const GRAPH_CONTENT_HASH_LIMIT = 12000;

let nodeFieldHints = {};
let nodeFieldRequired = {};

async function loadNodeFieldHints() {
  try {
    const r = await fetch(`${API}/ontology/node-fields`);
    if (!r.ok) return;
    const data = await r.json();
    nodeFieldHints = {};
    nodeFieldRequired = {};
    for (const [label, spec] of Object.entries(data)) {
      if (Array.isArray(spec)) {
        nodeFieldHints[label] = spec;
        nodeFieldRequired[label] = spec;
      } else if (spec && typeof spec === "object") {
        nodeFieldHints[label] = spec.fields || [];
        nodeFieldRequired[label] = spec.required || spec.fields || [];
      }
    }
  } catch { /* ignore */ }
}

const L2_CONTEXT_LABELS = new Set(["Expert", "Organization", "Location", "Event", "Timeline", "Facility"]);
const L2_ENRICHMENT_FIELDS = new Set(["quote", "source_quote", "extraction_confidence", "organization", "role"]);

function isExpectedNodeField(label, key, props) {
  const hints = nodeFieldHints[label] || [];
  if (!hints.includes(key) || key === "id") return false;
  if (label === "Expert" && key === "name" && propHasValue(props.full_name)) return false;
  if (label === "Organization" && key === "name" && propHasValue(props.legal_name)) return false;
  if (L2_CONTEXT_LABELS.has(label) && L2_ENRICHMENT_FIELDS.has(key)) return false;
  const required = nodeFieldRequired[label];
  if (Array.isArray(required) && required.length) return required.includes(key);
  return hints.includes(key);
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
  let expectedCount = 0;
  const rows = ordered.map((key) => {
    const has = propHasValue(props[key]);
    const expected = isExpectedNodeField(label, key, props);
    if (expected) {
      expectedCount += 1;
      if (has) expectedFilled += 1;
    }
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

  const summary = expectedCount
    ? `<p class="detail-props-summary">Заполнено <b>${expectedFilled}/${expectedCount}</b> ожидаемых · всего полей <b>${actualKeys.length}</b></p>`
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
  fd.append("processing_mode", "full");
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
    else if (action === "full") url = `${API}/documents/${encodeURIComponent(docId)}/reprocess-full`;
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
    setMarkdownViews(data.markdown, data.markdown_raw || "", data.markdown_marked || data.markdown, false);
    return;
  }
  const stepHint = data.step ? ` · ${STEP_RU[data.step] || data.step}` : "";
  if (data.status === "processing") {
    setMarkdownViews(`OCR → Markdown${stepHint}…`, "", "", true);
  } else if (data.status === "uploaded") {
    setMarkdownViews("В очереди на обработку…", "", "", true);
  } else if (data.status === "extracting") {
    setMarkdownViews(`Извлечение графа${stepHint}…`, "", "", true);
  } else if (data.status === "failed") {
    setMarkdownViews(data.error ? `Ошибка: ${data.error}` : "Ошибка обработки.", "", "", true);
  } else if (data.status === "md_ready" || data.status === "loaded") {
    setMarkdownViews("Markdown пуст или ещё не сохранён.", "", "", true);
  } else {
    setMarkdownViews("Ожидание worker…", "", "", true);
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

  const prevEntry = docsListCache.find((d) => d.id === docId);
  const prevSnapshot = prevEntry ? { ...prevEntry } : (prevStatus ? { id: docId, status: prevStatus } : null);

  await handleDocQdrantState(data, prevSnapshot);

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

function sanitizeMarkdownHtml(html) {
  if (window.DOMPurify?.sanitize) {
    return window.DOMPurify.sanitize(html, { USE_PROFILES: { html: true } });
  }
  return String(html || "").replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, "");
}

function renderMarkdownHtml(text) {
  const src = stripMdComments(text || "").slice(0, 120000);
  if (!src.trim()) return "";
  let html;
  if (window.marked?.parse) {
    html = window.marked.parse(src, { breaks: true, gfm: true });
  } else {
    html = esc(src).replace(/\n/g, "<br>");
  }
  return sanitizeMarkdownHtml(html);
}

function setMdViewMode(mode) {
  mdViewMode = mode === "raw" ? "raw" : mode === "marked" ? "marked" : "clean";
  const isClean = mdViewMode === "clean";
  const isRaw = mdViewMode === "raw";
  const isMarked = mdViewMode === "marked";
  els.mdViewCleanBtn?.classList.toggle("active", isClean);
  els.mdViewRawBtn?.classList.toggle("active", isRaw);
  els.mdViewMarkedBtn?.classList.toggle("active", isMarked);
  els.mdInlineCleanBtn?.classList.toggle("active", isClean);
  els.mdInlineRawBtn?.classList.toggle("active", isRaw);
  els.mdInlineMarkedBtn?.classList.toggle("active", isMarked);
  els.previewMdRender?.classList.toggle("hidden", !isClean);
  els.previewMdRaw?.classList.toggle("hidden", !isRaw);
  els.previewMdSource?.classList.toggle("hidden", !isMarked);
  els.docMdInlineClean?.classList.toggle("hidden", !isClean);
  els.docMdInlineRaw?.classList.toggle("hidden", !isRaw);
  els.docMdInlineMarked?.classList.toggle("hidden", !isMarked);
}

function updateMarkdownPreview(isEmpty) {
  const renderEl = els.previewMdRender;
  const rawEl = els.previewMdRaw;
  const sourceEl = els.previewMdSource;
  const inlineClean = els.docMdInlineClean;
  const inlineRaw = els.docMdInlineRaw;
  const inlineMarked = els.docMdInlineMarked;

  const emptyText = markdownClean || "—";
  const cleanHtml = isEmpty || !markdownClean.trim()
    ? esc(emptyText)
    : renderMarkdownHtml(markdownClean);
  const rawText = isEmpty || !(markdownRaw || markdownClean).trim()
    ? emptyText
    : (markdownRaw || markdownClean).slice(0, 120000);
  const markedText = isEmpty || !(markdownMarked || markdownClean).trim()
    ? emptyText
    : (markdownMarked || markdownClean).slice(0, 120000);

  if (renderEl) {
    renderEl.innerHTML = cleanHtml;
    renderEl.className = `preview md-panel doc-md-panel md-render-view${isEmpty || !markdownClean.trim() ? " empty" : ""}`;
  }
  if (rawEl) {
    rawEl.textContent = rawText;
    rawEl.className = `preview md-panel doc-md-panel md-raw-view hidden${isEmpty ? " empty" : ""}`;
  }
  if (sourceEl) {
    sourceEl.textContent = markedText;
    sourceEl.className = `preview md-panel doc-md-panel md-source-view hidden${isEmpty ? " empty" : ""}`;
  }
  if (inlineClean) {
    inlineClean.innerHTML = cleanHtml;
    inlineClean.className = `preview md-panel doc-md-inline md-clean-view${isEmpty || !markdownClean.trim() ? " empty" : ""}`;
  }
  if (inlineRaw) {
    inlineRaw.textContent = rawText;
    inlineRaw.className = `preview md-panel doc-md-inline md-raw-view hidden${isEmpty ? " empty" : ""}`;
  }
  if (inlineMarked) {
    inlineMarked.textContent = markedText;
    inlineMarked.className = `preview md-panel doc-md-inline md-marked-view hidden${isEmpty ? " empty" : ""}`;
  }
  setMdViewMode(mdViewMode);
}

function setMarkdownViews(clean, raw, marked, isEmpty) {
  markdownClean = clean || "";
  markdownRaw = raw || "";
  markdownMarked = marked || clean || "";
  updateMarkdownPreview(isEmpty);
}

function downloadDocumentMd(variant) {
  if (!selectedDoc) return;
  const v = variant || mdViewMode;
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

function slugEntityName(name) {
  return String(name || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-zа-яё0-9]+/gi, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
}

function canonicalEntityKey(node) {
  const label = node?.label || "";
  if (!ENTITY_LABELS.has(label)) return null;
  const props = node.props || {};
  const id = String(node.id || "");
  let base = id;
  const colonIdx = id.indexOf(":");
  if (colonIdx > 0) {
    const prefix = id.slice(0, colonIdx);
    if (prefix.length >= 8 && (prefix.includes("-") || prefix.startsWith("doc_"))) {
      base = id.slice(colonIdx + 1);
    }
  }
  const name = props.name_en || props.name_ru || props.title_ru || "";
  if (name) return `${label}:${slugEntityName(name)}`;
  return `${label}:${base}`;
}

function buildMultiDocCountMap(nodes) {
  const byKey = new Map();
  const out = new Map();
  (nodes || []).forEach((n) => {
    const key = canonicalEntityKey(n);
    if (!key) return;
    const docId = n.props?.source_doc_id || n.props?.document_id || n.props?._doc_id || "";
    if (!byKey.has(key)) byKey.set(key, new Set());
    if (docId) byKey.get(key).add(docId);
  });
  (nodes || []).forEach((n) => {
    const key = canonicalEntityKey(n);
    const count = key ? (byKey.get(key)?.size || 0) : 0;
    const fromProps = Number(n.props?.multi_doc_count || 0);
    const total = Math.max(count, fromProps);
    if (total >= 2) out.set(n.id, total);
  });
  return out;
}

function annotateGraphNodes(nodes, primaryLayer) {
  return (nodes || []).map((n) => {
    const layer = layerOf(n.label);
    const multiDoc = multiDocCountByNodeId.get(n.id) || 0;
    const isPrimary = !primaryLayer || primaryLayer === "all" || layer === primaryLayer;
    const isGhost = primaryLayer && primaryLayer !== "all" && !isPrimary;
    return {
      ...n,
      _ghost: isGhost,
      _primary: isPrimary,
      _multiDoc: multiDoc,
    };
  });
}

function stopConnectionFormationTimer() {
  if (connectionFormationTimer) {
    clearInterval(connectionFormationTimer);
    connectionFormationTimer = null;
  }
}

function renderConnectionFormationTimeline() {
  const el = els.connectionFormationTimeline;
  if (!el) return;
  if (!connectionFormationMode) {
    el.classList.add("hidden");
    el.innerHTML = "";
    return;
  }
  el.classList.remove("hidden");
  el.innerHTML = FORMATION_LAYERS.map((layer, idx) => {
    const step = idx + 1;
    const cls = step < connectionFormationStep
      ? "formation-step done"
      : step === connectionFormationStep
        ? "formation-step active"
        : "formation-step";
    return `<span class="${cls}" data-step="${step}">${esc(FORMATION_LAYER_LABELS[layer] || layer)}</span>`;
  }).join("");
}

function startConnectionFormationPlayback() {
  stopConnectionFormationTimer();
  connectionFormationStep = 1;
  renderConnectionFormationTimeline();
  scheduleGraphViewsRender();
  connectionFormationTimer = setInterval(() => {
    if (connectionFormationStep >= FORMATION_LAYERS.length) {
      stopConnectionFormationTimer();
      return;
    }
    connectionFormationStep += 1;
    renderConnectionFormationTimeline();
    resetGraphNetwork();
    scheduleGraphViewsRender();
  }, FORMATION_STEP_MS);
}

function toggleConnectionFormationMode() {
  connectionFormationMode = !connectionFormationMode;
  if (connectionFormationMode) {
    graphLayerFilter = "all";
    highlightCrossLayer = true;
    graphDensityMode = "full";
    updateDensityToggleUI();
  } else {
    stopConnectionFormationTimer();
    connectionFormationStep = 0;
  }
  els.connectionFormationBtn?.classList.toggle("active", connectionFormationMode);
  els.crossLayerToggle?.classList.toggle("active", highlightCrossLayer);
  renderConnectionFormationTimeline();
  if (connectionFormationMode) startConnectionFormationPlayback();
  else scheduleGraphViewsRender();
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
  const ready = isDocQdrantIndexed(docsListCache.find((x) => x.id === docId) || { id: docId });
  els.docPageMeta.textContent = `${nodes} узл · ${rels} св · ${cross} межсл. · Qdrant: ${ready ? "да" : "нет"}`;
}

function updateSearchBadge(docId) {
  updatePreviewMeta(docId);
}

function countCorpusQdrantIndexed() {
  return docsListCache.filter((d) => isDocQdrantIndexed(d)).length;
}

function getCorpusDocTotal() {
  if (docsTotalCount > 0) return docsTotalCount;
  return docsListCache.length;
}

function formatEmbeddingStatus(data) {
  if (!data) return "Эмбеддинги: недоступны";
  const chunks = data.l3_points ?? data.collections?.mkg_chunks?.points ?? 0;
  const claims = data.l4_points ?? data.collections?.mkg_claims?.points ?? 0;
  const total = data.total_points ?? chunks + claims;
  const qdrant = data.qdrant_ok !== false ? "OK" : "недоступен";
  const yandex = data.yandex_configured ? "настроен" : "не настроен";
  const docTotal = getCorpusDocTotal();
  const indexedDocs = countCorpusQdrantIndexed();
  const docPart = docTotal > 0 ? `${indexedDocs}/${docTotal} док. · ` : "";
  return `Qdrant ${qdrant} · ${docPart}${total} точек (L3 chunks ${chunks}, L4 claims ${claims}) · Yandex ${yandex}`;
}

function formatQdrantInfo(data) {
  if (!data) return "";
  const lines = [
    `Qdrant: ${data.qdrant_url}${data.qdrant_ok === false ? " (недоступен)" : ""}`,
    `Размер вектора: ${data.vector_size}`,
    `Yandex: ${data.yandex_configured ? "ключ настроен" : "ключ не задан — индексация недоступна, визуализация из Qdrant работает"}`,
  ];
  Object.entries(data.collections || {}).forEach(([name, c]) => {
    lines.push(`${name}: ${c.points} точек — ${c.purpose}`);
  });
  return lines.join("\n");
}

function qdrantRetryHtml(label, action) {
  return `<p class="muted">${esc(label)} <button type="button" class="btn btn-ghost btn-small qdrant-retry-btn" data-retry="${esc(action)}">Повторить</button></p>`;
}

function normalizeDocId(docId) {
  if (!docId) return docId;
  if (docId.startsWith("doc_") && !docId.includes(":")) return `doc:${docId.slice(4)}`;
  return docId;
}

function bindQdrantRetry(container) {
  container?.querySelectorAll(".qdrant-retry-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.retry;
      if (action === "status") refreshEmbeddingStatus();
      else if (action === "viz") loadQdrantClusterMap();
      else if (action === "points") loadQdrantPoints();
    });
  });
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
  const data = embeddingStatusCache;
  if (!data) {
    els.l3Stats.innerHTML = '<p class="muted">Статистика корпуса — загрузка…</p>';
    return;
  }
  const chunks = data.l3_points ?? data.collections?.mkg_chunks?.points ?? 0;
  const claims = data.l4_points ?? data.collections?.mkg_claims?.points ?? 0;
  const indexedCount = countCorpusQdrantIndexed();
  const totalCount = getCorpusDocTotal();
  els.l3Stats.innerHTML = `
    <div class="l3-stat"><span class="l3-stat-val">${chunks}</span><span class="l3-stat-label">L3</span></div>
    <div class="l3-stat"><span class="l3-stat-val">${claims}</span><span class="l3-stat-label">L4</span></div>
    <div class="l3-stat"><span class="l3-stat-val">${indexedCount} / ${totalCount}</span><span class="l3-stat-label">документов в Qdrant</span></div>`;
}

async function refreshEmbeddingStatus() {
  let statusOk = false;
  try {
    const r = await fetch(`${AGENT_API}/embeddings/status`);
    if (r.ok) {
      embeddingStatusCache = await r.json();
      statusOk = true;
      const line = formatEmbeddingStatus(embeddingStatusCache);
      if (els.l3EmbeddingStatus) els.l3EmbeddingStatus.textContent = line;
      if (els.l3QdrantInfo) els.l3QdrantInfo.textContent = formatQdrantInfo(embeddingStatusCache);
    } else {
      const err = await r.json().catch(() => ({}));
      const msg = err.detail || `HTTP ${r.status}`;
      if (els.l3EmbeddingStatus) {
        els.l3EmbeddingStatus.innerHTML = qdrantRetryHtml(`Статус эмбеддингов: ${msg}`, "status");
        bindQdrantRetry(els.l3EmbeddingStatus);
      }
    }
  } catch (e) {
    if (els.l3EmbeddingStatus) {
      els.l3EmbeddingStatus.innerHTML = qdrantRetryHtml(`Статус недоступен: ${e.message}`, "status");
      bindQdrantRetry(els.l3EmbeddingStatus);
    }
    if (els.l3QdrantInfo) els.l3QdrantInfo.textContent = "";
  }
  renderL3Stats();
  if (currentPage === "qdrant") {
    loadQdrantClusterMap();
    loadQdrantPoints();
  }
  return statusOk;
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
      if (!silent && docId === selectedDoc) {
        showQdrantToast(`Документ в Qdrant: +${data.indexed ?? 0} точек (L3 ${data.indexed_l3 ?? "?"}, L4 ${data.indexed_l4 ?? "?"}).`);
      }
    }
    if (docId === selectedDoc) updateSearchBadge(docId);
    if (!silent) {
      const l3 = data.indexed_l3 ?? data.collections?.mkg_chunks ?? "?";
      const l4 = data.indexed_l4 ?? data.collections?.mkg_claims ?? "?";
      appendQdrantLog(`Индексация L3+L4: +${data.indexed ?? 0} (L3 ${l3}, L4 ${l4}), пропущено ${data.skipped ?? 0}`);
    }
    await refreshEmbeddingStatus();
    await loadQdrantPoints();
    qdrantClusterAutoDone = false;
    await loadQdrantClusterMap();
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

async function autoIndexAfterExtraction(docId, doc = null) {
  if (!docId || isDocQdrantIndexed(doc || { id: docId })) return;
  if (isQdrantIndexingInProgress(doc || {})) return;
  const result = await indexEmbeddings(docId, { silent: true });
  if (result && ((result.indexed ?? 0) > 0 || !result.error)) {
    notifyQdrantIndexed(docId, doc || docsListCache.find((d) => d.id === docId));
  } else if (docNeedsQdrantIndex(doc || docsListCache.find((d) => d.id === docId) || {})) {
    showQdrantToast("Индексация Qdrant не завершена — нажмите «Индексировать в Qdrant» в карточке документа.", { error: true, ms: 7000 });
  }
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
  if (!query?.trim() || !targetEl) return;
  targetEl.innerHTML = '<p class="muted">Поиск…</p>';
  try {
    const r = await fetch(`${AGENT_API}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query.trim(), limit: 15, mode: "auto" }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Ошибка поиска");
    lastQdrantSearchHits = data.hits || [];
    renderQdrantSearchResults(targetEl, { showDoc: true, mode: data.mode });
  } catch (e) {
    lastQdrantSearchHits = [];
    targetEl.innerHTML = `<p class="muted">${esc(e.message)}</p>`;
  }
}

function filterQdrantHitsByKeyword(hits, keyword) {
  const q = (keyword || "").trim().toLowerCase();
  if (!q) return hits;
  return (hits || []).filter((hit) => {
    const text = [hit.text, hit.label, hit.node_id, hit.document_id]
      .filter(Boolean).join(" ").toLowerCase();
    return text.includes(q);
  });
}

function applyQdrantPostFilters(hits) {
  const f = qdrantPostFilters;
  return (hits || []).filter((hit) => {
    if (f.layers?.length && !f.layers.includes(hit.layer)) return false;
    if (f.minConfidence > 0) {
      const score = hit.score != null ? (hit.score <= 1 ? hit.score : hit.score / 100) : 0;
      if (score < f.minConfidence) return false;
    }
    if (f.docTypes?.length) {
      const d = docsListCache.find((x) => x.id === hit.document_id);
      const cat = inferDocCategory(d || { file_name: hit.document_id || "" });
      if (!f.docTypes.includes(cat)) return false;
    }
    return true;
  });
}

const QDRANT_FILTER_CHIP_DEFS = [
  { group: "docTypes", id: "patent", label: "Патент" },
  { group: "docTypes", id: "article", label: "Статья" },
  { group: "docTypes", id: "report", label: "Отчёт" },
  { group: "docTypes", id: "handbook", label: "Справочник" },
  { group: "layers", id: "L3", label: "L3" },
  { group: "layers", id: "L4", label: "L4" },
  { group: "minConfidence", id: "0.5", label: "≥50%" },
  { group: "minConfidence", id: "0.7", label: "≥70%" },
  { group: "minConfidence", id: "0.85", label: "≥85%" },
];

function renderQdrantFilterChips() {
  const root = els.qdrantFilterChips;
  if (!root) return;
  root.innerHTML = QDRANT_FILTER_CHIP_DEFS.map((chip) => {
    const active = chip.group === "minConfidence"
      ? qdrantPostFilters.minConfidence === Number(chip.id)
      : (qdrantPostFilters[chip.group] || []).includes(chip.id);
    return `<button type="button" class="layer-chip qdrant-filter-chip${active ? " active" : ""}"
      data-qf-group="${esc(chip.group)}" data-qf-id="${esc(chip.id)}">${esc(chip.label)}</button>`;
  }).join("");
  root.querySelectorAll(".qdrant-filter-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      const group = btn.dataset.qfGroup;
      const id = btn.dataset.qfId;
      if (group === "minConfidence") {
        const val = Number(id);
        qdrantPostFilters.minConfidence = qdrantPostFilters.minConfidence === val ? 0 : val;
      } else {
        const arr = qdrantPostFilters[group] || [];
        const idx = arr.indexOf(id);
        if (idx >= 0) arr.splice(idx, 1);
        else arr.push(id);
        qdrantPostFilters[group] = arr;
      }
      renderQdrantFilterChips();
      renderQdrantSearchResults(els.qdrantSearchResults, { showDoc: true });
    });
  });
}

function initQdrantPostFilters() {
  qdrantPostFilters = defaultQdrantPostFilters();
  renderQdrantFilterChips();
}

function renderQdrantSearchResults(targetEl, opts = {}) {
  const keyword = els.qdrantSearchKeyword?.value || "";
  let hits = applyQdrantPostFilters(lastQdrantSearchHits);
  hits = filterQdrantHitsByKeyword(hits, keyword);
  if (els.qdrantSearchMeta) {
    const total = lastQdrantSearchHits.length;
    const mode = opts.mode ? ` · режим: ${opts.mode}` : "";
    const filtered = hits.length !== total;
    const suffix = filtered ? ` · после фильтра: ${hits.length}` : "";
    els.qdrantSearchMeta.textContent = `весь корпус${mode} · ${total} результатов${suffix}`;
  }
  renderSearchHits(hits, targetEl, opts);
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
        if (els.detailTitle) els.detailTitle.textContent = "Узел";
        els.detailBody.classList.remove("has-split");
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

async function loadQdrantPoints() {
  if (!els.qdrantPointsList) {
    if (els.qdrantPointsCount) els.qdrantPointsCount.textContent = "(0)";
    return;
  }
  try {
    const r = await fetch(`${AGENT_API}/embeddings/points/all?limit=200`);
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      const msg = err.detail || `HTTP ${r.status}`;
      els.qdrantPointsList.innerHTML = qdrantRetryHtml(`Точки недоступны: ${msg}`, "points");
      bindQdrantRetry(els.qdrantPointsList);
      if (els.qdrantPointsCount) els.qdrantPointsCount.textContent = "(0)";
      return;
    }
    const data = await r.json();
    if (els.qdrantPointsCount) els.qdrantPointsCount.textContent = `(${data.total})`;
    if (!data.points?.length) {
      els.qdrantPointsList.innerHTML = '<p class="muted">Нет точек в Qdrant — проиндексируйте документы.</p>';
      return;
    }
    els.qdrantPointsList.innerHTML = data.points.map((p) => `
      <div class="qdrant-point-row" data-point-id="${esc(p.point_id)}" data-node-id="${esc(p.node_id || "")}" data-doc-id="${esc(p.document_id || "")}">
        <span class="qp-layer" style="background:${LAYER_COLOR[p.layer] || LAYER_COLOR["L?"]}">${esc(p.layer || "?")}</span>
        <span class="qp-label">${esc(p.label || "?")}</span>
        ${p.document_id ? `<span class="qp-doc muted">${esc(docName(p.document_id))}</span>` : ""}
        <code class="qp-id">${esc(p.node_id || p.point_id)}</code>
        <span class="qp-coll muted">${esc(p.collection)}</span>
        ${p.cluster_id != null ? `<span class="qp-cluster muted">${p.cluster_name ? esc(p.cluster_name) : `c${esc(String(p.cluster_id))}`}</span>` : ""}
        ${p.is_anomaly ? '<span class="qp-anomaly muted">anomaly</span>' : ""}
        <p class="qp-text">${esc(p.text || "")}</p>
      </div>`).join("");
    els.qdrantPointsList.querySelectorAll(".qdrant-point-row").forEach((row) => {
      row.addEventListener("click", () => {
        highlightQdrantPoint(row.dataset.pointId, { scroll: false });
        const p = qdrantVizPoints.find((pt) => pt.id === row.dataset.pointId || pt.node_id === row.dataset.nodeId);
        openQdrantPointDetail(p || {
          node_id: row.dataset.nodeId,
          neo4j_node_id: row.dataset.nodeId,
          text: row.querySelector(".qp-text")?.textContent || "",
        });
      });
    });
  } catch (e) {
    els.qdrantPointsList.innerHTML = qdrantRetryHtml(`Ошибка загрузки точек: ${e.message}`, "points");
    bindQdrantRetry(els.qdrantPointsList);
  }

  function docName(docId) {
    const d = docsListCache.find((x) => x.id === docId);
    return d?.file_name || docId;
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
      const chips = grouped[layer].map((rel) => renderRelChip(rel, { docId: selectedDoc })).join("");
      return `<div class="live-rel-group"><span class="lp-mini-badge l-${layer}">${layer}</span>${chips}</div>`;
    }).join("");
  bindRelChipClicks(els.liveRels, selectedDoc);
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
  if (isInlineGraph) {
    const headerDoc = graphScope === "all"
      ? { id: GRAPH_ALL_ID }
      : docsListCache.find((d) => d.id === selectedDoc);
    updateDocWorkHeader(headerDoc);
  } else {
    els.docWorkHeader?.classList.add("hidden");
  }

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

  const headerDoc = graphScope === "doc" && selectedDoc
    ? docsListCache.find((d) => d.id === selectedDoc)
    : null;
  updateGraphEmptyState(headerDoc);
}

function isDocGraphLive(docId) {
  if (!docId || docId === GRAPH_ALL_ID) return false;
  const st = docStatusCache.get(docId)
    || docsListCache.find((d) => d.id === docId)?.status;
  return ACTIVE_DOC_STATUSES.has(st) || st === "extracting";
}

function shouldRefreshGraphData(docId) {
  if (!docId) return false;
  if (docId !== lastGraphDocId || !visNetwork) return true;
  if (docId === GRAPH_ALL_ID) return false;
  return isDocGraphLive(docId);
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
      if (shouldRefreshGraphData(docId)) {
        loadGraph(docId, { silent: true });
      }
    }
  }
}

function renderDocCard(d) {
  const st = statusLabel(d);
  const typeHint = d.doc_type ? ` · ${d.doc_type}` : "";
  const isLive = ["uploaded", "processing", "extracting"].includes(d.status);
  const modeBadge = isAnswersOnlyMode(d)
    ? '<span class="doc-mode-badge" title="Загружен только для чата — граф не строился">только чат</span>'
    : "";
  return `
    <div class="doc ${selectedDoc === d.id ? "active" : ""} ${isLive ? "doc-live" : ""}" data-id="${esc(d.id)}" role="button">
      <div class="doc-name">${esc(d.file_name)}${modeBadge}</div>
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
        refreshGraphViewport({ fit: true, force: true });
        renderDocsList();
        return;
      }
      openDoc(id, { switchTo: "doc" });
    });
  });
}

async function maybeAutoClusterL4(points) {
  if (qdrantClusterAutoPending || qdrantClusterAutoDone) return false;
  const l4 = (points || []).filter((p) => p.layer === "L4");
  if (!l4.length) return false;
  const needsCluster = l4.some((p) => p.cluster_id == null);
  if (!needsCluster) return false;
  qdrantClusterAutoPending = true;
  try {
    appendQdrantLog("Авто-кластеризация L4 (HDBSCAN)…");
    const ok = await runL4Clustering({ silent: true, skipReload: true });
    if (ok) qdrantClusterAutoDone = true;
    return ok;
  } finally {
    qdrantClusterAutoPending = false;
  }
}

function isQdrantL4Anomaly(p) {
  return p.layer === "L4" && (p.cluster_id === -1 || p.is_anomaly || Number(p.cluster_id) < 0);
}

function filterQdrantVizL4(points) {
  return (points || []).filter((p) => p.layer === "L4");
}

function showQdrantToast(message, { error = false, ms = 4500 } = {}) {
  if (!els.qdrantToast) {
    if (els.qdrantIndexLog) els.qdrantIndexLog.textContent = message;
    return;
  }
  els.qdrantToast.textContent = message;
  els.qdrantToast.classList.toggle("qdrant-toast-error", !!error);
  els.qdrantToast.classList.remove("hidden");
  clearTimeout(showQdrantToast._t);
  showQdrantToast._t = setTimeout(() => {
    els.qdrantToast?.classList.add("hidden");
  }, ms);
}


function openSideDetailPanel(title, mainHtml, sideHtml) {
  if (els.detailTitle) els.detailTitle.textContent = title;
  els.detailBody.classList.add("has-split");
  els.detailBody.innerHTML = `
    <div class="detail-body-split">
      <div class="detail-body-main">${mainHtml}</div>
      <div class="detail-body-side">${sideHtml}</div>
    </div>`;
  els.detailPanel.classList.remove("hidden");
  els.appRoot.classList.add("has-detail");
}

function nodeTextPreview(node, limit = 200) {
  if (!node) return "";
  const props = node.props || {};
  for (const key of ["text", "quote", "name", "title", "value", "name_ru", "name_en"]) {
    const val = props[key];
    if (typeof val === "string" && val.trim()) {
      const text = val.trim().replace(/\n/g, " ");
      return text.length > limit ? `${text.slice(0, limit - 1)}…` : text;
    }
  }
  return "";
}

function renderRelNodeCard(node, roleLabel) {
  if (!node) {
    return `<div class="rel-node-card rel-node-missing"><h4 class="detail-section-title">${esc(roleLabel)}</h4><p class="muted">Узел не найден в графе</p></div>`;
  }
  const layer = layerOf(node.label);
  const preview = nodeTextPreview(node);
  return `
    <div class="rel-node-card">
      <h4 class="detail-section-title">${esc(roleLabel)}</h4>
      <span class="detail-layer" style="background:${LAYER_COLOR[layer] || LAYER_COLOR["L?"]}">${esc(layer)} · ${esc(node.label)}</span>
      <div class="detail-id">${esc(node.id)}</div>
      ${preview ? `<p class="rel-node-preview">${esc(preview)}</p>` : ""}
      <button type="button" class="btn btn-ghost btn-small rel-open-node-btn" data-node-id="${esc(node.id)}">Открыть узел</button>
    </div>`;
}

function renderRelPropsBlock(props) {
  const keys = Object.keys(props || {}).filter((k) => propHasValue(props[k]));
  if (!keys.length) return '<p class="muted small">Свойства связи не заданы</p>';
  return `<dl class="detail-props detail-props-compact">${keys.map((k) =>
    `<div class="prop-row prop-ok"><dt>${esc(k)}</dt><dd>${formatPropValue(props[k])}</dd></div>`,
  ).join("")}</dl>`;
}

function renderRelatedEdgesList(edges, emptyLabel) {
  if (!edges?.length) return `<p class="muted small">${esc(emptyLabel)}</p>`;
  return `<ul class="rel-detail-related">${edges.map((e) => {
    const from = e.from || e.from_ || "?";
    const to = e.to || "?";
    return `<li><button type="button" class="rel-related-edge-btn" data-from="${esc(from)}" data-to="${esc(to)}" data-type="${esc(e.type || "?")}"><code>${esc(e.type || "?")}</code> · ${esc(from)} → ${esc(to)}</button></li>`;
  }).join("")}</ul>`;
}

function findRelationshipInGraph(from, to, type) {
  return graphData.relationships.find((r) => {
    const start = r.from || r.from_;
    return start === from && r.to === to && r.type === type;
  }) || null;
}

function findNodeInGraph(nodeId) {
  return graphData.nodes.find((n) => n.id === nodeId) || null;
}

function buildRelationshipDetailFromGraph(from, to, type) {
  const rel = findRelationshipInGraph(from, to, type);
  if (!rel) return null;
  const source = findNodeInGraph(from);
  const target = findNodeInGraph(to);
  const related = graphData.relationships.filter((r) => {
    const start = r.from || r.from_;
    const end = r.to;
    if (start === from && end === to && r.type === type) return false;
    return start === from || end === from || start === to || end === to;
  }).slice(0, 12);
  return {
    type,
    from,
    to,
    props: rel.props || {},
    layer: source ? layerOf(source.label) : "L?",
    description: REL_TYPE_HINTS[type] || `Связь типа ${type}`,
    source_node: source,
    target_node: target,
    related_edges: related,
  };
}

function highlightGraphEdge(from, to, type) {
  if (!visNetwork || !visEdgesDataSet) return;
  const edges = visEdgesDataSet.get({
    filter: (e) => e.from === from && e.to === to && (!type || e.title === type),
  });
  if (!edges.length) return;
  visNetwork.selectNodes([from, to]);
  visNetwork.selectEdges([edges[0].id]);
  try {
    visNetwork.focus(from, { scale: 1.15, animation: { duration: 400, easingFunction: "easeInOutQuad" } });
  } catch { /* ignore focus errors on hidden graph */ }
}

function clearGraphEdgeHighlight() {
  if (!visNetwork) return;
  visNetwork.unselectAll();
}

function bindRelDetailActions(root, docId) {
  root?.querySelectorAll(".rel-open-node-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const node = findNodeInGraph(btn.dataset.nodeId);
      if (node) openDetailPanel(node);
    });
  });
  root?.querySelectorAll(".rel-related-edge-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      openRelationshipDetail({
        from: btn.dataset.from,
        to: btn.dataset.to,
        type: btn.dataset.type,
        docId,
      });
    });
  });
}

function bindRelChipClicks(root = document, docId = null) {
  const resolvedDocId = docId || selectedDoc;
  root?.querySelectorAll(".rel-chip-clickable").forEach((btn) => {
    btn.addEventListener("click", () => {
      openRelationshipDetail({
        from: btn.dataset.from,
        to: btn.dataset.to,
        type: btn.dataset.type,
        docId: btn.dataset.docId || resolvedDocId,
      });
    });
  });
}

const REL_TYPE_HINTS = {
  STRUCTURING: "Заголовок раздела структурирует абзац текста (иерархия документа L3).",
  TAGGED_WITH: "Абзац помечен языковым или типографским контекстом.",
  NEXT_PARAGRAPH: "Последовательный переход к следующему абзацу в тексте.",
  HAS_PARAGRAPH: "Документ содержит абзац текста.",
  CONTEXT_FOR: "Текст или таблица даёт контекст для сущности другого слоя.",
  DATA_SOURCE_FOR: "Фрагмент текста — источник данных для факта или измерения.",
  ABOUT: "Фрагмент текста описывает технологическое решение (L6).",
  WRITES_LOG: "Статус верификации фиксируется в журнале аудита (L5).",
  GOVERNED_BY: "Документ регулируется ролью безопасности.",
  USES_MAT: "Стадия или опыт использует материал.",
  PRODUCED_MEASURE: "Стадия или опыт породил измерение.",
  SHOWED_EFFECT: "Эксперимент или стадия показала эффект.",
};

function canEditGraphRelations() {
  const role = window.MKGAuth?.getRole?.();
  const id = role?.id || "";
  return id === "admin" || id === "engineer";
}

function renderExpertEditBlock(data, docId) {
  if (!canEditGraphRelations() || !docId || docId === GRAPH_ALL_ID) return "";
  const existing = (data.props || {}).expert_comment || "";
  const editor = (data.props || {}).edited_by || "";
  const editedAt = (data.props || {}).edited_at || "";
  const meta = editor ? `<p class="muted small">Последнее: ${esc(editor)}${editedAt ? ` · ${esc(editedAt)}` : ""}</p>` : "";
  return `
    <div class="rel-expert-edit" data-rel-from="${esc(data.from)}" data-rel-to="${esc(data.to)}" data-rel-type="${esc(data.type)}" data-doc-id="${esc(docId)}">
      <h4 class="detail-section-title">Комментарий эксперта</h4>
      ${meta}
      <textarea class="rel-expert-textarea" rows="3" placeholder="Уточнение связи, аудит…">${esc(existing)}</textarea>
      <div class="rel-expert-actions">
        <button type="button" class="btn btn-primary btn-small rel-expert-save-btn">Сохранить</button>
        <span class="rel-expert-status muted small"></span>
      </div>
    </div>`;
}

function bindExpertEditActions(root, docId) {
  root?.querySelectorAll(".rel-expert-edit").forEach((block) => {
    block.querySelector(".rel-expert-save-btn")?.addEventListener("click", async () => {
      const from = block.dataset.relFrom;
      const to = block.dataset.relTo;
      const type = block.dataset.relType;
      const resolvedDoc = block.dataset.docId || docId;
      const textarea = block.querySelector(".rel-expert-textarea");
      const statusEl = block.querySelector(".rel-expert-status");
      const comment = (textarea?.value || "").trim();
      if (!comment) {
        if (statusEl) statusEl.textContent = "Введите комментарий";
        return;
      }
      const role = window.MKGAuth?.getRole?.() || {};
      const user = window.MKGAuth?.getCurrentUser?.() || {};
      if (statusEl) statusEl.textContent = "Сохранение…";
      try {
        const qs = new URLSearchParams({ from, to, type });
        const r = await fetch(`${API}/graph/documents/${encodeURIComponent(resolvedDoc)}/relationship?${qs}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            expert_comment: comment,
            edited_by: user.display_name || role.name_ru || role.id || "expert",
            role_id: role.id || "engineer",
          }),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
        const rel = findRelationshipInGraph(from, to, type);
        if (rel) rel.props = { ...(rel.props || {}), ...(data.props || {}) };
        if (statusEl) statusEl.textContent = "Сохранено";
        showQdrantToast("Комментарий эксперта сохранён");
      } catch (e) {
        if (statusEl) statusEl.textContent = e.message || "Ошибка";
      }
    });
  });
}

function toggleGraphComparePanel() {
  graphComparePanelOpen = !graphComparePanelOpen;
  els.graphComparePanel?.classList.toggle("hidden", !graphComparePanelOpen);
  els.graphCompareBtn?.classList.toggle("active", graphComparePanelOpen);
  if (graphComparePanelOpen) renderCompareSelectedChips();
}

function renderCompareSelectedChips() {
  if (!els.graphCompareSelected) return;
  if (!compareSelectedNodeIds.size) {
    els.graphCompareSelected.innerHTML = '<p class="muted small">Ctrl+клик по Process/Material на графе (до 3).</p>';
    return;
  }
  els.graphCompareSelected.innerHTML = [...compareSelectedNodeIds].map((id) => {
    const node = findNodeInGraph(id);
    const name = node?.props?.name_ru || node?.props?.name_en || node?.props?.name || id;
    return `<span class="graph-compare-chip">${esc(node?.label || "?")}: ${esc(name)}</span>`;
  }).join("");
}

function toggleCompareNodeSelection(node, { multi = false } = {}) {
  if (!node || !COMPARE_ENTITY_LABELS.has(node.label)) return;
  if (!multi) compareSelectedNodeIds.clear();
  if (compareSelectedNodeIds.has(node.id)) compareSelectedNodeIds.delete(node.id);
  else if (compareSelectedNodeIds.size < 3) compareSelectedNodeIds.add(node.id);
  renderCompareSelectedChips();
  if (graphComparePanelOpen) renderCompareTable();
}

function measurementsNearEntity(nodeId, maxDepth = 3) {
  const out = [];
  const visited = new Set([nodeId]);
  let frontier = [nodeId];
  for (let depth = 0; depth < maxDepth && frontier.length; depth++) {
    const next = [];
    for (const nid of frontier) {
      for (const rel of graphData.relationships) {
        const from = rel.from || rel.from_;
        const to = rel.to;
        let other = null;
        if (from === nid) other = to;
        else if (to === nid) other = from;
        else continue;
        if (visited.has(other)) continue;
        visited.add(other);
        const n = findNodeInGraph(other);
        if (n?.label === "Measurement") {
          out.push(n);
        }
        next.push(other);
      }
    }
    frontier = next;
  }
  return out;
}

function renderCompareTable() {
  if (!els.graphCompareTableWrap) return;
  const ids = [...compareSelectedNodeIds];
  if (ids.length < 2) {
    els.graphCompareTableWrap.innerHTML = '<p class="muted small">Выберите минимум 2 узла Process или Material.</p>';
    return;
  }
  const paramSet = new Set();
  const columns = ids.map((id) => {
    const node = findNodeInGraph(id);
    const name = node?.props?.name_ru || node?.props?.name_en || node?.props?.name || id;
    const measurements = measurementsNearEntity(id);
    const byParam = {};
    measurements.forEach((m) => {
      const props = m.props || {};
      const param = String(props.parameter || props.name || "value").trim() || "value";
      paramSet.add(param);
      const val = props.numeric_value ?? props.value ?? props.concentration ?? props.temperature ?? "—";
      const unit = props.unit || "";
      byParam[param] = `${val}${unit ? ` ${unit}` : ""}`;
    });
    return { id, name, label: node?.label || "?", byParam };
  });
  const params = [...paramSet].sort((a, b) => a.localeCompare(b, "ru"));
  if (!params.length) {
    els.graphCompareTableWrap.innerHTML = '<p class="muted small">У выбранных сущностей нет связанных Measurement в графе.</p>';
    return;
  }
  const head = `<tr><th>Параметр</th>${columns.map((c) => `<th>${esc(c.label)}<br><span class="muted small">${esc(c.name)}</span></th>`).join("")}</tr>`;
  const body = params.map((p) =>
    `<tr><td>${esc(p)}</td>${columns.map((c) => `<td>${esc(c.byParam[p] || "—")}</td>`).join("")}</tr>`,
  ).join("");
  els.graphCompareTableWrap.innerHTML = `<table class="graph-compare-table"><thead>${head}</thead><tbody>${body}</tbody></table>`;
}

function loadTopicWatchlistFromStorage() {
  try {
    const raw = localStorage.getItem(WATCHLIST_STORAGE_KEY);
    if (!raw) return [];
    return raw.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean);
  } catch {
    return [];
  }
}

function saveTopicWatchlistToStorage(words) {
  try {
    localStorage.setItem(WATCHLIST_STORAGE_KEY, words.join(", "));
  } catch { /* ignore */ }
}

function initTopicWatchlistUi() {
  const words = loadTopicWatchlistFromStorage();
  if (els.topicWatchlistInput) els.topicWatchlistInput.value = words.join(", ");
}

function bindTopicWatchlistEvents() {
  els.topicWatchlistSaveBtn?.addEventListener("click", () => {
    const raw = (els.topicWatchlistInput?.value || "").trim();
    const words = raw.split(/[,;]+/).map((s) => s.trim().toLowerCase()).filter(Boolean);
    saveTopicWatchlistToStorage(words);
    if (els.topicWatchlistStatus) els.topicWatchlistStatus.textContent = words.length ? `Сохранено: ${words.length} тем` : "Подписки очищены";
  });
}

function notifyWatchlistMatches(items) {
  const watchlist = loadTopicWatchlistFromStorage();
  if (!watchlist.length || !items?.length) return;
  let known = [];
  try {
    known = JSON.parse(localStorage.getItem(KNOWN_DOCS_STORAGE_KEY) || "[]");
  } catch { known = []; }
  const knownSet = new Set(known);
  const isInitial = knownSet.size === 0;
  const newIds = [];
  for (const doc of items) {
    if (!doc?.id || knownSet.has(doc.id)) continue;
    newIds.push(doc.id);
    if (isInitial) continue;
    const title = String(doc.file_name || doc.id || "").toLowerCase();
    const hit = watchlist.find((w) => title.includes(w));
    if (hit) showQdrantToast(`Новый документ по теме «${doc.file_name || doc.id}» (watchlist: ${hit})`, { ms: 7000 });
  }
  try {
    localStorage.setItem(KNOWN_DOCS_STORAGE_KEY, JSON.stringify(items.map((d) => d.id).filter(Boolean)));
  } catch { /* ignore */ }
}

async function loadDashboardStats() {
  if (!els.dashboardCards) return;
  els.dashboardCards.innerHTML = '<div class="dashboard-card skeleton"><span class="dashboard-card-value">…</span><span class="dashboard-card-label">Загрузка</span></div>';
  try {
    const r = await fetch(`${API}/dashboard/stats`);
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
    els.dashboardCards.innerHTML = `
      <div class="dashboard-card"><span class="dashboard-card-value">${data.doc_count ?? 0}</span><span class="dashboard-card-label">Документов</span></div>
      <div class="dashboard-card dashboard-card-warn"><span class="dashboard-card-value">${data.l4_anomalies_count ?? 0}</span><span class="dashboard-card-label">L4-аномалии</span></div>
      <div class="dashboard-card dashboard-card-danger"><span class="dashboard-card-value">${data.contradiction_nodes_count ?? 0}</span><span class="dashboard-card-label">Contradiction</span></div>`;
    const domains = data.domains || [];
    els.dashboardDomains.innerHTML = domains.length
      ? `<div class="dashboard-domain-chips">${domains.map((d) =>
        `<span class="dashboard-domain-chip">${esc(d.label)} · ${d.doc_count}</span>`,
      ).join("")}</div>`
      : '<p class="muted small">Домены по заголовкам файлов пока не определены.</p>';
    const risks = data.risk_zones || [];
    els.dashboardRiskList.innerHTML = risks.length
      ? risks.map((rz) =>
        `<li class="dashboard-risk-item severity-${esc(rz.severity || "low")}"><strong>${esc(rz.title || rz.type)}</strong><span class="muted small">${esc(rz.detail || "")}</span></li>`,
      ).join("")
      : '<li class="muted small">Зоны риска не обнаружены.</li>';
  } catch (e) {
    els.dashboardCards.innerHTML = `<p class="muted small">Ошибка обзора: ${esc(e.message)}</p>`;
  }
}

function openRelationshipDetailPanel(data, docId) {
  const layer = data.layer || "L?";
  const title = `${data.type} · ${layer}`;
  const mainHtml = `
    <span class="detail-layer" style="background:${LAYER_COLOR[layer] || LAYER_COLOR["L?"]}">${esc(layer)} · ${esc(data.type)}</span>
    <p class="rel-detail-desc">${esc(data.description || REL_TYPE_HINTS[data.type] || `Связь ${data.type}`)}</p>
    <p class="muted small rel-detail-route"><code>${esc(data.from)}</code> → <code>${esc(data.to)}</code></p>
    <h4 class="detail-section-title">Свойства связи</h4>
    ${renderRelPropsBlock(data.props || {})}
    <h4 class="detail-section-title">Узлы</h4>
    ${renderRelNodeCard(data.source_node, "Источник")}
    ${renderRelNodeCard(data.target_node, "Цель")}
    ${renderExpertEditBlock(data, docId)}`;
  const sideHtml = `
    <h4 class="detail-section-title">Смежные связи</h4>
    ${renderRelatedEdgesList(data.related_edges, "Других связей у этих узлов пока нет.")}`;
  openSideDetailPanel(title, mainHtml, sideHtml);
  bindRelDetailActions(els.detailBody, docId);
  bindExpertEditActions(els.detailBody, docId);
  highlightGraphEdge(data.from, data.to, data.type);
}

async function openRelationshipDetail({ from, to, type, docId }) {
  if (!from || !to || !type) return;
  const resolvedDocId = docId || selectedDoc;
  openSideDetailPanel("Загрузка связи…", '<p class="muted">Загрузка…</p>', "");
  const cached = buildRelationshipDetailFromGraph(from, to, type);
  if (cached && graphScope === "doc" && (graphViewDocId === resolvedDocId || selectedDoc === resolvedDocId)) {
    openRelationshipDetailPanel(cached, resolvedDocId);
    return;
  }
  if (!resolvedDocId || resolvedDocId === GRAPH_ALL_ID) {
    if (cached) {
      openRelationshipDetailPanel(cached, resolvedDocId);
      return;
    }
    openSideDetailPanel("Связь", `<p class="muted">Выберите документ, чтобы загрузить детали связи.</p>`, "");
    return;
  }
  try {
    const qs = new URLSearchParams({ from, to, type });
    const r = await fetch(`${API}/graph/documents/${encodeURIComponent(resolvedDocId)}/relationship?${qs}`);
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
    openRelationshipDetailPanel(data, resolvedDocId);
  } catch (e) {
    if (cached) {
      openRelationshipDetailPanel(cached, resolvedDocId);
      return;
    }
    openSideDetailPanel("Ошибка", `<p class="muted">${esc(e.message)}</p>`, "");
  }
}

function bindQdrantDetailActions(root) {
  root?.querySelector(".qdrant-nearest-cluster-btn")?.addEventListener("click", (ev) => {
    openQdrantClusterDetail(Number(ev.currentTarget.dataset.clusterId));
  });
  root?.querySelector(".qdrant-open-cluster-btn")?.addEventListener("click", (ev) => {
    openQdrantClusterDetail(Number(ev.currentTarget.dataset.clusterId));
  });
}

function qdrantEdgeToRelChip(edge) {
  return {
    from: edge.from_node,
    to: edge.to_node,
    type: edge.type,
    from_short: edge.from_short || edge.from_label || (edge.from_node || "").split(":").pop()?.replace(/_/g, " ") || "?",
    to_short: edge.to_short || edge.to_label || (edge.to_node || "").split(":").pop()?.replace(/_/g, " ") || "?",
    layer: edge.layer || "L?",
  };
}

function renderQdrantEdgeRow(edge) {
  const rel = qdrantEdgeToRelChip(edge);
  const docId = edge.document_id || selectedDoc;
  const cross = edge.other_cluster_name
    ? `<span class="qdrant-edge-cluster muted small">→ кластер «${esc(edge.other_cluster_name)}»</span>`
    : (edge.other_cluster_id != null ? `<span class="qdrant-edge-cluster muted small">→ кластер #${esc(String(edge.other_cluster_id))}</span>` : "");
  const desc = edge.description ? `<p class="qdrant-edge-desc muted small">${esc(edge.description)}</p>` : "";
  const preview = (edge.from_text || edge.to_text)
    ? `<p class="qdrant-edge-preview muted small">${esc((edge.from_text || rel.from_short).slice(0, 80))} → ${esc((edge.to_text || rel.to_short).slice(0, 80))}</p>`
    : "";
  return `<li class="qdrant-edge-row">${renderRelChip(rel, { docId })}${cross}${desc}${preview}</li>`;
}

function renderQdrantEdgesList(edges, emptyLabel) {
  if (!edges?.length) {
    return `<p class="muted small">${esc(emptyLabel)}</p>`;
  }
  return `<ul class="qdrant-detail-edges">${edges.map((e) => renderQdrantEdgeRow(e)).join("")}</ul>`;
}

function bindQdrantEdgeClicks(root, docId = null) {
  bindRelChipClicks(root, docId);
}

function formatClusteringStatsBlock(ctx) {
  if (!ctx) return "";
  return `
    <dl class="qdrant-stats-dl">
      <div><dt>Документов</dt><dd>${ctx.doc_count ?? "—"}</dd></div>
      <div><dt>L4-точек</dt><dd>${ctx.l4_points ?? "—"}</dd></div>
      <div><dt>Среднее L4/док</dt><dd>${ctx.avg_l4_per_doc ?? "—"}</dd></div>
      <div><dt>HDBSCAN_MIN_CLUSTER_SIZE</dt><dd>${ctx.min_cluster_size ?? 2}</dd></div>
      <div><dt>min_samples</dt><dd>${ctx.min_samples ?? ctx.min_cluster_size ?? 2}</dd></div>
    </dl>`;
}

function buildNoClustersExplanation(l4Points, ctx, clusterCount, hasClusters) {
  const n = l4Points.length;
  const mcs = ctx?.min_cluster_size ?? 2;
  const ms = ctx?.min_samples ?? mcs;
  const stats = formatClusteringStatsBlock(ctx);
  const ran = hasClusters && ctx?.clustering_ran;
  let why = `<p><strong>Почему 0 кластеров?</strong> HDBSCAN уже запускался, но все ${n} L4-точек получили <code>cluster_id = -1</code> (noise).</p>`;
  if (!ran) {
    why = `<p><strong>Кластеризация ещё не выполнялась</strong> — метки cluster_id отсутствуют. Нажмите «Перекластеризовать».</p>`;
  } else {
    why += `<ul class="qdrant-no-cluster-list">
      <li>Эмбеддинги L4 <em>семантически разрознены</em> — нет плотных групп из ≥${mcs} похожих точек.</li>
      <li>При малом корпусе (${ctx?.l4_points ?? n} точек, ~${ctx?.avg_l4_per_doc ?? "?"} на документ) HDBSCAN часто помечает всё как noise.</li>
      <li>Текущие параметры: <code>min_cluster_size=${mcs}</code>, <code>min_samples=${ms}</code> (из <code>.env</code>).</li>
      <li>После смены <code>HDBSCAN_MIN_CLUSTER_SIZE</code> в <code>.env</code> — перезапустите gateway и нажмите «Перекластеризовать».</li>
      <li>Добавьте документы на <em>схожую тему</em> — кластеры появятся, когда появятся группы близких фактов.</li>
    </ul>`;
  }
  return `${why}${stats}
    <button type="button" class="btn btn-primary btn-small qdrant-cluster-run-btn">Перекластеризовать L4</button>`;
}

function chartDataPointFromEvent(chart, evt) {
  const pos = typeof Chart !== "undefined" && Chart.helpers?.getRelativePosition
    ? Chart.helpers.getRelativePosition(evt, chart)
    : { x: evt.offsetX, y: evt.offsetY };
  return {
    x: chart.scales.x.getValueForPixel(pos.x),
    y: chart.scales.y.getValueForPixel(pos.y),
  };
}

function pointInPolygon(x, y, polygon) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i, i += 1) {
    const xi = polygon[i].x;
    const yi = polygon[i].y;
    const xj = polygon[j].x;
    const yj = polygon[j].y;
    const intersect = ((yi > y) !== (yj > y))
      && (x < ((xj - xi) * (y - yi)) / (yj - yi + 1e-12) + xi);
    if (intersect) inside = !inside;
  }
  return inside;
}

function hitTestQdrantClusterRegion(chart, evt, regions) {
  if (!chart || !regions?.length) return null;
  const { x, y } = chartDataPointFromEvent(chart, evt);
  for (const region of regions) {
    if (region.type === "hull" && region.points?.length >= 3) {
      if (pointInPolygon(x, y, region.points)) return region.clusterId;
    } else if (region.type === "ellipse") {
      const dx = (x - region.cx) / Math.max(region.rx, 1e-6);
      const dy = (y - region.cy) / Math.max(region.ry, 1e-6);
      if (dx * dx + dy * dy <= 1) return region.clusterId;
    }
  }
  return null;
}

async function openQdrantClusterDetail(clusterId) {
  if (clusterId == null || Number(clusterId) < 0) return;
  openSideDetailPanel("Загрузка кластера…", '<p class="muted">Загрузка…</p>', "");
  try {
    const r = await fetch(`${API}/graph/l4/cluster/${encodeURIComponent(clusterId)}/detail`);
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
    const title = `${data.cluster_name} · #${data.cluster_id}`;
    const mainHtml = `
      <p class="qdrant-detail-desc">${esc(data.cluster_description || "Описание не сгенерировано.")}</p>
      <p class="muted small">${data.point_count} точек в кластере</p>
      ${data.members?.length ? `<h4 class="qdrant-detail-sub">Факты</h4><ul class="qdrant-detail-members">${data.members.slice(0, 12).map((m) => `<li><span class="muted">${esc(m.label || "")}</span> ${esc((m.text || "").slice(0, 160))}</li>`).join("")}</ul>` : ""}`;
    const sideHtml = `
      <h4 class="detail-section-title">Связи внутри кластера</h4>
      ${renderQdrantEdgesList(data.internal_edges, "Нет связей Neo4j между фактами этого кластера.")}
      <h4 class="detail-section-title">Межкластерные связи</h4>
      ${renderQdrantEdgesList(data.cross_cluster_edges, "Нет связей с другими кластерами.")}`;
    openSideDetailPanel(title, mainHtml, sideHtml);
    bindQdrantDetailActions(els.detailBody);
    bindQdrantEdgeClicks(els.detailBody);
  } catch (e) {
    openSideDetailPanel("Ошибка", `<p class="muted">${esc(e.message)}</p>`, "");
  }
}

async function openQdrantPointDetail(point) {
  if (!point) return;
  const nodeId = point.neo4j_node_id || point.node_id;
  if (!nodeId) return;
  openSideDetailPanel(isQdrantL4Anomaly(point) ? "L4-аномалия" : "L4-факт", '<p class="muted">Загрузка…</p>', "");
  try {
    const r = await fetch(`${API}/graph/l4/point/${encodeURIComponent(nodeId)}/detail`);
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
    const title = data.is_anomaly ? `Аномалия · ${data.label || "L4"}` : (data.cluster_name || data.label || "L4-факт");
    let anomalyBlock = "";
    if (data.is_anomaly) {
      anomalyBlock = `
        <p class="qdrant-detail-warn"><strong>Почему аномалия:</strong> ${esc(data.anomaly_reason || "HDBSCAN noise (cluster_id=-1)")}</p>
        ${data.anomaly_score != null ? `<p class="muted small">anomaly_score: ${esc(String(data.anomaly_score))}</p>` : ""}
        ${data.nearest_cluster ? `<p class="muted small">Ближайший кластер: <button type="button" class="btn btn-ghost btn-small qdrant-nearest-cluster-btn" data-cluster-id="${esc(String(data.nearest_cluster.cluster_id))}">«${esc(data.nearest_cluster.cluster_name)}» (#${esc(String(data.nearest_cluster.cluster_id))})</button></p>` : "<p class=\"muted small\">Ближайший кластер не определён — других кластеров нет.</p>"}`;
    } else if (data.cluster_id != null && Number(data.cluster_id) >= 0) {
      anomalyBlock = `<p class="muted small">Кластер: <button type="button" class="btn btn-ghost btn-small qdrant-open-cluster-btn" data-cluster-id="${esc(String(data.cluster_id))}">${esc(data.cluster_name || `Кластер ${data.cluster_id}`)}</button></p>`;
    }
    const mainHtml = `
      <p class="qdrant-detail-desc">${esc(data.text || point.text || "—")}</p>
      ${anomalyBlock}`;
    const sideHtml = `
      <h4 class="detail-section-title">Связи Neo4j</h4>
      ${renderQdrantEdgesList(data.edges, "Связей не найдено.")}`;
    openSideDetailPanel(title, mainHtml, sideHtml);
    bindQdrantDetailActions(els.detailBody);
    bindQdrantEdgeClicks(els.detailBody);
  } catch (e) {
    const mainHtml = `
      <p class="qdrant-detail-desc">${esc(point.text || "—")}</p>
      ${isQdrantL4Anomaly(point) ? `<p class="qdrant-detail-warn">${esc(point.anomaly_reason || "Аномалия HDBSCAN (вне кластера)")}</p>` : ""}
      <p class="muted small">${esc(e.message)}</p>`;
    openSideDetailPanel(isQdrantL4Anomaly(point) ? "L4-аномалия" : "L4-факт", mainHtml, "");
  }
}

function bindQdrantClusterRunButtons(root) {
  root?.querySelectorAll(".qdrant-cluster-run-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      qdrantClusterAutoDone = false;
      runL4Clustering();
    });
  });
}

function bindQdrantClusterCardClicks() {
  els.qdrantClusterCards?.querySelectorAll("[data-cluster-id]").forEach((el) => {
    el.addEventListener("click", () => openQdrantClusterDetail(Number(el.dataset.clusterId)));
  });
}

function updateQdrantAllAnomaliesBanner(l4Points, clusterCount, hasClusters, ctx = qdrantClusteringContext) {
  if (!els.qdrantVizEmptyState) return;
  els.qdrantVizEmptyState.classList.add("hidden");
  els.qdrantVizEmptyState.innerHTML = "";
}

async function loadQdrantClusterMap() {
  if (!els.qdrantVizCanvas) return;
  const docParam = "layer=L4&limit=500";
  if (els.qdrantVizPlaceholder) {
    els.qdrantVizPlaceholder.textContent = "Загрузка карты…";
    els.qdrantVizPlaceholder.classList.remove("hidden");
  }
  if (els.qdrantVizEmptyState) {
    els.qdrantVizEmptyState.classList.add("hidden");
    els.qdrantVizEmptyState.innerHTML = "";
  }
  try {
    const r = await fetch(`${AGENT_API}/embeddings/points/viz?${docParam}`);
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${r.status}`);
    }
    const data = await r.json();
    let points = filterQdrantVizL4(data.points || []);
    let hasClusters = data.has_clusters;
    let clusters = data.clusters || [];
    let clusterCount = data.cluster_count ?? clusters.length;
    let anomalyCount = data.anomaly_count ?? points.filter(isQdrantL4Anomaly).length;
    let data2 = null;
    const autoRan = await maybeAutoClusterL4(points);
    if (autoRan) {
      const r2 = await fetch(`${AGENT_API}/embeddings/points/viz?${docParam}`);
      if (r2.ok) {
        data2 = await r2.json();
        points = filterQdrantVizL4(data2.points || points);
        hasClusters = data2.has_clusters;
        clusters = data2.clusters || clusters;
        clusterCount = data2.cluster_count ?? clusters.length;
        anomalyCount = data2.anomaly_count ?? anomalyCount;
      }
    }
    qdrantVizPoints = points;
    qdrantVizClusters = clusters;
    qdrantClusteringContext = (data2 || data).clustering_context || null;
    if (els.qdrantClusterCount) els.qdrantClusterCount.textContent = `(${points.length})`;
    if (els.qdrantVizMeta) {
      let clusterHint = "";
      if (!hasClusters) {
        clusterHint = " · кластеризация не запускалась";
      } else if (clusterCount > 0) {
        clusterHint = ` · ${clusterCount} кластер(ов) · ${anomalyCount} аномалий`;
      } else {
        clusterHint = ` · 0 кластеров · ${anomalyCount} аномалий (все точки — noise)`;
      }
      els.qdrantVizMeta.textContent = `PCA · L4 only · весь корпус${clusterHint} · клик по области/точке — описание и связи`;
    }
    if (!points.length) {
      destroyQdrantVizChart();
      if (els.qdrantVizPlaceholder) {
        els.qdrantVizPlaceholder.textContent = "Нет L4-точек — постройте граф и проиндексируйте документ";
        els.qdrantVizPlaceholder.classList.remove("hidden");
      }
      if (els.qdrantVizLegend) els.qdrantVizLegend.innerHTML = "";
      if (els.qdrantClusterCards) els.qdrantClusterCards.innerHTML = "";
      return;
    }
    renderQdrantVizLegend(hasClusters, points, qdrantVizClusters, clusterCount);
    renderQdrantClusterCards(qdrantVizClusters, points, hasClusters, clusterCount);
    updateQdrantAllAnomaliesBanner(points, clusterCount, hasClusters, qdrantClusteringContext);
    qdrantVizRegions = qdrantVizClusters?.length ? buildQdrantClusterRegions(points, qdrantVizClusters) : [];
    const chartOk = renderQdrantVizChart(points, hasClusters, qdrantVizClusters, qdrantVizRegions);
    if (els.qdrantVizPlaceholder) {
      if (chartOk) {
        els.qdrantVizPlaceholder.classList.add("hidden");
      } else {
        els.qdrantVizPlaceholder.innerHTML = qdrantRetryHtml("Chart.js не загружен — карта недоступна", "viz");
        bindQdrantRetry(els.qdrantVizPlaceholder);
        els.qdrantVizPlaceholder.classList.remove("hidden");
      }
    }
  } catch (e) {
    destroyQdrantVizChart();
    if (els.qdrantVizEmptyState) {
      els.qdrantVizEmptyState.classList.add("hidden");
      els.qdrantVizEmptyState.innerHTML = "";
    }
    if (els.qdrantVizPlaceholder) {
      els.qdrantVizPlaceholder.innerHTML = qdrantRetryHtml(`Ошибка загрузки карты: ${e.message}`, "viz");
      bindQdrantRetry(els.qdrantVizPlaceholder);
      els.qdrantVizPlaceholder.classList.remove("hidden");
    }
    if (els.qdrantVizLegend) els.qdrantVizLegend.innerHTML = "";
    if (els.qdrantClusterCards) els.qdrantClusterCards.innerHTML = "";
  }
}

function renderQdrantClusterCards(clusterMeta, points, hasClusters, clusterCount = clusterMeta?.length || 0) {
  if (!els.qdrantClusterCards) return;
  const l4 = filterQdrantVizL4(points);
  if (!l4.length) {
    els.qdrantClusterCards.innerHTML = "";
    return;
  }
  if (clusterMeta?.length) {
    els.qdrantClusterCards.innerHTML = `
      <div class="qdrant-cluster-map">${clusterMeta.map((c) => `
        <div class="qdrant-cluster-group qdrant-cluster-clickable" data-cluster-id="${esc(String(c.id))}" role="button" tabindex="0">
          <div class="qdrant-cluster-head">
            <span class="qdrant-viz-legend-swatch qdrant-viz-legend-swatch-region" style="background:${esc(c.color || clusterColor(c.id))}"></span>
            <strong>${esc(c.name || `Кластер ${c.id}`)}</strong>
            <span class="muted">${c.count || 0} точек · клик — описание и связи</span>
          </div>
          ${c.description ? `<p class="muted small qdrant-cluster-card-desc">${esc(c.description.slice(0, 140))}${c.description.length > 140 ? "…" : ""}</p>` : ""}
        </div>`).join("")}</div>`;
    bindQdrantClusterCardClicks();
    const anomalies = l4.filter(isQdrantL4Anomaly).length;
    if (anomalies) {
      els.qdrantClusterCards.innerHTML += `<p class="muted small qdrant-anomaly-note">+ ${anomalies} аномалий (красные точки) — клик по точке на карте</p>`;
    }
    return;
  }
  const anomalies = l4.filter(isQdrantL4Anomaly).length;
  if (hasClusters && clusterCount === 0 && anomalies === l4.length) {
    els.qdrantClusterCards.innerHTML = `
      <div class="qdrant-cluster-empty-info">
        ${buildNoClustersExplanation(l4, qdrantClusteringContext, clusterCount, hasClusters)}
      </div>`;
    bindQdrantClusterRunButtons(els.qdrantClusterCards);
    return;
  }
  els.qdrantClusterCards.innerHTML = `<p class="muted small">L4 без меток кластеров — <button type="button" class="btn btn-ghost btn-small qdrant-cluster-run-btn">Запустить кластеризацию</button></p>`;
  bindQdrantClusterRunButtons(els.qdrantClusterCards);
}

function destroyQdrantVizChart() {
  if (qdrantVizChart) {
    qdrantVizChart.destroy();
    qdrantVizChart = null;
  }
}

function qdrantVizPointColor(p, hasClusters) {
  if (isQdrantL4Anomaly(p)) return QDRANT_VIZ_ANOMALY_COLOR;
  if (hasClusters && p.cluster_id != null && Number(p.cluster_id) >= 0) {
    return QDRANT_CLUSTER_PALETTE[Math.abs(Number(p.cluster_id)) % QDRANT_CLUSTER_PALETTE.length];
  }
  return QDRANT_VIZ_L4_COLOR;
}

function renderQdrantVizLegend(hasClusters, points, clusterMeta = [], clusterCount = clusterMeta.length) {
  if (!els.qdrantVizLegend) return;
  const items = [];
  if (!hasClusters) {
    items.push({ color: QDRANT_VIZ_L4_COLOR, label: `L4 без кластеров (${points.length})`, shape: "dot" });
  } else if (clusterCount > 0) {
    const metaById = new Map(clusterMeta.map((c) => [Number(c.id), c]));
    const clusterIds = [...new Set(
      points.filter((p) => p.layer === "L4" && p.cluster_id != null && Number(p.cluster_id) >= 0)
        .map((p) => p.cluster_id),
    )].sort((a, b) => Number(a) - Number(b));
    clusterIds.slice(0, 12).forEach((cid) => {
      const meta = metaById.get(Number(cid));
      items.push({
        color: meta?.color || clusterColor(cid),
        label: meta?.name ? `${meta.name} (${meta.count || ""})`.replace(" ()", "") : `кластер ${cid}`,
        shape: "region",
      });
    });
    const anomalies = points.filter(isQdrantL4Anomaly).length;
    if (anomalies) {
      items.push({
        color: QDRANT_VIZ_ANOMALY_COLOR,
        label: `аномалии — L4 вне кластеров (${anomalies})`,
        shape: "dot",
      });
    }
  } else {
    items.push({
      color: QDRANT_VIZ_ANOMALY_COLOR,
      label: `все точки — аномалии HDBSCAN (${points.length})`,
      shape: "dot",
    });
  }
  els.qdrantVizLegend.innerHTML = items.map((it) => `
    <span class="qdrant-viz-legend-item">
      <span class="qdrant-viz-legend-swatch${it.shape === "region" ? " qdrant-viz-legend-swatch-region" : ""}" style="background:${it.color}"></span>
      ${esc(it.label)}
    </span>`).join("");
}

function highlightQdrantPoint(pointId, opts = {}) {
  if (!pointId || !els.qdrantPointsList) return;
  const scroll = opts.scroll !== false;
  els.qdrantPointsList.querySelectorAll(".qdrant-point-row").forEach((el) => {
    el.classList.toggle("qdrant-point-highlight", el.dataset.pointId === pointId);
  });
  if (scroll) {
    const row = els.qdrantPointsList.querySelector(`[data-point-id="${CSS.escape(pointId)}"]`);
    row?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }
}

function renderQdrantVizChart(points, hasClusters, clusterMeta = [], regions = []) {
  if (typeof Chart === "undefined" || !els.qdrantVizCanvas) return false;
  destroyQdrantVizChart();
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const padX = Math.max((Math.max(...xs) - Math.min(...xs)) * 0.08, 0.05);
  const padY = Math.max((Math.max(...ys) - Math.min(...ys)) * 0.08, 0.05);
  const chartData = points.map((p) => ({
    x: p.x,
    y: p.y,
    _p: p,
  }));
  const hullRegions = regions?.length ? regions : (clusterMeta?.length ? buildQdrantClusterRegions(points, clusterMeta) : []);
  qdrantVizRegions = hullRegions;
  qdrantVizChart = new Chart(els.qdrantVizCanvas, {
    type: "scatter",
    data: {
      datasets: [{
        label: "L4",
        data: chartData,
        pointBackgroundColor: (ctx) => qdrantVizPointColor(ctx.raw._p, hasClusters),
        pointBorderColor: (ctx) => {
          const p = ctx.raw._p;
          if (isQdrantL4Anomaly(p)) return "#8b0000";
          if (hasClusters && p.cluster_id != null && Number(p.cluster_id) >= 0) {
            return clusterColor(p.cluster_id);
          }
          return "#ffffff";
        },
        pointBorderWidth: (ctx) => (isQdrantL4Anomaly(ctx.raw._p) ? 2 : 1.5),
        pointRadius: (ctx) => (isQdrantL4Anomaly(ctx.raw._p) ? 7 : 6),
        pointHoverRadius: 9,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 350 },
      plugins: {
        legend: { display: false },
        qdrantClusterHulls: { hulls: hullRegions, regions: hullRegions },
        tooltip: { enabled: false },
      },
      scales: {
        x: {
          type: "linear",
          min: Math.min(...xs) - padX,
          max: Math.max(...xs) + padX,
          grid: { color: "rgba(0,0,0,0.06)" },
          ticks: { display: false },
          border: { display: false },
        },
        y: {
          min: Math.min(...ys) - padY,
          max: Math.max(...ys) + padY,
          grid: { color: "rgba(0,0,0,0.06)" },
          ticks: { display: false },
          border: { display: false },
        },
      },
      onClick: (evt, elements) => {
        if (!qdrantVizChart) return;
        const hitCluster = hitTestQdrantClusterRegion(qdrantVizChart, evt, qdrantVizRegions);
        if (hitCluster != null && Number(hitCluster) >= 0) {
          openQdrantClusterDetail(hitCluster);
          return;
        }
        if (!elements.length) return;
        const idx = elements[0].index;
        const p = qdrantVizChart.data.datasets[0].data[idx]?._p;
        if (p?.id) highlightQdrantPoint(p.id);
        openQdrantPointDetail(p);
      },
    },
  });
  return true;
}

async function runL4Clustering(opts = {}) {
  const { silent = false, skipReload = false } = opts;
  if (!silent && els.qdrantIndexLog) {
    els.qdrantIndexLog.textContent = "Глобальная кластеризация L4…";
  }
  try {
    const r = await fetch(`${API}/graph/l4/cluster`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_id: null }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || data.message || "Ошибка кластеризации");
    if (data.debounced) {
      const debMsg = data.message || "Кластеризация отложена (debounce)";
      if (!silent) appendQdrantLog(debMsg);
      showQdrantToast(debMsg);
      return false;
    }
    const names = (data.named_clusters || []).map((c) => c.name).slice(0, 3).join(", ");
    const msg = `Готово: ${data.clusters || 0} кластеров, ${data.anomalies || 0} аномалий из ${data.points || data.clustered || 0} L4-точек${names ? ` · ${names}` : ""}`;
    const hint = data.noise_hint || data.message;
    if (!silent) {
      if (els.qdrantIndexLog) els.qdrantIndexLog.textContent = hint ? `${msg} — ${hint}` : msg;
    } else {
      appendQdrantLog(hint ? `${msg} — ${hint}` : msg);
    }
    showQdrantToast(hint && !data.clusters ? `${msg}. ${hint}` : msg, { error: !!(data.all_noise && !data.clusters) });
    if (!skipReload) {
      await loadQdrantClusterMap();
      await loadQdrantPoints();
      if (selectedDoc && graphVisible) await loadGraph(selectedDoc, { silent: true });
    }
    return true;
  } catch (e) {
    if (!silent && els.qdrantIndexLog) els.qdrantIndexLog.textContent = `Ошибка: ${e.message}`;
    else appendQdrantLog(`Ошибка кластеризации: ${e.message}`, true);
    showQdrantToast(`Ошибка: ${e.message}`, { error: true });
    return false;
  }
}

function clearGraphNodeSelection() {
  closeDetailPanel();
  if (visNetwork) visNetwork.unselectAll();
  document.querySelectorAll(".graph-node-item.active, .entity-card.active").forEach((el) => {
    el.classList.remove("active");
  });
}

function activateAllDocumentsGraph() {
  graphScope = "all";
  graphDensityMode = "full";
  graphVisible = true;
  graphViewDocId = GRAPH_ALL_ID;
  graphLayerFilter = "all";
  clearGraphNodeSelection();
  updateGraphScopeUI();
  updateDensityToggleUI();
  loadGraph(GRAPH_ALL_ID, { force: true });
  refreshGraphViewport({ fit: true, force: true });
}

function viewAllGraph() {
  docWorkTabManual = true;
  graphScope = "all";
  if (!isGraphHostPage()) {
    switchPage("docs");
  }
  activateAllDocumentsGraph();
  setDocWorkTab("graph", { skipGraphLoad: true });
}

function openNeo4jBrowser() {
  window.open(NEO4J_BROWSER_URL, "_blank", "noopener,noreferrer");
}

function resetGraphFilters() {
  clearGraphNodeSelection();
  graphLayerFilter = "all";
  highlightCrossLayer = false;
  resetGraphAdvancedFilters({ rerender: false });
  connectionFormationMode = false;
  connectionFormationStep = 0;
  stopConnectionFormationTimer();
  graphDensityMode = "full";
  if (els.crossLayerToggle) els.crossLayerToggle.classList.remove("active");
  if (els.connectionFormationBtn) els.connectionFormationBtn.classList.remove("active");
  renderConnectionFormationTimeline();
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
  if (graphViewMode === mode) return;
  graphViewMode = mode;
  const isMap = mode === "map";
  els.viewMapBtn?.classList.toggle("active", isMap);
  els.viewRelsBtn?.classList.toggle("active", !isMap);
  els.graphCanvasWrap?.classList.toggle("hidden", !isMap);
  els.graphMapView?.classList.toggle("hidden", !isMap);
  els.graphRelsView?.classList.toggle("hidden", isMap);
  if (!isMap) renderAllRelationshipsList();
  if (isMap) scheduleGraphViewsRender();
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
  const answersOnly = isAnswersOnlyMode(data);
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
  } else if (answersOnly) {
    els.docPrimaryBtn.textContent = extracting || data.status === "processing"
      ? "Обработка…"
      : "Построить полный граф";
    els.docPrimaryBtn.dataset.action = "full";
    els.docPrimaryBtn.disabled = extracting || data.status === "processing" || data.status === "uploaded";
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
      if (isAnswersOnlyMode(doc) && nodes === 0) {
        return { text: "только для чата", cls: "s-md_ready" };
      }
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

function nodeSearchText(node) {
  const props = node?.props || {};
  const parts = [
    props.name_ru, props.name_en, props.name, props.title, props.quote,
    props.source_quote, props.full_name, props.legal_name, props.description,
    props.chemical_formula, props.city, props.country, props.region,
    node?.label, node?.id,
  ];
  const aliases = nodeAliasesText(node);
  if (aliases) parts.push(aliases);
  return parts.filter((p) => typeof p === "string" && p.trim()).join(" ").toLowerCase();
}

function nodeAliasesText(node) {
  const props = node?.props || {};
  const aliases = props.aliases;
  if (Array.isArray(aliases)) {
    return aliases.filter((x) => typeof x === "string" && x.trim()).join(" ");
  }
  if (typeof aliases === "string" && aliases.trim()) return aliases.trim();
  return "";
}

function nodeMatchesKeyword(node, q) {
  const needle = (q || "").trim().toLowerCase();
  if (!needle) return true;
  const hay = nodeSearchText(node);
  if (hay.includes(needle)) return true;
  for (const [a, b] of SYNONYM_PAIRS) {
    if (needle.includes(a) && hay.includes(b)) return true;
    if (needle.includes(b) && hay.includes(a)) return true;
  }
  return false;
}

function inferDocCategory(meta) {
  const text = [
    meta?.file_name, meta?.doc_type, meta?.classification, meta?.source_file,
  ].filter(Boolean).join(" ").toLowerCase();
  if (/патент|patent|\.ru\d{6,}/.test(text)) return "patent";
  if (/справочник|handbook|manual|guide|reference/.test(text)) return "handbook";
  if (/отч[её]т|report|доклад|отчет|internal/.test(text)) return "report";
  if (/статья|article|paper|journal|conf|proceedings/.test(text)) return "article";
  return "other";
}

function nodeDocCategory(node) {
  const props = node?.props || {};
  const fromProps = props.doc_category || props.document_category;
  if (fromProps) return String(fromProps).toLowerCase();
  const docId = props.source_doc_id || props.document_id;
  if (docId) {
    const d = docsListCache.find((x) => x.id === docId);
    if (d) return inferDocCategory(d);
  }
  return inferDocCategory({ file_name: props.file_name || props.source_file, doc_type: props.doc_type });
}

function nodeSourceDocId(node) {
  const props = node?.props || {};
  return props.source_doc_id || props.document_id || null;
}

function nodeLanguage(node) {
  const props = node?.props || {};
  const lang = String(props.lang || props.language || props.lang_code || "").toLowerCase();
  if (lang.startsWith("ru")) return "ru";
  if (lang.startsWith("en")) return "en";
  if (node?.label === "LangContext") {
    const code = String(props.code || props.name || "").toLowerCase();
    if (code.includes("ru")) return "ru";
    if (code.includes("en")) return "en";
  }
  const text = nodeSearchText(node);
  const hasCyr = /[а-яё]/i.test(text);
  const hasLat = /[a-z]/i.test(text);
  if (hasCyr && !hasLat) return "ru";
  if (hasLat && !hasCyr) return "en";
  return null;
}

function nodeYear(node) {
  const props = node?.props || {};
  const raw = props.publication_year ?? props.pub_year ?? props.year
    ?? props.run_date ?? props.event_date ?? props.date;
  if (raw == null || raw === "") return null;
  if (typeof raw === "number" && Number.isFinite(raw)) return raw >= 1000 && raw <= 9999 ? raw : null;
  const s = String(raw);
  const m = s.match(/\b(19|20)\d{2}\b/);
  return m ? Number(m[0]) : null;
}

function nodeConfidence(node) {
  const props = node?.props || {};
  const v = props.extraction_confidence ?? props.confidence ?? props.confidence_score;
  if (v == null || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function nodeNumericValue(node) {
  if (node?.label !== "Measurement") return null;
  const props = node.props || {};
  const raw = props.numeric_value ?? props.value ?? props.concentration ?? props.temperature ?? props.flow_rate;
  if (raw == null || raw === "") return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

function isDomesticGeoNode(node) {
  const text = nodeGeographyText(node);
  return /\b(росси|russia|\bru\b|рф|российск)\b/i.test(text);
}

function nodeGeographyText(node) {
  const props = node?.props || {};
  return [props.city, props.country, props.region, props.name, props.name_ru]
    .filter((p) => typeof p === "string" && p.trim())
    .join(" ")
    .toLowerCase();
}

function advancedFiltersSignature(f) {
  if (!f?.active) return "";
  return JSON.stringify({
    searchText: f.searchText,
    entityTypes: [...(f.entityTypes || [])].sort(),
    docCategories: [...(f.docCategories || [])].sort(),
    relationTypes: [...(f.relationTypes || [])].sort(),
    geography: f.geography,
    practiceRegion: f.practiceRegion,
    yearMin: f.yearMin,
    yearMax: f.yearMax,
    minConfidence: f.minConfidence,
    materialKeyword: f.materialKeyword,
    processKeyword: f.processKeyword,
    language: f.language,
    numericMin: f.numericMin,
    numericMax: f.numericMax,
    numericParam: f.numericParam,
    showContradictions: f.showContradictions,
    showGaps: f.showGaps,
  });
}

function isContradictionRel(rel, nodeById) {
  if (CONTRADICTION_REL_TYPES.has(rel.type)) return true;
  const { from, to } = relEndpoints(rel);
  const a = nodeById.get(from);
  const b = nodeById.get(to);
  return (a && CONTRADICTION_NODE_LABELS.has(a.label)) || (b && CONTRADICTION_NODE_LABELS.has(b.label));
}

function isGapNode(node) {
  return GAP_NODE_LABELS.has(node?.label);
}

function applyAdvancedGraphFilters(nodes, rels) {
  const f = graphAdvancedFilters;
  if (!f.active) return { nodes, rels };

  const nodeById = new Map(nodes.map((n) => [n.id, n]));
  let keepIds = new Set(nodes.map((n) => n.id));

  const entitySet = new Set(f.entityTypes || []);
  const allEntitiesSelected = entitySet.size >= ALL_ENTITY_FILTER_IDS.length;
  if (!allEntitiesSelected && entitySet.size > 0) {
    const allowedLabels = new Set();
    entitySet.forEach((id) => {
      (ENTITY_LABELS_BY_FILTER_ID[id] || new Set()).forEach((l) => allowedLabels.add(l));
    });
    keepIds = new Set([...keepIds].filter((id) => allowedLabels.has(nodeById.get(id)?.label)));
  }

  const searchQ = (f.searchText || "").trim().toLowerCase();
  if (searchQ) {
    keepIds = new Set([...keepIds].filter((id) => nodeSearchText(nodeById.get(id)).includes(searchQ)));
  }

  const docCatSet = new Set(f.docCategories || []);
  if (docCatSet.size > 0 && docCatSet.size < ALL_DOC_CATEGORY_IDS.length) {
    const allowedDocIds = new Set(
      docsListCache
        .filter((d) => docCatSet.has(inferDocCategory(d)))
        .map((d) => d.id),
    );
    const docMatchIds = new Set();
    nodes.forEach((n) => {
      if (n.label === "Document" && docCatSet.has(nodeDocCategory(n))) docMatchIds.add(n.id);
      const srcDoc = nodeSourceDocId(n);
      if (srcDoc && allowedDocIds.has(srcDoc)) docMatchIds.add(n.id);
    });
    rels.forEach((r) => {
      const { from, to } = relEndpoints(r);
      if (docMatchIds.has(from) || docMatchIds.has(to)) {
        docMatchIds.add(from);
        docMatchIds.add(to);
      }
    });
    keepIds = new Set([...keepIds].filter((id) => docMatchIds.has(id)));
  }

  const langFilter = (f.language || "both").toLowerCase();
  if (langFilter === "ru" || langFilter === "en") {
    const langMatchIds = new Set();
    nodes.forEach((n) => {
      const lang = nodeLanguage(n);
      if (lang === langFilter || lang == null) langMatchIds.add(n.id);
      if (n.label === "LangContext") {
        const ctxLang = nodeLanguage(n);
        if (ctxLang === langFilter) langMatchIds.add(n.id);
      }
    });
    rels.forEach((r) => {
      if (r.type === "TAGGED_WITH" || r.type === "HAS_LANG") {
        const { from, to } = relEndpoints(r);
        const a = nodeById.get(from);
        const b = nodeById.get(to);
        if ((a?.label === "LangContext" && nodeLanguage(a) === langFilter)
          || (b?.label === "LangContext" && nodeLanguage(b) === langFilter)) {
          langMatchIds.add(from);
          langMatchIds.add(to);
        }
      }
    });
    keepIds = new Set([...keepIds].filter((id) => langMatchIds.has(id)));
  }

  const geo = (f.geography || "").trim().toLowerCase();
  if (geo) {
    const geoMatchIds = new Set();
    nodes.forEach((n) => {
      if (n.label === "Location" && nodeGeographyText(n).includes(geo)) geoMatchIds.add(n.id);
      if (nodeGeographyText(n).includes(geo)) geoMatchIds.add(n.id);
    });
    rels.forEach((r) => {
      const { from, to } = relEndpoints(r);
      if (geoMatchIds.has(from) || geoMatchIds.has(to)) {
        geoMatchIds.add(from);
        geoMatchIds.add(to);
      }
    });
    keepIds = new Set([...keepIds].filter((id) => geoMatchIds.has(id)));
  }

  const practice = (f.practiceRegion || "").trim().toLowerCase();
  if (practice === "domestic" || practice === "foreign") {
    const practiceMatchIds = new Set();
    nodes.forEach((n) => {
      const domestic = isDomesticGeoNode(n);
      if (n.label === "Location") {
        if (practice === "domestic" && domestic) practiceMatchIds.add(n.id);
        if (practice === "foreign" && !domestic) practiceMatchIds.add(n.id);
      } else if (domestic && practice === "domestic") {
        practiceMatchIds.add(n.id);
      } else if (!domestic && practice === "foreign" && nodeGeographyText(n)) {
        practiceMatchIds.add(n.id);
      }
    });
    rels.forEach((r) => {
      const { from, to } = relEndpoints(r);
      if (practiceMatchIds.has(from) || practiceMatchIds.has(to)) {
        practiceMatchIds.add(from);
        practiceMatchIds.add(to);
      }
    });
    keepIds = new Set([...keepIds].filter((id) => practiceMatchIds.has(id)));
  }

  const numMin = f.numericMin !== "" && f.numericMin != null ? Number(f.numericMin) : null;
  const numMax = f.numericMax !== "" && f.numericMax != null ? Number(f.numericMax) : null;
  const numParam = (f.numericParam || "").trim().toLowerCase();
  if ((numMin != null && Number.isFinite(numMin)) || (numMax != null && Number.isFinite(numMax))) {
    const measureMatch = new Set();
    nodes.forEach((n) => {
      if (n.label !== "Measurement") return;
      const props = n.props || {};
      if (numParam) {
        const param = String(props.parameter || props.name || "").toLowerCase();
        if (!param.includes(numParam)) return;
      }
      const val = nodeNumericValue(n);
      if (val == null) return;
      if (numMin != null && Number.isFinite(numMin) && val < numMin) return;
      if (numMax != null && Number.isFinite(numMax) && val > numMax) return;
      measureMatch.add(n.id);
    });
    rels.forEach((r) => {
      const { from, to } = relEndpoints(r);
      if (measureMatch.has(from) || measureMatch.has(to)) {
        measureMatch.add(from);
        measureMatch.add(to);
      }
    });
    keepIds = new Set([...keepIds].filter((id) => measureMatch.has(id)));
  }

  const yMin = Number(f.yearMin) || 1990;
  const yMax = Number(f.yearMax) || 2026;
  if (yMin > 1990 || yMax < 2026) {
    keepIds = new Set([...keepIds].filter((id) => {
      const y = nodeYear(nodeById.get(id));
      return y == null || (y >= yMin && y <= yMax);
    }));
  }

  const minConf = Number(f.minConfidence) || 0;
  if (minConf > 0) {
    keepIds = new Set([...keepIds].filter((id) => {
      const c = nodeConfidence(nodeById.get(id));
      return c == null || c >= minConf;
    }));
  }

  if ((f.materialKeyword || "").trim()) {
    const q = f.materialKeyword.trim();
    const matMatch = new Set(
      [...keepIds].filter((id) => {
        const n = nodeById.get(id);
        return n?.label === "Material" && nodeMatchesKeyword(n, q);
      }),
    );
    keepIds = matMatch.size ? matMatch : new Set();
  }
  if ((f.processKeyword || "").trim()) {
    const q = f.processKeyword.trim();
    const procMatch = new Set(
      [...keepIds].filter((id) => {
        const n = nodeById.get(id);
        return n?.label === "Process" && nodeMatchesKeyword(n, q);
      }),
    );
    keepIds = procMatch.size ? procMatch : new Set();
  }

  let expanded = true;
  while (expanded) {
    expanded = false;
    rels.forEach((r) => {
      const { from, to } = relEndpoints(r);
      if (keepIds.has(from) && !keepIds.has(to)) {
        keepIds.add(to);
        expanded = true;
      }
      if (keepIds.has(to) && !keepIds.has(from)) {
        keepIds.add(from);
        expanded = true;
      }
    });
  }

  let filteredRels = rels.filter((r) => {
    const { from, to } = relEndpoints(r);
    return keepIds.has(from) && keepIds.has(to);
  });

  const relSet = new Set(f.relationTypes || []);
  if (relSet.size > 0 && relSet.size < ALL_RELATION_FILTER_IDS.length) {
    filteredRels = filteredRels.filter((r) => relSet.has(r.type));
    const relNodeIds = new Set();
    filteredRels.forEach((r) => {
      const { from, to } = relEndpoints(r);
      relNodeIds.add(from);
      relNodeIds.add(to);
    });
    keepIds = new Set([...keepIds].filter((id) => relNodeIds.has(id)));
  }

  const filteredNodes = nodes.filter((n) => keepIds.has(n.id));
  return { nodes: filteredNodes, rels: filteredRels };
}

function populateGraphGeographyOptions() {
  const sel = els.graphFilterGeography;
  if (!sel) return;
  const current = sel.value;
  const values = new Set();
  graphData.nodes.forEach((n) => {
    if (n.label !== "Location") return;
    const props = n.props || {};
    [props.city, props.country, props.region, props.name_ru, props.name].forEach((v) => {
      if (typeof v === "string" && v.trim()) values.add(v.trim());
    });
  });
  const sorted = [...values].sort((a, b) => a.localeCompare(b, "ru"));
  sel.innerHTML = `<option value="">Все регионы</option>${sorted.map((v) =>
    `<option value="${esc(v)}">${esc(v)}</option>`).join("")}`;
  if (current && (current === "" || sorted.includes(current))) sel.value = current;
}

function readGraphFilterForm() {
  const entityTypes = [];
  els.graphEntityTypeChecks?.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
    if (cb.checked) entityTypes.push(cb.dataset.entityId);
  });
  const docCategories = [];
  els.graphDocTypeChecks?.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
    if (cb.checked) docCategories.push(cb.dataset.docCatId);
  });
  const relationTypes = [];
  els.graphRelationTypeChecks?.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
    if (cb.checked) relationTypes.push(cb.dataset.relTypeId);
  });
  return {
    searchText: els.graphFilterSearch?.value?.trim() || "",
    entityTypes,
    docCategories,
    relationTypes,
    geography: els.graphFilterGeography?.value || "",
    practiceRegion: els.graphFilterPracticeRegion?.value || "",
    yearMin: Number(els.graphFilterYearMin?.value) || 1990,
    yearMax: Number(els.graphFilterYearMax?.value) || 2026,
    minConfidence: Number(els.graphFilterConfidence?.value) || 0,
    materialKeyword: els.graphFilterMaterial?.value?.trim() || "",
    processKeyword: els.graphFilterProcess?.value?.trim() || "",
    language: els.graphFilterLanguage?.value || "both",
    numericMin: els.graphFilterParamMin?.value ?? els.graphFilterNumericMin?.value ?? "",
    numericMax: els.graphFilterParamMax?.value ?? els.graphFilterNumericMax?.value ?? "",
    numericParam: els.graphFilterNumericParam?.value?.trim() || "",
    showContradictions: !!els.graphFilterContradictions?.checked,
    showGaps: !!els.graphFilterGaps?.checked,
  };
}

function syncGraphFilterFormFromState(f) {
  if (els.graphFilterSearch) els.graphFilterSearch.value = f.searchText || "";
  els.graphEntityTypeChecks?.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
    cb.checked = (f.entityTypes || ALL_ENTITY_FILTER_IDS).includes(cb.dataset.entityId);
  });
  els.graphDocTypeChecks?.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
    cb.checked = (f.docCategories || ALL_DOC_CATEGORY_IDS).includes(cb.dataset.docCatId);
  });
  els.graphRelationTypeChecks?.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
    cb.checked = (f.relationTypes || ALL_RELATION_FILTER_IDS).includes(cb.dataset.relTypeId);
  });
  if (els.graphFilterGeography) els.graphFilterGeography.value = f.geography || "";
  if (els.graphFilterPracticeRegion) els.graphFilterPracticeRegion.value = f.practiceRegion || "";
  if (els.graphFilterLanguage) els.graphFilterLanguage.value = f.language || "both";
  if (els.graphFilterYearMin) els.graphFilterYearMin.value = String(f.yearMin ?? 1990);
  if (els.graphFilterYearMax) els.graphFilterYearMax.value = String(f.yearMax ?? 2026);
  updateGraphYearLabel();
  if (els.graphFilterConfidence) els.graphFilterConfidence.value = String(f.minConfidence ?? 0);
  if (els.graphFilterMaterial) els.graphFilterMaterial.value = f.materialKeyword || "";
  if (els.graphFilterProcess) els.graphFilterProcess.value = f.processKeyword || "";
  if (els.graphFilterParamMin) els.graphFilterParamMin.value = f.numericMin ?? "";
  if (els.graphFilterParamMax) els.graphFilterParamMax.value = f.numericMax ?? "";
  if (els.graphFilterNumericMin) els.graphFilterNumericMin.value = f.numericMin ?? "";
  if (els.graphFilterNumericMax) els.graphFilterNumericMax.value = f.numericMax ?? "";
  if (els.graphFilterNumericParam) els.graphFilterNumericParam.value = f.numericParam || "";
  if (els.graphFilterContradictions) els.graphFilterContradictions.checked = !!f.showContradictions;
  if (els.graphFilterGaps) els.graphFilterGaps.checked = !!f.showGaps;
}

function updateGraphYearLabel() {
  const min = Number(els.graphFilterYearMin?.value) || 1990;
  let max = Number(els.graphFilterYearMax?.value) || 2026;
  if (min > max) {
    max = min;
    if (els.graphFilterYearMax) els.graphFilterYearMax.value = String(min);
  }
  if (els.graphFilterYearLabel) els.graphFilterYearLabel.textContent = `${min} — ${max}`;
}

function updateGraphFilterStatus() {
  if (!els.graphFilterStatus) return;
  if (!graphAdvancedFilters.active) {
    els.graphFilterStatus.textContent = "";
    return;
  }
  const { nodes, rels } = applyAdvancedGraphFilters(
    [...graphData.nodes],
    [...graphData.relationships],
  );
  els.graphFilterStatus.textContent = `Фильтр: ${nodes.length} узл. · ${rels.length} связей`;
}

function saveGraphAdvancedFiltersSession() {
  try {
    sessionStorage.setItem(GRAPH_ADV_FILTERS_SESSION_KEY, JSON.stringify(graphAdvancedFilters));
  } catch { /* ignore */ }
}

function loadGraphAdvancedFiltersSession() {
  try {
    const raw = sessionStorage.getItem(GRAPH_ADV_FILTERS_SESSION_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw);
    graphAdvancedFilters = { ...defaultGraphAdvancedFilters(), ...parsed };
  } catch { /* ignore */ }
}

function applyGraphAdvancedFiltersFromForm() {
  const form = readGraphFilterForm();
  graphAdvancedFilters = { ...form, active: true };
  saveGraphAdvancedFiltersSession();
  syncGraphFilterFormFromState(graphAdvancedFilters);
  clearGraphNodeSelection();
  resetGraphNetwork();
  scheduleGraphViewsRender({ force: true });
  updateGraphFilterStatus();
}

function resetGraphAdvancedFilters({ rerender = true } = {}) {
  graphAdvancedFilters = defaultGraphAdvancedFilters();
  try { sessionStorage.removeItem(GRAPH_ADV_FILTERS_SESSION_KEY); } catch { /* ignore */ }
  syncGraphFilterFormFromState(graphAdvancedFilters);
  if (els.graphFilterStatus) els.graphFilterStatus.textContent = "";
  if (rerender) {
    clearGraphNodeSelection();
    resetGraphNetwork();
    scheduleGraphViewsRender({ force: true });
  }
}

function initGraphAdvancedFilters() {
  if (!els.graphEntityTypeChecks) return;
  loadGraphAdvancedFiltersSession();
  els.graphEntityTypeChecks.innerHTML = ENTITY_TYPE_FILTERS.map((e) => `
    <label class="graph-adv-check">
      <input type="checkbox" data-entity-id="${esc(e.id)}" checked />
      <span>${esc(e.label)}</span>
    </label>`).join("");
  if (els.graphDocTypeChecks) {
    els.graphDocTypeChecks.innerHTML = DOC_CATEGORY_FILTERS.map((d) => `
      <label class="graph-adv-check">
        <input type="checkbox" data-doc-cat-id="${esc(d.id)}" checked />
        <span>${esc(d.label)}</span>
      </label>`).join("");
  }
  if (els.graphRelationTypeChecks) {
    els.graphRelationTypeChecks.innerHTML = RELATION_TYPE_FILTERS.map((r) => `
      <label class="graph-adv-check">
        <input type="checkbox" data-rel-type-id="${esc(r.id)}" checked />
        <span>${esc(r.label)}</span>
      </label>`).join("");
  }
  syncGraphFilterFormFromState(graphAdvancedFilters);
  updateGraphYearLabel();

  const onYearInput = () => updateGraphYearLabel();
  els.graphFilterYearMin?.addEventListener("input", onYearInput);
  els.graphFilterYearMax?.addEventListener("input", onYearInput);

  els.graphFilterApplyBtn?.addEventListener("click", applyGraphAdvancedFiltersFromForm);
  els.graphFilterResetBtn?.addEventListener("click", () => resetGraphAdvancedFilters());

  [els.graphFilterContradictions, els.graphFilterGaps].forEach((el) => {
    el?.addEventListener("change", () => {
      if (!graphAdvancedFilters.active) return;
      const form = readGraphFilterForm();
      graphAdvancedFilters = { ...graphAdvancedFilters, ...form, active: true };
      saveGraphAdvancedFiltersSession();
      scheduleGraphViewsRender();
    });
  });
}

function filteredGraph() {
  const layerMap = nodeLayerMap();
  let nodes = [...graphData.nodes];
  let rels = [...graphData.relationships];
  let primaryLayer = graphLayerFilter;

  if (connectionFormationMode && connectionFormationStep > 0) {
    const activeLayers = new Set(FORMATION_LAYERS.slice(0, connectionFormationStep));
    const primary = nodes.filter((n) => activeLayers.has(layerOf(n.label)));
    const keepIds = new Set(primary.map((n) => n.id));
    let expanded = true;
    while (expanded) {
      expanded = false;
      rels.forEach((r) => {
        const { from, to } = relEndpoints(r);
        const fromLayer = layerMap.get(from);
        const toLayer = layerMap.get(to);
        const fromActive = keepIds.has(from) && activeLayers.has(fromLayer);
        const toActive = keepIds.has(to) && activeLayers.has(toLayer);
        if (fromActive && toLayer && !keepIds.has(to)) {
          keepIds.add(to);
          expanded = true;
        }
        if (toActive && fromLayer && !keepIds.has(from)) {
          keepIds.add(from);
          expanded = true;
        }
        if (keepIds.has(from) && keepIds.has(to) && fromLayer && toLayer
          && activeLayers.has(fromLayer) && activeLayers.has(toLayer)) {
          /* keep edge */
        }
      });
    }
    nodes = nodes.filter((n) => keepIds.has(n.id));
    rels = rels.filter((r) => {
      const { from, to } = relEndpoints(r);
      return keepIds.has(from) && keepIds.has(to);
    });
    primaryLayer = connectionFormationStep === 1 ? "L1" : "all";
    nodes = annotateGraphNodes(nodes, primaryLayer);
    ({ nodes, rels } = applyAdvancedGraphFilters(nodes, rels));
    if (graphDensityMode === "compact") return applyCompactGraphFilter(nodes, rels);
    return { nodes, rels };
  }

  if (graphLayerFilter !== "all") {
    const primary = nodes.filter((n) => layerOf(n.label) === graphLayerFilter);
    const keepIds = new Set(primary.map((n) => n.id));
    let expanded = true;
    while (expanded) {
      expanded = false;
      rels.forEach((r) => {
        const { from, to } = relEndpoints(r);
        if (keepIds.has(from) && !keepIds.has(to)) {
          keepIds.add(to);
          expanded = true;
        }
        if (keepIds.has(to) && !keepIds.has(from)) {
          keepIds.add(from);
          expanded = true;
        }
      });
    }
    nodes = nodes.filter((n) => keepIds.has(n.id));
    rels = rels.filter((r) => {
      const { from, to } = relEndpoints(r);
      return keepIds.has(from) && keepIds.has(to);
    });
    nodes = annotateGraphNodes(nodes, graphLayerFilter);
  } else {
    nodes = annotateGraphNodes(nodes, "all");
  }

  ({ nodes, rels } = applyAdvancedGraphFilters(nodes, rels));

  if (graphDensityMode === "compact") {
    return applyCompactGraphFilter(nodes, rels);
  }

  return { nodes, rels };
}

let activeGuideSection = "pipeline";
const guideContentCache = new Map();
let docSectionsLoaded = false;

const DOC_SECTIONS_FALLBACK = [
  { id: "pipeline", title: "Пайплайн и слои L1–L6" },
  { id: "layer-agents", title: "Межслойные агенты (L1–L6)" },
  { id: "chat-agents", title: "Чат, роли и AI-агенты" },
  { id: "analytics-synthesis", title: "Аналитика и синтез ответов" },
  { id: "agent-hierarchy", title: "Иерархия агентов" },
  { id: "orchestrator", title: "Оркестратор L1–L6" },
  { id: "key-requirements", title: "Ключевые требования хакатона" },
  { id: "functional-filters", title: "Функциональные фильтры" },
  { id: "roles-vs-agents", title: "Роли vs агенты" },
  { id: "additional-wishes", title: "Дополнительные пожелания (MVP)" },
];

const DOC_STATIC_FALLBACK = {
  pipeline: "/static/docs/21_pipeline_and_layers.md",
  "layer-agents": "/static/docs/24_layer_agents.md",
  "chat-agents": "/static/docs/22_chat_agents.md",
  "analytics-synthesis": "/static/docs/25_analytics_synthesis.md",
  "agent-hierarchy": "/static/docs/agent_hierarchy.md",
  orchestrator: "/static/docs/orchestrator.md",
  "key-requirements": "/static/docs/25_key_requirements.md",
  "functional-filters": "/static/docs/25_functional_filters.md",
  "roles-vs-agents": "/static/docs/roles-vs-agents.md",
  "additional-wishes": "/static/docs/27_additional_wishes.md",
};

function docLoadingSkeletonHtml() {
  return `<div class="doc-loading-skeleton" aria-busy="true" aria-label="Загрузка">
    <div class="doc-skeleton-bar wide"></div>
    <div class="doc-skeleton-bar"></div>
    <div class="doc-skeleton-bar medium"></div>
    <div class="doc-skeleton-bar short"></div>
  </div>`;
}

function renderDocSectionTabs(sections) {
  if (!els.docSectionTabs) return;
  const items = sections?.length ? sections : DOC_SECTIONS_FALLBACK;
  els.docSectionTabs.innerHTML = items.map((s) => (
    `<button type="button" class="doc-section-tab doc-work-tab${s.id === activeGuideSection ? " active" : ""}"
      role="tab" aria-selected="${s.id === activeGuideSection}" data-guide="${esc(s.id)}">${esc(s.title)}</button>`
  )).join("");
  els.docSectionTabs.querySelectorAll(".doc-section-tab").forEach((btn) => {
    btn.addEventListener("click", () => loadDocSection(btn.dataset.guide));
  });
}

async function loadDocSections() {
  if (docSectionsLoaded && els.docSectionTabs?.children.length) return;
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 10000);
    const r = await fetch(`${API}/docs/sections`, { signal: ctrl.signal });
    clearTimeout(timer);
    if (!r.ok) throw new Error("sections unavailable");
    const sections = await r.json();
    renderDocSectionTabs(sections);
    docSectionsLoaded = true;
  } catch {
    renderDocSectionTabs(DOC_SECTIONS_FALLBACK);
    docSectionsLoaded = true;
  }
}

async function fetchDocPayload(slug) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 15000);
  try {
    const r = await fetch(`${API}/docs/${encodeURIComponent(slug)}`, { signal: ctrl.signal });
    if (r.ok) return await r.json();
  } catch {
    /* try static fallback below */
  } finally {
    clearTimeout(timer);
  }
  const staticPath = DOC_STATIC_FALLBACK[slug];
  if (staticPath) {
    const r2 = await fetch(staticPath);
    if (r2.ok) {
      const meta = DOC_SECTIONS_FALLBACK.find((s) => s.id === slug);
      return { id: slug, title: meta?.title || slug, content: await r2.text() };
    }
  }
  throw new Error("Документ недоступен");
}

async function renderMermaidBlocks(container) {
  if (typeof mermaid === "undefined" || !container) return;
  container.querySelectorAll(".mermaid[data-processed]").forEach((el) => el.remove());
  const blocks = container.querySelectorAll("pre code.language-mermaid, code.language-mermaid");
  for (const block of blocks) {
    const parent = block.closest("pre") || block;
    const src = block.textContent || "";
    if (!src.trim()) continue;
    const div = document.createElement("div");
    div.className = "mermaid";
    div.textContent = src.trim();
    parent.replaceWith(div);
  }
  const nodes = container.querySelectorAll(".mermaid:not([data-processed])");
  if (!nodes.length) return;
  try {
    await Promise.race([
      mermaid.run({ nodes }),
      new Promise((_, reject) => setTimeout(() => reject(new Error("mermaid timeout")), 12000)),
    ]);
  } catch (err) {
    console.warn("mermaid render:", err);
  }
}

function renderGuideMarkdown(md) {
  if (typeof marked === "undefined") return esc(md);
  const raw = marked.parse(md || "", { gfm: true, breaks: false });
  if (typeof DOMPurify !== "undefined") {
    return DOMPurify.sanitize(raw, { ADD_TAGS: ["pre", "code"], ADD_ATTR: ["class", "id"] });
  }
  return raw;
}

async function loadDocSection(slug) {
  if (!els.guideContent) return;
  activeGuideSection = slug || activeGuideSection;
  els.docSectionTabs?.querySelectorAll(".doc-section-tab").forEach((btn) => {
    const on = btn.dataset.guide === activeGuideSection;
    btn.classList.toggle("active", on);
    btn.setAttribute("aria-selected", on ? "true" : "false");
  });
  if (guideContentCache.has(activeGuideSection)) {
    els.guideContent.innerHTML = guideContentCache.get(activeGuideSection);
    await renderMermaidBlocks(els.guideContent);
    return;
  }
  els.guideContent.innerHTML = docLoadingSkeletonHtml();
  try {
    const data = await fetchDocPayload(activeGuideSection);
    const html = renderGuideMarkdown(data.content || "");
    guideContentCache.set(activeGuideSection, html);
    els.guideContent.innerHTML = html;
    await renderMermaidBlocks(els.guideContent);
  } catch (e) {
    els.guideContent.innerHTML = `<div class="doc-error-box"><p>Не удалось загрузить раздел.</p><p class="muted small">${esc(e.message || "ошибка")}</p><button type="button" class="btn btn-small btn-ghost doc-retry-btn">Повторить</button></div>`;
    els.guideContent.querySelector(".doc-retry-btn")?.addEventListener("click", () => {
      guideContentCache.delete(activeGuideSection);
      loadDocSection(activeGuideSection);
    });
  }
}

const loadGuideSection = loadDocSection;

function openDocGuide(slug) {
  if (slug) activeGuideSection = slug;
  switchPage("guide");
  loadDocSections().then(() => loadDocSection(activeGuideSection));
}

function switchPage(page) {
  if (!page) return;
  if (page === "graphs" || page === "fullgraph") page = "doc";
  if (page === "search" || page === "home") page = "docs";
  const prevGraphScope = graphScope;
  const prevGraphDocId = lastGraphDocId;
  currentPage = page;
  const isGraphView = page === "doc" || page === "graphAll";
  const isDocsArea = page === "docs" || isGraphView;
  const isInlineGraph = isInlineGraphPage(page);
  els.pageDocs?.classList.toggle("hidden", page !== "docs");
  els.pageGraphShell?.classList.toggle("hidden", !isGraphView);
  els.pageQdrant?.classList.toggle("hidden", page !== "qdrant");
  els.pageChats?.classList.toggle("hidden", page !== "chats");
  els.pageGuide?.classList.toggle("hidden", page !== "guide");
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
    const enteringAllScope = graphScope === "all"
      && (prevGraphScope !== "all" || prevGraphDocId !== GRAPH_ALL_ID);
    if (enteringAllScope) {
      graphLayerFilter = "all";
      clearGraphNodeSelection();
    }
    updateGraphScopeUI();
    updateDensityToggleUI();
    if (graphScope === "doc" && selectedDoc) {
      graphViewDocId = selectedDoc;
    }
    if (enteringAllScope) {
      loadGraph(GRAPH_ALL_ID, { force: true });
    } else {
      updateGraphsPageState();
    }
    if (graphVisible || graphScope === "all") refreshGraphViewport({ fit: true, force: true });
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
    updateDocWorkHeader(graphScope === "all" ? { id: GRAPH_ALL_ID } : docsListCache.find((d) => d.id === selectedDoc));
    refreshGraphViewport({ fit: true, force: true });
    window.MKGAuth?.syncDocsUploadFallback?.();
  } else {
    updateGraphScopeUI();
    updateGraphVisibility();
  }
  if (page === "docs") {
    loadDocuments();
    window.MKGAuth?.syncDocsUploadFallback?.();
  } else {
    updateDocWorkArea(null);
    if (page !== "docs") els.docWorkHeader?.classList.add("hidden");
  }
  if (page === "qdrant") {
    refreshEmbeddingStatus();
    renderL3Stats();
    loadQdrantClusterMap();
    loadQdrantPoints();
  }
  if (page === "guide") {
    loadDocSections().then(() => loadDocSection(activeGuideSection));
  }
  if (page === "settings") {
    loadDashboardStats();
    initTopicWatchlistUi();
  }
  if (page === "chats") window.MKGAuth?.refreshChatsPage();
}

window.MKG = {
  get selectedDoc() { return selectedDoc; },
  get currentPage() { return currentPage; },
  switchPage,
  openDocGuide,
  openDocWithMd,
  downloadDocumentMd,
  renderMarkdownHtml,
  renderDocPipelineHtml,
  getDocPipelineStates,
  formatLogEntry,
  ensurePipeline,
  indexEmbeddings,
  isDocIndexed: (docId) => {
    const doc = docsListCache.find((d) => d.id === docId);
    return isDocQdrantIndexed(doc || { id: docId });
  },
  markDocIndexed: (docId) => { indexedDocsSet.add(docId); saveIndexedDocs(); },
  showQdrantToast,
  isDocQdrantIndexed,
  trackPipelineDoc(docId) { if (docId) pipelineQueue.add(docId); },
  retryPipelineStage,
  bindRetryButtons,
  setPollUploadHook(fn) { pollUploadDocExternal = fn; },
};

function closeDetailPanel() {
  els.detailPanel.classList.add("hidden");
  els.detailBody.classList.remove("has-split");
  els.appRoot.classList.remove("has-detail");
  clearGraphEdgeHighlight();
}

function openDetailPanel(node) {
  if (!node) return;
  els.detailBody.classList.remove("has-split");
  if (node._collapsed) {
    if (els.detailTitle) els.detailTitle.textContent = "Узел";
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
  const multiDoc = node._multiDoc || multiDocCountByNodeId.get(node.id) || Number(props.multi_doc_count || 0);
  const multiDocBadge = multiDoc >= 2
    ? `<span class="detail-badge detail-badge-multidoc">связь с ${multiDoc} документами</span>`
    : "";

  if (els.detailTitle) els.detailTitle.textContent = `${layer} · ${node.label}`;
  els.detailBody.classList.add("has-split");
  els.detailBody.innerHTML = `
    <div class="detail-body-split">
      <div class="detail-body-main">
        <span class="detail-layer" style="background:${LAYER_COLOR[layer] || LAYER_COLOR["L?"]}">${esc(layer)} · ${esc(node.label)}</span>
        <div class="detail-id">${esc(node.id)} ${clusterBadge}${anomalyBadge}${multiDocBadge}</div>
        <section class="detail-section">
          <h4 class="detail-section-title">Метаданные узла</h4>
          ${propsHtml}
        </section>
      </div>
      <div class="detail-body-side detail-rels">
        <h4 class="detail-section-title">Входящие (${incoming.length})</h4>
        ${renderRelBlock(incoming, "in")}
        <h4 class="detail-section-title">Исходящие (${outgoing.length})</h4>
        ${renderRelBlock(outgoing, "out")}
      </div>
    </div>`;

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
      const nextLayer = btn.dataset.layer;
      if (nextLayer === graphLayerFilter) {
        if (nextLayer === "all" && els.appRoot?.classList.contains("has-detail")) {
          clearGraphNodeSelection();
        }
        return;
      }
      graphLayerFilter = nextLayer;
      clearGraphNodeSelection();
      if (connectionFormationMode) toggleConnectionFormationMode();
      scheduleGraphViewsRender();
    });
  });
  if (els.crossLayerToggle) {
    els.crossLayerToggle.classList.toggle("active", highlightCrossLayer);
  }
  if (els.connectionFormationBtn) {
    els.connectionFormationBtn.classList.toggle("active", connectionFormationMode);
  }
}

function renderGraphNodeList(nodes) {
  if (!nodes.length) {
    els.graphNodeList.innerHTML = '<div class="muted" style="padding:12px">Нет узлов</div>';
    return;
  }
  els.graphNodeList.innerHTML = nodes.slice(0, 200).map((n) => {
    const ghostCls = n._ghost ? " ghost-context" : "";
    const multiCls = (n._multiDoc || 0) >= 2 ? " multi-doc" : "";
    const multiBadge = (n._multiDoc || 0) >= 2 ? ` · 🔗${n._multiDoc}` : "";
    return `
    <button type="button" class="graph-node-item${ghostCls}${multiCls}" data-id="${esc(n.id)}">
      <div class="gn-label">${esc(n.label)}${esc(multiBadge)}</div>
      <div class="gn-id">${esc(shortNodeLabel(n))}</div>
      <div class="gn-layer">${esc(layerOf(n.label))}${n._ghost ? " · контекст" : ""}</div>
    </button>`;
  }).join("");
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
      <div class="rel-row ${cross ? "rel-cross-layer" : ""}${cross && highlightCrossLayer ? " highlighted" : ""}" data-from="${esc(from)}" data-to="${esc(to)}">
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
  return `${graphLayerFilter}|${highlightCrossLayer}|${connectionFormationMode}|${connectionFormationStep}|${graphDensityMode}|${graphViewMode}|${advancedFiltersSignature(graphAdvancedFilters)}|${graphDataKey(nodes, rels)}`;
}

function resetGraphNetwork() {
  clearTimeout(graphViewportTimer);
  graphViewportTimer = null;
  if (visNetwork) {
    visNetwork.destroy();
    visNetwork = null;
  }
  visNodesDataSet = null;
  visEdgesDataSet = null;
  lastGraphRenderKey = "";
  graphPhysicsStable = false;
}

function unfreezeGraphNodes() {
  if (!visNodesDataSet) return;
  const ids = visNodesDataSet.getIds();
  if (!ids.length) return;
  visNodesDataSet.update(ids.map((id) => ({ id, fixed: false })));
}

function freezeGraphPhysics() {
  if (!visNetwork || graphPhysicsStable) return;
  visNetwork.setOptions({ physics: { enabled: false } });
  if (visNodesDataSet && visNetwork) {
    const positions = visNetwork.getPositions(visNodesDataSet.getIds());
    visNodesDataSet.update(
      Object.entries(positions).map(([id, pos]) => ({
        id,
        x: pos.x,
        y: pos.y,
        fixed: { x: true, y: true },
      })),
    );
  }
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
        stabilization: { iterations: 55, fit: false, updateInterval: 20 },
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
      stabilization: { iterations: 80, fit: false, updateInterval: 25 },
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
  const nodeById = new Map(nodes.map((n) => [n.id, n]));
  const compact = graphDensityMode === "compact";
  const highlightContradictions = graphAdvancedFilters.active && graphAdvancedFilters.showContradictions;
  const highlightGaps = graphAdvancedFilters.active && graphAdvancedFilters.showGaps;
  const visNodes = nodes.map((n) => {
    const layer = layerOf(n.label);
    const baseColor = LAYER_COLOR[layer] || LAYER_COLOR["L?"];
    const isGhost = n._ghost === true;
    const multiDoc = n._multiDoc || multiDocCountByNodeId.get(n.id) || 0;
    const props = n.props || {};
    const clusterId = props.cluster_id;
    const isL4 = layer === "L4";
    const isAnomaly = props.is_anomaly === true || clusterId === -1;
    let label = shortGraphLabel(n);
    if (multiDoc >= 2) label = `${label}\n🔗${multiDoc}`;
    const colorBg = isGhost ? "rgba(176, 190, 197, 0.45)" : baseColor;
    let colorBorder = multiDoc >= 2 ? "#ff9800" : (isGhost ? "#b0bec5" : "#fff");
    let borderWidth = multiDoc >= 2 ? 2.5 : (isGhost ? 1 : 1);
    if (isL4 && clusterId != null && !isGhost) {
      if (isAnomaly) {
        colorBorder = QDRANT_VIZ_ANOMALY_COLOR;
        borderWidth = 3;
      } else if (clusterId >= 0) {
        colorBorder = clusterColor(clusterId);
        borderWidth = 2.5;
      }
    }
    if (highlightGaps && isGapNode(n)) {
      colorBorder = "#c62828";
      borderWidth = Math.max(borderWidth, 3);
      colorBg = isGhost ? colorBg : "#ffebee";
    }
    const clusterHint = props.cluster_name ? `\n⬤ ${props.cluster_name}` : "";
    const item = {
      id: n.id,
      label,
      title: `${n.label}: ${n.id}${clusterHint}${multiDoc >= 2 ? ` · связь с ${multiDoc} документами` : ""}${isGhost ? " · контекст другого слоя" : ""}${isAnomaly ? " · L4-аномалия" : ""}`,
      color: {
        background: colorBg,
        border: colorBorder,
        highlight: { background: isGhost ? "#78909c" : "#01579b", border: "#fff" },
      },
      font: {
        color: isGhost ? "#546e7a" : "#fff",
        size: compact ? 9 : 11,
        face: "Inter, sans-serif",
      },
      shape: n._collapsed ? "ellipse" : "box",
      margin: compact ? 4 : 8,
      widthConstraint: compact ? { maximum: 90 } : undefined,
      borderWidth,
      opacity: isGhost ? 0.55 : 1,
    };
    if (compact) item.level = nodeHierarchicalLevel(n.label);
    return item;
  });
  const edgeLimit = compact ? MAX_COMPACT_EDGES : 500;
  const visEdges = rels.slice(0, edgeLimit).map((r, i) => {
    const cross = isCrossLayerRel(r, layerMap);
    const emphasize = cross && highlightCrossLayer;
    const contradiction = highlightContradictions && isContradictionRel(r, nodeById);
    const gapEdge = highlightGaps && GAP_REL_TYPES.has(r.type);
    const showLabel = !compact && (emphasize || cross || contradiction || rels.length < 25);
    return {
      id: `e${i}`,
      from: r.from || r.from_,
      to: r.to,
      label: showLabel ? r.type : undefined,
      title: r.type,
      arrows: { to: { enabled: true, scaleFactor: compact ? 0.45 : 0.6 } },
      font: {
        size: emphasize || contradiction ? 9 : 8,
        align: "middle",
        strokeWidth: 0,
        color: contradiction ? "#c62828" : (emphasize ? "#e65100" : (cross ? "#e65100" : "#546e7a")),
      },
      color: contradiction
        ? { color: "rgba(198,40,40,0.95)", highlight: "#b71c1c" }
        : gapEdge
          ? { color: "rgba(183,28,28,0.75)", highlight: "#c62828" }
          : cross
            ? {
              color: emphasize ? "rgba(255,152,0,0.95)" : "rgba(255,152,0,0.55)",
              highlight: "#e65100",
            }
            : { color: "rgba(144,202,249,0.7)", highlight: "#0288d1" },
      width: contradiction ? 3 : (gapEdge ? 2.2 : (cross ? (emphasize ? 2.8 : (compact ? 1.2 : 2)) : 0.8)),
      smooth: { type: "dynamic", roundness: compact ? 0.35 : 0.5 },
      dashes: contradiction ? [8, 4] : (cross ? false : undefined),
    };
  });
  return { visNodes, visEdges };
}

function syncVisGraphData(visNodes, visEdges, { clearPositions = false } = {}) {
  if (!visNodesDataSet || !visEdgesDataSet) return;
  const nodeIds = new Set(visNodes.map((n) => n.id));
  const edgeIds = new Set(visEdges.map((e) => e.id));
  const staleNodes = visNodesDataSet.getIds().filter((id) => !nodeIds.has(id));
  const staleEdges = visEdgesDataSet.getIds().filter((id) => !edgeIds.has(id));
  if (staleNodes.length) visNodesDataSet.remove(staleNodes);
  if (staleEdges.length) visEdgesDataSet.remove(staleEdges);
  const nodesToApply = clearPositions
    ? visNodes.map((n) => ({ ...n, x: undefined, y: undefined, fixed: false }))
    : visNodes;
  visNodesDataSet.update(nodesToApply);
  visEdgesDataSet.update(visEdges);
}

function ensureGraphContainerReady(callback, attempt = 0) {
  const wrap = els.graphCanvasWrap;
  if (!wrap || wrap.classList.contains("hidden")) return;
  if (wrap.offsetWidth >= 20 && wrap.offsetHeight >= 20) {
    callback();
    return;
  }
  if (attempt >= 12) {
    callback();
    return;
  }
  requestAnimationFrame(() => ensureGraphContainerReady(callback, attempt + 1));
}

function attachGraphStabilizationHandlers() {
  if (!visNetwork) return;
  graphPhysicsStable = false;
  let fitted = false;
  const onStable = () => {
    if (!visNetwork || fitted) return;
    fitted = true;
    freezeGraphPhysics();
    visNetwork.fit({ animation: { duration: 280, easingFunction: "easeInOutQuad" } });
  };
  visNetwork.once("stabilizationIterationsDone", onStable);
  visNetwork.once("stabilized", onStable);
}

function relayoutGraphNetwork(visNodes, visEdges, nodeCount) {
  if (!visNetwork || !visNodesDataSet) return;
  graphPhysicsStable = false;
  visNetwork.releaseNodePositions();
  syncVisGraphData(visNodes, visEdges, { clearPositions: true });
  visNetwork.setOptions(getVisNetworkOptions(nodeCount));
  attachGraphStabilizationHandlers();
  const iterations = Math.min(100, Math.max(40, nodeCount));
  visNetwork.stabilize(iterations);
}

function refreshGraphViewport({ fit = false, force = false } = {}) {
  if (!visNetwork) return;
  if (!force && graphPhysicsStable && !fit) return;
  clearTimeout(graphViewportTimer);
  graphViewportTimer = setTimeout(() => {
    graphViewportTimer = null;
    ensureGraphContainerReady(() => {
      if (!visNetwork) return;
      visNetwork.redraw();
      if (fit) {
        visNetwork.fit({ animation: { duration: 220, easingFunction: "easeInOutQuad" } });
      }
    });
  }, fit ? 0 : GRAPH_VIEWPORT_DEBOUNCE_MS);
}

function scheduleGraphViewsRender(opts = {}) {
  clearTimeout(graphViewsRenderTimer);
  graphViewsRenderTimer = setTimeout(() => {
    graphViewsRenderTimer = null;
    renderGraphViews(opts);
  }, GRAPH_FILTER_DEBOUNCE_MS);
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

  const prevDensity = lastGraphRenderKey.split("|")[2];
  const densityChanged = prevDensity && prevDensity !== graphDensityMode;

  if (visNetwork && visNodesDataSet && !densityChanged) {
    lastGraphRenderKey = renderKey;
    ensureGraphContainerReady(() => relayoutGraphNetwork(visNodes, visEdges, nodes.length));
    return;
  }

  resetGraphNetwork();
  els.graphCanvas.innerHTML = "";
  updateDensityToggleUI();
  visNodesDataSet = new vis.DataSet(visNodes);
  visEdgesDataSet = new vis.DataSet(visEdges);
  ensureGraphContainerReady(() => {
    if (!els.graphCanvas) return;
    visNetwork = new vis.Network(
      els.graphCanvas,
      { nodes: visNodesDataSet, edges: visEdgesDataSet },
      getVisNetworkOptions(nodes.length),
    );
    visNetwork.on("click", (params) => {
      if (!params.nodes.length) return;
      const nodeId = params.nodes[0];
      const node = nodes.find((n) => n.id === nodeId) || graphData.nodes.find((n) => n.id === nodeId);
      const multi = params.event?.srcEvent?.ctrlKey || params.event?.srcEvent?.metaKey;
      if (graphComparePanelOpen && node && COMPARE_ENTITY_LABELS.has(node.label)) {
        toggleCompareNodeSelection(node, { multi });
        return;
      }
      openDetailPanel(node);
    });
    attachGraphStabilizationHandlers();
    lastGraphRenderKey = renderKey;
  });
}

const L4_OUTLIERS_HELP = "HDBSCAN noise: точки L4 с cluster_id = −1, не вошедшие ни в один кластер.";

function l4PointsLabel(n) {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return "точка";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return "точки";
  return "точек";
}

function renderGraphClusterLegend(nodes) {
  if (!els.graphClusterLegend) return;
  const clusters = new Map();
  let outliers = 0;
  nodes.forEach((n) => {
    if (layerOf(n.label) !== "L4") return;
    const props = n.props || {};
    const cid = props.cluster_id;
    if (props.is_anomaly || cid === -1) {
      outliers += 1;
      return;
    }
    if (cid == null || cid < 0) return;
    const key = Number(cid);
    if (!clusters.has(key)) {
      clusters.set(key, {
        id: key,
        name: props.cluster_name || `Кластер ${key}`,
        color: clusterColor(key),
        count: 0,
      });
    }
    clusters.get(key).count += 1;
  });
  if (!clusters.size && !outliers) {
    els.graphClusterLegend.classList.add("hidden");
    els.graphClusterLegend.innerHTML = "";
    return;
  }
  const clusterItems = [...clusters.values()].sort((a, b) => a.id - b.id).slice(0, 12);
  const clusterHtml = clusterItems.map((it) => `
    <span class="graph-cluster-legend-item" title="${esc(it.name)}">
      <span class="graph-cluster-legend-swatch" style="border-color:${it.color}"></span>
      <span class="graph-cluster-legend-label">${esc(it.name)}</span>
      <span class="graph-cluster-legend-count muted">${it.count}</span>
    </span>`).join("");
  const outliersHtml = outliers
    ? `<div class="graph-toolbar-legend-outliers">
        <span class="graph-cluster-legend-item graph-cluster-legend-outlier">
          <span class="graph-cluster-legend-swatch" style="border-color:${QDRANT_VIZ_ANOMALY_COLOR}"></span>
          <span class="graph-cluster-legend-label" title="${esc(L4_OUTLIERS_HELP)}">Выбросы L4: ${outliers}</span>
        </span>
      </div>`
    : "";
  els.graphClusterLegend.innerHTML = `
    <div class="graph-toolbar-legend-clusters">${clusterHtml}</div>
    ${outliersHtml}`;
  els.graphClusterLegend.classList.remove("hidden");
}

function renderGraphViews(opts = {}) {
  const skipLayerFilters = opts.skipLayerFilters === true;
  if (!skipLayerFilters) renderLayerFilters();
  updateCrossLayerStat();
  const { nodes, rels } = filteredGraph();
  renderGraphNodeList(nodes);
  renderGraphClusterLegend(nodes);
  if (graphViewMode === "rels") {
    renderAllRelationshipsList();
  } else {
    renderGraphMap(nodes, rels);
  }
  renderL3Stats();
}

function getGraphMinHeight() {
  return Math.max(400, Math.round(window.innerHeight * 0.6));
}

function getGraphMaxHeight() {
  return Math.round(window.innerHeight * 0.92);
}

function initGraphToolbarCollapse() {
  const shell = els.graphToolbarShell;
  const toggle = els.graphToolbarToggle;
  if (!shell || !toggle) return;
  const key = "mkg_graph_filters_open";
  const legacy = localStorage.getItem("mkg_graph_toolbar_collapsed");
  if (localStorage.getItem(key) === null && legacy !== null) {
    localStorage.setItem(key, legacy === "1" ? "false" : "true");
  }
  const setOpen = (open) => {
    shell.classList.toggle("collapsed", !open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    toggle.title = open ? "Свернуть фильтры слоёв" : "Развернуть фильтры слоёв";
  };
  setOpen(localStorage.getItem(key) !== "false");
  toggle.addEventListener("click", () => {
    const open = shell.classList.contains("collapsed");
    setOpen(open);
    localStorage.setItem(key, open ? "true" : "false");
    refreshGraphViewport({ force: true });
  });
}

function initGraphResize() {
  const handle = els.graphResizeHandle;
  const wrap = els.graphCanvasWrap;
  if (!handle || !wrap) return;
  const minH = getGraphMinHeight();
  const saved = localStorage.getItem("mkg_graph_h");
  if (saved) {
    const parsed = parseInt(saved, 10);
    const h = Math.max(minH, Math.min(getGraphMaxHeight(), Number.isFinite(parsed) ? parsed : minH));
    wrap.style.height = `${h}px`;
    if (parsed !== h) localStorage.setItem("mkg_graph_h", String(h));
  }
  let startY = 0;
  let startH = 0;
  const onMove = (e) => {
    const h = Math.max(getGraphMinHeight(), Math.min(getGraphMaxHeight(), startH + (e.clientY - startY)));
    wrap.style.height = `${h}px`;
    refreshGraphViewport({ force: true });
  };
  const onUp = () => {
    document.body.classList.remove("mkg-resizing-row");
    localStorage.setItem("mkg_graph_h", String(wrap.offsetHeight));
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("mouseup", onUp);
  };
  handle.addEventListener("mousedown", (e) => {
    e.preventDefault();
    startY = e.clientY;
    startH = wrap.offsetHeight;
    document.body.classList.add("mkg-resizing-row");
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  });
}

function getGraphNodePanelMinHeight() {
  return 160;
}

function getGraphNodePanelMaxHeight() {
  return Math.round(window.innerHeight * 0.55);
}

function syncGraphNodePanelHandle() {
  const hidden = els.graphMapView?.classList.contains("graph-node-list-hidden");
  els.graphNodePanelResizeHandle?.classList.toggle("hidden", !!hidden || !graphNodeListVisible);
}

function applyGraphNodePanelHeight(h) {
  const list = els.graphNodeList;
  if (!list) return h;
  const clamped = Math.max(getGraphNodePanelMinHeight(), Math.min(getGraphNodePanelMaxHeight(), h));
  list.style.height = `${clamped}px`;
  list.style.maxHeight = `${clamped}px`;
  return clamped;
}

function initGraphNodePanelResize() {
  const handle = els.graphNodePanelResizeHandle;
  if (!handle || !els.graphNodeList) return;

  const saved = localStorage.getItem("mkg_graph_node_h");
  const parsed = saved ? parseInt(saved, 10) : 280;
  applyGraphNodePanelHeight(Number.isFinite(parsed) ? parsed : 280);
  syncGraphNodePanelHandle();

  let startY = 0;
  let startH = 0;
  const onMove = (e) => {
    applyGraphNodePanelHeight(startH + (e.clientY - startY));
  };
  const onUp = () => {
    document.body.classList.remove("mkg-resizing-row");
    localStorage.setItem("mkg_graph_node_h", String(parseInt(els.graphNodeList.style.height || "280", 10)));
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("mouseup", onUp);
  };
  handle.addEventListener("mousedown", (e) => {
    if (els.graphMapView?.classList.contains("graph-node-list-hidden")) return;
    e.preventDefault();
    startY = e.clientY;
    startH = parseInt(els.graphNodeList.style.height || "280", 10);
    document.body.classList.add("mkg-resizing-row");
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  });
}

function toggleGraphNodeList() {
  graphNodeListVisible = !graphNodeListVisible;
  els.graphMapView?.classList.toggle("graph-node-list-hidden", !graphNodeListVisible);
  els.toggleNodeListBtn?.classList.toggle("active", graphNodeListVisible);
  syncGraphNodePanelHandle();
  refreshGraphViewport({ force: true });
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
  const force = opts.force === true;
  const docChanged = docId !== lastGraphDocId;
  if (docChanged) {
    resetGraphNetwork();
    lastGraphDocId = docId;
    lastGraphDataKey = "";
    clearGraphNodeSelection();
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
      updateGraphEmptyState(docsListCache.find((d) => d.id === docId));
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
    multiDocCountByNodeId = buildMultiDocCountMap(nodes);
    lastGraphDataKey = newKey;
    populateGraphGeographyOptions();
    updateGraphFilterStatus();
    if (!dataChanged && !force) {
      updateCrossLayerStat();
      if (!silent) renderGraphViews();
      return;
    }
    if (force && !docChanged) clearGraphNodeSelection();
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
  const doc = docsListCache.find((d) => d.id === selectedDoc);
  if (doc && isAnswersOnlyMode(doc)) {
    await startFullPipeline(selectedDoc, els.docPrimaryBtn);
    return;
  }
  if (els.docPrimaryBtn) els.docPrimaryBtn.disabled = true;
  await fetch(`${API}/documents/${encodeURIComponent(selectedDoc)}/submit`, { method: "POST" });
  pipelineQueue.add(selectedDoc);
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
    refreshGraphViewport({ fit: true, force: true });
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
  if (docPanelMode === "logs") loadLogs(id, { force: true });
  updateGraphsPageState();
  if (currentPage === "docs") renderDocsList();
  if (currentPage === "qdrant") {
    loadQdrantPoints();
    loadQdrantClusterMap();
    renderL3Stats();
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
      forceGraph: isDocGraphLive(selectedDoc),
    });
  } catch { /* ignore */ }
}

async function loadDocuments() {
  return renderDocsList();
}

function renderDocsListLoading() {
  if (!els.docs) return;
  els.docs.innerHTML = '<div class="muted docs-list-loading">Загрузка документов…</div>';
}

function isTransientFetchError(err) {
  const msg = String(err?.message || err || "").toLowerCase();
  return msg.includes("failed to fetch") || msg.includes("networkerror") || msg.includes("load failed");
}

async function fetchDocumentsPage() {
  const url = `${API}/documents?page=1&page_size=50`;
  let lastErr;
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      return await fetch(url);
    } catch (e) {
      lastErr = e;
      if (attempt === 0 && isTransientFetchError(e)) {
        await new Promise((resolve) => setTimeout(resolve, 800));
        continue;
      }
      throw e;
    }
  }
  throw lastErr;
}

function renderDocsListError(message, status) {
  if (!els.docs) return;
  const detail = status ? `HTTP ${status}` : esc(message || "неизвестная ошибка");
  els.docs.innerHTML = `<div class="doc-error-box docs-list-error">
    <p>Не удалось загрузить документы</p>
    <p class="muted small">${detail}</p>
    <button type="button" class="btn btn-small btn-ghost doc-retry-btn" id="docsListRetryBtn">Повторить</button>
  </div>`;
  els.docs.querySelector("#docsListRetryBtn")?.addEventListener("click", () => renderDocsList());
  window.MKGAuth?.syncDocsUploadFallback?.();
}

async function renderDocsList({ silent = false } = {}) {
  if (!els.docs) return;
  const seq = ++docsListFetchSeq;
  const showLoading = !docsListLoaded && !silent;
  if (showLoading) renderDocsListLoading();
  try {
    const r = await fetchDocumentsPage();
    if (seq !== docsListFetchSeq) return;
    if (!r.ok) {
      let detail = "";
      try {
        const err = await r.json();
        detail = err.detail || err.message || "";
      } catch { /* ignore */ }
      if (silent && docsListLoaded) return;
      renderDocsListError(detail || r.statusText, r.status);
      return;
    }
    const data = await r.json();
    if (seq !== docsListFetchSeq) return;
    docsListLoaded = true;
    docsListCache = data.items || [];
    docsTotalCount = typeof data.total === "number" ? data.total : docsListCache.length;
    notifyWatchlistMatches(docsListCache);
    updateGraphsPageState();
    renderL3Stats();
    if (embeddingStatusCache && els.l3EmbeddingStatus) {
      els.l3EmbeddingStatus.textContent = formatEmbeddingStatus(embeddingStatusCache);
    }
    if (!data.items?.length) {
      els.docs.innerHTML = '<div class="muted">Пока нет документов — загрузите файл выше</div>';
      window.MKGAuth?.syncDocsUploadFallback?.();
      return;
    }
    const q = docListFilterText.trim().toLowerCase();
    const filtered = q
      ? data.items.filter((d) => (d.file_name || d.id || "").toLowerCase().includes(q))
      : data.items;
    if (!filtered.length) {
      els.docs.innerHTML = '<div class="muted">Нет документов по фильтру</div>';
      window.MKGAuth?.syncDocsUploadFallback?.();
      return;
    }
    els.docs.innerHTML = filtered.map(renderDocCard).join("");
    bindDocCards(els.docs);
    const sel = docsListCache.find((x) => x.id === selectedDoc);
    updateDocWorkArea(sel || null);
    await pollSelectedDocumentPreview();
    for (const id of [...pipelineQueue]) {
      try {
        await ensurePipeline(id);
      } catch { /* per-doc pipeline errors must not break the list */ }
    }
    window.MKGAuth?.syncDocsUploadFallback?.();
  } catch (e) {
    if (seq !== docsListFetchSeq) return;
    if (silent && docsListLoaded) return;
    renderDocsListError(e.message || String(e));
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
  els.docUploadFallbackBtn?.addEventListener("click", (e) => { e.stopPropagation(); openFilePicker(); });
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
  els.l3IndexBtn?.addEventListener("click", () => {
    if (!selectedDoc) {
      appendQdrantLog("Выберите документ на вкладке «Документы» для индексации одного файла", true);
      return;
    }
    indexEmbeddings(selectedDoc);
  });
  els.l3IndexAllBtn?.addEventListener("click", indexAllEmbeddings);
  els.l4ClusterBtn?.addEventListener("click", runL4Clustering);
  els.qdrantSearchForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    runSearch(els.qdrantSearchQuery?.value, els.qdrantSearchResults);
  });
  els.qdrantSearchKeyword?.addEventListener("input", () => {
    if (!lastQdrantSearchHits.length) return;
    renderQdrantSearchResults(els.qdrantSearchResults, { showDoc: true });
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
        activateAllDocumentsGraph();
      } else {
        viewGraph();
      }
    } else if (action === "full") {
      startFullPipeline(selectedDoc, els.docPrimaryBtn);
    } else submitToGraph();
  });
  els.graphEmptyActionBtn?.addEventListener("click", () => {
    const docId = els.graphEmptyActionBtn?.dataset.docId || selectedDoc;
    startFullPipeline(docId, els.graphEmptyActionBtn);
  });
  els.docRebuildGraphBtn?.addEventListener("click", rebuildGraphConnections);
  els.docReprocessBtn?.addEventListener("click", async () => {
    if (!selectedDoc) return;
    await fetch(`${API}/documents/${encodeURIComponent(selectedDoc)}/reprocess`, { method: "POST" });
    await openDoc(selectedDoc, { keepPage: true });
  });
  els.docMdBtn?.addEventListener("click", () => toggleDocPanel("md"));
  els.docLogsBtn?.addEventListener("click", () => toggleDocPanel("logs"));
  els.mdViewCleanBtn?.addEventListener("click", () => setMdViewMode("clean"));
  els.mdViewRawBtn?.addEventListener("click", () => setMdViewMode("raw"));
  els.mdViewMarkedBtn?.addEventListener("click", () => setMdViewMode("marked"));
  els.mdInlineCleanBtn?.addEventListener("click", () => setMdViewMode("clean"));
  els.mdInlineRawBtn?.addEventListener("click", () => setMdViewMode("raw"));
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
    highlightCrossLayer = !highlightCrossLayer;
    els.crossLayerToggle?.classList.toggle("active", highlightCrossLayer);
    scheduleGraphViewsRender();
  });
  els.connectionFormationBtn?.addEventListener("click", toggleConnectionFormationMode);
  els.toggleNodeListBtn?.addEventListener("click", toggleGraphNodeList);
  els.viewMapBtn?.addEventListener("click", () => setGraphViewMode("map"));
  els.viewRelsBtn?.addEventListener("click", () => setGraphViewMode("rels"));
  els.originalGraphBtn?.addEventListener("click", resetGraphFilters);
  els.headerNeo4jBtn?.addEventListener("click", openNeo4jBrowser);
  els.graphCompareBtn?.addEventListener("click", toggleGraphComparePanel);
  els.graphCompareClearBtn?.addEventListener("click", () => {
    compareSelectedNodeIds.clear();
    renderCompareSelectedChips();
    renderCompareTable();
  });
  els.graphCompareRefreshBtn?.addEventListener("click", renderCompareTable);
  els.dashboardRefreshBtn?.addEventListener("click", loadDashboardStats);
  bindTopicWatchlistEvents();
  initGraphToolbarCollapse();
  initGraphAdvancedFilters();
  initQdrantPostFilters();
  initGraphResize();
  initGraphNodePanelResize();
}

function boot() {
  if (window.marked?.setOptions) {
    window.marked.setOptions({ breaks: true, gfm: true });
  }
  if (typeof mermaid !== "undefined") {
    mermaid.initialize({ startOnLoad: false, theme: "neutral", securityLevel: "loose" });
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
  setInterval(() => renderDocsList({ silent: true }), 1500);
  setInterval(refreshEmbeddingStatus, 30000);
  window.MKGAuth?.init();
}

boot();
