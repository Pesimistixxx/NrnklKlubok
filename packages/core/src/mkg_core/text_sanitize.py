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


def sanitize_user_facing_text(text: str) -> str:
    """Убрать document_id, neo4j_node_id, коды слоёв и прочие техметки из ответа."""
    if not text or not str(text).strip():
        return text
    out = str(text)
    for pattern in (_DOC_ID, _NEO4J_ID, _NODE_ID, _BRACKET_META, _LAYER_PHRASE, _LAYER_DOT, _HEX_DOC):
        out = pattern.sub("", out)
    out = _ORPHAN_DOTS.sub(" · ", out)
    out = _EMPTY_PARENS.sub("", out)
    out = _MULTI_SPACE.sub(" ", out)
    return out.strip()
