"""Удаление внутренних метаданных MKG из текста ответа для пользователя."""
from __future__ import annotations

import re

_DOC_ID = re.compile(r"(?:document_id|doc_id)\s*[:=]\s*[\w:-]+", re.IGNORECASE)
_NEO4J_ID = re.compile(r"neo4j_node_id\s*[:=]\s*[^\]\n,)]+", re.IGNORECASE)
_NODE_ID = re.compile(r"(?<!\w)node_id\s*[:=]\s*[\w:-]+", re.IGNORECASE)
_BRACKET_META = re.compile(
    r"\[[^\]]*(?:TextParagraph|HeadingContext|Claim|Material|doc:)[^\]]*\]",
    re.IGNORECASE,
)
_LAYER_PHRASE = re.compile(r"(?:слой|layer)\s*L[1-6]\b", re.IGNORECASE)
_LAYER_DOT = re.compile(r"·\s*L[1-6]\b")
_HEX_DOC = re.compile(r"\bdoc:[a-f0-9]{8,}\b", re.IGNORECASE)
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_EMPTY_PARENS = re.compile(r"\(\s*\)")
_ORPHAN_DOTS = re.compile(r"(\s*·\s*){2,}")
# Pipeline / retrieval stats — только для trace, не для текста ответа пользователю
_SITUATION_EVAL_LINE = re.compile(
    r"^\s*Оценка ситуации\s*·[^\n]*$",
    re.MULTILINE | re.IGNORECASE,
)
_SITUATION_EVAL_INLINE = re.compile(
    r"Оценка ситуации\s*·\s*L[1-6]\s*:\s*\d+\s*узл\.\s*,\s*\d+\s*св\.\s*,\s*\d+\s*хитов\s*—\s*[^\n]+",
    re.IGNORECASE,
)
_LAYER_STATS_LINE = re.compile(
    r"^\s*(?:Слой\s*)?L[1-6]\s*:\s*\d+\s*узл\.\s*,\s*\d+\s*св\.\s*,\s*\d+\s*хитов[^\n]*$",
    re.MULTILINE | re.IGNORECASE,
)
_LAYER_STATS_INLINE = re.compile(
    r"(?:Слой\s*)?L[1-6]\s*:\s*\d+\s*узл\.\s*,\s*\d+\s*св\.\s*(?:,\s*\d+\s*хитов)?(?:\s*—\s*[^\n.]+)?",
    re.IGNORECASE,
)
_GRAPH_COUNT_STATS = re.compile(
    r"\d+\s*узл\.\s*,\s*\d+\s*св\.\s*,\s*\d+\s*хитов",
    re.IGNORECASE,
)
_REASONING_STATS = re.compile(
    r"(?:найдено\s+)?\d+\s*узл\.\s*,\s*\d+\s*(?:св\.|связ(?:ей|\.))\s*,\s*(?:Qdrant/keyword\s+)?хитов\s+\d+",
    re.IGNORECASE,
)
_RETRIEVAL_METHOD_TAIL = re.compile(
    r"—\s*(?:Text:\s*)?Qdrant\s+L[1-6][^\n.]*",
    re.IGNORECASE,
)
_EMPTY_SECTION_LINE = re.compile(r"^\s*[-·—]\s*$", re.MULTILINE)


def strip_graph_pipeline_stats(text: str) -> str:
    """Убрать счётчики узлов/связей/хитов и метки retrieval из пользовательского текста."""
    if not text or not str(text).strip():
        return text
    out = str(text)
    for pattern in (
        _SITUATION_EVAL_LINE,
        _SITUATION_EVAL_INLINE,
        _LAYER_STATS_LINE,
        _LAYER_STATS_INLINE,
        _GRAPH_COUNT_STATS,
        _REASONING_STATS,
        _RETRIEVAL_METHOD_TAIL,
    ):
        out = pattern.sub("", out)
    out = _EMPTY_SECTION_LINE.sub("", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def sanitize_user_facing_text(text: str) -> str:
    """Убрать document_id, neo4j_node_id, коды слоёв и прочие техметки из ответа."""
    if not text or not str(text).strip():
        return text
    out = strip_graph_pipeline_stats(str(text))
    for pattern in (_DOC_ID, _NEO4J_ID, _NODE_ID, _BRACKET_META, _LAYER_PHRASE, _LAYER_DOT, _HEX_DOC):
        out = pattern.sub("", out)
    out = _ORPHAN_DOTS.sub(" · ", out)
    out = _EMPTY_PARENS.sub("", out)
    out = _MULTI_SPACE.sub(" ", out)
    return out.strip()
