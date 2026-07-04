"""Сборка размеченного Markdown (L1–L6, узлы/связи) поверх чистого MD."""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

_LAYER_TITLES = {
    "L1": "Сущности (Material, Process, Equipment…)",
    "L2": "Контекст (Expert, Organization, Timeline…)",
    "L3": "Текст (TextParagraph, LangContext…)",
    "L4": "Факты (ExperimentRun, Measurement, Claim…)",
    "L5": "Классификация и доступ",
    "L6": "Технико-экономика и экология",
}

_LABEL_LAYER: dict[str, str] = {
    "Material": "L1",
    "Process": "L1",
    "Equipment": "L1",
    "ChemicalReagent": "L1",
    "StandardMetric": "L1",
    "Expert": "L2",
    "Organization": "L2",
    "Location": "L2",
    "Timeline": "L2",
    "Event": "L2",
    "Facility": "L2",
    "Document": "L2",
    "TextParagraph": "L3",
    "TextSection": "L3",
    "LangContext": "L3",
    "ExperimentRun": "L4",
    "TechStage": "L4",
    "Measurement": "L4",
    "Deviation": "L4",
    "TrendVector": "L4",
    "Formula": "L4",
    "EnvironmentalCondition": "L4",
    "Effect": "L4",
    "Claim": "L4",
    "SecurityRole": "L5",
    "VerificationStatus": "L5",
    "AuditTrail": "L5",
    "TechnologySolution": "L6",
    "EconomicIndicator": "L6",
    "EnvironmentalIndicator": "L6",
}


def _block_kind(text: str) -> str:
    if text.lstrip().startswith("#"):
        return "heading"
    if text.lstrip().startswith("|") and "|" in text:
        return "table"
    return "paragraph"


def inject_l3_markers(document_id: str, clean_md: str) -> str:
    """Чистый MD + HTML-комментарии L3 перед каждым блоком."""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", clean_md.strip()) if b.strip()]
    if not blocks:
        return clean_md
    out: list[str] = []
    for idx, block in enumerate(blocks):
        kind = _block_kind(block)
        out.append(f"<!-- L3:TextParagraph id={document_id}:p:{idx} kind={kind} -->")
        out.append(block)
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def _node_line(node: dict[str, Any]) -> list[str]:
    label = str(node.get("label") or "?")
    node_id = str(node.get("id") or "?")
    props = node.get("props") or {}
    layer = _LABEL_LAYER.get(label, "L?")
    lines = [f"- `[{label}:{node_id}]` · слой **{layer}**"]

    skip = {"id", "quote", "raw_text_ru"}
    extras = {k: v for k, v in props.items() if k not in skip and v not in (None, "", [])}
    if extras:
        parts = [f"{k}={v!r}" if not isinstance(v, str) else f"{k}={v}" for k, v in list(extras.items())[:6]]
        lines[0] += " · " + " · ".join(parts)

    quote = props.get("quote") or props.get("raw_text_ru")
    if isinstance(quote, str) and quote.strip():
        q = quote.strip().replace("\n", " ")
        if len(q) > 200:
            q = q[:200] + "…"
        lines.append(f"  > {q}")

    conf = props.get("extraction_confidence")
    if conf is not None:
        lines.append(f"  · confidence: {conf}")

    return lines


def build_marked_markdown(document_id: str, clean_md: str, graph: dict[str, Any] | None) -> str:
    """Размеченный MD: L3-комментарии + каталог узлов/связей по слоям."""
    body = inject_l3_markers(document_id, clean_md)
    parts = [body.rstrip(), "", "---", "", "# Разметка узлов MKG", ""]

    nodes = (graph or {}).get("nodes") or []
    rels = (graph or {}).get("relationships") or []

    if not nodes:
        parts.append("_Узлы появятся после извлечения («В граф»)._")
        parts.append("")
        parts.append("Структура L3 уже отмечена комментариями `<!-- L3:TextParagraph … -->` в тексте выше.")
        return "\n".join(parts)

    by_layer: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        label = str(node.get("label") or "?")
        layer = _LABEL_LAYER.get(label, "L?")
        by_layer[layer].append(node)

    for layer in ("L1", "L2", "L3", "L4", "L5", "L6", "L?"):
        layer_nodes = by_layer.get(layer) or []
        if not layer_nodes:
            continue
        title = _LAYER_TITLES.get(layer, layer)
        parts.append(f"## {layer} · {title}")
        parts.append("")
        for node in sorted(layer_nodes, key=lambda n: str(n.get("id", ""))):
            parts.extend(_node_line(node))
        parts.append("")

    if rels:
        parts.append("## Связи")
        parts.append("")
        for rel in rels[:200]:
            rtype = rel.get("type", "?")
            start = rel.get("from") or rel.get("from_", "?")
            end = rel.get("to", "?")
            parts.append(f"- `{start}` → **{rtype}** → `{end}`")
        if len(rels) > 200:
            parts.append(f"- _… ещё {len(rels) - 200} связей_")
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"
