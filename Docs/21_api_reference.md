# Справочник REST API MKG

Краткий обзор HTTP API gateway. Полная спецификация Agent API: [`14_agent_api.md`](14_agent_api.md).

**Базовый URL:** `http://localhost:8000`  
**Префикс API:** `/api/v1`  
**OpenAPI:** `http://localhost:8000/docs`  
**Версия gateway:** 0.4.0

> **doc_id** может содержать двоеточие (`doc:c745b5ca…`). В URL path кодируйте как `%3A`.

---

## Health и диагностика

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/health` | `{ "status": "ok" }` |
| GET | `/api/v1/diagnostics` | Postgres, Neo4j, Qdrant, Redis, Yandex |
| GET | `/api/v1/formats` | Поддерживаемые форматы и лимит размера |
| GET | `/api/v1/ontology/node-fields` | Ожидаемые props по label узла |

---

## Документы и Markdown

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/documents` | Список документов (`page`, `page_size`) |
| GET | `/api/v1/documents/{id}` | Метаданные документа |
| POST | `/api/v1/documents` | Загрузка файла (`file`, `classification`, `processing_mode=full\|answers_only`) |
| POST | `/api/v1/documents/batch` | Пакетная загрузка (`files[]`) |
| GET | `/api/v1/documents/{id}/markdown` | Markdown: `variant=clean\|marked`, `download=1` |
| GET | `/api/v1/documents/{id}/source` | Исходный файл |
| GET | `/api/v1/documents/{id}/preview` | Превью: source, md, graph stats, L4 stats |
| GET | `/api/v1/documents/{id}/logs` | Логи пайплайна |
| POST | `/api/v1/documents/{id}/reprocess` | Повтор OCR → Markdown |
| POST | `/api/v1/documents/{id}/submit` | Запуск extraction → граф → Neo4j |
| POST | `/api/v1/documents/{id}/cancel-extraction` | Отмена extraction |
| POST | `/api/v1/documents/{id}/neo4j-sync` | Повторная синхронизация графа в Neo4j |
| POST | `/api/v1/documents/{id}/index` | Индексация Qdrant (+ auto L4 cluster в режиме `full`) |
| POST | `/api/v1/documents/{id}/l4-cluster` | HDBSCAN L4 (только `full`) |
| GET | `/api/v1/documents/{id}/pipeline/layers` | Статус слоёв L1–L6 |
| GET | `/api/v1/pipeline/{id}` | Краткий trace пайплайна |

### Примеры

```bash
# Загрузка (полный пайплайн)
curl -s -X POST http://localhost:8000/api/v1/documents \
  -F "file=@report.pdf" \
  -F "classification=открытый" \
  -F "processing_mode=full"

# Markdown с разметкой L1–L6
curl -s "http://localhost:8000/api/v1/documents/<doc_id>/markdown?variant=marked&download=1" -o marked.md

# Retry этапа
curl -s -X POST "http://localhost:8000/api/v1/documents/<doc_id>/reprocess"
curl -s -X POST "http://localhost:8000/api/v1/documents/<doc_id>/submit"
curl -s -X POST "http://localhost:8000/api/v1/documents/<doc_id>/index"
curl -s -X POST "http://localhost:8000/api/v1/documents/<doc_id>/l4-cluster"
```

---

## Граф и аномалии L4

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/graph/documents/{id}` | JSON-граф документа |
| GET | `/api/v1/graph/all` | Объединённый граф всех документов |
| POST | `/api/v1/graph/l4/cluster` | HDBSCAN по L4-векторам Qdrant |
| GET | `/api/v1/graph/anomalies` | Список L4-аномалий (`document_id`, `limit`, `auto_cluster`) |

```bash
curl -s -X POST http://localhost:8000/api/v1/graph/l4/cluster \
  -H "Content-Type: application/json" \
  -d '{"document_id": "<doc_id>", "min_cluster_size": 3}'

curl -s "http://localhost:8000/api/v1/graph/anomalies?document_id=<doc_id>&limit=100"
```

---

## Чат, роли и query

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/roles` | Список ролей MKG |
| GET | `/api/v1/roles/{id}/prompt` | Промпт роли (custom + default) |
| PUT | `/api/v1/roles/{id}/prompt` | Сохранить кастомный промпт |
| DELETE | `/api/v1/roles/{id}/prompt` | Сброс к default |
| POST | `/api/v1/users/session` | Сессия пользователя с ролью |
| GET | `/api/v1/chat/threads` | Список тредов |
| POST | `/api/v1/chat/threads` | Создать тред |
| GET | `/api/v1/chat/threads/{id}/messages` | Сообщения треда |
| POST | `/api/v1/chat/threads/{id}/messages` | Добавить сообщение |
| **POST** | **`/api/v1/chat/complete`** | **Диалог: dual search L3+L4+Neo4j, sources, graph, trace** |
| POST | `/api/v1/query` | Программный запрос (`mode=dialog` или agent mode) |

