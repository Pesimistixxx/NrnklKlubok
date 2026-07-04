"""Upload metadata: geography, source, material date, auto-tags for graph/Qdrant."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from mkg_core.graph_payload import GraphPayload
from mkg_core.ontology import L4_LABELS

_GEO_ALIASES: dict[str, str] = {
    "ru": "RU",
    "rf": "RU",
    "russia": "RU",
    "россия": "RU",
    "рф": "RU",
    "domestic": "RU",
    "отечественный": "RU",
    "отечественная": "RU",
    "foreign": "foreign",
    "international": "international",
    "зарубежный": "foreign",
    "зарубежная": "foreign",
    "международный": "international",
}

_EXTRACTED_LABELS = frozenset(L4_LABELS) | frozenset(
    {
        "Material",
        "Process",
        "Equipment",
        "ChemicalReagent",
        "StandardMetric",
        "PhaseState",
        "Property",
        "TechnologySolution",
        "EconomicIndicator",
        "EnvironmentalIndicator",
        "Expert",
        "Organization",
        "Location",
        "Event",
        "Facility",
    }
)


def normalize_geography(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    key = str(raw).strip().lower()
    return _GEO_ALIASES.get(key, str(raw).strip())


def parse_material_date(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()[:10]
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except ValueError:
        return None


def build_tags(
    *,
    geography: str | None,
    material_date: str | None,
    source_location: str | None,
) -> list[str]:
    tags: list[str] = []
    if geography:
        tags.append(f"geography:{geography}")
        geo_l = geography.lower()
        if geo_l in ("ru", "domestic", "россия", "рф"):
            tags.append("geo:domestic")
        elif geo_l in ("foreign", "international", "зарубежный", "зарубежная"):
            tags.append("geo:foreign")
    if material_date and len(material_date) >= 4:
        tags.append(f"year:{material_date[:4]}")
    if source_location:
        loc = source_location.strip()
        if loc:
            tags.append(f"source:{loc[:120]}")
    return tags


def prepare_upload_metadata(
    *,
    source_location: str | None = None,
    geography: str | None = None,
    material_date: str | None = None,
    upload_date: str | None = None,
) -> dict[str, Any]:
    src = (source_location or "").strip() or None
    geo = normalize_geography(geography) or None
    if not geo and src:
        geo = normalize_geography(src)
    mat_date = parse_material_date(material_date)
    ingested = upload_date or datetime.now(timezone.utc).isoformat()
    tags = build_tags(geography=geo, material_date=mat_date, source_location=src)
    out: dict[str, Any] = {"ingested_at": ingested}
    if src:
        out["source_location"] = src
    if geo:
        out["geography"] = geo
    if mat_date:
        out["material_date"] = mat_date
    if tags:
        out["tags"] = tags
    return out


def doc_meta_graph_props(rec: dict[str, Any]) -> dict[str, Any]:
    props: dict[str, Any] = {}
    for key in ("source_location", "geography", "material_date", "ingested_at"):
        val = rec.get(key)
        if val:
            props[key] = val
    tags = rec.get("tags")
    if tags:
        props["tags"] = list(tags) if isinstance(tags, (list, tuple)) else [str(tags)]
    return props


def qdrant_meta_payload(rec: dict[str, Any]) -> dict[str, Any]:
    """Subset of metadata for Qdrant point payload."""
    out: dict[str, Any] = {}
    for key in ("source_location", "geography", "material_date", "ingested_at"):
        val = rec.get(key)
        if val:
            out[key] = val
    tags = rec.get("tags")
    if tags:
        out["tags"] = list(tags) if isinstance(tags, (list, tuple)) else [str(tags)]
    return out


def apply_metadata_to_graph(payload: GraphPayload, document_id: str) -> GraphPayload:
    from mkg_core.store import get_repo

    rec = get_repo().get(document_id) or {}
    meta = doc_meta_graph_props(rec)
    if not meta:
        return payload

    nodes: list[dict[str, Any]] = []
    for node in payload.nodes:
        label = str(node.get("label") or "")
        node_id = str(node.get("id") or "")
        if label == "Document" and node_id == document_id:
            props = dict(node.get("props") or {})
            props.update(meta)
            for k in ("file_name", "hash_sum", "classification", "doc_type", "lang"):
                if rec.get(k):
                    props[k] = rec[k]
            nodes.append({**node, "props": props})
        elif label == "TextParagraph" or label in _EXTRACTED_LABELS:
            props = dict(node.get("props") or {})
            for k, v in meta.items():
                if v is not None and props.get(k) is None:
                    props[k] = v
            nodes.append({**node, "props": props})
        else:
            nodes.append(node)
    return GraphPayload(nodes=nodes, relationships=payload.relationships)
