"""HRM-inspired adaptive halting controller (ACT-like halt head).

Высокоуровневый контроллер решает, продолжать ли рассуждение (ещё один раунд
слоёв L1–L6) или остановиться. Решение принимается по эвристикам (marginal gain,
pending bus, бюджет раундов) и опционально по LLM «halt head», который может
переопределить эвристику только в пределах [min_rounds, hard_cap].
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agent_bus import ALL_LAYERS, get_pending_requests
from app.utils import remaining_seconds


_HALT_PROMPT = """
Ты Halt Head (высокоуровневый контроллер HRM) для оркестратора MKG.
Низкоуровневые слоевые агенты L1–L6 уже отработали текущий раунд рассуждения.
Твоя задача — решить, достаточно ли собрано evidence, чтобы дать качественный ответ,
или нужен ещё один раунд исследования графа.
Сигналы: marginal_gain — сколько новых узлов+связей добавил последний раунд
(мало → выгода от продолжения падает); pending_bus — незакрытые запросы между
агентами (есть → возможно стоит продолжить); round/min_rounds/hard_cap — бюджет.
Верни только JSON:
{"decision": "halt" | "continue", "confidence": 0.0, "reason": "кратко на русском"}
halt = остановиться и синтезировать ответ. continue = ещё один раунд.
""".strip()


@dataclass
class HaltDecision:
    halt: bool
    reason: str
    confidence: float
    marginal_gain: int
    source: str  # "heuristic" | "llm" | "budget" | "min_rounds"
    signals: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "halt": self.halt,
            "reason": self.reason,
            "confidence": round(float(self.confidence), 3),
            "marginal_gain": int(self.marginal_gain),
            "source": self.source,
            "signals": self.signals,
        }


def _graph_size(state: dict[str, Any]) -> int:
    acc = state.get("accumulated_graph") or {}
    nodes = acc.get("nodes") or []
    rels = acc.get("relationships") or []
    return len(nodes) + len(rels)


def compute_marginal_gain(state: dict[str, Any]) -> int:
    """Новые (узлы+связи), добавленные с прошлого раунда."""
    current = _graph_size(state)
    last = int(state.get("last_round_graph_size") or 0)
    return max(0, current - last)


def _layer_counts(state: dict[str, Any]) -> dict[str, int]:
    counts = {l: 0 for l in ALL_LAYERS}
    for lr in state.get("layer_results") or []:
        layer = str(lr.get("layer") or "").upper()
        if layer in counts:
            counts[layer] += len(lr.get("nodes_found") or [])
    return counts


def _accumulated_summary(state: dict[str, Any]) -> dict[str, Any]:
    acc = state.get("accumulated_graph") or {}
    return {
        "node_count": len(acc.get("nodes") or []),
        "rel_count": len(acc.get("relationships") or []),
        "new_connections": len(acc.get("new_connections") or []),
    }


async def decide_halt(
    state: dict[str, Any],
    settings: Any,
    llm: Any = None,
) -> HaltDecision:
    """Решить halt/continue для текущего раунда рассуждения.

    Всегда возвращает HaltDecision. LLM-ошибки безопасно откатываются к эвристике.
    """
    round_num = int(state.get("round") or 0)
    min_rounds = int(state.get("min_rounds") or getattr(settings, "agent_loop_min_rounds", 2))
    hard_cap = int(
        state.get("hard_max_rounds")
        or getattr(settings, "agent_loop_hard_cap", 6)
    )
    sampled_budget = int(state.get("sampled_round_budget") or state.get("max_rounds") or hard_cap)
    gain = compute_marginal_gain(state)
    bus = state.get("agent_bus") or []
    pending = get_pending_requests(bus, round_num=round_num)
    signals: dict[str, Any] = {
        "round": round_num,
        "min_rounds": min_rounds,
        "hard_cap": hard_cap,
        "sampled_budget": sampled_budget,
        "marginal_gain": gain,
        "pending_bus": len(pending),
        "graph_size": _graph_size(state),
    }

    # 1) Никогда не останавливаемся до min_rounds.
    if round_num + 1 < min_rounds:
        return HaltDecision(
            halt=False,
            reason=f"round {round_num + 1} < min_rounds {min_rounds}",
            confidence=1.0,
            marginal_gain=gain,
            source="min_rounds",
            signals=signals,
        )

    # 2) Достигнут жёсткий потолок — остановка безусловна.
    if round_num + 1 >= hard_cap:
        return HaltDecision(
            halt=True,
            reason=f"round {round_num + 1} >= hard_cap {hard_cap}",
            confidence=1.0,
            marginal_gain=gain,
            source="budget",
            signals=signals,
        )

    # Достигнут стохастически выбранный бюджет раундов — тоже остановка.
    if round_num + 1 >= sampled_budget:
        return HaltDecision(
            halt=True,
            reason=f"round {round_num + 1} >= sampled_budget {sampled_budget}",
            confidence=0.9,
            marginal_gain=gain,
            source="budget",
            signals=signals,
        )

    # 3) Эвристика: малый прирост и нет незакрытых запросов → можно остановиться.
    min_gain = int(getattr(settings, "agent_halt_min_gain", 2))
    heuristic_halt = gain < min_gain and not pending
    decision = HaltDecision(
        halt=heuristic_halt,
        reason=(
            f"marginal_gain {gain} < min_gain {min_gain} и нет pending-запросов"
            if heuristic_halt
            else f"marginal_gain {gain} >= min_gain {min_gain} или есть pending ({len(pending)})"
        ),
        confidence=0.6 if heuristic_halt else 0.55,
        marginal_gain=gain,
        source="heuristic",
        signals=signals,
    )

    # 4) LLM halt head может переопределить эвристику в пределах [min_rounds, hard_cap].
    use_llm = bool(getattr(settings, "agent_halt_use_llm", True)) and llm is not None
    time_ok = remaining_seconds(state, getattr(settings, "timeout_seconds", 45.0)) > 3.0
    if use_llm and time_ok:
        timeout = min(getattr(settings, "planner_timeout", 1.2), 2.0)
        try:
            acc = state.get("accumulated_graph") or {}
            result = await llm.generate_json(
                instructions=_HALT_PROMPT,
                payload={
                    "query": state.get("query"),
                    "round": round_num,
                    "min_rounds": min_rounds,
                    "hard_cap": hard_cap,
                    "marginal_gain": gain,
                    "pending_bus": [
                        {"from": m.get("from"), "to": m.get("to"), "type": m.get("type")}
                        for m in pending[:6]
                    ],
                    "layer_counts": _layer_counts(state),
                    "accumulated_summary": _accumulated_summary(state),
                },
                max_tokens=120,
                timeout=timeout,
            )
            if isinstance(result, dict):
                raw = str(result.get("decision") or "").strip().lower()
                if raw in ("halt", "continue"):
                    llm_halt = raw == "halt"
                    try:
                        conf = float(result.get("confidence"))
                    except (TypeError, ValueError):
                        conf = 0.7
                    conf = max(0.0, min(1.0, conf))
                    reason = str(result.get("reason") or "llm halt head")[:200]
                    signals["llm_decision"] = raw
                    signals["heuristic_halt"] = heuristic_halt
                    # LLM действует только в границах [min_rounds, hard_cap] —
                    # они уже гарантированы проверками 1) и 2) выше.
                    decision = HaltDecision(
                        halt=llm_halt,
                        reason=reason,
                        confidence=conf,
                        marginal_gain=gain,
                        source="llm",
                        signals=signals,
                    )
        except Exception as exc:  # noqa: BLE001 - откат к эвристике
            signals["llm_error"] = str(exc)[:160]
            decision.signals = signals

    return decision
