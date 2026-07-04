# Agent API — руководство для LLM-агентов

Gateway MKG предоставляет REST API для программного доступа к документам, шести слоям онтологии (L1–L6), графу знаний и семантическому поиску. API спроектирован для LLM-агентов, RAG-пайплайнов и внешних интеграций.

**Базовый URL:** `http://localhost:8000/api/v1/agents`  
**OpenAPI / Swagger:** `http://localhost:8000/docs` (тег `agents`)  
**Версия gateway:** 0.4.0

> **Важно:** `doc_id` содержит двоеточие (`doc:c502a955d926b0c8`). В URL path кодируйте его как `%3A`, иначе часть клиентов обрежет путь:  
> `.../documents/doc%3Ac502a955d926b0c8/layers/L1`

---

## Быстрый старт

```bash
# Список документов со статистикой по слоям
curl -s http://localhost:8000/api/v1/agents/docs | jq .

# Сводка по документу
curl -s http://localhost:8000/api/v1/agents/documents/doc_c502a955d926b0c8 | jq .

# Узлы слоя L1 (сущности)
curl -s "http://localhost:8000/api/v1/agents/documents/doc_c502a955d926b0c8/layers/L1" | jq .

# Поиск (keyword, если Qdrant пуст; semantic после индексации)
curl -s -X POST http://localhost:8000/api/v1/agents/documents/doc_c502a955d926b0c8/search \
  -H "Content-Type: application/json" \
  -d '{"query": "тектонические нарушения", "limit": 5}' | jq .
```

> Пользовательский UI: [`19_user_guide.md`](19_user_guide.md) · L3/Qdrant: [`15_l3_qdrant_clustering.md`](15_l3_qdrant_clustering.md)

---

## Загрузка документов

### UI

Главная → drag-and-drop → **Обработать** → worker: ingestion (OCR, Markdown).

### API (основной gateway, не agents)

```bash
# Один файл
curl -s -X POST http://localhost:8000/api/v1/documents \
  -F "file=@article.pdf" \
  -F "classification=открытый" | jq .

# Ответ: {"id":"doc:abc123...","status":"uploaded",...}

# Пакетная загрузка
curl -s -X POST http://localhost:8000/api/v1/documents/batch \
  -F "files=@a.pdf" \
  -F "files=@b.docx" \
  -F "classification=открытый" | jq .

# Запуск извлечения графа
curl -s -X POST http://localhost:8000/api/v1/documents/doc_abc123/submit | jq .
```

После `submit` worker выполняет extraction; межслойные связи добавляет `_bridge_text_to_layers` в `packages/extraction/src/mkg_extraction/extractor.py`.

---

## Аутентификация

В MVP **аутентификация не требуется**. Gateway доступен в локальной/dev-среде без API-ключа. Для production рекомендуется reverse proxy с JWT или API key.

---

## Модель слоёв L1–L6

| Слой | Название | Примеры node labels |
|------|----------|---------------------|
| **L1** | Сущности | `Material`, `Process`, `Equipment`, `ChemicalReagent`, `StandardMetric` |
| **L2** | Контекст | `Expert`, `Organization`, `Location`, `Timeline`, `Event`, `Facility`, `Document` |
| **L3** | Текст | `TextParagraph`, `TextSection`, `LangContext`, `HeadingContext` |
| **L4** | Факты | `ExperimentRun`, `TechStage`, `Measurement`, `Claim`, `Effect`, `Formula`… |
| **L5** | Классификация и доступ | `SecurityRole`, `VerificationStatus`, `AuditTrail` |
| **L6** | Технико-экономика | `TechnologySolution`, `EconomicIndicator`, `EnvironmentalIndicator` |

Полный справочник: `GET /agents/ontology`.

---

## Эндпоинты

### `GET /agents/docs`

Список документов с counts по слоям и статусом пайплайна.

**Query:** `page` (default 1), `page_size` (default 50)

