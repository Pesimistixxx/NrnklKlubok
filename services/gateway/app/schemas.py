"""Pydantic-схемы API gateway."""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DocStatus(str, Enum):
    uploaded = "uploaded"
    processing = "processing"
    md_ready = "md_ready"
    extracting = "extracting"
    loaded = "loaded"
    failed = "failed"


class DocumentOut(BaseModel):
    id: str
    file_name: str
    doc_type: str | None = None
    mime_type: str | None = None
    classification: str = "открытый"
    organization: str | None = None
    hash_sum: str
    status: DocStatus
    upload_date: datetime
    size_bytes: int
    step: str | None = None
    error: str | None = None
    neo4j_synced: bool | None = None
    graph_nodes: int | None = None
    graph_relationships: int | None = None
    processing_mode: str | None = "full"
    l4_clusters: int | None = None
    l4_anomalies: int | None = None
    l4_clustered: int | None = None
    source_location: str | None = None
    geography: str | None = None
    material_date: date | None = None
    tags: list[str] = Field(default_factory=list)
    ingested_at: datetime | None = None


class DocumentList(BaseModel):
    items: list[DocumentOut]
    total: int
    page: int
    page_size: int
    restricted_count: int = 0


class BatchUploadItem(BaseModel):
    file_name: str
    document: DocumentOut | None = None
    error: str | None = None


class BatchUploadOut(BaseModel):
    uploaded: int
    failed: int
    items: list[BatchUploadItem]


class FormatsOut(BaseModel):
    extensions: list[str]
    max_size_bytes: int
    groups: dict[str, list[str]]


class RuntimeConfigOut(BaseModel):
    llm_model: str
    ocr_model: str
    emb_doc_model: str
    emb_query_model: str
    llm_models: list[str]
    ocr_models: list[str]
    emb_doc_models: list[str]
    emb_query_models: list[str]
    ocr_model_labels: dict[str, str] = Field(default_factory=dict)
    emb_model_labels: dict[str, str] = Field(default_factory=dict)
    services: list[dict[str, Any]] = Field(default_factory=list)


class PipelineLogOut(BaseModel):
    document_id: str
    items: list[dict[str, Any]]


class ClearDatabaseOut(BaseModel):
    ok: bool
    storage: dict[str, int]
    postgres_documents: int
    neo4j_cleared: bool


class ReindexEntitiesOut(BaseModel):
    documents: int
    indexed: int
    skipped: int
    collection: str
    per_document: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class ReindexCorpusOut(BaseModel):
    documents: int
    indexed_l3: int
    indexed_l4: int
    indexed_entities: int
    skipped: int
    per_document: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class RuntimeConfigUpdate(BaseModel):
    llm_model: str | None = None
    ocr_model: str | None = None
    emb_doc_model: str | None = None
    emb_query_model: str | None = None


class DiagnosticsOut(BaseModel):
    status: str
    env: str
    checks: list[dict[str, Any]]
    yandex_key_hint: str | None = None


class GraphNode(BaseModel):
    id: str
    label: str
    props: dict


