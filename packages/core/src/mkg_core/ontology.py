"""Каноническая онтология MKG и санитайзер графа.

Единый источник правды о 6 слоях: какие метки узлов допустимы, какие типы
связей существуют и между какими метками они логичны (from → to). Здесь же —
очистка props от мусора (placeholder-значения, пустые строки, None) и отсев
неинформативных узлов.

Цель: в граф попадают только логичные, наполненные смыслом узлы и связи,
а не "шлак" от LLM (выдуманные метки/типы, пустые ноды, связи в никуда).
"""
from __future__ import annotations

from typing import Any

from mkg_core.graph_payload import GraphPayload, dedupe_graph_payload

# ── Слои и метки узлов ──────────────────────────────────────────────
L1_LABELS = frozenset(
    {"Material", "Process", "Equipment", "ChemicalReagent", "StandardMetric", "PhaseState", "Property"}
)
L2_LABELS = frozenset(
    {"Document", "Expert", "Location", "Organization", "Event", "Timeline", "Facility"}
)
L3_LABELS = frozenset(
    {"TextParagraph", "TableMatrix", "HeadingContext", "LangContext", "SynonymMap"}
)
L4_LABELS = frozenset(
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
L5_LABELS = frozenset(
    {"VerificationStatus", "SecurityRole", "Contradiction", "AuditTrail", "KnowledgeGap"}
)
L6_LABELS = frozenset({"TechnologySolution", "EconomicIndicator", "EnvironmentalIndicator"})

LABEL_LAYER: dict[str, str] = {
    **{label: "L1" for label in L1_LABELS},
    **{label: "L2" for label in L2_LABELS},
    **{label: "L3" for label in L3_LABELS},
    **{label: "L4" for label in L4_LABELS},
    **{label: "L5" for label in L5_LABELS},
    **{label: "L6" for label in L6_LABELS},
}

ALL_LABELS = frozenset(LABEL_LAYER)

# ── Правила связей: type → (допустимые метки from, допустимые метки to) ──
# Направление имеет смысл: например USES_MAT ведёт от стадии/опыта к материалу.
# Наборы `to` расширены разумными альтернативами, чтобы не терять связи,
# которые LLM часто вешает на ExperimentRun вместо TechStage.
_ANY_L1 = L1_LABELS

REL_RULES: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    # L1 внутренние
    "IN_PHASE": (frozenset({"Material"}), frozenset({"PhaseState"})),
    "HAS_PROPERTY": (frozenset({"Material", "Process"}), frozenset({"Property"})),
    # L2 + L2 → L3
    "AUTHORED": (frozenset({"Expert"}), frozenset({"Document"})),
    "ISSUED_AT": (frozenset({"Document"}), frozenset({"Location"})),
    "BELONGS_TO": (frozenset({"Document"}), frozenset({"Organization"})),
    "HAS_EVENT": (frozenset({"Document"}), frozenset({"Event"})),
    "ON_TIMELINE": (frozenset({"Event", "Document"}), frozenset({"Timeline"})),
    "HAS_PARAGRAPH": (frozenset({"Document"}), frozenset({"TextParagraph"})),
    "HAS_TABLE": (frozenset({"Document"}), frozenset({"TableMatrix"})),
    "HAS_HEADER": (frozenset({"Document"}), frozenset({"HeadingContext"})),
    "HAS_LANG": (frozenset({"Document"}), frozenset({"LangContext"})),
    # L3 внутренние и L3 → L4/L1
    "NEXT_PARAGRAPH": (frozenset({"TextParagraph"}), frozenset({"TextParagraph"})),
    "STRUCTURING": (frozenset({"HeadingContext"}), frozenset({"TextParagraph"})),
    "MAPS_TO": (frozenset({"SynonymMap"}), _ANY_L1),
    "TAGGED_WITH": (frozenset({"TextParagraph"}), frozenset({"LangContext"})),
    "CONTEXT_FOR": (
        frozenset({"TextParagraph", "TableMatrix"}),
        L2_LABELS
        | frozenset({"ExperimentRun", "TechStage", "Measurement", "Effect", "Claim"})
        | frozenset({"VerificationStatus", "SecurityRole"}),
    ),
    "DATA_SOURCE_FOR": (
        frozenset({"TextParagraph", "TableMatrix"}),
        _ANY_L1
        | frozenset({"Measurement", "ExperimentRun", "TechStage", "Effect", "Claim", "Formula", "Deviation"}),
    ),
    "ABOUT": (frozenset({"TextParagraph", "TableMatrix"}), L6_LABELS),
    # L4 внутренние и L4 → L1/L2
    "CONDUCTED_AT": (frozenset({"ExperimentRun"}), frozenset({"Facility"})),
    "EXECUTES_STAGE": (frozenset({"ExperimentRun"}), frozenset({"TechStage"})),
    "PRODUCED_MEASURE": (frozenset({"TechStage", "ExperimentRun"}), frozenset({"Measurement"})),
    "TRIGGERED_DEV": (frozenset({"TechStage", "ExperimentRun"}), frozenset({"Deviation"})),
    "COMPUTED_BY": (frozenset({"Measurement"}), frozenset({"Formula"})),
    "HAS_TREND": (frozenset({"Measurement"}), frozenset({"TrendVector"})),
    "USES_MAT": (frozenset({"TechStage", "ExperimentRun"}), frozenset({"Material"})),
    "OPERATES_PROC": (frozenset({"TechStage", "ExperimentRun"}), frozenset({"Process"})),
    "IN_EQUIPMENT": (frozenset({"TechStage", "ExperimentRun"}), frozenset({"Equipment"})),
    "CONSUMES_REAGENT": (frozenset({"TechStage", "ExperimentRun"}), frozenset({"ChemicalReagent"})),
    "EVALUATED_AGAINST": (frozenset({"Measurement"}), frozenset({"StandardMetric"})),
    "PRODUCES_OUTPUT": (frozenset({"TechStage", "ExperimentRun"}), frozenset({"Material"})),
    "SHOWED_EFFECT": (frozenset({"ExperimentRun", "TechStage"}), frozenset({"Effect"})),
    "UNDER_CONDITIONS": (frozenset({"ExperimentRun"}), frozenset({"EnvironmentalCondition"})),
    "PREVIOUS_VERSION": (frozenset({"Measurement"}), frozenset({"Measurement"})),
    # Claim (гибкий факт-узел L4)
    "ASSERTED_BY": (
        frozenset({"Claim"}),
        frozenset({"Document", "Expert", "ExperimentRun", "TechStage", "Organization"}),
    ),
    "DERIVED_FROM": (
        frozenset({"Claim"}),
        frozenset({"TextParagraph", "TableMatrix", "Measurement", "Claim", "ExperimentRun"}),
    ),
    "HAS_OBJECT": (
        frozenset({"Claim"}),
        _ANY_L1 | frozenset({"ExperimentRun", "TechStage", "Measurement", "Effect", "TechnologySolution"}),
    ),
    # L4/L2 → L5 и внутри L5
    "HAS_VALIDATION": (frozenset({"ExperimentRun"}), frozenset({"VerificationStatus"})),
    "FOUND_ANOMALY": (frozenset({"Measurement"}), frozenset({"Contradiction"})),
    "BASE_FOR_CONFLICT": (frozenset({"StandardMetric"}), frozenset({"Contradiction"})),
    "GOVERNED_BY": (frozenset({"Document"}), frozenset({"SecurityRole"})),
    "WRITES_LOG": (frozenset({"VerificationStatus"}), frozenset({"AuditTrail"})),
    "RESOLVED_BY": (frozenset({"Contradiction"}), frozenset({"Expert"})),
    "FIXED_IN": (frozenset({"Contradiction"}), frozenset({"Document"})),
    "LINKED_GAP": (frozenset({"Contradiction"}), frozenset({"KnowledgeGap"})),
    "DETECTED_MISSING": (frozenset({"Process", "Material"}), frozenset({"KnowledgeGap"})),
    # L6
    "DESCRIBES_SOLUTION": (frozenset({"TechnologySolution"}), frozenset({"Process"})),
    "USES_MATERIAL_TS": (frozenset({"TechnologySolution"}), frozenset({"Material"})),
    "HAS_ECONOMIC_INDICATOR": (frozenset({"TechnologySolution"}), frozenset({"EconomicIndicator"})),
    "HAS_ENVIRONMENTAL_INDICATOR": (frozenset({"TechnologySolution"}), frozenset({"EnvironmentalIndicator"})),
    "SOURCE": (frozenset({"TechnologySolution"}), frozenset({"Document"})),
    "COMPARABLE_TO": (frozenset({"TechnologySolution"}), frozenset({"TechnologySolution"})),
}