**Пример ответа:**

```json
{
  "items": [
    {
      "id": "doc:c502a955d926b0c8",
      "file_name": "article.pdf",
      "status": "loaded",
      "step": "done",
      "layer_counts": {"L1": 12, "L2": 5, "L3": 48, "L4": 20, "L5": 3, "L6": 2},
      "total_nodes": 90,
      "total_relationships": 210,
      "layers": [
        {"id": "L1", "title": "Сущности (Material, Process, Equipment…)", "status": "done", "nodes": 12, "relationships": 15}
      ]
    }
  ],
  "total": 3,
  "page": 1,
  "page_size": 50
}
```

---

### `GET /agents/documents/{doc_id}`

Метаданные документа + сводка L1–L6 (как `/docs`, но для одного документа). Дополнительно: `error`, `neo4j_synced`.

---

### `GET /agents/documents/{doc_id}/layers`

Полный пайплайн слоёв (аналог UI `/api/v1/documents/{id}/pipeline/layers`):

- статус каждого слоя: `pending`, `running`, `partial`, `done`, `empty`, `failed`
- число узлов и связей на слой
- `recent_relationships` — последние связи для контекста

---

### `GET /agents/documents/{doc_id}/layers/{layer_id}`

Узлы и связи **одного** слоя (`L1` … `L6`).

**Query:** `label` — фильтр по Neo4j label (например `Material`).

**Пример:** `GET .../layers/L4?label=Claim`

```json
{
  "document_id": "doc:c502a955d926b0c8",
  "layer_id": "L4",
  "title": "Факты (ExperimentRun, Measurement, Claim…)",
  "node_count": 20,
  "relationship_count": 35,
  "nodes": [{"id": "claim:method_applicability", "label": "Claim", "props": {"quote": "…"}}],
  "relationships": [{"type": "SOURCE", "from": "claim:…", "to": "doc:…", "props": {}}]
}
```

---

### `GET /agents/documents/{doc_id}/graph`

Полный граф документа (узлы + связи из JSON-хранилища).

**Query-фильтры:**

| Параметр | Описание |
|----------|----------|
| `layer` | L1–L6 — только узлы слоя и их связи |
| `label` | Neo4j label узла |
| `rel_type` | тип связи, напр. `HAS_PARAGRAPH` |

---

### `GET /agents/documents/{doc_id}/relationships`

Все связи документа.

**Query:** `rel_type`, `layer` (слой узла-источника `from`).

---

### `GET /agents/documents/{doc_id}/nodes/{node_id}`

Детали узла с соседями:

- `node` — полный узел
- `layer` — L1–L6
- `text` — извлечённый текст (quote, raw_text_ru…)
- `incoming` / `outgoing` — связи
- `neighbors` — соседние узлы

**Типичный workflow:** найти Claim → получить `SOURCE` → перейти к TextParagraph.

```bash
curl -s http://localhost:8000/api/v1/agents/documents/doc_c502a955d926b0c8/nodes/claim:method_applicability | jq .
```

---

### `GET /agents/documents/{doc_id}/nodes`

Поиск узлов по keyword, label и слою.

**Query:**

| Параметр | Описание |
|----------|----------|
| `q` | Подстрока в id, label, props (name, quote…) |
| `label` | Neo4j label, напр. `Material` |
| `layer` | L1–L6 |
| `limit` | default 50, max 500 |

```bash
# Все Material слоя L1
curl -s "http://localhost:8000/api/v1/agents/documents/doc_c502a955d926b0c8/nodes?label=Material&layer=L1" | jq .

# Keyword по id/цитате
curl -s "http://localhost:8000/api/v1/agents/documents/doc_c502a955d926b0c8/nodes?q=никель&limit=20" | jq .
```

---

### `GET /agents/documents/{doc_id}/text`

Markdown документа.

**Query:** `with_paragraph_index=true` — вставляет HTML-комментарии L3 перед каждым абзацем:

