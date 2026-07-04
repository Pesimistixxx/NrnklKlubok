"""Шаблон структурированного ответа MKG (аналитика и синтез)."""
from __future__ import annotations

from typing import Any

ANSWER_SECTION_TITLES: tuple[str, ...] = (
    "Сводка",
    "Источники по группам (метод / год / география)",
    "Консенсус и разногласия",
    "Уверенность (N источников, уровень достоверности)",
    "Пробелы в знаниях",
    "Рекомендации (кейсы, эксперты, темы)",
    "Уточняющий вопрос",
)

ANSWER_SECTION_TITLES_EN: tuple[str, ...] = (
    "Summary",
    "Sources by group (method / year / geography)",
    "Consensus and disagreements",
    "Confidence (N sources, reliability level)",
    "Knowledge gaps",
    "Recommendations (cases, experts, topics)",
    "Follow-up question",
)

ANSWER_STRUCTURE_TEMPLATE = """\
## Сводка
Краткий вывод по вопросу (2–4 предложения).

## Источники по группам (метод / год / география)
- **Метод / процесс:** …
- **Год / период:** …
- **География (РФ / зарубеж):** …
- **Уровень детализации:** …

## Консенсус и разногласия
- **Консенсус:** …
- **Разногласия / противоречия:** …

## Уверенность (N источников, уровень достоверности)
N источников · уровень: высокая / средняя / низкая · краткое обоснование.

## Пробелы в знаниях
- Неизученные или слабо покрытые комбинации материал–режим–условия.
- Технологии только в отечественной или только в зарубежной литературе.

## Рекомендации (кейсы, эксперты, темы)
- Похожие кейсы и решения из смежных областей.
- Эксперты / команды по теме.
- Темы для углублённого изучения.

## Уточняющий вопрос
(опционально — один вопрос, если ответ неполный)
"""

def chat_structure_rules(lang: str = "ru") -> str:
    """Markdown section rules for chat answers; headers match reply language."""
    if lang == "en":
        titles = ANSWER_SECTION_TITLES_EN
        return (
            "Answer structure — Markdown with ## sections (headers in English, same as the answer):\n"
            + "\n".join(f"- ## {title}" for title in titles[:-1])
            + "\n- ## Follow-up question (optional if the answer is complete)\n"
            "Never include graph counters (nodes, edges, hits), L1–L6 layer codes, "
            "situation evaluation strings, or retrieval jargon (Qdrant, Neo4j, keyword-fallback) "
            "in user-facing sections — those belong in trace/pipeline only. "
            "In Sources by group, group evidence by method/process, year, geography (domestic/abroad), "
            "and detail level. In Consensus and disagreements, separate agreed conclusions from conflicts. "
            "In Confidence, cite source count and reliability (high/medium/low) using extraction_confidence when present. "
            "In Knowledge gaps, list uncovered material–mode–condition combos and technologies covered only domestically or abroad. "
            "In Recommendations, suggest similar cases, graph experts, and topics to explore. "
            "Use GFM pipe tables when tabular data fits. "
            "Omit Follow-up question when the answer is complete."
        )
    return (
        "Структура ответа — Markdown с разделами ## (заголовки на том же языке, что и ответ):\n"
        + "\n".join(f"- ## {title}" for title in ANSWER_SECTION_TITLES[:-1])
        + "\n- ## Уточняющий вопрос (опционально, если ответ неполный)\n"
        "Никогда не включай в разделы ответа счётчики графа (узл., св., хитов), метки L1–L6, "
        "«Оценка ситуации», названия retrieval (Qdrant, Neo4j, keyword-fallback) — "
        "это только для trace/пайплайна, не для пользователя. "
        "В «Источники по группам» группируй evidence по методу/процессу, году, географии (РФ/зарубеж), "
        "уровню детализации. В «Консенсус и разногласия» явно раздели согласованные выводы и расхождения. "
        "В «Уверенность» укажи число опорных источников и уровень достоверности (высокая/средняя/низкая) "
        "по extraction_confidence, если он есть во входе. "
        "В «Пробелы» перечисли непокрытые material–mode–condition и технологии только РФ или только зарубеж. "
        "В «Рекомендации» — похожие кейсы, эксперты из графа, темы для углубления. "
        "Для табличных данных используй GFM pipe-таблицы Markdown: | Колонка A | Колонка B |, "
        "строка-разделитель | --- | --- |, затем строки данных. "
        "Раздел «Уточняющий вопрос» опускай, если ответ полный."
    )


