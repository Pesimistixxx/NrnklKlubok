"""Pydantic-схемы API gateway."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

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


class DocumentList(BaseModel):
    items: list[DocumentOut]
    total: int
    page: int
    page_size: int


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
    from_short: str
    type: str
    to_short: str
    layer: str = ""


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


class AgentSearchOut(BaseModel):
    document_id: str
    query: str
    mode: str
    hits: list[AgentSearchHit]
    index: dict[str, Any] | None = None


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
    label: str | None = None
    layer: str | None = None
    text: str | None = None


class AgentQdrantPointsOut(BaseModel):
    document_id: str
    total: int
    points: list[AgentQdrantPointOut]


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