class GraphRelationship(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: str
    from_: str = Field(alias="from")
    to: str
    props: dict


class GraphOut(BaseModel):
    document_id: str
    nodes: list[GraphNode]
    relationships: list[GraphRelationship]


class LayerRelationshipSample(BaseModel):
    from_: str = Field(alias="from")
    type: str
    to: str

    model_config = ConfigDict(populate_by_name=True)


class LayerPipelineItem(BaseModel):
    id: str
    title: str
    status: str
    nodes: int
    relationships: int
    relationship_samples: list[LayerRelationshipSample]


class LayerRecentRel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    from_: str = Field(alias="from", default="")
    from_short: str
    type: str
    to: str = ""
    to_short: str
    layer: str = ""
    props: dict = Field(default_factory=dict)


class GraphRelationshipDetailOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    document_id: str
    type: str
    from_: str = Field(alias="from")
    to: str
    props: dict = Field(default_factory=dict)
    layer: str = ""
    description: str = ""
    source_node: GraphNode | None = None
    target_node: GraphNode | None = None
    related_edges: list[GraphRelationship] = Field(default_factory=list)


class GraphRelationshipPatchIn(BaseModel):
    expert_comment: str = Field(..., min_length=1, max_length=4000)
    edited_by: str = Field(default="", max_length=120)
    role_id: str = Field(default="engineer", max_length=32)


class GraphRelationshipPatchOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    document_id: str
    type: str
    from_: str = Field(alias="from")
    to: str
    props: dict = Field(default_factory=dict)
    expert_edits_count: int = 0


class LayerPipelineOut(BaseModel):
    status: str | None = None
    step: str | None = None
    layers: list[LayerPipelineItem]
    total_nodes: int
    total_relationships: int
    recent_relationships: list[LayerRecentRel] = Field(default_factory=list)


# ── Agent API ────────────────────────────────────────────────────────────────


class AgentDocSummaryOut(BaseModel):
    id: str
    file_name: str
    status: str
    step: str | None = None
    error: str | None = None
    neo4j_synced: bool | None = None
    layer_counts: dict[str, int] = Field(default_factory=dict)
    total_nodes: int = 0
    total_relationships: int = 0
    layers: list[LayerPipelineItem] = Field(default_factory=list)


class AgentDocListOut(BaseModel):
    items: list[AgentDocSummaryOut]
    total: int
    page: int
    page_size: int


class AgentGraphOut(BaseModel):
    document_id: str
    nodes: list[GraphNode]
    relationships: list[GraphRelationship]


class AgentLayerDetailOut(BaseModel):
    document_id: str
    layer_id: str
    title: str
    nodes: list[GraphNode]
    relationships: list[GraphRelationship]
    node_count: int
    relationship_count: int


class AgentRelationshipsOut(BaseModel):
    document_id: str
    total: int
    relationships: list[GraphRelationship]


class AgentNodeDetailOut(BaseModel):
    document_id: str
    node: GraphNode
    layer: str
    text: str | None = None
    incoming: list[GraphRelationship]
    outgoing: list[GraphRelationship]
    neighbors: list[GraphNode]


class AgentNodesListOut(BaseModel):
    document_id: str
    total: int
    query: str | None = None
    layer: str | None = None
    label: str | None = None
    nodes: list[GraphNode] = Field(default_factory=list)


class AgentTextOut(BaseModel):
    document_id: str
    markdown: str
    paragraph_count: int
    with_paragraph_index: bool = False


class AgentParagraphOut(BaseModel):
    node_id: str
    index: int
    text: str
    char_start: int | None = None
    char_end: int | None = None


class AgentParagraphsOut(BaseModel):
    document_id: str
    source: str
    total: int
    paragraphs: list[AgentParagraphOut]


class AgentSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Поисковый запрос")
    limit: int = Field(default=10, ge=1, le=100)
    mode: str = Field(default="auto", description="auto | semantic | keyword")
    layers: list[str] | None = Field(default=None, description="Фильтр L1–L6")
    index_if_missing: bool = Field(
        default=True,
        description="Проиндексировать в Qdrant при первом semantic-поиске",
    )


class AgentSearchHit(BaseModel):
    node_id: str
    label: str
    layer: str
    score: float
    text: str
    props: dict[str, Any] = Field(default_factory=dict)
    mode: str = "keyword"
    document_id: str | None = None
    md_file: str = ""


class AgentSearchOut(BaseModel):
    document_id: str | None = None
    query: str
    mode: str
    hits: list[AgentSearchHit]
    index: dict[str, Any] | None = None
    note: str | None = None


class GlobalSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=20, ge=1, le=100)
    mode: str = Field(default="auto", description="auto | semantic")
    layers: list[str] | None = None
    document_ids: list[str] | None = Field(
        default=None,
        description="Ограничить поиск указанными документами",
    )
    role_id: str | None = Field(default=None, description="Роль для фильтра по грифу")


class UnifiedSearchRequest(GlobalSearchRequest):
    """Alias for POST /api/v1/search."""


class UnifiedSearchHit(BaseModel):
    node_id: str
    label: str
    layer: str
    score: float
    text: str
    document_id: str | None = None
    entity_type: str | None = None
    collection: str | None = None
    mode: str = "semantic"
    retrieval_factors: list[str] = Field(default_factory=list)
    cluster_id: int | None = None
    is_anomaly: bool | None = None
    anomaly_score: float | None = None
    md_file: str = ""


class UnifiedSearchOut(BaseModel):
    query: str
    mode: str
    hits: list[UnifiedSearchHit]
    total: int
    collections: dict[str, int] = Field(default_factory=dict)
    note: str | None = None


class EntitySearchHit(BaseModel):
    node_id: str
    entity_type: str
    label: str
    layer: str = "L1"
    score: float
    text: str
    document_id: str | None = None
    geography: str | None = None
    tags: list[str] = Field(default_factory=list)
    mode: str = "semantic"
    retrieval_factors: list[str] = Field(default_factory=list)


