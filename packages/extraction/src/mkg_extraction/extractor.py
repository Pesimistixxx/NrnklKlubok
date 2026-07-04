"""Extraction pipeline.

Режимы:
1) LLM-first (основной): L2 + L1/L4 + L6 через PromptRegistry + YandexLLMClient.
2) Rule-based fallback (если LLM недоступен).

При этом остальные слои тоже учитываются:
- L3 собирается детерминированно из markdown (TextParagraph/Heading/Lang).
- L5 собирается детерминированно (SecurityRole/VerificationStatus/AuditTrail + связи).
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import asyncio
from typing import Any

log = logging.getLogger(__name__)

from mkg_core import Neo4jClient, YandexLLMClient, get_settings
from mkg_core.api_errors import format_api_error, is_fatal_api_error
from mkg_core.graph_payload import GraphPayload, dedupe_graph_payload
from mkg_core.ontology import sanitize_graph_payload
from mkg_core.runtime_config import get_llm_model

try:
    from mkg_prompts import PromptRegistry
except Exception:  # pragma: no cover
    PromptRegistry = None  # type: ignore[misc,assignment]


class ExtractionCancelled(Exception):
    """Извлечение остановлено пользователем."""


def _check_cancel(document_id: str) -> None:
    from mkg_core.store import get_repo

    if get_repo().is_cancel_requested(document_id):
        raise ExtractionCancelled("Извлечение остановлено пользователем")


def _dedup_words(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for v in values:
        token = v.strip().lower()
        if len(token) < 3 or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def _contains_token(text: str, token: str) -> bool:
    if " " in token:
        return token in text
    return re.search(rf"(?<!\w){re.escape(token)}(?!\w)", text) is not None


def _generic_heuristic_terms(block: str) -> tuple[list[str], list[str]]:
    """Generic extraction when ontology dictionary is unavailable."""
    process_terms: list[str] = []
    material_terms: list[str] = []
    block_l = block.lower()
    process_patterns = (
        r"(?:процесс|метод|технология|этап)\s+([а-яa-z0-9][а-яa-z0-9 \-]{2,40})",
        r"(?:process|method|technology|stage)\s+([a-z0-9][a-z0-9 \-]{2,40})",
    )
    material_patterns = (
        r"(?:материал|вещество|сырье|реагент)\s+([а-яa-z0-9][а-яa-z0-9 \-]{2,40})",
        r"(?:material|substance|reagent)\s+([a-z0-9][a-z0-9 \-]{2,40})",
    )
    for pattern in process_patterns:
        for m in re.finditer(pattern, block_l):
            term = " ".join(m.group(1).split()[:4]).strip(" -")
            if len(term) >= 3:
                process_terms.append(term)
    for pattern in material_patterns:
        for m in re.finditer(pattern, block_l):
            term = " ".join(m.group(1).split()[:4]).strip(" -")
            if len(term) >= 3:
                material_terms.append(term)
    # Chemical-like formulas are treated as material tokens.
    for m in re.finditer(r"\b(?:[A-Z][a-z]?\d{0,3}){2,}\b", block):
        material_terms.append(m.group(0).lower())
    return _dedup_words(process_terms), _dedup_words(material_terms)


_ONTOLOGY_CACHE: tuple[dict[str, tuple[str, str]], dict[str, tuple[str, str]]] | None = None


async def _load_ontology_terms() -> tuple[dict[str, tuple[str, str]], dict[str, tuple[str, str]]]:
    """Подгружает Process/Material термины из Neo4j (name_ru/name_en/aliases)."""
    global _ONTOLOGY_CACHE
    if _ONTOLOGY_CACHE is not None:
        return _ONTOLOGY_CACHE

    process_terms: dict[str, tuple[str, str]] = {}
    material_terms: dict[str, tuple[str, str]] = {}
    try:
        neo4j = Neo4jClient.instance()
        proc_rows = await neo4j.run(
            """
            MATCH (p:Process)
            RETURN p.id AS id, p.name_ru AS name_ru, p.name_en AS name_en, p.aliases AS aliases
            """
        )
        mat_rows = await neo4j.run(
            """
            MATCH (m:Material)
            RETURN m.id AS id, m.name_ru AS name_ru, m.name_en AS name_en, m.aliases AS aliases
            """
        )
    except Exception:
        _ONTOLOGY_CACHE = (process_terms, material_terms)
        return _ONTOLOGY_CACHE

    for row in proc_rows:
        name_ru = str(row.get("name_ru") or "")
        name_en = str(row.get("name_en") or "")
        canonical = name_en or name_ru or "process"
        node_id = str(row.get("id") or f"process:{_slug(canonical)}")
        aliases = row.get("aliases") if isinstance(row.get("aliases"), list) else []
        values = _dedup_words(
            [name_ru, name_en]
            + [str(x) for x in aliases]
        )
        for token in values:
            process_terms[token] = (node_id, name_en)
    for row in mat_rows:
        name_ru = str(row.get("name_ru") or "")
        name_en = str(row.get("name_en") or "")
        canonical = name_en or name_ru or "material"
        node_id = str(row.get("id") or f"material:{_slug(canonical)}")
        aliases = row.get("aliases") if isinstance(row.get("aliases"), list) else []
        values = _dedup_words(
            [name_ru, name_en]
            + [str(x) for x in aliases]
        )
        for token in values:
            material_terms[token] = (node_id, name_en)
    _ONTOLOGY_CACHE = (process_terms, material_terms)
    return _ONTOLOGY_CACHE


def _slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-zA-Z0-9а-яА-Я_ -]+", "", value)
    return re.sub(r"[ _-]+", "_", value).strip("_")


def _hash_id(prefix: str, text: str) -> str:
    return f"{prefix}:{hashlib.sha1(text.encode('utf-8')).hexdigest()[:12]}"


async def _extract_rule_based(document_id: str, markdown: str) -> GraphPayload:
    nodes: list[dict[str, Any]] = []
    rels: list[dict[str, Any]] = []
    process_terms, material_terms = await _load_ontology_terms()

    # Document
    nodes.append({"id": document_id, "label": "Document", "props": {"id": document_id}})

    blocks = [b.strip() for b in re.split(r"\n\s*\n", markdown) if b.strip()]
    heading_id: str | None = None
    exp_id = _hash_id("exp", document_id)
    nodes.append({"id": exp_id, "label": "ExperimentRun", "props": {"id": exp_id, "confidence": 0.5}})

    # Dictionary dedup
    seen_nodes: set[tuple[str, str]] = {(document_id, "Document"), (exp_id, "ExperimentRun")}
    seen_rels: set[tuple[str, str, str]] = set()

    for idx, block in enumerate(blocks):
        para_id = f"{document_id}:p:{idx}"
        nodes.append(
            {
                "id": para_id,
                "label": "TextParagraph",
                "props": {
                    "id": para_id,
                    "raw_text_ru": block,
                    "char_start": 0,
                    "char_end": len(block),
                },
            }
        )
        rels.append(
            {
                "type": "HAS_PARAGRAPH",
                "from": document_id,
                "to": para_id,
                "props": {"index": idx, "is_part_of_summary": False},
            }
        )
        if block.startswith("#"):
            title = block.lstrip("#").strip()
            heading_id = f"{document_id}:h:{_slug(title) or idx}"
            if (heading_id, "HeadingContext") not in seen_nodes:
                level = len(block) - len(block.lstrip("#"))
                nodes.append(
                    {
                        "id": heading_id,
                        "label": "HeadingContext",
                        "props": {"id": heading_id, "title_ru": title, "markdown_level": max(level, 1)},
                    }
                )
                seen_nodes.add((heading_id, "HeadingContext"))
            rel_key = (heading_id, "STRUCTURING", para_id)
            if rel_key not in seen_rels:
                rels.append({"type": "STRUCTURING", "from": heading_id, "to": para_id, "props": {}})
                seen_rels.add(rel_key)
            continue

        if heading_id:
            rel_key = (heading_id, "STRUCTURING", para_id)
            if rel_key not in seen_rels:
                rels.append({"type": "STRUCTURING", "from": heading_id, "to": para_id, "props": {}})
                seen_rels.add(rel_key)

        block_l = block.lower()
        for token, (proc_id, name_en) in process_terms.items():
            if _contains_token(block_l, token) and (proc_id, "Process") not in seen_nodes:
                nodes.append(
                    {
                        "id": proc_id,
                        "label": "Process",
                        "props": {"id": proc_id, "name_ru": token, "name_en": name_en, "aliases": [token]},
                    }
                )
                seen_nodes.add((proc_id, "Process"))
            if _contains_token(block_l, token):
                rel_key = (exp_id, "OPERATES_PROC", proc_id)
                if rel_key not in seen_rels:
                    rels.append({"type": "OPERATES_PROC", "from": exp_id, "to": proc_id, "props": {}})
                    seen_rels.add(rel_key)

        for token, (mat_id, name_en) in material_terms.items():
            if _contains_token(block_l, token) and (mat_id, "Material") not in seen_nodes:
                nodes.append(
                    {
                        "id": mat_id,
                        "label": "Material",
                        "props": {"id": mat_id, "name_ru": token, "name_en": name_en, "aliases": [token]},
                    }
                )
                seen_nodes.add((mat_id, "Material"))
            if _contains_token(block_l, token):
                rel_key = (exp_id, "USES_MAT", mat_id)
                if rel_key not in seen_rels:
                    rels.append(
                        {
                            "type": "USES_MAT",
                            "from": exp_id,
                            "to": mat_id,
                            "props": {"stage": 1, "aggregate_state": "unknown", "concentration": None},
                        }
                    )
                    seen_rels.add(rel_key)

        if not process_terms and not material_terms:
            heur_proc, heur_mat = _generic_heuristic_terms(block)
            for token in heur_proc:
                proc_id = f"process:{_slug(token)}"
                if (proc_id, "Process") not in seen_nodes:
                    nodes.append(
                        {
                            "id": proc_id,
                            "label": "Process",
                            "props": {"id": proc_id, "name_ru": token, "name_en": token, "aliases": [token]},
                        }
                    )
                    seen_nodes.add((proc_id, "Process"))
                rel_key = (exp_id, "OPERATES_PROC", proc_id)
                if rel_key not in seen_rels:
                    rels.append({"type": "OPERATES_PROC", "from": exp_id, "to": proc_id, "props": {"mode": "unknown"}})
                    seen_rels.add(rel_key)
            for token in heur_mat:
                mat_id = f"material:{_slug(token)}"
                if (mat_id, "Material") not in seen_nodes:
                    nodes.append(
                        {
                            "id": mat_id,
                            "label": "Material",
                            "props": {"id": mat_id, "name_ru": token, "name_en": token, "aliases": [token]},
                        }
                    )
                    seen_nodes.add((mat_id, "Material"))
                rel_key = (exp_id, "USES_MAT", mat_id)
                if rel_key not in seen_rels:
                    rels.append(
                        {
                            "type": "USES_MAT",
                            "from": exp_id,
                            "to": mat_id,
                            "props": {"stage": 1, "aggregate_state": "unknown", "concentration": None},
                        }
                    )
                    seen_rels.add(rel_key)

    # Если онтология недоступна, хотя бы фиксируем измерения как L4-данные.
    if not process_terms and not material_terms:
        for idx, block in enumerate(blocks):
            for m_idx, match in enumerate(re.finditer(r"(\d+(?:[.,]\d+)?)\s*(°C|K|г/л|%|pH|м3/т|кВт·ч)", block, flags=re.IGNORECASE)):
                value_raw = match.group(1).replace(",", ".")
                unit = match.group(2)
                meas_id = f"{document_id}:m:{idx}:{m_idx}"
                nodes.append(
                    {
                        "id": meas_id,
                        "label": "Measurement",
                        "props": {
                            "id": meas_id,
                            "parameter": "unknown",
                            "numeric_value": float(value_raw),
                            "unit": unit,
                            "confidence": 0.35,
                        },
                    }
                )
                rels.append({"type": "CONTEXT_FOR", "from": f"{document_id}:p:{idx}", "to": exp_id, "props": {"confidence": 0.35}})

    return GraphPayload(nodes=nodes, relationships=rels)


def _safe_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _split_for_map_reduce(markdown: str, max_chunk_chars: int = 7000) -> list[str]:
    """Разбивает markdown на крупные смысловые чанки для map-reduce extraction."""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", markdown) if b.strip()]
    if not blocks:
        return [markdown]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for block in blocks:
        add_len = len(block) + 2
        if current and current_len + add_len > max_chunk_chars:
            chunks.append("\n\n".join(current))
            current = [block]
            current_len = len(block)
        else:
            current.append(block)
            current_len += add_len
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _add_unique_node(nodes: list[dict[str, Any]], seen: set[tuple[str, str]], node: dict[str, Any]) -> None:
    node_id = node.get("id")
    label = node.get("label")
    if not node_id or not label:
        return
    key = (str(node_id), str(label))
    if key in seen:
        return
    seen.add(key)
    nodes.append(node)


def _build_l3(document_id: str, markdown: str, lang: str | None) -> GraphPayload:
    nodes: list[dict[str, Any]] = []
    rels: list[dict[str, Any]] = []
    seen_nodes: set[tuple[str, str]] = set()
    seen_rels: set[tuple[str, str, str]] = set()

    lang_id = f"{document_id}:lang"
    _add_unique_node(
        nodes,
        seen_nodes,
        {
            "id": lang_id,
            "label": "LangContext",
            "props": {"id": lang_id, "primary_language": lang or "unknown", "encoding": "utf-8"},
        },
    )

    heading_id: str | None = None
    blocks = [b.strip() for b in re.split(r"\n\s*\n", markdown) if b.strip()]
    for idx, block in enumerate(blocks):
        para_id = f"{document_id}:p:{idx}"
        _add_unique_node(
            nodes,
            seen_nodes,
            {
                "id": para_id,
                "label": "TextParagraph",
                "props": {
                    "id": para_id,
                    "raw_text_ru": block,
                    "char_start": 0,
                    "char_end": len(block),
                },
            },
        )
        rel_key = (document_id, "HAS_PARAGRAPH", para_id)
        if rel_key not in seen_rels:
            rels.append(
                {
                    "type": "HAS_PARAGRAPH",
                    "from": document_id,
                    "to": para_id,
                    "props": {"index": idx, "is_part_of_summary": False},
                }
            )
            seen_rels.add(rel_key)
        rel_key = (para_id, "TAGGED_WITH", lang_id)
        if rel_key not in seen_rels:
            rels.append({"type": "TAGGED_WITH", "from": para_id, "to": lang_id, "props": {}})
            seen_rels.add(rel_key)

        if idx > 0:
            prev_id = f"{document_id}:p:{idx - 1}"
            rel_key = (prev_id, "NEXT_PARAGRAPH", para_id)
            if rel_key not in seen_rels:
                rels.append(
                    {
                        "type": "NEXT_PARAGRAPH",
                        "from": prev_id,
                        "to": para_id,
                        "props": {"transition_type": "continuation", "logical_bridge": ""},
                    }
                )
                seen_rels.add(rel_key)

        if block.startswith("#"):
            title = block.lstrip("#").strip()
            heading_id = f"{document_id}:h:{_slug(title) or idx}"
            level = len(block) - len(block.lstrip("#"))
            _add_unique_node(
                nodes,
                seen_nodes,
                {
                    "id": heading_id,
                    "label": "HeadingContext",
                    "props": {"id": heading_id, "title_ru": title, "title_en": "", "markdown_level": max(level, 1)},
                },
            )
        if heading_id:
            rel_key = (heading_id, "STRUCTURING", para_id)
            if rel_key not in seen_rels:
                rels.append({"type": "STRUCTURING", "from": heading_id, "to": para_id, "props": {}})
                seen_rels.add(rel_key)

    rels.append({"type": "HAS_LANG", "from": document_id, "to": lang_id, "props": {}})
    return GraphPayload(nodes=nodes, relationships=rels)


def _build_l5(document_id: str, classification: str = "открытый") -> GraphPayload:
    nodes: list[dict[str, Any]] = []
    rels: list[dict[str, Any]] = []

    sec_id = f"{document_id}:sec"
    ver_id = f"{document_id}:ver"
    aud_id = f"{document_id}:audit"

    nodes.append(
        {
            "id": sec_id,
            "label": "SecurityRole",
            "props": {
                "id": sec_id,
                "required_clearance": classification,
                "encryption_type": "none",
            },
        }
    )
    nodes.append(
        {
            "id": ver_id,
            "label": "VerificationStatus",
            "props": {"id": ver_id, "level": "preliminary", "confidence_score": 0.5},
        }
    )
    nodes.append(
        {
            "id": aud_id,
            "label": "AuditTrail",
            "props": {"id": aud_id, "transaction_id": _hash_id("tx", document_id), "operation_type": "extract"},
        }
    )

    rels.append(
        {
            "type": "GOVERNED_BY",
            "from": document_id,
            "to": sec_id,
            "props": {"data_owner": "mkg", "restriction_policy": "classification"},
        }
    )
    rels.append({"type": "WRITES_LOG", "from": ver_id, "to": aud_id, "props": {}})
    return GraphPayload(nodes=nodes, relationships=rels)


def _normalize_llm_payload(raw: dict[str, Any]) -> GraphPayload:
    nodes_raw = raw.get("nodes", [])
    rels_raw = raw.get("relationships", [])
    nodes: list[dict[str, Any]] = []
    rels: list[dict[str, Any]] = []
    if isinstance(nodes_raw, list):
        for n in nodes_raw:
            if not isinstance(n, dict):
                continue
            node_id = n.get("id") or n.get("tmp_id")
            label = n.get("label")
            props = n.get("props", {})
            if node_id and label:
                nodes.append({"id": str(node_id), "label": str(label), "props": props if isinstance(props, dict) else {}})
    if isinstance(rels_raw, list):
        for r in rels_raw:
            if not isinstance(r, dict):
                continue
            rel_type = r.get("type")
            start = r.get("from")
            end = r.get("to")
            props = r.get("props", {})
            if rel_type and start and end:
                rels.append(
                    {
                        "type": str(rel_type),
                        "from": str(start),
                        "to": str(end),
                        "props": props if isinstance(props, dict) else {},
                    }
                )
    return dedupe_graph_payload(GraphPayload(nodes=nodes, relationships=rels))


def _payload_from_meta_object(document_id: str, raw: dict[str, Any]) -> GraphPayload:
    """Fallback для document_meta, если модель вернула не nodes/relationships, а плоский JSON."""
    nodes: list[dict[str, Any]] = []
    rels: list[dict[str, Any]] = []
    authors = raw.get("authors", [])
    if isinstance(authors, list):
        for idx, name in enumerate(authors):
            if not isinstance(name, str) or not name.strip():
                continue
            exp_id = f"{document_id}:expert:{idx}"
            nodes.append(
                {
                    "id": exp_id,
                    "label": "Expert",
                    "props": {"id": exp_id, "full_name": name.strip()},
                }
            )
            rels.append({"type": "AUTHORED", "from": exp_id, "to": document_id, "props": {"role": "author"}})
    org = raw.get("organization")
    if isinstance(org, str) and org.strip():
        org_id = f"{document_id}:org:{_slug(org)}"
        nodes.append({"id": org_id, "label": "Organization", "props": {"id": org_id, "legal_name": org.strip()}})
        rels.append({"type": "BELONGS_TO", "from": document_id, "to": org_id, "props": {}})
    loc = raw.get("location")
    if isinstance(loc, str) and loc.strip():
        loc_id = f"{document_id}:loc:{_slug(loc)}"
        nodes.append({"id": loc_id, "label": "Location", "props": {"id": loc_id, "city": loc.strip()}})
        rels.append({"type": "ISSUED_AT", "from": document_id, "to": loc_id, "props": {}})
    return GraphPayload(nodes=nodes, relationships=rels)


def _merge_payloads(*parts: GraphPayload) -> GraphPayload:
    combined = GraphPayload(nodes=[], relationships=[])
    for part in parts:
        combined = GraphPayload(
            nodes=combined.nodes + part.nodes,
            relationships=combined.relationships + part.relationships,
        )
    return dedupe_graph_payload(combined)


def _ensure_document_and_sources(document_id: str, payload: GraphPayload) -> GraphPayload:
    has_doc = any(n.get("id") == document_id and n.get("label") == "Document" for n in payload.nodes)
    nodes = list(payload.nodes)
    if not has_doc:
        nodes.insert(0, {"id": document_id, "label": "Document", "props": {"id": document_id}})
    return GraphPayload(nodes=nodes, relationships=payload.relationships)


_L1_LABELS = frozenset(
    {"Material", "Process", "Equipment", "ChemicalReagent", "StandardMetric", "PhaseState", "Property"}
)
_L2_LABELS = frozenset({"Expert", "Organization", "Location", "Timeline", "Event", "Facility"})
_L4_LABELS = frozenset(
    {
        "ExperimentRun",
        "TechStage",
        "Measurement",
        "Deviation",
        "TrendVector",
        "Formula",
        "EnvironmentalCondition",
        "Effect",
        "Claim",
    }
)
_L6_LABELS = frozenset({"TechnologySolution", "EconomicIndicator", "EnvironmentalIndicator"})
_L5_LABELS = frozenset({"SecurityRole", "VerificationStatus", "AuditTrail"})


def _norm_bridge_text(text: str) -> str:
    text = re.sub(r"[\u200b-\u200d\ufeff]", "", text)
    text = re.sub(r"\s+", " ", text.lower().strip())
    return text.replace("ё", "е")


def _bridge_tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[\w\u0400-\u04ff]{3,}", _norm_bridge_text(text))}


def _paragraphs_from_payload(
    document_id: str, markdown: str, nodes: list[dict[str, Any]]
) -> list[tuple[str, str]]:
    paras: list[tuple[str, str]] = []
    for node in nodes:
        if node.get("label") != "TextParagraph":
            continue
        text = str((node.get("props") or {}).get("raw_text_ru") or "").strip()
        if text:
            paras.append((str(node["id"]), text))
    if paras:
        return paras
    blocks = [b.strip() for b in re.split(r"\n\s*\n", markdown) if b.strip()]
    return [(f"{document_id}:p:{idx}", block) for idx, block in enumerate(blocks)]


def _find_paragraph_for_text(snippet: str, paragraphs: list[tuple[str, str]]) -> str | None:
    snippet = snippet.strip()
    if len(snippet) < 8 or not paragraphs:
        return None
    norm_snip = _norm_bridge_text(snippet)
    for para_id, text in paragraphs:
        if norm_snip in _norm_bridge_text(text):
            return para_id
    for prefix_len in (120, 80, 50, 30):
        prefix = norm_snip[:prefix_len]
        if len(prefix) < 15:
            break
        for para_id, text in paragraphs:
            if prefix in _norm_bridge_text(text):
                return para_id
    source_tokens = _bridge_tokens(snippet)
    if len(source_tokens) < 2:
        return None
    best_id: str | None = None
    best_score = 0.0
    min_score = 0.35 if len(source_tokens) >= 4 else 0.5
    for para_id, text in paragraphs:
        para_tokens = _bridge_tokens(text)
        if not para_tokens:
            continue
        score = len(source_tokens & para_tokens) / len(source_tokens)
        if score > best_score and score >= min_score:
            best_score = score
            best_id = para_id
    return best_id


def _node_text_snippets(node: dict[str, Any]) -> list[str]:
    props = node.get("props") or {}
    snippets: list[str] = []
    for key in (
        "quote",
        "source_quote",
        "text",
        "description",
        "title",
        "title_ru",
        "title_en",
        "name",
        "name_ru",
        "name_en",
        "full_name",
        "legal_name",
        "city",
        "value",
        "raw_text_ru",
    ):
        val = props.get(key)
        if isinstance(val, str) and val.strip():
            snippets.append(val.strip())
    node_id = str(node.get("id") or "")
    if ":" in node_id:
        slug_text = node_id.split(":", 1)[-1].replace("_", " ")
        if len(slug_text) >= 8:
            snippets.append(slug_text)
    return snippets


def _rel_quotes_by_node(relationships: list[dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for rel in relationships:
        props = rel.get("props") if isinstance(rel.get("props"), dict) else {}
        quote = props.get("quote") or props.get("source_quote") or props.get("text")
        if not isinstance(quote, str):
            continue
        quote = quote.strip()
        if len(quote) < 8:
            continue
        for endpoint in (rel.get("from"), rel.get("to")):
            if endpoint:
                out.setdefault(str(endpoint), []).append(quote)
    return out


def _bridge_text_to_layers(document_id: str, markdown: str, payload: GraphPayload) -> GraphPayload:
    """Связать L3 TextParagraph с сущностями L1/L2/L4/L6 по цитатам и перекрытию текста."""
    paragraphs = _paragraphs_from_payload(document_id, markdown, payload.nodes)
    if not paragraphs:
        log.warning("bridge doc_id=%s skipped: no paragraphs", document_id)
        return payload

    para_ids = {pid for pid, _ in paragraphs}
    rel_quotes = _rel_quotes_by_node(payload.relationships)
    seen_rels: set[tuple[str, str, str]] = {
        (str(r.get("from") or r.get("from_") or ""), str(r.get("type") or ""), str(r.get("to") or ""))
        for r in payload.relationships
    }
    new_rels = list(payload.relationships)
    entity_linked_paras: set[str] = set()
    cross_counts: dict[str, int] = {"DATA_SOURCE_FOR": 0, "CONTEXT_FOR": 0, "ABOUT": 0}
    matched_entities = 0
    unmatched_entities = 0

    def add_rel(
        rel_type: str,
        start: str,
        end: str,
        *,
        bridge: str,
        confidence: float = 0.8,
        track_entity_link: bool = False,
    ) -> None:
        key = (start, rel_type, end)
        if key in seen_rels or not start or not end:
            return
        new_rels.append(
            {
                "type": rel_type,
                "from": start,
                "to": end,
                "props": {"bridge": bridge, "confidence": confidence},
            }
        )
        seen_rels.add(key)
        cross_counts[rel_type] = cross_counts.get(rel_type, 0) + 1
        if track_entity_link and start in para_ids:
            entity_linked_paras.add(start)

    bridge_labels = _L1_LABELS | _L2_LABELS | _L4_LABELS | _L6_LABELS
    for node in payload.nodes:
        label = str(node.get("label") or "")
        node_id = str(node.get("id") or "")
        if not node_id or label in {"TextParagraph", "LangContext", "HeadingContext", "Document"}:
            continue

        snippets = _node_text_snippets(node)
        for rel_quote in rel_quotes.get(node_id, []):
            if rel_quote not in snippets:
                snippets.append(rel_quote)

        para_id: str | None = None
        bridge_mode = "quote_match"
        for snippet in snippets:
            para_id = _find_paragraph_for_text(snippet, paragraphs)
            if para_id:
                break

        if not para_id and label in bridge_labels:
            unmatched_entities += 1
            continue
        if para_id:
            matched_entities += 1

        if not para_id:
            continue

        if label in _L4_LABELS or label in _L1_LABELS:
            add_rel("DATA_SOURCE_FOR", para_id, node_id, bridge=bridge_mode, track_entity_link=True)
        elif label in _L2_LABELS:
            add_rel("CONTEXT_FOR", para_id, node_id, bridge="context_match", track_entity_link=True)
        elif label in _L6_LABELS:
            add_rel("ABOUT", para_id, node_id, bridge="topic_match", track_entity_link=True)

    # SecurityRole уже привязан к документу через GOVERNED_BY (_build_l5) —
    # не дублируем шумными CONTEXT_FOR от каждого абзаца.
    # VerificationStatus логично относить к опытам (HAS_VALIDATION по модели ТЗ),
    # а не к тексту: связываем со всеми ExperimentRun документа.
    run_ids = [
        str(n.get("id")) for n in payload.nodes
        if n.get("label") == "ExperimentRun" and n.get("id")
    ]
    ver_ids = [
        str(n.get("id")) for n in payload.nodes
        if n.get("label") == "VerificationStatus" and n.get("id")
    ]
    for run_id in run_ids:
        for ver_id in ver_ids:
            add_rel("HAS_VALIDATION", run_id, ver_id, bridge="verification_scope", confidence=0.5)

    cross_total = sum(cross_counts.values())
    log.info(
        "bridge doc_id=%s cross_rels=%s matched_entities=%s unmatched_entities=%s paragraphs=%s",
        document_id,
        cross_total,
        matched_entities,
        unmatched_entities,
        len(paragraphs),
    )
    if cross_total:
        log.info("bridge doc_id=%s cross_rels_by_type=%s", document_id, cross_counts)

    return GraphPayload(nodes=payload.nodes, relationships=new_rels)


async def _report_extraction_step(document_id: str, step: str) -> None:
    try:
        from mkg_core.store import get_repo
        from mkg_core.meta_db import update_document_status

        get_repo().set_status(document_id, "extracting", step=step)
        await update_document_status(document_id, "extracting", step=step)
    except Exception:
        pass


async def _persist_partial_graph(document_id: str, payload: GraphPayload, step: str) -> None:
    """Сохранить промежуточный граф для live-UI во время async extraction."""
    try:
        from mkg_core.meta_db import update_document_status
        from mkg_core.store import get_repo

        cleaned = sanitize_graph_payload(payload).as_dict()
        nodes = len(cleaned.get("nodes") or [])
        rels = len(cleaned.get("relationships") or [])
        get_repo().save_graph(document_id, cleaned)
        get_repo().set_status(
            document_id,
            "extracting",
            step=step,
            graph_nodes=nodes,
            graph_relationships=rels,
        )
        await update_document_status(
            document_id,
            "extracting",
            step=step,
            graph_nodes=nodes,
            graph_relationships=rels,
        )
    except Exception:
        pass


async def extract_from_markdown(
    document_id: str,
    markdown: str,
    *,
    file_name: str = "",
    classification: str = "открытый",
    lang: str | None = None,
) -> GraphPayload:
    """LLM extraction + deterministic L3/L5 fallback-safe composition."""
    settings = get_settings()
    _check_cancel(document_id)
    l3 = _build_l3(document_id, markdown, lang=lang)
    l5 = _build_l5(document_id, classification=classification)
    _check_cancel(document_id)
    await _report_extraction_step(document_id, "layer_L3")
    await _report_extraction_step(document_id, "layer_L5")
    await _persist_partial_graph(document_id, _merge_payloads(l3, l5), "layer_L3")

    if PromptRegistry is None:
        rb = await _extract_rule_based(document_id, markdown)
        merged = _merge_payloads(rb, l3, l5)
        merged = _ensure_document_and_sources(document_id, merged)
        return sanitize_graph_payload(_bridge_text_to_layers(document_id, markdown, merged))

    try:
        model = await get_llm_model()
        PromptRegistry.configure(settings.prompts_path, model=model)
        reg = PromptRegistry.instance()
        llm = YandexLLMClient.instance()

        l2_schema = (
            '{"nodes":[{"id":"<id>","label":"Expert|Organization|Location|Timeline|Event|Facility","props":{}}],'
            '"relationships":[{"type":"AUTHORED|BELONGS_TO|ISSUED_AT|ON_TIMELINE|HAS_EVENT","from":"<id>","to":"<id>","props":{}}]}'
        )
        ef_schema = (
            '{"nodes":[{"id":"<id>","label":"Material|Process|Equipment|ChemicalReagent|StandardMetric|'
            'ExperimentRun|TechStage|Measurement|Deviation|TrendVector|Formula|EnvironmentalCondition|Effect|Claim","props":{}}],'
            '"relationships":[{"type":"USES_MAT|OPERATES_PROC|IN_EQUIPMENT|CONSUMES_REAGENT|EVALUATED_AGAINST|'
            'CONDUCTED_AT|EXECUTES_STAGE|PRODUCED_MEASURE|TRIGGERED_DEV|HAS_TREND|COMPUTED_BY|SHOWED_EFFECT|UNDER_CONDITIONS|'
            'DATA_SOURCE_FOR|CONTEXT_FOR|DERIVED_FROM|ASSERTED_BY|ABOUT|HAS_OBJECT","from":"<id>","to":"<id>","props":{}}]}'
        )
        l6_schema = (
            '{"nodes":[{"id":"<id>","label":"TechnologySolution|EconomicIndicator|EnvironmentalIndicator","props":{}}],'
            '"relationships":[{"type":"DESCRIBES_SOLUTION|USES_MATERIAL_TS|HAS_ECONOMIC_INDICATOR|HAS_ENVIRONMENTAL_INDICATOR|SOURCE|COMPARABLE_TO",'
            '"from":"<id>","to":"<id>","props":{}}]}'
        )

        meta_prompt = reg.get(
            stage="extraction",
            prompt_type="document_meta",
            text=markdown[:8000],
            schema=l2_schema,
        )
        ef_chunks = _split_for_map_reduce(markdown, max_chunk_chars=7000)
        l6_prompt = reg.get(
            stage="extraction",
            prompt_type="economics",
            text=markdown[:12000],
            schema=l6_schema,
        )

        await _report_extraction_step(document_id, "layer_L2_L6")
        _check_cancel(document_id)
        meta_raw, l6_raw = await asyncio.gather(
            llm.chat(**meta_prompt),
            llm.chat(**l6_prompt),
        )
        _check_cancel(document_id)

        meta_json = _safe_json(meta_raw)
        meta_payload = _normalize_llm_payload(meta_json)
        if not meta_payload.nodes:
            meta_payload = _payload_from_meta_object(document_id, meta_json)
        l6_payload = _normalize_llm_payload(_safe_json(l6_raw))
        await _persist_partial_graph(
            document_id,
            _merge_payloads(l3, l5, meta_payload),
            "layer_L2",
        )
        await _persist_partial_graph(
            document_id,
            _merge_payloads(l3, l5, meta_payload, l6_payload),
            "layer_L6",
        )

        concurrency = max(1, settings.llm_concurrency)
        sem = asyncio.Semaphore(concurrency)

        async def _extract_ef_chunk(chunk: str) -> GraphPayload:
            _check_cancel(document_id)
            ef_prompt = reg.get(
                stage="extraction",
                prompt_type="entities_facts",
                text=chunk,
                schema=ef_schema,
                layer_hint="L1,L4",
                rules=(
                    "Не выдумывай id. Используй детерминированные ключи: material:*, process:*, run:*, "
                    "stage:*, measure:*; для каждого факта добавляй source quote в props при наличии."
                ),
            )
            try:
                async with sem:
                    ef_raw = await llm.chat(**ef_prompt)
                return _normalize_llm_payload(_safe_json(ef_raw))
            except ExtractionCancelled:
                raise
            except Exception as exc:
                # Фатальные ошибки останавливают весь extraction, единичный сбой
                # чанка (парсинг/timeout) не должен терять факты остальных чанков.
                if is_fatal_api_error(exc):
                    raise
                log.warning("ef chunk extraction failed doc_id=%s: %s", document_id, exc)
                return GraphPayload(nodes=[], relationships=[])

        await _report_extraction_step(document_id, "layer_L1_L4")
        _check_cancel(document_id)
        base_payload = _merge_payloads(l3, l5, meta_payload, l6_payload)
        ef_payload = GraphPayload(nodes=[], relationships=[])
        chunk_total = len(ef_chunks)
        chunk_tasks = [asyncio.create_task(_extract_ef_chunk(c)) for c in ef_chunks]
        done = 0
        for finished in asyncio.as_completed(chunk_tasks):
            part = await finished
            ef_payload = _merge_payloads(ef_payload, part)
            done += 1
            step = f"layer_L1_L4_{done}/{chunk_total}" if chunk_total > 1 else "layer_L1_L4"
            await _persist_partial_graph(
                document_id,
                _merge_payloads(base_payload, ef_payload),
                step,
            )
        _check_cancel(document_id)

        merged = _merge_payloads(meta_payload, ef_payload, l6_payload, l3, l5)
        merged = _ensure_document_and_sources(document_id, merged)
        merged = _bridge_text_to_layers(document_id, markdown, merged)
        return sanitize_graph_payload(merged)
    except ExtractionCancelled:
        raise
    except Exception as exc:
        model = await get_llm_model()
        if is_fatal_api_error(exc):
            raise RuntimeError(format_api_error(exc, model=model)) from exc
        # Нефатальный сбой LLM: не теряем уже построенные L3/L5, деградируем на
        # rule-based извлечение вместо полного провала документа.
        log.warning(
            "LLM extraction failed doc_id=%s, fallback to rule-based: %s",
            document_id,
            exc,
        )
        rb = await _extract_rule_based(document_id, markdown)
        merged = _merge_payloads(rb, l3, l5)
        merged = _ensure_document_and_sources(document_id, merged)
        return sanitize_graph_payload(_bridge_text_to_layers(document_id, markdown, merged))
