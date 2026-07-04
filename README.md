# MKG — Единая карта знаний R&D (горно-металлургия)

Интеллектуальная платформа, которая собирает разрозненные R&D-источники (отчёты, статьи,
патенты, протоколы, книги, таблицы), приводит их к единому размеченному Markdown, извлекает
сущности и факты, раскладывает их по **6 онтологическим слоям (L1–L6)** в граф **Neo4j**,
индексирует текст и факты в **Qdrant**, выявляет аномалии (HDBSCAN L4) и отвечает на сложные
многопараметрические запросы через **чат с источниками** и **LangGraph-агентов**.

Стек: **Neo4j · Qdrant · Postgres · Redis · FastAPI · arq · LangGraph · YandexGPT 5.x · Vision OCR**.

> **Статус:** хакатонный MVP. Ролевая модель — фильтрация по грифу на чтении (без криптоаутентификации).
> Не выставляйте сервис в интернет без reverse-proxy и auth — см. [`SECURITY.md`](./SECURITY.md).

## С чего начать

| Хочу… | Куда смотреть |
|-------|---------------|
| Понять суть за 3 минуты | [`Docs/00_overview.md`](./Docs/00_overview.md) |
| **Оценить соответствие ТЗ** | [`Docs/01_tz_compliance.md`](./Docs/01_tz_compliance.md) |
| Разобраться в архитектуре | [`Docs/02_architecture.md`](./Docs/02_architecture.md) |
| Запустить локально | [Быстрый старт](#быстрый-старт) · [`Docs/18_smoke_test.md`](./Docs/18_smoke_test.md) |
| Дёргать REST API | [`Docs/21_api_reference.md`](./Docs/21_api_reference.md) |
| Работать в UI | [`Docs/19_user_guide.md`](./Docs/19_user_guide.md) |

## Документация

| Файл | Содержание |
|------|------------|
| [Docs/00_overview.md](./Docs/00_overview.md) | Суть системы, карта документов, где что в коде |
| [Docs/01_tz_compliance.md](./Docs/01_tz_compliance.md) | **Матрица соответствия ТЗ (для жюри)** |
| [Docs/02_architecture.md](./Docs/02_architecture.md) | Архитектура, сервисы, хранилища, потоки данных |
| [Docs/03_implementation_gap.md](./Docs/03_implementation_gap.md) | Целевая модель L1–L6 vs MVP, приоритеты |
| [Docs/21_pipeline_and_layers.md](./Docs/21_pipeline_and_layers.md) | L1–L6, L3 vs L4, HDBSCAN, режимы upload |
| [Docs/22_chat_agents.md](./Docs/22_chat_agents.md) | Роли, AI-режимы, trace, anomaly agent |
| [Docs/29_hrm_adaptive_reasoning.md](./Docs/29_hrm_adaptive_reasoning.md) | **HRM: адаптивное число циклов рассуждения (halt/continue)** |
| [Docs/21_api_reference.md](./Docs/21_api_reference.md) | Сводка REST API (`/api/v1/…`) |
| [Docs/28_access_and_security.md](./Docs/28_access_and_security.md) | Роли, гриф, RBAC на чтении, аудит |
| [Docs/19_user_guide.md](./Docs/19_user_guide.md) | UI: Чат, Документы, пайплайн, роли |
| [Docs/18_smoke_test.md](./Docs/18_smoke_test.md) | Запуск docker compose и проверка |
| [Docs/20_project_status.md](./Docs/20_project_status.md) | Текущий этап и матрица готовности |
| [Docs/14_agent_api.md](./Docs/14_agent_api.md) | Agent REST API (+ capabilities, Qdrant) |
| [Docs/15_l3_qdrant_clustering.md](./Docs/15_l3_qdrant_clustering.md) | L3, Qdrant, кластеризация L4 |
| [Docs/21_multiagent_system.md](./Docs/21_multiagent_system.md) | LangGraph agents service |
| [Docs/13_roadmap.md](./Docs/13_roadmap.md) | Этапы: что сделано / в работе |

## Структура репозитория

```
Docs/                          # Документация проекта (единственный источник истины)
infra/postgres/init.sql        # Postgres: documents, collab, runtime_config
packages/
  core/src/mkg_core/           # config, llm, embeddings, l4_clustering, graph_traversal,
                               #   data_access, ontology, comparison, search_query
  ingestion/                   # OCR, парсеры форматов, pipeline → markdown
  extraction/                  # LLM L1–L6 → graph payload → Neo4j (extractor, loader)
  graph/                       # schema.cypher, init_schema.py
  prompts/                     # mkg_prompts — реестр доменных промптов
services/
  gateway/                     # REST API + Web UI (static/), RBAC, docs API
  worker/                      # arq: run_ingestion, run_extraction
  agents/                      # LangGraph: audit, hypothesis, anomaly, review, recommend
  analytics/                   # confidence, batch clustering (фоновый скелет)
docker-compose.yml             # gateway, worker, agents, analytics + neo4j/qdrant/postgres/redis
.env.example
```

## Архитектура (кратко)

```
Web UI (gateway :8000)
  → POST /documents → worker (arq/Redis)
       → OCR → Markdown (clean + marked)
       → extraction L1–L6 → Neo4j (MERGE)
       → Qdrant: mkg_chunks (L3) · mkg_claims (L4) · mkg_entities (L1)
       → L4 HDBSCAN → cluster_id / is_anomaly
  → Чат: unified search (L1+L3+L4) + Neo4j traversal + LLM synthesis
  → Agents service (:8010): Audit / Hypotheses / Anomalies / Review / Recommend
```

Хранилища: **Neo4j** (граф), **Qdrant** (векторы), **Postgres** (метаданные, роли, промпты,
матрица доступа), **Redis** (очередь arq), **локальный storage** (source / md / graph / json / логи).

Подробно: [`Docs/02_architecture.md`](./Docs/02_architecture.md).

## Что реализовано

| Компонент | Статус |
|-----------|--------|
| Upload + validation (full / answers_only), 11 форматов | ✅ |
| OCR, парсеры, Markdown clean + marked | ✅ |
| Extraction L1–L6, bridge L3 ↔ L1–L6 | ✅ |
| Neo4j MERGE, UI-граф (vis-network), «Все документы» | ✅ |
| Qdrant L1/L3/L4 index + **unified semantic search** | ✅ |
| L4 HDBSCAN + anomalies API + карта кластеров | ✅ |
| Чат: роли, источники, trace, Save MD, **direct-reply для приветствий** | ✅ |
| LangGraph agents (audit, hypothesis, anomaly, review, recommend) | ✅ |
| **RBAC на чтении: матрица role × classification** | ✅ |
| Дашборд руководителя, сравнение технологий (L6), экспорт | ✅ |
| Contradiction engine (полный), composite confidence | 🟡 |
| Entity resolution + `pint`, TableMatrix, SynonymMap | ⬜ |
| Vision→Mermaid агент, production auth (JWT/TLS) | ⬜ |

Полная оценка по ТЗ: [`Docs/01_tz_compliance.md`](./Docs/01_tz_compliance.md).

## Пайплайн одного файла

1. `POST /api/v1/documents` — сохраняет source, ставит `run_ingestion` (при недоступности Redis — inline).
2. Worker: OCR/парсинг → **clean** и **marked** Markdown.
3. При `AUTO_EXTRACT_AFTER_INGEST=true` — extraction L1–L6 → JSON graph → Neo4j.
4. Worker автоиндексирует Qdrant (L3 chunks, L4 claims, L1 entities); retry: `POST …/index`.
5. Worker запускает L4 HDBSCAN (режим `full`); retry: `POST …/l4-cluster`.
6. Поиск/чат: unified search (L1+L3+L4) + обход графа Neo4j → ответ с источниками.

Один вызов `POST /api/v1/documents` при живом worker и ключах Yandex запускает всю цепочку;
статус проверяется через `GET /api/v1/documents/{id}` до `status=loaded`.

## API (основное)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/documents` | Загрузка (`processing_mode=full\|answers_only`, метаданные) |
| GET | `/api/v1/documents/{id}` | Метаданные + статус пайплайна |
| GET | `/api/v1/documents/{id}/markdown` | Markdown: `variant=clean\|marked\|raw` |
| POST | `/api/v1/documents/{id}/submit` | Extraction → Neo4j |
| POST | `/api/v1/documents/{id}/index` | Qdrant + L4 cluster |
| POST | `/api/v1/search` | **Unified search L1+L3+L4** |
| POST | `/api/v1/chat/complete` | Диалог с retrieval + источниками |
| POST | `/api/v1/agents-service/run` | LangGraph (audit / hypothesis / anomaly / …) |
| GET | `/api/v1/graph/anomalies` | L4-аномалии |
| GET/PUT | `/api/v1/settings/data-access` | Матрица доступа role × гриф (PUT — admin) |
| POST | `/api/v1/admin/reindex` | Backfill Qdrant L1+L3+L4 |

Заголовок `X-MKG-Role` управляет фильтрацией по грифу (без него — роль `viewer`).
Полный список: [`Docs/21_api_reference.md`](./Docs/21_api_reference.md).

## Стек

Python 3.11 · FastAPI · Neo4j 5 · Qdrant · Postgres 16 · Redis 7 · arq · LangGraph ·
YandexGPT 5.x (Responses API) · Yandex Vision OCR · HDBSCAN / scikit-learn.

## Быстрый старт

```bash
cp .env.example .env   # заполните YANDEX_API_KEY + YANDEX_FOLDER_ID
docker compose --project-name mkg-local up --build
# UI:      http://localhost:8000
# API doc: http://localhost:8000/docs
# Agents:  http://localhost:8010/health
```

Ключевые переменные: `YANDEX_API_KEY`, `YANDEX_FOLDER_ID`, `AUTO_EXTRACT_AFTER_INGEST`,
`GRAPH_TRAVERSAL_MAX_HOPS`, `HDBSCAN_MIN_CLUSTER_SIZE`. Полный список — в `.env.example`.

> Ключ Yandex должен иметь scope `yc.ai.languageModels.execute` (роль `ai.languageModels.user`
> на каталоге). Без валидного ключа LLM-вызовы вернут 401/502.

Локально без Docker:

```bash
pip install -e packages/core -e packages/ingestion -e packages/extraction
pip install -r services/gateway/requirements.txt
uvicorn app.main:app --app-dir services/gateway --reload
cd services/worker && arq app.main.WorkerSettings
```

Схема Neo4j применяется при первой загрузке. Вручную:

```bash
python packages/graph/init_schema.py
```

Проверка после запуска: [`Docs/18_smoke_test.md`](./Docs/18_smoke_test.md).