ALL_REL_TYPES = frozenset(REL_RULES)

# Синонимы типов связей, которые LLM выдаёт вместо канонических.
_REL_ALIASES: dict[str, str] = {
    "DESCRIBES_PROC": "DESCRIBES_SOLUTION",
    "DESCRIBES": "DESCRIBES_SOLUTION",
    "HAS_ECONOMIC": "HAS_ECONOMIC_INDICATOR",
    "HAS_ENVIRONMENTAL": "HAS_ENVIRONMENTAL_INDICATOR",
    "HAS_HEADING": "HAS_HEADER",
    "PRODUCED_MEASUREMENT": "PRODUCED_MEASURE",
    "SHOWS_EFFECT": "SHOWED_EFFECT",
    "HAS_EFFECT": "SHOWED_EFFECT",
}


def normalize_rel_type(rel_type: str, from_label: str | None = None) -> str:
    """Приводит тип связи к каноническому виду (с учётом метки источника)."""
    rt = (rel_type or "").strip().upper()
    if rt == "USES_MATERIAL":
        return "USES_MATERIAL_TS" if from_label == "TechnologySolution" else "USES_MAT"
    return _REL_ALIASES.get(rt, rt)


# ── Очистка props ───────────────────────────────────────────────────
_PLACEHOLDERS = frozenset(
    {
        "",
        "-",
        "—",
        "?",
        "n/a",
        "na",
        "none",
        "null",
        "nil",
        "unknown",
        "unspecified",
        "not specified",
        "not available",
        "tbd",
        "<id>",
        "<value>",
        "нет",
        "нет данных",
        "не указано",
        "не указан",
        "не определено",
        "неизвестно",
        "отсутствует",
    }
)

