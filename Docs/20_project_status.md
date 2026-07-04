# Статус проекта MKG (актуально)

> Обновляйте этот файл при смене этапа. UI показывает строку этапа на «Главной» (`GET /api/v1/agents/capabilities`).

## Текущий этап: **MVP-2**

**Ingestion + Extraction + Neo4j + Qdrant semantic search + Agent API для 8 ролей.**

| Область | Статус | Комментарий |
|---------|--------|-------------|
| Upload / OCR / MD | ✅ | PDF, DOCX, XLSX, MD… |
| Extraction L1–L6 | ✅ | LLM + детерминированный L3/L5 |
| Bridge L3 ↔ L1–L6 | ✅ | `_bridge_text_to_layers` |
| Neo4j MERGE | ✅ | `neo4j_synced` в карточке документа |
| Qdrant index + search | ✅ | UI: вкладка Qdrant, точки, лог |
| UI граф | ✅ | Компактный / Полный граф, resize canvas |
| Agent API | ✅ | `/agents/capabilities`, 8 агентов |
| Validation L5 | ⬜ | Contradiction engine |
| RAG synthesis | ⬜ | Мульти-агентный ответ |
| RBAC | ⬜ | SecurityRole UI |
| HDBSCAN anomalies | ⬜ | analytics |

## Этапы roadmap

| Этап | Название | Готовность |
|------|----------|------------|
| 0 | Проектирование, Docs, docker | ✅ |
| 1 | Ingestion | ✅ ~90% (map-reduce книг — частично) |
| 2 | Extraction + граф + Agent API | ✅ ~85% |
| 3 | Достоверность, противоречия | ⬜ ~15% |
| 4 | RAG query-answer | ⬜ ~25% (только search) |
| 5 | RBAC, дашборды L6 | ⬜ |

## 8 агентов ТЗ vs реализация

| ID | Агент | API |
|----|-------|-----|
| `ingestion` | Приём документов | ✅ upload, text, paragraphs |
| `extraction` | NLP L1–L6 | ✅ submit, layers |
| `graph_fusion` | Neo4j | ✅ graph, nodes, relationships |
| `retrieval` | Qdrant search | ✅ search, embeddings/* |
| `validation` | L5 | ⬜ partial |
| `synthesis` | Отчёты | ⬜ partial (docs list) |
| `security` | RBAC | ⬜ partial |
| `notification` | Логи | ✅ document logs |

Полная спецификация: [`14_agent_api.md`](14_agent_api.md).

## UI (навигация)

| Вкладка | Назначение |
|---------|------------|
| Главная | Загрузка, этап проекта |
| Граф | Компактный vis-network |
| Полный граф | Все L3 абзацы |
| Qdrant | Индексация, точки, лог |
| Настройки | LLM, OCR, embedding doc/query |

Превью документа: панель над контентом (▼) — Markdown, поиск, логи, «Построить граф», «Пере-OCR».
