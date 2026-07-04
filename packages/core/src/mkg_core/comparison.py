"""Сравнительный анализ технологий: таблицы из графа MKG + LLM для пробелов."""
from __future__ import annotations

import json
import re
from typing import Any

COMPARE_ENTITY_LABELS = frozenset({"Process", "Material", "TechnologySolution"})

COMPARE_INTENT_RE = re.compile(
    r"(?:"
    r"сравн|сopостав|compare|comparison|"
    r"таблиц[аы]?\s+сравн|"
    r"\bvs\.?\b|"
    r"против\b|"
    r"как(?:ая|ой|ие)\s+(?:технолог|метод|процесс|материал).*лучш|"
    r"difference\s+between|"
    r"which\s+(?:is|are)\s+better"
    r")",
    re.IGNORECASE,
)

ND = "н/д"

_COLUMN_PATTERNS: dict[str, tuple[str, ...]] = {
    "efficiency": ("efficiency", "yield", "recovery", "выход", "эффектив", "извлеч", "степень", "recovery_rate"),
    "capex": ("capex", "капекс", "capital", "затрат", "стоимость", "cost", "инвест", "эконом"),
    "cold_climate": ("cold", "arctic", "холод", "мороз", "арктик", "низк", "subzero", "permafrost", "зим"),
    "eco_restrictions": ("eco", "эколог", "environment", "выброс", "emission", "лимит", "норматив", "загрязн", "pdk"),
}

_INDICATOR_LABELS = {
    "capex": "EconomicIndicator",
    "eco_restrictions": "EnvironmentalIndicator",
}


def is_comparison_query(text: str) -> bool:
    return bool(COMPARE_INTENT_RE.search(text or ""))


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def node_display_name(node: dict[str, Any]) -> str:
    props = node.get("props") if isinstance(node.get("props"), dict) else {}
    for key in ("name_ru", "name_en", "name", "title_ru", "title", "text"):
        val = props.get(key)
        if val:
            return str(val)[:120]
    return str(node.get("id") or "—")[:120]


def _matches_patterns(text: str, patterns: tuple[str, ...]) -> bool:
    blob = _norm(text)
    return any(p in blob for p in patterns)


def _neighbor_ids(graph: dict[str, Any], node_id: str, *, max_hops: int = 2) -> set[str]:
    rels = graph.get("relationships") or []
    frontier = {node_id}
    seen = {node_id}
    for _ in range(max_hops):
        nxt: set[str] = set()
        for rel in rels:
            f = str(rel.get("from") or "")
            t = str(rel.get("to") or "")
            if f in frontier and t not in seen:
                nxt.add(t)
            elif t in frontier and f not in seen:
                nxt.add(f)
        if not nxt:
            break
        seen |= nxt
        frontier = nxt
    seen.discard(node_id)
    return seen


def _nodes_by_id(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(n.get("id") or ""): n for n in graph.get("nodes") or [] if n.get("id")}


def measurements_for_entity(graph: dict[str, Any], entity_id: str) -> list[dict[str, Any]]:
    by_id = _nodes_by_id(graph)
    out: list[dict[str, Any]] = []
    for nid in _neighbor_ids(graph, entity_id):
        node = by_id.get(nid)
        if node and str(node.get("label") or "") == "Measurement":
            out.append(node)
    return out


def _linked_indicators(graph: dict[str, Any], entity_id: str, indicator_label: str) -> list[str]:
    by_id = _nodes_by_id(graph)
    texts: list[str] = []
    rels = graph.get("relationships") or []
    tech_ids = {entity_id}
    if str(by_id.get(entity_id, {}).get("label") or "") != "TechnologySolution":
        for rel in rels:
            f, t = str(rel.get("from") or ""), str(rel.get("to") or "")
            rtype = str(rel.get("type") or "")
            if rtype in ("DESCRIBES_SOLUTION", "USES_MATERIAL_TS", "COMPARABLE_TO"):
                if f == entity_id and by_id.get(t, {}).get("label") == "TechnologySolution":
                    tech_ids.add(t)
                elif t == entity_id and by_id.get(f, {}).get("label") == "TechnologySolution":
                    tech_ids.add(f)
    for rel in rels:
        f, t = str(rel.get("from") or ""), str(rel.get("to") or "")
        rtype = str(rel.get("type") or "")
        if rtype == "HAS_ECONOMIC_INDICATOR" and indicator_label == "EconomicIndicator":
            if f in tech_ids and t in by_id:
                texts.append(node_display_name(by_id[t]))
        elif rtype == "HAS_ENVIRONMENTAL_INDICATOR" and indicator_label == "EnvironmentalIndicator":
            if f in tech_ids and t in by_id:
                texts.append(node_display_name(by_id[t]))
    return texts[:3]