### POST /api/v1/chat/complete

```json
{
  "message": "Какие материалы упоминаются?",
  "role_id": "analyst",
  "history": [{"role": "user", "content": "…"}],
  "system_prompt": null,
  "include_graph": true,
  "include_artifacts": true,
  "document_ids": ["doc:abc"]
}
```

Ответ: `reply`, `sources[]`, `graph`, `artifacts[]`, `trace[]`, `timing_ms`.

---

## Agents service (LangGraph proxy)

Gateway проксирует сервис `agents` (порт 8010):

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/agents-service/health` | Health agents service |
| GET | `/api/v1/agents-service/modes` | Режимы: audit, hypothesis, anomaly, … |
| **POST** | **`/api/v1/agents-service/run`** | **Запуск LangGraph-анализа** |

```json
{
  "query": "Найди противоречия в данных о pH",
  "mode": "audit",
  "doc_ids": ["doc:abc"],
  "user_role": "validator",
  "limit": 5
}
```

Режимы (`mode`): `audit`, `hypothesis`, `literature_review`, `recommendation`, `anomaly`.

Ответ: `summary`, `trace[]`, `issues` / `hypotheses` / `anomalies`, `elapsed_ms`.

---

## Agent API (кратко)

Префикс: `/api/v1/agents`

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/agents/docs` | Документы + layer counts |
| GET | `/agents/documents/{id}/layers/{L1-L6}` | Узлы слоя |
| POST | `/agents/documents/{id}/search` | Semantic / keyword search |
| POST | `/agents/documents/{id}/embeddings/index` | Индексация Qdrant |
| GET | `/agents/documents/{id}/embeddings/points` | Точки Qdrant |
| POST | `/agents/analytics/l4-cluster` | HDBSCAN L4 |
| GET | `/agents/capabilities` | Реестр 8 агентов + этап проекта |
| GET | `/agents/ontology` | Справочник онтологии |

Подробно: [`14_agent_api.md`](14_agent_api.md).

---

## Конфигурация и admin

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/config/models` | LLM, OCR, embedding doc/query |
| PUT | `/api/v1/config/models` | Обновить runtime-конфиг (Postgres) |
| POST | `/api/v1/admin/clear?confirm=true` | Очистка storage, Postgres, Neo4j |

---

## Переменные окружения (ключевые)

| Переменная | Назначение |
|------------|------------|
| `YANDEX_API_KEY` | LLM, OCR, embeddings (обязательно для AI) |
| `YANDEX_FOLDER_ID` | Каталог Yandex Cloud |
| `GRAPH_TRAVERSAL_MAX_HOPS` | Глубина обхода графа в чате (default `2`) |
| `HDBSCAN_MIN_CLUSTER_SIZE` | Мин. размер кластера L4 (default `3`) |
| `HDBSCAN_MIN_SAMPLES` | Опционально для HDBSCAN |
| `AUTO_EXTRACT_AFTER_INGEST` | Авто-extraction после OCR (default `true`) |
| `AGENTS_URL` | URL LangGraph service (default `http://agents:8010`) |
| `NEO4J_URI`, `QDRANT_URL`, `REDIS_URL`, `DATABASE_URL` | Хранилища |

Полный список: `.env.example`. **Не коммитьте `.env` с секретами.**

---

## Docker-сервисы

| Сервис | Порт | Роль |
|--------|------|------|
| `gateway` | 8000 | REST API + UI |
| `worker` | — | arq: ingestion, extraction |
| `agents` | 8010 | LangGraph analytics |
| `analytics` | — | Confidence, batch clustering (фон) |
| `neo4j` | 7474, 7687 | Граф |
| `qdrant` | 6333 | Векторы |
| `postgres` | 5433→5432 | Метаданные, collab, config |
| `redis` | 6379 | Очередь arq |

```bash
docker compose --project-name mkg-local up --build
```

---

## Связанные документы

| Документ | Содержание |
|----------|------------|
| [`14_agent_api.md`](14_agent_api.md) | Agent API для интеграций |
| [`22_pipeline_layers.md`](22_pipeline_layers.md) | L1–L6, L3 vs L4, HDBSCAN |
| [`19_user_guide.md`](19_user_guide.md) | UI: Чат, Документы, retry-кнопки |
| [`18_smoke_test.md`](18_smoke_test.md) | Проверка после запуска |
