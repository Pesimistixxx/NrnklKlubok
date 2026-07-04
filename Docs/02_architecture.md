# Архитектура системы

## Принцип

Асинхронная сервис-ориентированная архитектура: 4 контейнера логики + 3 хранилища + брокер.
Не «куча микросервисов», а модульная структура с чёткими границами, готовая к дроблению.

## Компоненты

```
                          ┌────────────────────────────┐
                          │           Web UI            │
                          │ upload · library · md-view  │
                          │ graph-view (ноды/связи)     │
                          └──────────────┬──────────────┘
                                         │ REST
                          ┌──────────────▼──────────────┐
                          │        gateway (FastAPI)     │
                          │  /documents /preview /graph  │
                          │  /library /search (позже)    │
                          └───┬───────────┬──────────┬───┘
                     enqueue  │           │ read     │ read
                    ┌─────────▼──┐   ┌────▼─────┐ ┌──▼───────┐
                    │   redis    │   │ postgres │ │  neo4j   │
                    │  (broker)  │   │ (jobs,   │ │ (граф    │
                    └─────┬──────┘   │  audit)  │ │  знаний) │
                          │          └──────────┘ └────▲─────┘
              ┌───────────▼───────────┐                │ write
              │        worker         │                │
              │ ingestion→extraction  │────────────────┘
              │ →resolve→load(Cypher) │        ┌───────────────┐
              └───────────┬───────────┘        │    qdrant     │
                          │  embeddings         │ (векторы     │
                          └────────────────────▶│  чанки/claims)│
                          ┌───────────────┐     └───────▲───────┘
                          │   analytics   │─────────────┘
                          │ confidence ·  │  cluster/anomaly → back to neo4j
                          │ contradictions│
                          └───────┬───────┘
                                  │ вызовы LLM/OCR/embeddings
                          ┌───────▼───────────────────────┐
                          │        Yandex AI Studio        │
                          │ YandexGPT 5.x · Vision OCR ·   │
                          │ text-search-* embeddings       │
                          └────────────────────────────────┘
```

## Роли контейнеров

| Сервис | Ответственность | Стек |
|--------|-----------------|------|
| `gateway` | REST API, UI, Agent API, загрузка, preview, граф, поиск | FastAPI, Pydantic |
| `worker` | OCR → Markdown → extraction L1–L6 → Neo4j MERGE | **arq** (Redis), `mkg_*` пакеты |
| `analytics` | Пересчёт confidence, противоречия, HDBSCAN → Neo4j | **скелет**, не в hot-path MVP |
| `rag` (позже) | Мульти-агентный ответ по графу + Qdrant | — |

## Поток данных (актуальный MVP)

```
Upload (gateway)
  → arq: run_ingestion → Markdown + storage
  → UI: «Построить граф» → arq: run_extraction
       → LLM L1/L2/L4/L6 + детерминированный L3/L5
       → _bridge_text_to_layers (межсл. связи)
       → load_graph → Neo4j
  → UI: L3 / Qdrant → index_document_graph → Qdrant (mkg_chunks, mkg_claims)
  → UI: Поиск → hybrid semantic + keyword (Agent API)
```

Эмбеддинги **не** пишутся в свойства Neo4j — только в Qdrant. См. [`15_l3_qdrant_clustering.md`](15_l3_qdrant_clustering.md).

## Соответствие целевой модели

Полная таблица узлов/связей/ТЗ vs код: [`03_implementation_gap.md`](03_implementation_gap.md).

## Хранилища

| Хранилище | Данные |
|-----------|--------|
| **Neo4j** (локально в compose по умолчанию) | Граф знаний: 6 слоёв, `Claim`, противоречия, доверие |
| **Qdrant** | Векторы чанков и `Claim`; кластеры и аномалии |
| **Postgres** | Задания пайплайна, статусы документов, аудит, пользователи, runtime-конфиг достоверности |
| **Redis** | Брокер очереди задач для worker/analytics |

## Общие пакеты (`packages/`)

- `core` — конфиг (env), синглтоны клиентов (Yandex LLM, Neo4j, Qdrant), логирование.
- `prompts` (`mkg_prompts`) — реестр промптов ingestion / extraction (`catalog/<stage>/`).
- `graph` — Cypher-шаблоны, схема, загрузчик JSON→граф.
- `ingestion` — OCR, чанкинг, очистка, Markdown, диаграммы.
- `extraction` — послойное извлечение, resolver, нормализация единиц; fallback-словарь Process/Material загружается из Neo4j.
- `confidence` — расчёт композитного доверия.

## Синглтоны

Все внешние клиенты — синглтоны (ленивая инициализация из env):
- `PromptRegistry` — реестр промптов (реализован).
- `YandexLLMClient` — обёртка над Yandex AI Studio (chat, vision, embeddings) с per-task конфигами.
- `Neo4jClient` — драйвер + сессии.
- `QdrantClientSingleton` — коллекции чанков и claims.

Конфиги моделей (temperature, max_tokens) под каждую задачу берутся из реестра промптов,
а не хардкодятся в коде.

## Асинхронность

- Загрузка файла → gateway кладёт задачу в очередь → worker обрабатывает.
- Статус документа и этап (`status`, `step`) хранится в Postgres (`documents`) и дублируется в локальном repo как fallback.
- Тяжёлые шаги (OCR, извлечение) не блокируют HTTP-запрос.

## Развёртывание

`docker-compose.yml` (Compose Spec, `name: mkg-local`) поднимает: `gateway`, `worker`, `analytics`, `neo4j`, `qdrant`,
`postgres`, `redis`. При необходимости Neo4j может быть внешним — тогда меняется `NEO4J_URI` в `.env`.
Секреты (`YANDEX_API_KEY`, `YANDEX_FOLDER_ID`, Neo4j creds) — только в `.env`.