def _cell_from_measurements(measurements: list[dict[str, Any]], column: str) -> str | None:
    patterns = _COLUMN_PATTERNS.get(column, ())
    for m in measurements:
        props = m.get("props") if isinstance(m.get("props"), dict) else {}
        param = str(props.get("parameter") or props.get("name") or "")
        blob = f"{param} {props.get('conditions') or ''} {props.get('text') or ''}"
        if not _matches_patterns(blob, patterns):
            continue
        val = props.get("numeric_value") if props.get("numeric_value") is not None else props.get("value")
        unit = str(props.get("unit") or "").strip()
        if val is not None:
            return f"{val}{(' ' + unit) if unit else ''}"[:80]
        text = str(props.get("text") or param or "").strip()
        if text:
            return text[:80]
    return None


def _prop_cell(props: dict[str, Any], column: str) -> str | None:
    direct_keys: dict[str, tuple[str, ...]] = {
        "efficiency": ("efficiency", "yield", "recovery"),
        "capex": ("capex", "cost", "capital_cost"),
        "cold_climate": ("cold_climate", "arctic", "low_temp"),
        "eco_restrictions": ("eco_restrictions", "environmental", "eco_limits"),
    }
    for key in direct_keys.get(column, ()):
        val = props.get(key)
        if val not in (None, "", "—"):
            return str(val)[:80]
    return None


def extract_row_from_node(
    node: dict[str, Any],
    graph: dict[str, Any],
    *,
    document_id: str,
    file_name: str = "",
) -> dict[str, Any]:
    props = node.get("props") if isinstance(node.get("props"), dict) else {}
    node_id = str(node.get("id") or "")
    measurements = measurements_for_entity(graph, node_id)
    meas_count = len(measurements)

    cells: dict[str, str] = {}
    for col in _COLUMN_PATTERNS:
        val = _prop_cell(props, col) or _cell_from_measurements(measurements, col)
        if not val and col in _INDICATOR_LABELS:
            inds = _linked_indicators(graph, node_id, _INDICATOR_LABELS[col])
            if inds:
                val = "; ".join(inds)
        cells[col] = val or ND

    sources: list[str] = []
    if file_name:
        sources.append(file_name[:60])
    elif document_id:
        sources.append(document_id[-12:])
    if meas_count:
        sources.append(f"{meas_count} meas.")

    return {
        "technology": node_display_name(node),
        "type": str(node.get("label") or ""),
        "efficiency": cells["efficiency"],
        "capex": cells["capex"],
        "cold_climate": cells["cold_climate"],
        "eco_restrictions": cells["eco_restrictions"],
        "source_count": meas_count,
        "sources": ", ".join(sources) if sources else ND,
        "document_id": document_id,
        "node_id": node_id,
        "_llm_filled": False,
    }


def _query_tokens(query: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]{3,}", _norm(query))
    stop = {
        "сравни", "сравнение", "compare", "comparison", "технолог", "технологии",
        "technology", "technologies", "таблица", "table", "between", "and", "или",
        "против", "какие", "какой", "какая", "лучше", "better", "which",
    }
    return [t for t in tokens if t not in stop]


def _row_matches_query(row: dict[str, Any], tokens: list[str]) -> bool:
    if not tokens:
        return True
    blob = _norm(f"{row.get('technology')} {row.get('type')}")
    return any(tok in blob for tok in tokens)


def extract_comparison_from_graph(
    graph: dict[str, Any],
    *,
    document_id: str,
    file_name: str = "",
    query: str = "",
    limit: int = 10,
) -> list[dict[str, Any]]:
    if not graph.get("nodes"):
        return []
    tokens = _query_tokens(query)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for node in graph.get("nodes") or []:
        label = str(node.get("label") or "")
        if label not in COMPARE_ENTITY_LABELS:
            continue
        name = node_display_name(node)
        key = f"{label}:{_norm(name)}"
        if key in seen:
            continue
        seen.add(key)
        row = extract_row_from_node(node, graph, document_id=document_id, file_name=file_name)
        if _row_matches_query(row, tokens):
            rows.append(row)
        if len(rows) >= limit:
            break
    return rows


