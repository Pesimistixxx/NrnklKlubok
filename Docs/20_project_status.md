# Статус проекта MKG (актуально)

> UI cache: `?v=43`. Обновляйте этот файл при смене этапа.

## Текущий этап: **MVP-2+**

**Полный пайплайн документов + dual search в чате + L4 HDBSCAN + LangGraph agents.**

| Область | Статус | Комментарий |
|---------|--------|-------------|
| Upload / OCR / MD (clean+marked) | ✅ | PDF, DOCX, XLSX, MD… |
| Extraction L1–L6 | ✅ | LLM + детерминированный L3/L5 |
| UI: Пайплайн \| Markdown \| Graph | ✅ | Retry ↺ per stage |
| Neo4j MERGE | ✅ | `neo4j_synced`, resync API |
| Qdrant L3 (`mkg_chunks`) | ✅ | Auto после extraction |
| Qdrant L4 (`mkg_claims`) | ✅ | Claim, Measurement… |
| L4 HDBSCAN + anomalies API | ✅ | `GET /graph/anomalies` |
| Chat dual search + traversal | ✅ | L3+L4, `GRAPH_TRAVERSAL_MAX_HOPS` |
| Chat upload full / answers_only | ✅ | Modal при 📎 |
| Trace / reasoning chain | ✅ | qdrant → graph → LLM / agent |
| Sources + Save as MD | ✅ | Links to markdown API |
| 8 ролей + anomaly_hunter | ✅ | `roles.py` |
| 5 AI modes incl. anomaly_mode | ✅ | agents service |
| POST /api/v1/query | ✅ | dialog + agent modes |
| Agent API capabilities | ✅ | 8 agents registry |
| Contradiction engine (full) | ⬜ | partial audit_mode |
| Entity resolution + pint | ⬜ | roadmap |
| RBAC UI | ⬜ | SecurityRole partial |
| Composite confidence | ⬜ | postgres config only |

## Этапы roadmap

| Этап | Название | Готовность |
|------|----------|------------|
| 0 | Docs, docker, schema | ✅ |
| 1 | Ingestion + MD | ✅ ~95% |
| 2 | Extraction + Neo4j + Qdrant | ✅ ~90% |
| 2b | L4 HDBSCAN + chat RAG | ✅ ~85% |
| 3 | Достоверность, contradictions | ⬜ ~20% |
| 4 | Multi-agent synthesis (full) | 🟡 ~60% (5 modes) |
| 5 | RBAC, дашборды L6 | ⬜ |

## 8 агентов ТЗ vs реализация

| ID | Агент | Статус |
|----|-------|--------|
| `ingestion` | Приём документов | ✅ upload, markdown, paragraphs |
| `extraction` | NLP L1–L6 | ✅ submit, layers pipeline |
| `graph_fusion` | Neo4j | ✅ graph, nodes, relationships |
| `retrieval` | Qdrant + anomalies | ✅ search, embeddings, L4 cluster |
| `validation` | L5 | 🟡 audit_mode partial |
| `synthesis` | Отчёты | 🟡 hypothesis, review, recommend |
| `security` | RBAC | 🟡 partial |
| `notification` | Логи | ✅ document logs |

## 8 ролей UI

| ID | Роль | Agents |
|----|------|--------|
| `admin` | Администратор | ✅ |
| `researcher` | Исследователь | ✅ |
| `engineer` | Инженер данных | ❌ |
| `analyst` | Аналитик | ✅ |
| `validator` | Валидатор | ✅ |
| `security` | Безопасность | ❌ |
| `anomaly_hunter` | Охотник за аномалиями | ✅ |
| `viewer` | Наблюдатель | ❌ |

## UI навигация

| Вкладка | Функции |
|---------|---------|
| Чат | Роль, AI-mode, 📎, trace, sources, MD export |
| Документы | Pipeline chips L1–L6 stages, MD tabs, graph |
| Qdrant | Index, search, points map, L4 |
| Настройки | Models, clear DB |

## Ключевые API (новое с MVP-2+)

| Method | Path |
|--------|------|
| POST | `/api/v1/query` |
| POST | `/api/v1/chat/complete` |
| GET | `/api/v1/graph/anomalies` |
| POST | `/api/v1/graph/l4/cluster` |
| POST | `/api/v1/documents/{id}/l4-cluster` |
| POST | `/api/v1/documents/{id}/index` |
| GET | `/api/v1/documents/{id}/pipeline/layers` |
| POST | `/api/v1/agents-service/run` |

Спецификация Agent API: [`14_agent_api.md`](14_agent_api.md).  
Пайплайн: [`21_pipeline_and_layers.md`](21_pipeline_and_layers.md).  
Чат: [`22_chat_agents.md`](22_chat_agents.md).
