"""Structured query facets for multi-parameter MKG search (material, process, geo, time, numeric)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_RU_GEO_RE = re.compile(
    r"\b(росси[яй]|russia|российск|рф|moscow|москв|спб|санкт-петербург)\b",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


@dataclass
class QueryFacets:
    materials: list[str] = field(default_factory=list)
    processes: list[str] = field(default_factory=list)
    geography: list[str] = field(default_factory=list)
    year_min: int | None = None
    year_max: int | None = None
    numeric_min: float | None = None
    numeric_max: float | None = None
    numeric_param: str | None = None
    conditions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.materials:
            out["materials"] = list(self.materials)
        if self.processes:
            out["processes"] = list(self.processes)
        if self.geography:
            out["geography"] = list(self.geography)
        if self.year_min is not None:
            out["year_min"] = self.year_min
        if self.year_max is not None:
            out["year_max"] = self.year_max
        if self.numeric_min is not None:
            out["numeric_min"] = self.numeric_min
        if self.numeric_max is not None:
            out["numeric_max"] = self.numeric_max
        if self.numeric_param:
            out["numeric_param"] = self.numeric_param
        if self.conditions:
            out["conditions"] = list(self.conditions)
        return out

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> QueryFacets:
        if not raw:
            return cls()
        years = raw.get("years")
        year_min = _coerce_int(raw.get("year_min"))
        year_max = _coerce_int(raw.get("year_max"))
        if isinstance(years, list) and years:
            parsed = [_parse_year_token(str(y)) for y in years]
            nums = [y for y in parsed if y is not None]
            if nums and year_min is None:
                year_min = min(nums)
            if nums and year_max is None:
                year_max = max(nums)
        return cls(
            materials=_as_str_list(raw.get("materials")),
            processes=_as_str_list(raw.get("processes")),
            geography=_normalize_geography(raw.get("geography")),
            year_min=year_min,
            year_max=year_max,
            numeric_min=_coerce_float(raw.get("numeric_min")),
            numeric_max=_coerce_float(raw.get("numeric_max")),
            numeric_param=str(raw.get("numeric_param") or "").strip() or None,
            conditions=_as_str_list(raw.get("conditions")),
        )


def parse_facets_from_plan(plan: dict[str, Any] | None) -> QueryFacets:
    """Extract query_facets from orchestrator plan or scope dict."""
    if not plan:
        return QueryFacets()
    nested = plan.get("query_facets")
    if isinstance(nested, dict):
        return QueryFacets.from_dict(nested)
    return QueryFacets.from_dict(plan)


def enrich_search_with_facets(query: str, facets: QueryFacets, *, limit: int = 800) -> str:
    """Append facet keywords to semantic search query."""
    parts = [query.strip()]
    for group in (facets.materials, facets.processes, facets.conditions):
        parts.extend(group[:3])
    for geo in facets.geography[:2]:
        if geo in ("domestic", "foreign"):
            parts.append("Россия" if geo == "domestic" else "зарубежная практика")
        else:
            parts.append(geo)
    if facets.numeric_param:
        parts.append(facets.numeric_param)
    clean = re.sub(r"\s+", " ", " ".join(p for p in parts if p)).strip()
    return clean[:limit] if len(clean) > limit else clean


def filter_hits_by_facets(hits: list[dict[str, Any]], facets: QueryFacets) -> list[dict[str, Any]]:
    """Post-filter search hits by structured facets (soft: keep if no facet set)."""
    if not facets.to_dict():
        return hits
    out: list[dict[str, Any]] = []
    for hit in hits:
        props = hit.get("props") if isinstance(hit.get("props"), dict) else {}
        label = str(hit.get("label") or "")
        if _node_matches_facets(label, props, facets, text=str(hit.get("text") or "")):
            out.append(hit)
    return out if out else hits


def _node_matches_facets(
    label: str,
    props: dict[str, Any],
    facets: QueryFacets,
    *,
    text: str = "",
) -> bool:
    blob = _node_text_blob(label, props, text)
    if facets.materials and label == "Material":
        if not any(m.lower() in blob for m in facets.materials):
            return False
    if facets.processes and label == "Process":
        if not any(p.lower() in blob for p in facets.processes):
            return False
    if facets.geography:
        geo_ok = _geo_matches(facets.geography, props, blob)
        if facets.geography and label in ("Location", "Document", "Organization", "Facility", "Expert"):
            if not geo_ok:
                return False
        elif facets.geography and not geo_ok and _geo_strict(facets.geography):
            return False
    if facets.year_min is not None or facets.year_max is not None:
        year = _node_year(props)
        if year is not None:
            if facets.year_min is not None and year < facets.year_min:
                return False
            if facets.year_max is not None and year > facets.year_max:
                return False
    if facets.numeric_min is not None or facets.numeric_max is not None:
        if label == "Measurement":
            val = _node_numeric(props, facets.numeric_param)
            if val is not None:
                if facets.numeric_min is not None and val < facets.numeric_min:
                    return False
                if facets.numeric_max is not None and val > facets.numeric_max:
                    return False
    return True


def _geo_strict(geography: list[str]) -> bool:
    return any(g in ("domestic", "foreign") for g in geography)


def _geo_matches(geography: list[str], props: dict[str, Any], blob: str) -> bool:
    domestic = is_domestic_geo(blob, props)
    for g in geography:
        gl = g.lower().strip()
        if gl in ("domestic", "ru", "россия", "российская"):
            if domestic:
                return True
        elif gl in ("foreign", "зарубежная", "зарубежный"):
            if not domestic:
                return True
        elif gl in blob:
            return True
    return not _geo_strict(geography)


def is_domestic_geo(text: str, props: dict[str, Any] | None = None) -> bool:
    parts = [text]
    if props:
        for k in ("country", "region", "city", "name", "name_ru", "lang"):
            v = props.get(k)
            if isinstance(v, str) and v.strip():
                parts.append(v)
    combined = " ".join(parts)
    return bool(_RU_GEO_RE.search(combined))


def _node_text_blob(label: str, props: dict[str, Any], extra: str) -> str:
    keys = (
        "name_ru", "name_en", "name", "title", "text", "quote", "source_quote",
        "country", "region", "city", "parameter", "conditions", "description",
        "chemical_formula",
    )
    parts = [label, extra]
    for k in keys:
        v = props.get(k)
        if isinstance(v, str) and v.strip():
            parts.append(v)
    return " ".join(parts).lower()


def _node_year(props: dict[str, Any]) -> int | None:
    for k in ("publication_year", "pub_year", "year", "run_date", "event_date", "date", "updated_at"):
        raw = props.get(k)
        if raw is None or raw == "":
            continue
        if isinstance(raw, (int, float)) and 1000 <= int(raw) <= 9999:
            return int(raw)
        m = _YEAR_RE.search(str(raw))
        if m:
            return int(m.group(0))
    return None


def _node_numeric(props: dict[str, Any], param_hint: str | None) -> float | None:
    if param_hint:
        param = str(props.get("parameter") or props.get("name") or "").lower()
        if param_hint.lower() not in param:
            return None
    for k in ("numeric_value", "value", "concentration", "temperature", "flow_rate"):
        raw = props.get(k)
        if raw is None or raw == "":
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return None


def source_date_from_props(props: dict[str, Any]) -> str | None:
    for k in ("updated_at", "publication_year", "pub_year", "year", "run_date", "event_date", "date"):
        v = props.get(k)
        if v is None or v == "":
            continue
        return str(v)[:32]
    return None


def reliability_from_props(props: dict[str, Any]) -> float | None:
    for k in ("extraction_confidence", "confidence", "confidence_score"):
        v = props.get(k)
        if v is None or v == "":
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return None


def _as_str_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        if isinstance(raw, str) and raw.strip():
            return [raw.strip()]
        return []
    return [str(x).strip() for x in raw if str(x).strip()]


def _normalize_geography(raw: Any) -> list[str]:
    items = _as_str_list(raw)
    out: list[str] = []
    for g in items:
        gl = g.lower()
        if gl in ("ru", "россия", "российская", "domestic"):
            out.append("domestic")
        elif gl in ("foreign", "зарубежная", "зарубежный", "international"):
            out.append("foreign")
        else:
            out.append(g)
    return out


def _coerce_int(v: Any) -> int | None:
    if v is None or v == "":
        return None
    try:
        n = int(v)
        return n if 1000 <= n <= 9999 else None
    except (TypeError, ValueError):
        m = _YEAR_RE.search(str(v))
        return int(m.group(0)) if m else None


def _coerce_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _parse_year_token(token: str) -> int | None:
    token = token.strip()
    if "-" in token:
        parts = token.split("-", 1)
        return _coerce_int(parts[0])
    return _coerce_int(token)
