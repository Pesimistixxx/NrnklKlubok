"""Conversational vs domain query classification (greetings, meta, small talk)."""
from __future__ import annotations

import re
from typing import Literal

ConversationalIntent = Literal["greeting", "meta", "thanks", "ack"]

_GREETING_EXACT = frozenset(
    {
        "hello",
        "hi",
        "hey",
        "heya",
        "hiya",
        "yo",
        "sup",
        "howdy",
        "greetings",
        "привет",
        "здравствуй",
        "здравствуйте",
        "салют",
        "хай",
        "добрый день",
        "доброе утро",
        "добрый вечер",
        "доброй ночи",
        "good morning",
        "good evening",
        "good afternoon",
        "good night",
    }
)

_THANKS_EXACT = frozenset(
    {
        "thanks",
        "thank you",
        "thx",
        "ty",
        "спасибо",
        "благодарю",
        "мерси",
    }
)

_ACK_EXACT = frozenset(
    {
        "ok",
        "okay",
        "ок",
        "окей",
        "ага",
        "понятно",
        "ясно",
        "cool",
        "nice",
    }
)

_META_PATTERNS = (
    re.compile(r"^(?:who are you|what are you|what(?:'s| is) your name)\??$", re.I),
    re.compile(r"^(?:кто ты|что ты(?: такое)?|как тебя зовут|ты кто)\??$", re.I),
    re.compile(r"^(?:what can you do|how can you help|help me)\??$", re.I),
    re.compile(
        r"^(?:чем можешь помочь|что умеешь|как ты работаешь|помоги|расскажи о себе)\??$",
        re.I,
    ),
)

_DOMAIN_HINT_RE = re.compile(
    r"\b(?:"
    r"никел|nickel|cobalt|кобальт|медь|copper|желез|iron|"
    r"материал|material|процесс|process|технолог|technology|"
    r"сплав|alloy|конcentr|температур|temperature|давлен|pressure|"
    r"документ|document|граф|graph|qdrant|neo4j|"
    r"анomal|факт|fact|кластер|cluster|"
    r"что такое|what is|как работает|how does"
    r")\b",
    re.I,
)

_TOKEN_RE = re.compile(r"[\w\u0400-\u04FF]+", re.UNICODE)


def _normalize(text: str) -> str:
    clean = re.sub(r"[^\w\u0400-\u04FF\s]", " ", (text or "").strip().lower())
    return re.sub(r"\s+", " ", clean).strip()


def _has_domain_signal(query: str) -> bool:
    if _DOMAIN_HINT_RE.search(query):
        return True
    try:
        from mkg_core.alias_expansion import get_alias_lookup

        lookup = get_alias_lookup()
        tokens = [_normalize(t) for t in _TOKEN_RE.findall(query) if len(_normalize(t)) >= 2]
        if any(t in lookup for t in tokens):
            return True
    except Exception:
        pass
    return False


def classify_query_intent(query: str) -> ConversationalIntent | None:
    """Return conversational intent or None if the query needs corpus retrieval."""
    q = (query or "").strip()
    if not q or _has_domain_signal(q):
        return None
    try:
        from mkg_core.search_query import is_continuation_query

        if is_continuation_query(q):
            return None
    except Exception:
        pass

    norm = _normalize(q)
    if not norm:
        return None
    words = norm.split()
    if len(words) > 6:
        return None

    if norm in _GREETING_EXACT:
        return "greeting"
    if len(words) == 1 and words[0] in {g for g in _GREETING_EXACT if " " not in g}:
        return "greeting"
    if norm in _THANKS_EXACT:
        return "thanks"
    if norm in _ACK_EXACT and len(words) <= 2:
        return "ack"
    for pat in _META_PATTERNS:
        if pat.match(norm):
            return "meta"
    return None


def is_conversational_query(query: str) -> bool:
    return classify_query_intent(query) is not None


def conversational_system_note(intent: ConversationalIntent, *, lang: str = "ru") -> str:
    """Extra system instructions for direct conversational replies (no RAG)."""
    if lang == "en":
        base = (
            "The user sent a conversational message (not a knowledge-map question). "
            "Reply briefly and warmly in English. Do NOT cite documents, papers, or random corpus fragments. "
            "Introduce yourself as the MKG knowledge-map assistant and invite a question about "
            "materials, processes, or uploaded documents."
        )
    else:
        base = (
            "Пользователь написал бытовую реплику (не вопрос по карте знаний). "
            "Ответь кратко и дружелюбно на русском. НЕ цитируй документы, статьи и случайные фрагменты корпуса. "
            "Представься как ассистент карты знаний MKG и предложи задать вопрос по материалам, "
            "процессам или загруженным документам."
        )
    if intent == "meta":
        if lang == "en":
            return base + " Explain what MKG can do: search documents, graph layers L1–L6, compare technologies."
        return base + " Кратко опиши возможности MKG: поиск по документам, слои L1–L6, сравнение технологий."
    if intent == "thanks":
        if lang == "en":
            return base + " Acknowledge thanks in one short sentence."
        return base + " Поблагодари в одном коротком предложении."
    if intent == "ack":
        if lang == "en":
            return base + " Acknowledge briefly; ask if they have a question about the knowledge map."
        return base + " Кратко подтверди; спроси, есть ли вопрос по карте знаний."
    return base


def retrieval_confidence_ok(hits: list[dict], query: str, *, min_score: float = 0.42) -> bool:
    """False when top retrieval score is too low for a short non-domain query."""
    if is_conversational_query(query):
        return False
    if not hits:
        return False
    top = max(float(h.get("score") or 0) for h in hits)
    words = query.strip().split()
    if len(words) <= 3 and top < min_score:
        return False
    return True
