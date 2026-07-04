"""In-process JSON message bus for inter-layer agent communication (MVP)."""
from __future__ import annotations

import uuid
from typing import Any

REQUEST_TYPES = frozenset({"request_evidence", "graph_expand", "question", "gap_found"})
RESPONSE_TYPES = frozenset({"response", "evidence", "graph_patch"})

ALL_LAYERS = ("L1", "L2", "L3", "L4", "L5", "L6")


def layer_to_agent_id(layer: str) -> str:
    return f"{str(layer).lower()}_agent"


def agent_id_to_layer(agent_id: str) -> str:
    return str(agent_id).replace("_agent", "").upper()


def publish(bus: list[dict[str, Any]] | None, message: dict[str, Any]) -> list[dict[str, Any]]:
    """Append a message to the bus; returns new list (immutable append)."""
    msg = dict(message)
    msg.setdefault("id", str(uuid.uuid4())[:8])
    out = list(bus or [])
    out.append(msg)
    return out


def get_messages_for(
    bus: list[dict[str, Any]] | None,
    agent_id: str,
    *,
    round_num: int | None = None,
    types: frozenset[str] | None = None,
    include_broadcast: bool = True,
) -> list[dict[str, Any]]:
    """Messages addressed to agent_id (or broadcast)."""
    aid = agent_id.lower()
    hits: list[dict[str, Any]] = []
    for msg in bus or []:
        if round_num is not None and msg.get("round") != round_num:
            continue
        to = str(msg.get("to") or "").lower()
        if to == aid:
            hits.append(msg)
        elif include_broadcast and to == "broadcast":
            hits.append(msg)
    if types:
        hits = [m for m in hits if str(m.get("type") or "") in types]
    return hits


def get_pending_requests(
    bus: list[dict[str, Any]] | None,
    *,
    round_num: int | None = None,
) -> list[dict[str, Any]]:
    """Request messages that have no matching response yet."""
    answered: set[str] = set()
    for msg in bus or []:
        if str(msg.get("type") or "") in RESPONSE_TYPES:
            ref = msg.get("in_reply_to") or msg.get("reply_to")
            if ref:
                answered.add(str(ref))
    pending: list[dict[str, Any]] = []
    for msg in bus or []:
        if round_num is not None and msg.get("round") != round_num:
            continue
        mtype = str(msg.get("type") or "")
        if mtype not in REQUEST_TYPES:
            continue
        if str(msg.get("id") or "") in answered:
            continue
        pending.append(msg)
    return pending


def make_message(
    *,
    from_agent: str,
    to: str,
    type_: str,
    payload: dict[str, Any],
    round_num: int,
    in_reply_to: str | None = None,
) -> dict[str, Any]:
    msg: dict[str, Any] = {
        "from": from_agent,
        "to": to,
        "type": type_,
        "payload": payload,
        "round": round_num,
    }
    if in_reply_to:
        msg["in_reply_to"] = in_reply_to
    return msg


def respond(
    bus: list[dict[str, Any]] | None,
    *,
    from_agent: str,
    to: str,
    request_id: str,
    type_: str,
    payload: dict[str, Any],
    round_num: int,
) -> list[dict[str, Any]]:
    return publish(
        bus,
        make_message(
            from_agent=from_agent,
            to=to,
            type_=type_,
            payload=payload,
            round_num=round_num,
            in_reply_to=request_id,
        ),
    )


def bus_summary(bus: list[dict[str, Any]] | None, *, limit: int = 12) -> list[dict[str, Any]]:
    """Compact view for trace / UI."""
    out: list[dict[str, Any]] = []
    for msg in (bus or [])[-limit:]:
        payload = msg.get("payload") or {}
        preview = (
            payload.get("question")
            or payload.get("gap")
            or payload.get("summary")
            or payload.get("reason")
            or ""
        )
        out.append(
            {
                "id": msg.get("id"),
                "from": msg.get("from"),
                "to": msg.get("to"),
                "type": msg.get("type"),
                "round": msg.get("round"),
                "preview": str(preview)[:120] if preview else "",
            }
        )
    return out