class EntitySearchOut(BaseModel):
    query: str
    types: list[str]
    hits: list[EntitySearchHit]
    total: int
    collection: str


class AgentOntologyLayer(BaseModel):
    id: str
    title: str
    node_labels: list[str]


class AgentOntologyOut(BaseModel):
    layers: list[AgentOntologyLayer]
    node_labels: dict[str, str]
    relationship_types: list[str]


class AgentEmbeddingCollection(BaseModel):
    purpose: str
    points: int


class AgentEmbeddingStatusOut(BaseModel):
    provider: str
    embed_doc_model: str
    embed_query_model: str
    embed_client: str
    qdrant_url: str
    qdrant_ok: bool = True
    total_points: int = 0
    entity_points: int | None = None
    collections: dict[str, AgentEmbeddingCollection]
    vector_size: int
    yandex_configured: bool
    auto_index_on_search: bool
    pipeline_auto_index: bool
    note: str


class AgentQdrantPointOut(BaseModel):
    collection: str
    point_id: str
    node_id: str | None = None
    neo4j_node_id: str | None = None
    document_id: str | None = None
    label: str | None = None
    layer: str | None = None
    text: str | None = None
    cluster_id: int | None = None
    cluster_name: str | None = None
    is_anomaly: bool | None = None
    anomaly_score: float | None = None


class AgentQdrantPointsOut(BaseModel):
    document_id: str
    total: int
    points: list[AgentQdrantPointOut]


class AgentQdrantVizPointOut(BaseModel):
    id: str
    x: float
    y: float
    layer: str | None = None
    cluster_id: int | None = None
    cluster_name: str | None = None
    cluster_description: str | None = None
    is_anomaly: bool | None = None
    anomaly_reason: str | None = None
    anomaly_score: float | None = None
    label: str | None = None
    node_id: str | None = None
    neo4j_node_id: str | None = None
    text: str | None = None
    document_id: str | None = None
    collection: str | None = None


class AgentClusterInfoOut(BaseModel):
    id: int
    name: str
    count: int = 0
    color: str | None = None
    description: str | None = None


class L4ClusteringContextOut(BaseModel):
    document_id: str | None = None
    doc_count: int = 0
    docs_with_graph: int = 0
    l3_points: int = 0
    l4_points: int = 0
    avg_l4_per_doc: float = 0.0
    min_cluster_size: int = 2
    min_samples: int = 2
    has_cluster_labels: bool = False
    cluster_count: int = 0
    anomaly_count: int = 0
    clustering_ran: bool = False


class AgentQdrantVizOut(BaseModel):
    document_id: str | None = None
    total: int
    l4_total: int = 0
    cluster_count: int = 0
    anomaly_count: int = 0
    has_clusters: bool = False
    has_named_clusters: bool = False
    method: str = "pca"
    layer_filter: str | None = None
    clusters: list[AgentClusterInfoOut] = Field(default_factory=list)
    points: list[AgentQdrantVizPointOut]
    clustering_context: L4ClusteringContextOut | None = None


class AgentEndpointOut(BaseModel):
    method: str
    path: str
    summary: str
    status: str = "ready"


class AgentCapabilityOut(BaseModel):
    id: str
    name_ru: str
    layer_scope: str
    implementation: str
    endpoints: list[AgentEndpointOut]


class AgentCapabilitiesOut(BaseModel):
    project_stage: str
    stage_label_ru: str
    agents: list[AgentCapabilityOut]


class RoleOut(BaseModel):
    id: str
    name_ru: str
    agent_id: str
    agents_user_role: str
    can_upload: bool
    can_extract: bool
    can_admin: bool
    can_run_agents: bool
    description: str
    icon: str = "•"
    tagline: str = ""
    accent_color: str = "#0071e3"
    capability_ru: str = ""
    differs_from: str = ""
    allowed_classifications: list[str] = Field(default_factory=lambda: ["открытый"])


class RolesOut(BaseModel):
    roles: list[RoleOut]


class DataAccessOut(BaseModel):
    classifications: list[str]
    roles: list[str]
    role_names: dict[str, str] = Field(default_factory=dict)
    matrix: dict[str, dict[str, bool]]
    defaults: dict[str, list[str]] = Field(default_factory=dict)
    current_role: str = "viewer"
    allowed_classifications: list[str] = Field(default_factory=lambda: ["открытый"])


class DataAccessUpdate(BaseModel):
    matrix: dict[str, dict[str, bool]]


class RolePromptOut(BaseModel):
    role_id: str
    name_ru: str
    system_prompt: str
    default_prompt: str
    is_custom: bool