```html
<!-- L3:TextParagraph id=doc:xxx:p:0 kind=paragraph -->
```

---

### `GET /agents/documents/{doc_id}/paragraphs`

Список L3-абзацев:

- **source=`graph`** — после extraction (узлы `TextParagraph`)
- **source=`markdown`** — до extraction (split по `\n\n`)

```json
{
  "document_id": "doc:c502a955d926b0c8",
  "source": "graph",
  "total": 48,
  "paragraphs": [
    {"node_id": "doc:c502a955d926b0c8:p:0", "index": 0, "text": "В статье представлена…"}
  ]
}
```

---

### `POST /agents/documents/{doc_id}/search`

Поиск по документу.

**Тело запроса:**

```json
{
  "query": "моделирование тектонических нарушений",
  "limit": 10,
  "mode": "auto",
  "layers": ["L3", "L4"],
  "index_if_missing": true
}
```

| Поле | Описание |
|------|----------|
| `mode` | `auto` — semantic если есть Qdrant, иначе keyword; `semantic` / `keyword` — принудительно |
| `layers` | ограничить L1–L6 |
| `index_if_missing` | при первом поиске проиндексировать TextParagraph и Claim в Qdrant |

**curl-примеры:**

```bash
# Индекс → semantic
curl -s -X POST http://localhost:8000/api/v1/agents/documents/doc_c502a955d926b0c8/embeddings/index | jq .
curl -s -X POST http://localhost:8000/api/v1/agents/documents/doc_c502a955d926b0c8/search \
  -H "Content-Type: application/json" \
  -d '{"query": "CAE Fidesys", "mode": "semantic", "limit": 5}' | jq .

# Keyword по L3
curl -s -X POST http://localhost:8000/api/v1/agents/documents/doc_c502a955d926b0c8/search \
  -H "Content-Type: application/json" \
  -d '{"query": "тектонические", "mode": "keyword", "layers": ["L3"]}' | jq .

# GET узлы слоя (без embedding)
curl -s "http://localhost:8000/api/v1/agents/documents/doc_c502a955d926b0c8/layers/L4?label=Claim" | jq .
```

**Пример ответа (keyword):**

```json
{
  "document_id": "doc:c502a955d926b0c8",
  "query": "тектонические нарушения",
  "mode": "keyword",
  "hits": [
    {
      "node_id": "doc:c502a955d926b0c8:p:2",
      "label": "TextParagraph",
      "layer": "L3",
      "score": 1.0,
      "text": "В статье представлена оригинальная методика…",
      "mode": "keyword"
    }
  ],
  "index": null
}
```

---

### `POST /agents/documents/{doc_id}/embeddings/index`

Явная индексация L3 (`TextParagraph`) и L4 (`Claim`) в Qdrant через Yandex embeddings.

```json
{"document_id": "doc:…", "indexed": 68, "skipped": 0}
```

```bash
curl -s -X POST http://localhost:8000/api/v1/agents/documents/doc_c502a955d926b0c8/embeddings/index | jq .
curl -s http://localhost:8000/api/v1/agents/embeddings/status | jq .
```

---

## Межслойные связи (cross-layer)

Функция `_bridge_text_to_layers` (`packages/extraction/src/mkg_extraction/extractor.py`) вызывается **после** LLM-extraction. Она сопоставляет цитаты узлов L1/L2/L4/L6 с абзацами L3 и добавляет:

| Тип | Направление | Слои |
|-----|-------------|------|
| `DATA_SOURCE_FOR` | TextParagraph → L1/L4 | L3 → L1, L4 |
| `CONTEXT_FOR` | TextParagraph → L2/L5 | L3 → L2, L5 |
| `ABOUT` | TextParagraph → L6 | L3 → L6 |

Props связи: `bridge` (`quote_match`, `context_match`, …), `confidence`.

**API — все связи документа:**

