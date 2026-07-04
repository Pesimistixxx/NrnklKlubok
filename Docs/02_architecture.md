# Архитектура системы

## Принцип

Асинхронная модульная архитектура: gateway + worker + agents + analytics + 4 хранилища.
Чёткие границы пакетов `mkg_*`, готовность к масштабированию без «зоопарка микросервисов».

## Компоненты

```
                          ┌────────────────────────────────────────┐
                          │                 Web UI                  │
                          │  Чат · Документы (Pipeline/MD/Graph)   │
                          │  Qdrant · Настройки · Документация      │
                          └──────────────────┬─────────────────────┘
                                             │ REST /api/v1
                          ┌──────────────────▼─────────────────────┐
                          │           gateway (FastAPI)             │
                          │  documents · graph · collab · agents    │
                          │  graph/anomalies · agents-service proxy │
                          └───┬──────────┬──────────┬──────────┬───┘
                     enqueue │          │          │          │
                    ┌────────▼──┐  ┌────▼────┐ ┌───▼────┐ ┌──▼────────┐
                    │   redis   │  │postgres │ │ neo4j  │ │  agents   │
                    │  (arq)    │  │ meta +  │ │ граф   │ │ LangGraph │
                    └─────┬─────┘  │ runtime │ │ L1–L6  │ │ 5 modes   │
                          │        └─────────┘ └───▲────┘ └─────▲─────┘
              ┌───────────▼───────────┐            │ write       │ read API
              │        worker         │────────────┘             │
              │ ingestion→extraction  │        ┌─────────────────┘
              │ →neo4j→qdrant→l4      │        │
              └───────────┬───────────┘        │
                          │  embeddings         │
                          └────────────────────▶┌───────────────┐
                                                │    qdrant     │
                          ┌───────────────┐     │ mkg_chunks L3 │
                          │   analytics   │     │ mkg_claims L4 │
                          │ (скелет)      │     └───────────────┘
                          └───────────────┘
                                  │
                          ┌───────▼───────────────────────┐
                          │        Yandex AI Studio        │
                          │ GPT 5.x · Vision OCR · embed   │
                          └────────────────────────────────┘
```

## Роли контейнеров

| Сервис | Ответственность | Стек |
|--------|-----------------|------|
| `gateway` | REST, UI, Agent API, collab/chat, L4 anomalies | FastAPI |
| `worker` | OCR → MD → extraction → Neo4j → Qdrant → L4 HDBSCAN | arq, `mkg_*` |
| `agents` | LangGraph: audit, hypothesis, anomaly, review, recommend | LangGraph |
| `analytics` | Confidence, contradictions (скелет, не hot-path) | Python |

## Поток данных (актуальный)

### Режим `full`

```
Upload (gateway, processing_mode=full)
  → arq: run_ingestion → Markdown clean + marked
  → after_ingest → arq: run_extraction (если AUTO_EXTRACT_AFTER_INGEST)
       → LLM L1/L2/L4/L6 + детерминированный L3/L5
       → _bridge_text_to_layers
       → load_graph → Neo4j
       → index_document_graph → Qdrant (mkg_chunks + mkg_claims)
       → apply_document_l4_cluster → HDBSCAN, is_anomaly на L4
  → UI: Пайплайн | Markdown | Граф
  → Chat: search_global (обе коллекции) → graph_traversal → LLM
```

### Режим `answers_only`

```
Upload (processing_mode=answers_only)
  → run_ingestion → Markdown
  → index_document_markdown → только mkg_chunks
  → статус loaded (без Neo4j, без L4)
```

## Коллекции Qdrant (L1 / L3 / L4)

| | L1 | L3 | L4 |
|---|----|----|----|
| Коллекция | `mkg_entities` | `mkg_chunks` | `mkg_claims` |
| Узлы | Material, Process, Equipment… | TextParagraph, MD chunks | Claim, Measurement, Effect… |
| Назначение | Поиск сущностей | Semantic search цитат | Факты + HDBSCAN anomalies |
| Кластеризация | Нет | Нет | HDBSCAN (`HDBSCAN_MIN_CLUSTER_SIZE`) |

**Unified search** (`mkg_core.embeddings.search_global`) параллельно опрашивает все три коллекции
и объединяет hits по score — единый путь и для UI-поиска, и для чата (`search_chat_retrieval`).
Эмбеддинги хранятся **только** в Qdrant, не в Neo4j.
См. [`22_pipeline_layers.md`](22_pipeline_layers.md), [`21_api_reference.md`](21_api_reference.md).

## Управление доступом (RBAC на чтении)

`packages/core/src/mkg_core/data_access.py` + `services/gateway/app/data_access_api.py`:
матрица **role × classification** (гриф) хранится в Postgres `runtime_config.data_access_matrix`.
Заголовок `X-MKG-Role` (или роль сессии) определяет `allowed_classifications`; фильтрация
применяется на чтении в `GET /documents`, `GET /graph/*`, `POST /search`, RAG чата.
Без заголовка — роль `viewer` (минимальный доступ). Детали: [`28_access_and_security.md`](28_access_and_security.md).

## Хранилища

| Хранилище | Данные |
|-----------|--------|
| **Neo4j** | Граф L1–L6, Document, связи |
| **Qdrant** | Векторы L3/L4, payload cluster_id / is_anomaly |
| **Postgres** | documents, runtime_config, collab (users, threads) |
| **Redis** | Очередь arq |
| **storage/** | source, md, graph JSON, llm_cache |

## Пакеты (`packages/`)

- `core` — config, llm, embeddings, l4_clustering, graph_traversal, layer_pipeline, data_access, ontology, comparison, search_query
- `ingestion` — OCR, parsers, pipeline
- `extraction` — extractor, loader
- `graph` — schema.cypher, init_schema
- `prompts` — реестр промптов по этапам

> **Замечание по инфраструктуре:** сервис `analytics` — фоновый скелет (confidence/clustering),
> не находится в hot-path запросов; вся продуктивная логика кластеризации выполняется в `worker`/`core`.

## Конфигурация (ключевые env)

| Переменная | Назначение |
|------------|------------|
| `YANDEX_API_KEY`, `YANDEX_FOLDER_ID` | LLM, OCR, embeddings |
| `NEO4J_URI`, `NEO4J_PASSWORD` | Граф |
| `QDRANT_URL`, `QDRANT_COLLECTION_*` | Векторный индекс |
| `AUTO_EXTRACT_AFTER_INGEST` | Авто-extraction после OCR |
| `GRAPH_TRAVERSAL_MAX_HOPS` | Глубина обхода графа в чате (default 2) |
| `HDBSCAN_MIN_CLUSTER_SIZE` | Мин. размер кластера L4 (default 3) |
| `AGENTS_URL` | LangGraph service |

## Развёртывание

`docker compose --project-name mkg-local up --build` поднимает:
`gateway`, `worker`, `agents`, `analytics`, `neo4j`, `qdrant`, `postgres`, `redis`.

Секреты — только в `.env` (не коммитить).
