# MKG — Единая карта знаний R&D (горно-металлургия)

Платформа на Neo4j + Qdrant + Postgres + Yandex AI Studio: загрузка документов,
OCR → Markdown → извлечение сущностей L1–L6 в граф, семантический поиск,
HDBSCAN-анomalies L4, LangGraph-аналитика и диалоговый чат с источниками.

## Документация

| Файл | Содержание |
|------|------------|
| [Docs/00_overview.md](./Docs/00_overview.md) | Суть системы, карта документов, где что в коде |
| [Docs/02_architecture.md](./Docs/02_architecture.md) | Архитектура и сервисы |
| [Docs/21_pipeline_and_layers.md](./Docs/21_pipeline_and_layers.md) | **L1–L6, L3 vs L4, HDBSCAN, dual search** |
| [Docs/22_chat_agents.md](./Docs/22_chat_agents.md) | **Роли, AI-режимы, trace, anomaly agent** |
| [Docs/21_api_reference.md](./Docs/21_api_reference.md) | **Сводка REST API** (`/api/v1/…`) |
| [Docs/19_user_guide.md](./Docs/19_user_guide.md) | UI: Чат, Документы, пайплайн, роли |
| [Docs/18_smoke_test.md](./Docs/18_smoke_test.md) | Запуск docker compose и проверка |
| [Docs/20_project_status.md](./Docs/20_project_status.md) | Текущий этап MVP-2 |
| [Docs/14_agent_api.md](./Docs/14_agent_api.md) | Agent REST API (+ capabilities, Qdrant) |
| [Docs/15_l3_qdrant_clustering.md](./Docs/15_l3_qdrant_clustering.md) | L3, Qdrant, кластеризация L4 |
| [Docs/21_multiagent_system.md](./Docs/21_multiagent_system.md) | LangGraph agents service |
| [Docs/03_implementation_gap.md](./Docs/03_implementation_gap.md) | Целевая модель L1–L6 vs MVP |
| [Docs/13_roadmap.md](./Docs/13_roadmap.md) | Этапы: что сделано / в работе |

## Структура репозитория

```
Docs/                          # Документация проекта
infra/postgres/init.sql        # Postgres: documents, collab, runtime_config
packages/
  core/src/mkg_core/           # config, llm, embeddings, l4_clustering, graph_traversal
  ingestion/                   # OCR, parsers, pipeline → markdown
  extraction/                  # LLM L1–L6 → graph payload → Neo4j
  graph/                       # schema.cypher, init_schema.py
  prompts/                     # mkg_prompts — реестр промптов
services/
  gateway/                     # REST API + UI (static/)
  worker/                      # arq: run_ingestion, run_extraction
  agents/                      # LangGraph: audit, hypothesis, anomaly
  analytics/                   # confidence, batch clustering
docker-compose.yml             # gateway, worker, agents, analytics + infra
.env.example
```

## Архитектура (текущая)

```
UI (gateway :8000)
  → upload → worker (arq/Redis)
       → OCR → Markdown (clean + marked)
       → extraction L1–L6 → Neo4j
       → Qdrant L3 embeddings (mkg_chunks) + L4 (mkg_claims)
       → L4 HDBSCAN → cluster_id / is_anomaly
  → Чат: dual search (L3+L4) + Neo4j traversal
  → Agents service (:8010): Audit / Hypotheses / Anomalies / …
```

Хранилища: **Neo4j** (граф), **Qdrant** (векторы), **Postgres** (метаданные, роли, промпты),
**Redis** (очередь), **локальный storage** (source/md/graph/json).

## Что реализовано

| Компонент | Статус |
|-----------|--------|
| Upload + validation (full / answers_only) | ✅ |
| OCR, парсеры, Markdown clean + marked | ✅ |
| Extraction L1–L6, bridge L3 ↔ L1–L6 | ✅ |
| Neo4j MERGE, UI граф (vis-network) | ✅ |
| Qdrant L3/L4 index + semantic search | ✅ |
| **L4 HDBSCAN + anomalies API** | ✅ |
| **Чат: dual search, sources, trace, Save MD** | ✅ |
| **LangGraph agents** (audit, hypothesis, anomaly) | ✅ |
| Pipeline retry-кнопки по этапам | ✅ |
| Ролевые промпты (custom save) | ✅ |
| Agent API + capabilities | ✅ |
| Contradiction engine, полный RAG synthesis | ⬜ |
| RBAC UI, визуальный конструктор | ⬜ |

## Пайплайн одного файла

1. `POST /api/v1/documents` — сохраняет source, ставит `run_ingestion`.
2. Worker: OCR/парсинг → **clean** и **marked** Markdown.
3. При `AUTO_EXTRACT_AFTER_INGEST=true` — extraction L1–L6 → JSON graph → Neo4j.
4. Worker автоиндексирует Qdrant (L3 chunks, L4 claims, L1 entities); retry: `POST …/index`.
5. Worker запускает L4 HDBSCAN (режим `full`); retry: `POST …/l4-cluster`.

Подробнее: [Docs/22_pipeline_layers.md](./Docs/22_pipeline_layers.md).

## API (основное)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/documents` | Загрузка (`processing_mode=full\|answers_only`) |
| GET | `/api/v1/documents/{id}/markdown` | Markdown: `variant=clean\|marked` |
| POST | `/api/v1/documents/{id}/submit` | Extraction → Neo4j |
| POST | `/api/v1/documents/{id}/index` | Qdrant + L4 cluster |
| POST | `/api/v1/chat/complete` | Диалог с dual search |
| POST | `/api/v1/agents-service/run` | LangGraph (audit / hypothesis / anomaly) |
| GET | `/api/v1/graph/anomalies` | L4-аномалии |
| POST | `/api/v1/graph/l4/cluster` | HDBSCAN L4 |
| POST | `/api/v1/query` | Тестовый query API |
| POST | `/api/v1/admin/clear?confirm=true` | Очистка базы |

Полный список: [Docs/21_api_reference.md](./Docs/21_api_reference.md).

## Стек

Python 3.11 · FastAPI · Neo4j · Qdrant · Postgres · Redis · arq · LangGraph · YandexGPT 5.x · Vision OCR · HDBSCAN

## Быстрый старт

```bash
cp .env.example .env   # YANDEX_API_KEY + YANDEX_FOLDER_ID
docker compose --project-name mkg-local up --build
# UI: http://localhost:8000
# Agents: http://localhost:8010/health
```

Ключевые переменные: `YANDEX_API_KEY`, `YANDEX_FOLDER_ID`, `GRAPH_TRAVERSAL_MAX_HOPS`, `HDBSCAN_MIN_CLUSTER_SIZE`.

Локально без Docker:

```bash
pip install -e packages/core -e packages/ingestion -e packages/extraction
pip install -r services/gateway/requirements.txt
uvicorn app.main:app --app-dir services/gateway --reload
cd services/worker && arq app.main.WorkerSettings
```

Проверка: [Docs/18_smoke_test.md](./Docs/18_smoke_test.md).

Схема Neo4j применяется при первой загрузке. Вручную:

```bash
python packages/graph/init_schema.py
```