def merge_repo_comparison(
    repo: Any,
    *,
    document_ids: list[str] | None = None,
    query: str = "",
    limit: int = 10,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Собрать строки сравнения по всем (или выбранным) документам."""
    from mkg_core.graph_payload import GraphPayload, dedupe_graph_payload

    meta: dict[str, Any] = {"partial": False, "llm_filled": False, "gap_count": 0, "doc_count": 0}
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    if document_ids:
        items = [repo.get(d) for d in document_ids if repo.get(d)]
        items = [i for i in items if i]
    else:
        items, _total = repo.list(page=1, page_size=500)

    for rec in items:
        graph_raw = repo.read_graph(rec["id"])
        if not graph_raw or not graph_raw.get("nodes"):
            continue
        meta["doc_count"] += 1
        graph = dedupe_graph_payload(
            GraphPayload(
                nodes=list(graph_raw.get("nodes") or []),
                relationships=list(graph_raw.get("relationships") or []),
            )
        ).as_dict()
        file_name = str(rec.get("file_name") or rec["id"])
        for row in extract_comparison_from_graph(
            graph,
            document_id=rec["id"],
            file_name=file_name,
            query=query,
            limit=limit,
        ):
            key = f"{row.get('type')}:{_norm(row.get('technology') or '')}"
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
            if len(rows) >= limit:
                break
        if len(rows) >= limit:
            break

    gap_count = sum(
        1
        for r in rows
        for col in ("efficiency", "capex", "cold_climate", "eco_restrictions")
        if r.get(col) == ND
    )
    meta["gap_count"] = gap_count
    meta["partial"] = bool(rows) and gap_count > 0
    return rows, meta


def rows_to_markdown(
    rows: list[dict[str, Any]],
    *,
    lang: str = "ru",
    gap_note: str = "",
) -> str:
    if not rows:
        if lang == "en":
            return "## Technology comparison\n\nNo Process/Material/TechnologySolution nodes in the graph."
        return "## Сравнение технологий\n\nВ графе нет узлов Process/Material/TechnologySolution для сравнения."

    if lang == "en":
        title = "## Technology comparison"
        headers = ["Technology", "Efficiency", "CAPEX", "Cold climate", "Eco limits", "Sources"]
    else:
        title = "## Сравнение технологий"
        headers = ["Технология", "Эффективность", "CAPEX", "Холодный климат", "Экология", "Источники"]

    def esc_cell(val: Any) -> str:
        s = str(val or ND).replace("|", "\\|").replace("\n", " ")
        return s[:100]

    lines = [
        title,
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    esc_cell(row.get("technology")),
                    esc_cell(row.get("efficiency")),
                    esc_cell(row.get("capex")),
                    esc_cell(row.get("cold_climate")),
                    esc_cell(row.get("eco_restrictions")),
                    esc_cell(row.get("sources") or row.get("source_count")),
                ]
            )
            + " |"
        )
    if gap_note:
        lines.extend(["", gap_note])
    elif any(r.get("_llm_filled") for r in rows):
        if lang == "en":
            lines.append("")
            lines.append("*Some cells were inferred by LLM from document fragments (not verified in graph).*")
        else:
            lines.append("")
            lines.append("*Часть ячеек дополнена LLM по фрагментам документов (не подтверждено в графе).*")
    return "\n".join(lines)


def rows_to_csv(rows: list[dict[str, Any]]) -> str:
    header = "technology,type,efficiency,capex,cold_climate,eco_restrictions,sources,document_id,node_id"
    lines = [header]
    for row in rows:
        cells = [
            str(row.get("technology") or "").replace('"', '""'),
            str(row.get("type") or ""),
            str(row.get("efficiency") or ND),
            str(row.get("capex") or ND),
            str(row.get("cold_climate") or ND),
            str(row.get("eco_restrictions") or ND),
            str(row.get("sources") or row.get("source_count") or ""),
            str(row.get("document_id") or ""),
            str(row.get("node_id") or ""),
        ]
        lines.append(",".join(f'"{c}"' if i == 0 else c for i, c in enumerate(cells)))
    return "\n".join(lines)


def _hits_context(hits: list[dict[str, Any]], *, limit: int = 6) -> str:
    lines: list[str] = []
    for i, h in enumerate(hits[:limit], 1):
        text = str(h.get("text") or h.get("snippet") or "")[:400]
        if text:
            lines.append(f"{i}. {text}")
    return "\n".join(lines)


async def fill_comparison_gaps_llm(
    rows: list[dict[str, Any]],
    *,
    query: str,
    context_chunks: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """Заполнить ячейки «н/д» через LLM по фрагментам."""
    if not rows:
        return rows, False
    gaps = [
        (ri, col)
        for ri, row in enumerate(rows)
        for col in ("efficiency", "capex", "cold_climate", "eco_restrictions")
        if row.get(col) == ND
    ]
    if not gaps:
        return rows, False

    from mkg_core.config import get_settings
    from mkg_core.llm import YandexLLMClient

    settings = get_settings()
    if not settings.yandex_api_key or not settings.yandex_folder_id:
        return rows, False

    ctx = _hits_context(context_chunks or [])
    if not ctx:
        return rows, False

    tech_list = json.dumps(
        [{"technology": r.get("technology"), "type": r.get("type")} for r in rows],
        ensure_ascii=False,
    )
    system = (
        "Ты аналитик MKG. По фрагментам документов заполни пробелы в таблице сравнения технологий. "
        "Ответ — только JSON-массив объектов с полями: technology, efficiency, capex, cold_climate, eco_restrictions. "
        "Заполняй только то, что явно следует из текста; иначе оставь «н/д». Кратко (до 80 символов на ячейку)."
    )
    user = f"Запрос: {query}\n\nТехнологии:\n{tech_list}\n\nФрагменты:\n{ctx}"
    try:
        llm = YandexLLMClient.instance()
        raw = await llm.chat(system, user, temperature=0.2, max_tokens=768)
    except Exception:
        return rows, False

    text = (raw or "").strip()
    start = text.find("[")
    end = text.rfind("]")
    if start < 0 or end <= start:
        return rows, False
    try:
        filled = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return rows, False
    if not isinstance(filled, list):
        return rows, False

    by_name = {_norm(str(x.get("technology") or "")): x for x in filled if isinstance(x, dict)}
    changed = False
    out = [dict(r) for r in rows]
    for row in out:
        patch = by_name.get(_norm(str(row.get("technology") or "")))
        if not patch:
            continue
        for col in ("efficiency", "capex", "cold_climate", "eco_restrictions"):
            if row.get(col) != ND:
                continue
            val = str(patch.get(col) or "").strip()
            if val and val.lower() not in ("н/д", "n/a", "—", "-", "null", "none"):
                row[col] = val[:80]
                row["_llm_filled"] = True
                changed = True
    return out, changed


async def run_comparison_analysis(
    query: str,
    *,
    document_ids: list[str] | None = None,
    hits: list[dict[str, Any]] | None = None,
    walked_graph: dict[str, Any] | None = None,
    repo: Any | None = None,
    limit: int = 8,
    use_llm: bool = True,
    lang: str = "ru",
) -> dict[str, Any]:
    """Построить таблицу сравнения для чата и API."""
    from mkg_core.store import get_repo

    repo = repo or get_repo()
    rows, meta = merge_repo_comparison(repo, document_ids=document_ids, query=query, limit=limit)

    if walked_graph and walked_graph.get("nodes"):
        doc_ids = list(document_ids or [])
        doc_id = doc_ids[0] if doc_ids else ""
        file_name = ""
        if doc_id:
            rec = repo.get(doc_id) or {}
            file_name = str(rec.get("file_name") or "")
        extra = extract_comparison_from_graph(
            walked_graph,
            document_id=doc_id,
            file_name=file_name,
            query=query,
            limit=limit,
        )
        seen = {_norm(r.get("technology") or "") for r in rows}
        for row in extra:
            key = _norm(row.get("technology") or "")
            if key not in seen:
                rows.append(row)
                seen.add(key)
            if len(rows) >= limit:
                break

    llm_filled = False
    if use_llm and meta.get("gap_count", 0) > 0:
        rows, llm_filled = await fill_comparison_gaps_llm(rows, query=query, context_chunks=hits)
        meta["llm_filled"] = llm_filled

    gap_note = ""
    gap_count = sum(
        1
        for r in rows
        for col in ("efficiency", "capex", "cold_climate", "eco_restrictions")
        if r.get(col) == ND
    )
    if gap_count and lang == "en":
        gap_note = f"*Partial table: {gap_count} cell(s) without graph data (shown as n/a).*"
    elif gap_count:
        gap_note = f"*Частичная таблица: {gap_count} ячеек без данных в графе (отмечены «н/д»).*"

    markdown = rows_to_markdown(rows, lang=lang, gap_note=gap_note)
    return {
        "rows": rows,
        "markdown": markdown,
        "partial": bool(rows) and gap_count > 0,
        "gap_count": gap_count,
        "llm_filled": llm_filled,
        "meta": meta,
    }