class RolePromptUpdate(BaseModel):
    system_prompt: str = Field(..., min_length=1, max_length=12000)


class UserSessionIn(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    role_id: str = Field(..., min_length=1, max_length=32)
    user_id: str | None = None


class UserOut(BaseModel):
    id: str
    display_name: str
    role_id: str
    created_at: datetime | None = None
    last_seen_at: datetime | None = None


class ChatThreadCreate(BaseModel):
    title: str = Field(default="Новый чат", max_length=200)
    kind: str = Field(default="team", pattern="^(team|agent)$")
    created_by: str | None = None


class ChatThreadUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class ChatThreadOut(BaseModel):
    id: str
    title: str
    kind: str
    created_by: str | None = None
    created_at: datetime | None = None
    message_count: int = 0
    last_message_at: datetime | None = None


class ChatThreadsOut(BaseModel):
    items: list[ChatThreadOut]
    total: int


class MessageCreate(BaseModel):
    author_id: str | None = None
    author_name: str = Field(..., min_length=1, max_length=120)
    author_role: str
    body: str = Field(..., min_length=1, max_length=20000)
    msg_type: str = Field(default="user", pattern="^(user|agent|system)$")
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "JSON meta; for agent messages may include trace, layer_results and graph "
            "(nodes, relationships, graph_walk_steps, walk_path) — trimmed server-side"
        ),
    )


class MessageUpdate(BaseModel):
    body: str = Field(..., min_length=1, max_length=20000)


class ChatMessageOut(BaseModel):
    id: str
    thread_id: str
    author_id: str | None = None
    author_name: str
    author_role: str
    body: str
    msg_type: str
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class ChatMessagesOut(BaseModel):
    thread_id: str
    items: list[ChatMessageOut]
    total: int


class ChatHistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=8000)


class ChatCompleteIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    role_id: str
    history: list[ChatHistoryTurn] = Field(default_factory=list, max_length=20)
    system_prompt: str | None = Field(default=None, max_length=12000)
    include_graph: bool = True
    include_artifacts: bool = True
    speed_mode: Literal["fast", "full", "compare"] = Field(
        default="full",
        description="fast — RAG за ~3–4 с; full — оркестратор; compare — таблица сравнения технологий",
    )
    document_ids: list[str] = Field(
        default_factory=list,
        description="Ограничить поиск Qdrant документами, загруженными в чат",
    )
    ui_lang: str | None = Field(
        default=None,
        max_length=8,
        description="Язык UI (ru/en) — fallback, если язык запроса неоднозначен",
    )


class ChatArtifact(BaseModel):
    type: Literal["chart", "image"]
    title: str = ""
    chart_type: str | None = Field(default=None, description="bar | line | doughnut | pie")
    labels: list[str] = Field(default_factory=list)
    datasets: list[dict[str, Any]] = Field(default_factory=list)
    format: str | None = Field(default=None, description="svg для type=image")
    content: str | None = Field(default=None, description="SVG/HTML содержимое для type=image")


