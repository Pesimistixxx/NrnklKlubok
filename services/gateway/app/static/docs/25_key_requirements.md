# Ключевые требования хакатона

UI cache: `?v=95`. Полная версия: `Docs/25_key_requirements.md`.

| # | Требование | Статус |
|---|------------|--------|
| 1 | Мультипараметрические запросы | ✅ `query_facets`, planner, layer agents |
| 2 | Верификация (источник, confidence, дата) | ✅ источники в чате, badges |
| 3 | Гео RU/зарубеж | ✅ facets + фильтры графа |
| 4 | Числовые диапазоны | 🟡 Measurement filter; L6 TEP — roadmap |
| 5 | Масштабируемость доменов | ✅ `ontology.py` DOMAIN_PROMPT_HINTS |

Код: `query_facets.py`, `orchestrator_graph.py`, `layer_nodes.py`.
