# Статус проекта MKG (актуально)

> UI cache: `?v=95`. Обновляйте этот файл при смене этапа.

## Текущий этап: **MVP-3 (post-sprint)**

**Полный пайплайн + гибкий оркестратор L1–L6 + structured answers + corpus Qdrant + graph all-docs + hackathon MVPs.**

| Область | Статус | Комментарий |
|---------|--------|-------------|
| Upload / OCR / MD (clean+marked) | ✅ | PDF, DOCX, XLSX, MD… |
| Extraction L1–L6 | ✅ | LLM + детерминированный L3/L5 |
| UI: Пайплайн \| Markdown \| Graph | ✅ | Retry ↺; **reprocess-full** для answers_only |
| Граф «Все документы» | ✅ | `graphScope=all`, расширенные фильтры |
| Neo4j MERGE | ✅ | `neo4j_sync`, resync API |
| Qdrant L3+L4 corpus | ✅ | N/M docs; search без per-doc filter |
| L4 HDBSCAN + cluster UI | ✅ | Карта, клик по кластеру, anomalies API |
| Chat: role + fast/full toggle | ✅ | **Без AI-mode pills** |
| Chat: async orchestrator + live graph | ✅ | `/run/async` + poll ~420 ms |
| Structured answers (## sections) | ✅ | Сводка, источники, gaps, … |
| Пояснить / Обновить | ✅ | Section explain + regenerate |
| Sources collapsed | ✅ | `<details>` по умолчанию |
| Chat titles from 1st message | ✅ | `derive_thread_title` |
| query_facets + graph filters | ✅ | [`25_key_requirements.md`](25_key_requirements.md) |
| Analytics synthesis | ✅ | [`25_analytics_synthesis.md`](25_analytics_synthesis.md) |
| Additional wishes MVP | ✅ | Export JSON-LD/PDF, dashboard, compare, expert edit |
| Trace / agent bus | ✅ | Non-linear L1–L6, `AGENT_LOOP_MAX_ROUNDS` |
| 8 ролей + anomaly_hunter | ✅ | `roles.py` |
| 6 AI modes (API only) | ✅ | agents service |
| POST /api/v1/query | ✅ | programmatic modes |
| Server auth / RBAC UI | ⬜ | localhost MVP, role = client choice |
| Contradiction engine (full) | 🟡 | partial audit_mode + dashboard count |
| Entity resolution + pint | ⬜ | roadmap |
| Composite confidence | ⬜ | postgres config only |

## Этапы roadmap

| Этап | Название | Готовность |
|------|----------|------------|
| 0 | Docs, docker, schema | ✅ |
| 1 | Ingestion + MD | ✅ ~95% |
| 2 | Extraction + Neo4j + Qdrant | ✅ ~95% |
| 2b | L4 HDBSCAN + chat RAG | ✅ ~90% |
| 2c | Orchestrator bus + async UI | ✅ ~85% |
| 3 | Достоверность, contradictions | 🟡 ~35% |
| 4 | Multi-agent synthesis (full) | 🟡 ~75% |
| 5 | RBAC, production auth | ⬜ |

## 8 агентов ТЗ vs реализация

| ID | Агент | Статус |
|----|-------|--------|
| `ingestion` | Приём документов | ✅ upload, markdown, paragraphs |
| `extraction` | NLP L1–L6 | ✅ submit, layers pipeline |
| `graph_fusion` | Neo4j | ✅ graph, nodes, relationships, all-docs |
| `retrieval` | Qdrant + anomalies | ✅ corpus search, L4 cluster map |
| `validation` | L5 | 🟡 audit_mode partial |
| `synthesis` | Отчёты | 🟡 structured chat + hypothesis/review |
| `security` | RBAC | 🟡 role prompts; no server auth |
| `notification` | Логи | ✅ watchlist toast MVP |

## UI навигация

| Вкладка | Функции |
|---------|---------|
| Чат | Роль, fast/full, threads, live graph, trace, sources, Пояснить/Обновить, MD/JSON-LD/PDF |
| Документы | Pipeline, MD, graph, all-docs, advanced filters, compare |
| Qdrant | Corpus stats N/M, index all, search chips, cluster map |
| Настройки | Models, dashboard, watchlist, clear DB |
| Документация | In-app md sections |

## Ключевые API

| Method | Path |
|--------|------|
| POST | `/api/v1/chat/complete` |
| POST | `/api/v1/agents-service/run/async` |
| GET | `/api/v1/agents-service/run/{run_id}` |
| POST | `/api/v1/query` |
| POST | `/api/v1/documents/{id}/reprocess-full` |
| GET | `/api/v1/graph/anomalies` |
| GET | `/api/v1/dashboard/stats` |
| PATCH | `/api/v1/graph/documents/{id}/relationship` |

Спецификация Agent API: [`14_agent_api.md`](14_agent_api.md).  
Пайплайн: [`21_pipeline_and_layers.md`](21_pipeline_and_layers.md).  
Чат: [`22_chat_agents.md`](22_chat_agents.md).