class ContextGraphOut(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    relationships: list[GraphRelationship] = Field(default_factory=list)
    seed_count: int = 0
    document_ids: list[str] = Field(default_factory=list)
    graph_walk_steps: list[dict[str, Any]] = Field(default_factory=list)
    walk_path: list[dict[str, Any]] = Field(default_factory=list)


class ChatSourceOut(BaseModel):
    document_id: str
    file_name: str = ""
    node_id: str = ""
    label: str = ""
    layer: str = ""
    score: float = 0
    text: str = ""
    md_file: str = ""
    md_url: str = ""
    extraction_confidence: float | None = None
    source_date: str | None = None


class ChatCompleteOut(BaseModel):
    reply: str
    trace: list[dict[str, Any]] = Field(default_factory=list)
    graph: ContextGraphOut | None = None
    artifacts: list[ChatArtifact] = Field(default_factory=list)
    sources: list[ChatSourceOut] = Field(default_factory=list)
    layer_results: list[dict[str, Any]] | None = None
    timing_ms: int = 0
    speed_mode: Literal["fast", "full", "compare"] = "full"


class QueryTestIn(BaseModel):
    """Тело POST /api/v1/query — программное тестирование сложных вопросов."""

    question: str = Field(..., min_length=1, max_length=8000)
    role_id: str = "researcher"
    mode: str | None = Field(default=None, description="dialog | hypothesis_mode | audit_mode | …")
    history: list[ChatHistoryTurn] = Field(default_factory=list, max_length=20)
    include_graph: bool = True
    include_artifacts: bool = True
    system_prompt: str | None = None


class QueryTestOut(BaseModel):
    answer: str
    trace: list[dict[str, Any]] = Field(default_factory=list)
    graph: ContextGraphOut | None = None
    artifacts: list[ChatArtifact] = Field(default_factory=list)
    timing_ms: int = 0
    mode: str = "dialog"


class AgentServiceRunIn(BaseModel):
    query: str = Field(..., min_length=1)
    mode: str | None = None
    doc_ids: list[str] = Field(default_factory=list)
    user_role: str = "researcher"
    limit: int = Field(default=5, ge=1, le=20)
    history: list[ChatHistoryTurn] = Field(default_factory=list, max_length=20)
    speed_mode: Literal["fast", "full", "compare"] = "full"


class AgentServiceRunOut(BaseModel):
    mode: str
    query: str
    elapsed_ms: int = 0
    summary: str = ""
    issues: list[dict[str, Any]] = Field(default_factory=list)
    hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    anomalies: list[dict[str, Any]] = Field(default_factory=list)
    literature_review: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    graph: ContextGraphOut | None = None
    trace: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    layer_results: list[dict[str, Any]] | None = None
    orchestrator_plan: dict[str, Any] | None = None


class AgentServiceModeInfo(BaseModel):
    id: str
    title: str
    description: str


class AgentServiceModesOut(BaseModel):
    modes: list[AgentServiceModeInfo]


class L4ClusterRequest(BaseModel):
    document_id: str | None = Field(None, description="Опционально: проиндексировать документ перед глобальной кластеризацией")
    min_cluster_size: int | None = Field(None, ge=2, le=50)


class L4ClusterOut(BaseModel):
    document_id: str | None = None
    clustered: int = 0
    anomalies: int = 0
    points: int = 0
    clusters: int = 0
    global_: bool = Field(default=True, alias="global")
    cluster_names: dict[str, str] = Field(default_factory=dict)
    cluster_descriptions: dict[str, str] = Field(default_factory=dict)
    named_clusters: list[dict[str, Any]] = Field(default_factory=list)
    min_cluster_size: int | None = None
    min_samples: int | None = None
    all_noise: bool | None = None
    noise_hint: str | None = None
    message: str | None = None
    debounced: bool | None = None

    model_config = {"populate_by_name": True}


class L4ClusterEdgeOut(BaseModel):
    document_id: str | None = None
    from_node: str = ""
    to_node: str = ""
    type: str = ""
    from_label: str | None = None
    to_label: str | None = None
    from_short: str = ""
    to_short: str = ""
    from_text: str = ""
    to_text: str = ""
    layer: str = "L?"
    description: str = ""
    other_cluster_id: int | None = None
    other_cluster_name: str | None = None


class L4ClusterMemberOut(BaseModel):
    node_id: str
    document_id: str = ""
    label: str = ""
    text: str = ""


class L4ClusterDetailOut(BaseModel):
    cluster_id: int
    cluster_name: str
    cluster_description: str = ""
    point_count: int = 0
    members: list[L4ClusterMemberOut] = Field(default_factory=list)
    internal_edges: list[L4ClusterEdgeOut] = Field(default_factory=list)
    cross_cluster_edges: list[L4ClusterEdgeOut] = Field(default_factory=list)
    clustering_context: L4ClusteringContextOut | None = None


class L4NearestClusterOut(BaseModel):
    cluster_id: int
    cluster_name: str = ""
    distance: float = 0.0


class L4PointDetailOut(BaseModel):
    node_id: str
    point_id: str | None = None
    document_id: str = ""
    label: str = ""
    text: str = ""
    cluster_id: int | None = None
    cluster_name: str | None = None
    is_anomaly: bool = False
    anomaly_score: float | None = None
    anomaly_reason: str = ""
    nearest_cluster: L4NearestClusterOut | None = None
    edges: list[L4ClusterEdgeOut] = Field(default_factory=list)
    clustering_context: L4ClusteringContextOut | None = None


class AnomalyNodeOut(BaseModel):
    document_id: str | None = None
    node_id: str
    label: str = ""
    layer: str = "L4"
    text: str = ""
    cluster_id: int | None = None
    anomaly_score: float | None = None
    is_anomaly: bool = True
    anomaly_reason: str = ""
    props: dict[str, Any] = Field(default_factory=dict)


class AnomaliesListOut(BaseModel):
    total: int
    document_id: str | None = None
    items: list[AnomalyNodeOut] = Field(default_factory=list)