CHAT_STRUCTURE_RULES = chat_structure_rules("ru")

SYNTH_STRUCTURE_RULES = (
    "Поле summary — Markdown-текст для пользователя строго по шаблону разделов ##:\n"
    + ANSWER_STRUCTURE_TEMPLATE
    + "\nНе копируй situation_evaluation, reasoning_step и прочие техстроки из layer_results — "
    "используй только смысл найденных узлов/фрагментов. "
    "Используй переданные layer_results, sources, knowledge_gaps, experts, anomalies, gaps. "
    "KnowledgeGap из графа → раздел «Пробелы в знаниях». Expert → «Рекомендации». "
    "L4-аномалии (cluster_id=-1) упоминай в «Консенсус и разногласия» или «Пробелы», если релевантно."
)

FAST_STRUCTURE_NOTE = (
    "В режиме быстрого ответа разделы ## сохрани, но будь лаконичен: "
    "«Сводка» — 2–3 предложения; остальные разделы — по 1–2 пункта; "
    "«Рекомендации» и «Уточняющий вопрос» — только если нужны. "
    "Если переданы фрагменты MKG — опирайся на них и цитируй doc/node; "
    "не пиши «нет данных в контексте», если фрагменты релевантны. "
    "Если фрагментов нет — в «Источники» явно укажи, что поиск MKG не нашёл совпадений."
)


def extract_synthesis_entities(graph: dict[str, Any] | None) -> dict[str, Any]:
    """Извлечь KnowledgeGap, Expert, аномалии и сводку источников из накопленного графа."""
    nodes = list((graph or {}).get("nodes") or [])
    knowledge_gaps: list[dict[str, Any]] = []
    experts: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []
    source_hints: list[dict[str, Any]] = []

    for node in nodes:
        label = str(node.get("label") or "")
        props = node.get("props") or {}
        text = (
            props.get("name_ru")
            or props.get("quote")
            or props.get("raw_text_ru")
            or props.get("description")
            or props.get("text")
            or ""
        )[:240]
        entry = {
            "id": node.get("id"),
            "label": label,
            "text": text,
            "doc_id": props.get("_doc_id") or props.get("document_id") or props.get("source_doc_id"),
            "year": props.get("year") or props.get("publication_year"),
            "geography": props.get("geography") or props.get("country"),
            "extraction_confidence": props.get("extraction_confidence"),
        }
        if label == "KnowledgeGap":
            knowledge_gaps.append({**entry, "gap_type": props.get("gap_type") or props.get("type")})
        elif label == "Expert":
            experts.append(
                {
                    **entry,
                    "full_name": props.get("full_name") or props.get("name"),
                    "organization": props.get("organization"),
                    "role": props.get("role"),
                }
            )
        elif label in ("Claim", "ExperimentRun", "Material", "Process", "TextParagraph"):
            cluster_id = props.get("cluster_id")
            if cluster_id == -1 or str(cluster_id) == "-1":
                anomalies.append({**entry, "cluster_id": cluster_id, "reason": "HDBSCAN noise"})
            source_hints.append(entry)

    return {
        "knowledge_gaps": knowledge_gaps[:12],
        "experts": experts[:8],
        "anomalies": anomalies[:8],
        "source_hints": source_hints[:20],
    }
