# Единая карта знаний R&D для горно-металлургической отрасли

> Рабочее название: **MKG** (Mining Knowledge Graph).

## Суть системы одним абзацем

Платформа собирает разрозненные R&D-источники (отчёты, статьи, патенты, протоколы,
книги, таблицы), приводит их к единому размеченному виду, извлекает сущности и факты,
раскладывает их по **6 онтологическим слоям** в граф Neo4j, индексирует текст и факты
в Qdrant, кластеризует L4 (HDBSCAN) и выявляет аномалии. Поверх этого работают **чат**
с dual search (L3+L4+Neo4j), **LangGraph-агенты** (аудит, гипотезы, аномалии) и
Agent API для интеграций. Итог — система, которая отвечает на сложные запросы,
показывает источник каждого факта и цепочку рассуждений.

## Ключевые боли, которые решаем

| Боль | Как решаем |
|------|-----------|
| Знания разрознены, теряется институциональная память | Единый граф + текстовая матрица + версионирование |
| Дублирование экспериментов | Entity Resolution + поиск похожих фактов через Qdrant |
| Противоречивые выводы | Движок противоречий (в работе) + audit mode + L4 anomalies |
| «Поверхностная» достоверность | **Композитная модель доверия** (частично) |
| Слабый текстовый слой | OCR→Markdown, L3 TextParagraph, semantic search |

## Комплект документации

| Файл | Что внутри |
|------|-----------|
| `00_overview.md` | Краткая суть проекта и текущий статус |
| `02_architecture.md` | Архитектура, сервисы, хранилища |
| `21_pipeline_and_layers.md` | **L1–L6, L3 vs L4, HDBSCAN, режимы upload** |
| `22_chat_agents.md` | **Роли, AI-режимы, trace, POST /query** |
| `21_api_reference.md` | Сводка REST API |
| `19_user_guide.md` | UI: Чат, Документы, пайплайн, роли |
| `18_smoke_test.md` | Пошаговая проверка локального запуска |
| `20_project_status.md` | Текущий этап MVP-2 и матрица готовности |
| `14_agent_api.md` | Agent REST API для интеграций |
| `15_l3_qdrant_clustering.md` | L3, Qdrant, кластеризация L4 |
| `21_multiagent_system.md` | LangGraph agents service |
| `03_implementation_gap.md` | Целевая модель vs MVP |
| `13_roadmap.md` | Дорожная карта |

## Где что происходит (по коду)

1. **Upload**: `services/gateway/app/main.py` (`POST /api/v1/documents`, `processing_mode`).
2. **Ingestion**: `services/worker/app/tasks.py::run_ingestion` → `mkg_ingestion.pipeline`.
3. **Extraction**: `run_extraction` → `mkg_extraction.extractor` (L1–L6 + bridge L3).
4. **Neo4j**: `mkg_extraction.loader.load_graph` (MERGE).
5. **Qdrant L3/L4**: `mkg_core.embeddings` — `POST /documents/{id}/index`.
6. **L4 HDBSCAN**: `mkg_core.l4_clustering` — `POST /graph/l4/cluster`, `/documents/{id}/l4-cluster`.
7. **Чат**: `services/gateway/app/chat_engine.py` — dual search + graph traversal.
8. **LangGraph**: `services/agents/` — proxy `POST /api/v1/agents-service/run`.

## Пайплайн (актуальный)

```
Upload → OCR → MD (clean + marked) → L1–L6 → Graph → Neo4j
  → Qdrant (L3 chunks + L4 claims) → L4 HDBSCAN (clusters + anomalies)
```

- **L3** — только семантический поиск (`mkg_chunks`).
- **L4** — dual search + HDBSCAN-кластеры и выбросы (`mkg_claims`).

Подробно: [`21_pipeline_and_layers.md`](21_pipeline_and_layers.md), [`22_chat_agents.md`](22_chat_agents.md).

## Текущий статус MVP (кратко)

| Готово | В работе / не сделано |
|--------|------------------------|
| Upload (full / answers_only), OCR, MD, L1–L6, Neo4j | Contradiction engine (полный) |
| Qdrant index + semantic + dual search | Entity resolution + pint |
| L4 HDBSCAN + anomalies API + UI | RBAC UI |
| Чат: roles, sources, trace, Save MD | Визуальный конструктор графа |
| LangGraph: audit, hypothesis, anomaly | Полный RAG synthesis |
| Agent API, pipeline retry-кнопки | TableMatrix, SynonymMap |

Подробное сравнение с целевой моделью: [`03_implementation_gap.md`](03_implementation_gap.md).

## Что на текущем этапе (MVP-2)

1. **Чат** — диалог по роли, dual search L3+L4+Neo4j, режимы Audit / Hypotheses / Anomalies, trace, источники, «Сохранить как MD».
2. **Документы** — upload full или «только для ответов»; пайплайн с retry-кнопками по этапам.
3. Вкладки: **Пайплайн** / **Markdown** / **Граф** / **Qdrant** (кластеры L4).
4. **Настройки** — модели LLM / OCR / embedding; ролевые промпты.
5. **Agents service** — LangGraph поверх Agent API.

Следующий этап: полный contradiction engine, композитный confidence, RBAC.
