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

CHAT_STRUCTURE_RULES = (
    "Структура ответа — Markdown с разделами ## (обязательно на русском):\n"
    + "\n".join(f"- ## {title}" for title in ANSWER_SECTION_TITLES[:-1])
    + "\n- ## Уточняющий вопрос (опционально, если ответ неполный)\n"
    "В «Источники по группам» группируй evidence по методу/процессу, году, географии (РФ/зарубеж), "
    "уровню детализации. В «Консенсус и разногласия» явно раздели согласованные выводы и расхождения. "
    "В «Уверенность» укажи число опорных источников и уровень достоверности (высокая/средняя/низкая) "
    "по extraction_confidence, если он есть во входе. "
    "В «Пробелы» перечисли непокрытые material–mode–condition и технологии только РФ или только зарубеж. "
    "В «Рекомендации» — похожие кейсы, эксперты из графа, темы для углубления. "
    "Раздел «Уточняющий вопрос» опускай, если ответ полный."
)

SYNTH_STRUCTURE_RULES = (
    "Поле summary — Markdown-текст для пользователя строго по шаблону разделов ##:\n"
    + ANSWER_STRUCTURE_TEMPLATE
    + "\nИспользуй переданные layer_results, sources, knowledge_gaps, experts, anomalies, gaps. "
    "KnowledgeGap из графа → раздел «Пробелы в знаниях». Expert → «Рекомендации». "
    "L4-аномалии (cluster_id=-1) упоминай в «Консенсус и разногласия» или «Пробелы», если релевантно."
)

FAST_STRUCTURE_NOTE = (
    "В режиме быстрого ответа разделы могут быть короче, но заголовки ## сохрани; "
    "«Рекомендации» и «Уточняющий вопрос» — по необходимости."
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