_NUMERIC_FIELDS = frozenset(
    {
        "numeric_value",
        "value",
        "measurement_error",
        "target_value",
        "min_allowed",
        "max_allowed",
        "value_min",
        "value_max",
        "temp_air_min",
        "temp_air_max",
        "humidity_min",
        "humidity_max",
        "temperature_boundary",
        "slope_coefficient",
        "rows_count",
        "trl_level",
        "confidence",
        "extraction_confidence",
        "confidence_score",
        "priority_score",
        "duration_periods",
        "total_duration_sec",
    }
)


def _is_placeholder(text: str) -> bool:
    return text.strip().lower() in _PLACEHOLDERS


def _coerce_number(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        raw = value.strip().replace(",", ".")
        raw = raw.replace("%", "").strip()
        try:
            num = float(raw)
        except ValueError:
            return None
        return int(num) if num.is_integer() else num
    return None


def _clean_value(key: str, value: Any) -> Any:
    """Возвращает очищенное значение или None, если это мусор/placeholder."""
    if value is None:
        return None
    if key in _NUMERIC_FIELDS:
        return _coerce_number(value)
    if isinstance(value, str):
        stripped = value.strip()
        if _is_placeholder(stripped):
            return None
        return stripped
    if isinstance(value, list):
        cleaned = [
            v.strip() for v in value
            if isinstance(v, str) and v.strip() and not _is_placeholder(v)
        ]
        cleaned += [v for v in value if not isinstance(v, str) and v is not None]
        return cleaned or None
    if isinstance(value, dict):
        return value or None
    return value


def clean_props(props: dict[str, Any] | None, node_id: str) -> dict[str, Any]:
    """Убирает placeholder/пустые значения; гарантирует корректный id."""
    result: dict[str, Any] = {}
    for key, value in (props or {}).items():
        if key == "id":
            continue
        cleaned = _clean_value(key, value)
        if cleaned is None:
            continue
        result[key] = cleaned
    result["id"] = node_id
    return result


# ── Информативность узлов ───────────────────────────────────────────
# Структурные узлы-«якоря» держим всегда (несут смысл через связи).
_ALWAYS_KEEP = frozenset(
    {
        "Document",
        "TextParagraph",
        "HeadingContext",
        "LangContext",
        "TableMatrix",
        "SynonymMap",
        "SecurityRole",
        "VerificationStatus",
        "AuditTrail",
        "Contradiction",
        "KnowledgeGap",
        "Timeline",
        "ExperimentRun",
        "TechStage",
    }
)

# Метка → поля-имена; узел информативен, если заполнено хотя бы одно.
_NAME_FIELDS: dict[str, tuple[str, ...]] = {
    "Material": ("name_ru", "name_en", "name", "chemical_formula", "aliases"),
    "Process": ("name_ru", "name_en", "name", "aliases"),
    "Equipment": ("name_ru", "name_en", "name", "aliases"),
    "ChemicalReagent": ("iupac_name", "name", "name_ru", "aliases"),
    "StandardMetric": ("param_name", "name"),
    "PhaseState": ("state_type", "description_ru"),
    "Property": ("name_ru", "name_en", "name", "value_string"),
    "Expert": ("full_name", "name"),
    "Organization": ("legal_name", "name"),
    "Location": ("country", "region", "city", "industrial_site"),
    "Event": ("event_name", "name"),
    "Facility": ("name",),
    "Effect": ("description_ru", "description_en", "description", "effect_type"),
    "Formula": ("latex_expression", "expression"),
    "Deviation": ("defect_type", "description", "action_taken_text"),
    "TrendVector": ("direction",),
    "EnvironmentalCondition": ("climate_type",),
    "Claim": ("text", "statement", "predicate", "description", "name"),
    "TechnologySolution": ("name_ru", "name_en", "name", "description"),
}

# Ожидаемые props по метке — для UI и проверки полноты extraction.
_COMMON_LLM_PROPS: tuple[str, ...] = ("quote", "source_quote", "extraction_confidence")

NODE_PROP_HINTS: dict[str, tuple[str, ...]] = {
    "Material": _NAME_FIELDS["Material"] + _COMMON_LLM_PROPS + ("description",),
    "Process": _NAME_FIELDS["Process"] + _COMMON_LLM_PROPS,
    "Equipment": _NAME_FIELDS["Equipment"] + _COMMON_LLM_PROPS,
    "ChemicalReagent": _NAME_FIELDS["ChemicalReagent"] + _COMMON_LLM_PROPS,
    "StandardMetric": _NAME_FIELDS["StandardMetric"] + _COMMON_LLM_PROPS + ("unit", "min_allowed", "max_allowed"),
    "PhaseState": _NAME_FIELDS["PhaseState"],
    "Property": _NAME_FIELDS["Property"] + ("value", "unit"),
    "Document": ("file_name", "hash_sum", "classification", "doc_type", "lang"),
    "Expert": _NAME_FIELDS["Expert"] + _COMMON_LLM_PROPS + ("organization", "role"),
    "Organization": _NAME_FIELDS["Organization"] + _COMMON_LLM_PROPS + ("country", "inn"),
    "Location": _NAME_FIELDS["Location"] + _COMMON_LLM_PROPS,
    "Event": _NAME_FIELDS["Event"] + _COMMON_LLM_PROPS + ("date", "description"),
    "Timeline": ("name", "period_start", "period_end"),
    "Facility": _NAME_FIELDS["Facility"] + _COMMON_LLM_PROPS + ("location",),
    "TextParagraph": ("raw_text_ru", "char_start", "char_end"),
    "HeadingContext": ("title_ru", "markdown_level"),
    "LangContext": ("lang_code", "name"),
    "TableMatrix": ("rows_count", "cols_count", "caption"),
    "SynonymMap": ("canonical", "synonyms"),
    "ExperimentRun": ("confidence", "run_date", "description") + _COMMON_LLM_PROPS,
    "TechStage": ("stage_name", "name_ru", "stage_order", "description") + _COMMON_LLM_PROPS,
    "Measurement": ("parameter", "numeric_value", "unit", "measurement_error", "conditions", "cluster_id", "is_anomaly", "anomaly_score") + _COMMON_LLM_PROPS,
    "Deviation": _NAME_FIELDS["Deviation"] + _COMMON_LLM_PROPS,
    "TrendVector": _NAME_FIELDS["TrendVector"] + ("slope_coefficient",) + _COMMON_LLM_PROPS,
    "Formula": _NAME_FIELDS["Formula"] + _COMMON_LLM_PROPS,
    "EnvironmentalCondition": _NAME_FIELDS["EnvironmentalCondition"] + _COMMON_LLM_PROPS,
    "Effect": _NAME_FIELDS["Effect"] + _COMMON_LLM_PROPS,
    "Claim": _NAME_FIELDS["Claim"] + _COMMON_LLM_PROPS + ("cluster_id", "is_anomaly", "anomaly_score"),
    "SecurityRole": ("role_name", "clearance_level"),
    "VerificationStatus": ("status", "verified_by", "verified_at"),
    "AuditTrail": ("action", "actor", "timestamp"),
    "TechnologySolution": _NAME_FIELDS["TechnologySolution"] + _COMMON_LLM_PROPS + ("trl_level",),
    "EconomicIndicator": ("name", "value", "unit", "currency") + _COMMON_LLM_PROPS,
    "EnvironmentalIndicator": ("name", "value", "unit") + _COMMON_LLM_PROPS,
}

# Узлы, требующие числового значения (без числа — это не факт, а мусор).
_NUMERIC_REQUIRED: dict[str, tuple[str, ...]] = {
    "Measurement": ("numeric_value",),
    "EconomicIndicator": ("value",),
    "EnvironmentalIndicator": ("value",),
    "TrendVector": ("slope_coefficient",),
}


def _has_value(props: dict[str, Any], fields: tuple[str, ...]) -> bool:
    for field in fields:
        val = props.get(field)
        if isinstance(val, str) and len(val.strip()) >= 2:
            return True
        if isinstance(val, list) and val:
            return True
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return True
    return False


def is_informative(label: str, props: dict[str, Any]) -> bool:
    """Узел несёт полезную информацию (иначе — отсеять как мусор)."""
    if label in _ALWAYS_KEEP:
        return True
    numeric_fields = _NUMERIC_REQUIRED.get(label)
    if numeric_fields:
        has_number = any(
            isinstance(props.get(f), (int, float)) and not isinstance(props.get(f), bool)
            for f in numeric_fields
        )
        if not has_number:
            return False
    name_fields = _NAME_FIELDS.get(label)
    if name_fields:
        return _has_value(props, name_fields)
    # Неизвестная (но допустимая) метка: хотя бы одно непустое смысловое поле.
    return any(k != "id" for k in props)


# ── Санитайзер графа ────────────────────────────────────────────────
def sanitize_graph_payload(payload: GraphPayload) -> GraphPayload:
    """Оставляет только логичные и наполненные узлы/связи для всех 6 слоёв.

    - метки не из онтологии → отбрасываются;
    - props чистятся от placeholder/пустых значений, числа приводятся к типам;
    - неинформативные узлы (без имени/значения) отсекаются;
    - типы связей нормализуются к каноническим; неизвестные — отбрасываются;
    - связи с несуществующими концами или недопустимыми (from→to) метками — отбрасываются.
    """
    clean_nodes: list[dict[str, Any]] = []
    label_by_id: dict[str, str] = {}
    for node in payload.nodes:
        node_id = str(node.get("id") or "").strip()
        label = str(node.get("label") or "").strip()
        if not node_id or label not in ALL_LABELS:
            continue
        props = clean_props(node.get("props") if isinstance(node.get("props"), dict) else {}, node_id)
        if not is_informative(label, props):
            continue
        clean_nodes.append({"id": node_id, "label": label, "props": props})
        label_by_id[node_id] = label

    clean_rels: list[dict[str, Any]] = []
    for rel in payload.relationships:
        start = str(rel.get("from") or "").strip()
        end = str(rel.get("to") or "").strip()
        if not start or not end or start not in label_by_id or end not in label_by_id:
            continue
        from_label = label_by_id[start]
        rel_type = normalize_rel_type(str(rel.get("type") or ""), from_label)
        rule = REL_RULES.get(rel_type)
        if rule is None:
            continue
        allowed_from, allowed_to = rule
        if from_label not in allowed_from or label_by_id[end] not in allowed_to:
            continue
        props_raw = rel.get("props") if isinstance(rel.get("props"), dict) else {}
        props: dict[str, Any] = {}
        for key, value in props_raw.items():
            cleaned = _clean_value(key, value)
            if cleaned is not None:
                props[key] = cleaned
        clean_rels.append({"type": rel_type, "from": start, "to": end, "props": props})

    return dedupe_graph_payload(GraphPayload(nodes=clean_nodes, relationships=clean_rels))