```bash
curl -s "http://localhost:8000/api/v1/agents/documents/doc_c502a955d926b0c8/relationships" | jq .

# Только CONTEXT_FOR
curl -s "http://localhost:8000/api/v1/agents/documents/doc_c502a955d926b0c8/relationships?rel_type=DATA_SOURCE_FOR" | jq .

# Связи, исходящие из слоя L3
curl -s "http://localhost:8000/api/v1/agents/documents/doc_c502a955d926b0c8/relationships?layer=L3" | jq .
```

В UI межслойные рёбра подсвечены **оранжевым**; фильтр «Межслойные связи» показывает только их.

---

### `GET /agents/ontology`

Справочник онтологии: слои, mapping label→layer, типы связей.

---

### `GET /agents/embeddings/status`

Где живут эмбеддинги и статистика Qdrant.

```json
{
  "provider": "yandex",
  "embed_doc_model": "text-search-doc/latest",
  "embed_query_model": "text-search-query/latest",
  "embed_client": "packages/core/src/mkg_core/llm.py::YandexLLMClient.embed",
  "qdrant_url": "http://qdrant:6333",
  "collections": {
    "mkg_chunks": {"purpose": "L3 TextParagraph chunks", "points": 0},
    "mkg_claims": {"purpose": "L4 Claim nodes", "points": 0}
  },
  "vector_size": 256,
  "yandex_configured": true,
  "auto_index_on_search": true,
  "pipeline_auto_index": false,
  "note": "Extraction pipeline не пишет в Qdrant автоматически…"
}
```

---

### `GET /agents/documents/{doc_id}/embeddings/points`

Список проиндексированных точек Qdrant для документа (scroll, **без векторов**) — аналог просмотра узлов в Neo4j Browser.

**Query:**

| Параметр | Описание |
|----------|----------|
| `collection` | `mkg_chunks` или `mkg_claims` (опционально; по умолчанию обе) |
| `limit` | default 100, max 500 |

**Пример:**

```bash
curl -s "http://localhost:8000/api/v1/agents/documents/doc%3Ac502a955d926b0c8/embeddings/points?limit=50" | jq .
```

**Пример ответа:**

```json
{
  "document_id": "doc:c502a955d926b0c8",
  "total": 48,
  "points": [
    {
      "collection": "mkg_chunks",
      "point_id": "123456789012345",
      "node_id": "doc:c502a955d926b0c8:p:0",
      "label": "TextParagraph",
      "layer": "L3",
      "text": "В статье представлена оригинальная методика…"
    }
  ]
}
```

Реализация: `packages/core/src/mkg_core/embeddings.py::list_indexed_points`.  
UI: вкладка **Qdrant** → список точек + лог индексации.

---

### `GET /agents/capabilities`

Реестр **8 агентов** из ТЗ с привязкой к REST endpoint'ам. Используется оркестраторами, LLM-агентами и строкой этапа на «Главной» в UI.

**Пример:**

```bash
curl -s http://localhost:8000/api/v1/agents/capabilities | jq .
```

**Пример ответа (сокращённо):**

```json
{
  "project_stage": "MVP-2",
  "stage_label_ru": "Ingestion + Extraction + Neo4j + Qdrant search; validation/RAG — в работе",
  "agents": [
    {
      "id": "ingestion",
      "name_ru": "Агент приёма документов",
      "layer_scope": "L2/L3",
      "implementation": "worker.run_ingestion + gateway upload",
      "endpoints": [
        {"method": "POST", "path": "/api/v1/documents", "summary": "Загрузка файла", "status": "ready"},
        {"method": "GET", "path": "/api/v1/agents/documents/{id}/text", "summary": "Markdown документа", "status": "ready"}
      ]
    },
    {
      "id": "retrieval",
      "name_ru": "Поисковый агент (Retrieval)",
      "layer_scope": "L3/L4 + Qdrant",
      "implementation": "embeddings.search_document",
      "endpoints": [
        {"method": "POST", "path": "/api/v1/agents/documents/{id}/search", "summary": "Semantic/keyword", "status": "ready"},
        {"method": "GET", "path": "/api/v1/agents/documents/{id}/embeddings/points", "summary": "Точки Qdrant", "status": "ready"}
      ]
    }
  ]
}
```

