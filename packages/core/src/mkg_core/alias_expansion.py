"""RU/EN alias expansion for search queries (Material, Process, Equipment)."""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

_ALIAS_LABELS = frozenset({"Material", "Process", "Equipment", "ChemicalReagent"})
_TOKEN_RE = re.compile(r"[\w\u0400-\u04FF]+", re.UNICODE)


def _norm_token(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _node_terms(props: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    for key in ("name_ru", "name_en", "name", "chemical_formula"):
        val = props.get(key)
        if isinstance(val, str) and val.strip():
            terms.append(val.strip())
    aliases = props.get("aliases")
    if isinstance(aliases, list):
        for item in aliases:
            if isinstance(item, str) and item.strip():
                terms.append(item.strip())
    elif isinstance(aliases, str) and aliases.strip():
        terms.append(aliases.strip())
    return terms


@lru_cache(maxsize=1)
def _alias_lookup_cached(repo_id: int, graph_fingerprint: str) -> dict[str, set[str]]:
    """Build token -> related terms map from all document graphs."""
    from mkg_core.store import get_repo

    _ = repo_id  # bust cache when repo instance changes
    lookup: dict[str, set[str]] = {}
    repo = get_repo()
    items, _ = repo.list(page=1, page_size=200)
    for rec in items:
        graph = repo.read_graph(rec["id"]) or {}
        for node in graph.get("nodes") or []:
            label = str(node.get("label") or "")
            if label not in _ALIAS_LABELS:
                continue
            props = node.get("props") if isinstance(node.get("props"), dict) else {}
            terms = _node_terms(props)
            if len(terms) < 2:
                continue
            canonical = {_norm_token(t) for t in terms}
            for term in terms:
                key = _norm_token(term)
                if len(key) < 2:
                    continue
                bucket = lookup.setdefault(key, set())
                bucket.update(canonical)
    return lookup


def _graph_fingerprint() -> str:
    from mkg_core.store import get_repo

    repo = get_repo()
    items, total = repo.list(page=1, page_size=200)
    parts = [str(total)]
    for rec in items[:40]:
        parts.append(f"{rec.get('id')}:{rec.get('graph_nodes') or 0}")
    return "|".join(parts)


def get_alias_lookup() -> dict[str, set[str]]:
    from mkg_core.store import get_repo

    repo = get_repo()
    return _alias_lookup_cached(id(repo), _graph_fingerprint())


def expand_search_query(query: str, *, limit: int = 600) -> tuple[str, list[str]]:
    """Append RU/EN alias terms found in ontology graphs for query tokens."""
    q = (query or "").strip()
    if not q:
        return q, []
    lookup = get_alias_lookup()
    if not lookup:
        return q, []
    tokens = [_norm_token(t) for t in _TOKEN_RE.findall(q) if len(_norm_token(t)) >= 2]
    added: list[str] = []
    seen = {_norm_token(q)}
    for token in tokens:
        related = lookup.get(token)
        if not related:
            continue
        for term in sorted(related):
            if term in seen or term == token:
                continue
            seen.add(term)
            added.append(term)
    if not added:
        return q, []
    expanded = f"{q} {' '.join(added[:12])}".strip()
    if len(expanded) > limit:
        expanded = expanded[: limit - 1].rstrip() + "…"
    return expanded, added