| ID агента | Название | Статус endpoint'ов |
|-----------|----------|-------------------|
| `ingestion` | Приём документов | ✅ ready |
| `extraction` | NLP L1–L6 | ✅ ready |
| `graph_fusion` | Слияние графа / Neo4j | ✅ ready |
| `retrieval` | Qdrant + search | ✅ ready |
| `validation` | L5 валидация | ⬜ partial |
| `synthesis` | Аналитика / отчёты | ⬜ partial |
| `security` | RBAC | ⬜ partial |
| `notification` | Логи пайплайна | ✅ ready |

Код: `services/gateway/app/agent_api.py::get_agent_capabilities`.

---

## Runtime-конфиг моделей (UI «Настройки»)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/config/models` | Текущие модели + списки допустимых значений |
| PUT | `/api/v1/config/models` | Обновить одну или несколько моделей |

**Поля:**

| Поле | Сервис |
|------|--------|
| `llm_model` | Extraction L1–L6 + фильтр чанков ingestion |
| `ocr_model` | OCR PDF/изображений (`auto` = авто по типу файла) |
| `emb_doc_model` | Qdrant индексация (text-search-doc/*) |
| `emb_query_model` | Qdrant semantic search (text-search-query/*) |

Хранение: Postgres `runtime_config`. Применяется worker'ом к **новым** задачам.

Пример PUT:

```json
{
  "llm_model": "yandexgpt-5.1",
  "ocr_model": "auto",
  "emb_doc_model": "text-search-doc/latest",
  "emb_query_model": "text-search-query/latest"
}
```

---

## Эмбеддинги — где и как

### Поток (diagram)

```
Markdown + Graph JSON
        │
        ▼
POST /agents/documents/{id}/embeddings/index
  (или index_if_missing при search)
        │
        ▼
packages/core/embeddings.py
  ├─ TextParagraph (L3) → mkg_chunks
  └─ Claim (L4)         → mkg_claims
        │
        ▼
YandexLLMClient.embed()  ← llm.py, text-search-doc/query
        │
        ▼
QdrantClientSingleton    ← qdrant.py, vector 256
        │
        ▼
POST /agents/documents/{id}/search  mode=semantic
```

### Клиент Yandex

| Компонент | Путь |
|-----------|------|
| **Embed API** | `packages/core/src/mkg_core/llm.py` → `YandexLLMClient.embed()` |
| **Endpoint** | `https://llm.api.cloud.yandex.net/foundationModels/v1/textEmbedding` |
| **Модели** | `text-search-doc/latest` (документы), `text-search-query/latest` (запросы) |
| **Конфиг** | `.env`: `YANDEX_API_KEY`, `YANDEX_FOLDER_ID`, `YANDEX_EMB_DOC`, `YANDEX_EMB_QUERY` |
| **Кэш** | `packages/core/src/mkg_core/llm_cache.py` (дисковый кэш векторов) |

### Qdrant

| Компонент | Путь |
|-----------|------|
| **Клиент** | `packages/core/src/mkg_core/qdrant.py` → `QdrantClientSingleton` |
| **Коллекции** | `mkg_chunks` (L3), `mkg_claims` (L4) |
| **Индексация/поиск** | `packages/core/src/mkg_core/embeddings.py` |
| **Размер вектора** | 256 (env `QDRANT_VECTOR_SIZE`) |

**Индексация сейчас:**

- UI: вкладка **Qdrant** → «Индексировать» / «Все документы»; после extraction UI также вызывает индексацию автоматически. Превью документа (▼) — Markdown, поиск, логи.
- API: `POST .../embeddings/index`, `GET .../embeddings/points`, или `POST .../search` с `index_if_missing=true`.

Worker **не** пишет в Qdrant напрямую — только через gateway/Agent API.

**Кластеризация L4 / аномалии:** реализовано — HDBSCAN в `l4_clustering.py`, метки `cluster_id` / `is_anomaly` на L4-узлах и в Qdrant payload. API: `POST /api/v1/graph/l4/cluster`, `GET /api/v1/graph/anomalies`, `POST /api/v1/agents/analytics/l4-cluster`. Подробно: [`22_pipeline_layers.md`](22_pipeline_layers.md), [`15_l3_qdrant_clustering.md`](15_l3_qdrant_clustering.md).

Связь outliers с Contradiction L5 — **следующий этап**.

---

## Типичные сценарии агента

### 1. Найти факты о материале

```
GET /agents/docs                          → выбрать doc_id со status=loaded
GET /agents/documents/{id}/layers/L1      → Material, Process
POST /agents/documents/{id}/search        → {"query": "никель", "layers": ["L1","L4"]}
GET /agents/documents/{id}/nodes/{node_id}→ соседи и связи USES_MAT
```

### 2. Проследить Claim → исходный абзац

```
GET /agents/documents/{id}/layers/L4?label=Claim
GET /agents/documents/{id}/nodes/claim:xxx   → outgoing SOURCE → TextParagraph
GET /agents/documents/{id}/paragraphs          → текст по node_id :p:N
```

### 3. Обойти соседей в графе

```
GET /agents/documents/{id}/nodes/process:xxx
→ neighbors, incoming OPERATES_PROC, outgoing USES_MAT
```

### 4. Семантический RAG

```
GET /agents/capabilities                     → реестр агентов и этап проекта
POST /agents/documents/{id}/embeddings/index   → заполнить Qdrant
GET  /agents/documents/{id}/embeddings/points  → проверить точки
POST /agents/documents/{id}/search             → mode=semantic
→ hits[].node_id → GET /nodes/{id} для контекста
```

---

## Коды ошибок

| HTTP | detail | Причина |
|------|--------|---------|
| 404 | Документ не найден | неверный `doc_id` |
| 404 | Граф ещё не сформирован | extraction не выполнен |
| 404 | Markdown ещё не готов | ingestion не завершён |
| 404 | Узел не найден | неверный `node_id` |
| 404 | Текст документа недоступен | нет md и графа |
| 400 | layer_id должен быть… | неверный слой (не L1–L6) |

---

## Связь с основным API

| Agent API | Эквивалент / источник |
|-----------|----------------------|
| `/agents/documents/{id}/layers` | `/api/v1/documents/{id}/pipeline/layers` |
| `/agents/documents/{id}/graph` | `/api/v1/graph/documents/{id}` |
| `POST /agents/analytics/l4-cluster` | `POST /api/v1/graph/l4/cluster`, `POST /api/v1/documents/{id}/l4-cluster` |

Agent API добавляет: фильтры по слоям, соседей узлов, paragraphs, search, ontology, embeddings status, **capabilities registry**, **Qdrant points scroll**.

---

## Переменные окружения (embeddings)

```env
YANDEX_API_KEY=...
YANDEX_FOLDER_ID=...
YANDEX_EMB_DOC=text-search-doc/latest
YANDEX_EMB_QUERY=text-search-query/latest
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION_CHUNKS=mkg_chunks
QDRANT_COLLECTION_CLAIMS=mkg_claims
QDRANT_VECTOR_SIZE=256
LLM_CACHE_EMBEDDINGS=true
```

---

## Docker

```bash
docker compose --project-name mkg-local up --build -d gateway
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/agents/capabilities
curl http://localhost:8000/api/v1/agents/ontology
```

Gateway монтирует `./data/storage` — графы и markdown общие с worker.
