# Чат, роли и AI-агенты

## Обзор

Вкладка **Чат** объединяет:

- **Роль пользователя** — права и системный промпт (8 ролей).
- **AI-режим** — диалог LLM или LangGraph-агент (5 режимов).
- **Загрузку файлов** (📎) с выбором полного пайплайна или «только для ответов».
- **Trace** — цепочка reasoning: поиск → граф → LLM / шаги агента.
- **Источники** и **Сохранить как MD** — экспорт ответа с ссылками на документы.

UI cache: `?v=43` (при странном поведении — **Ctrl+F5**).

## Роли пользователя

Источник: `services/gateway/app/roles.py` · API: `GET /api/v1/roles`

| ID | Название | Agent ID | `can_run_agents` | Назначение |
|----|----------|----------|------------------|------------|
| `admin` | Администратор | security | ✅ | Настройки, очистка базы |
| `researcher` | Исследователь | synthesis | ✅ | Гипотезы, обзоры, советы |
| `engineer` | Инженер данных | ingestion | ❌ | Пайплайн OCR→MD→Neo4j |
| `analyst` | Аналитик | retrieval | ✅ | Qdrant, граф, паттерны |
| `validator` | Валидатор | validation | ✅ | Аудит фактов |
| `security` | Безопасность | security | ❌ | RBAC, грифы L5 |
| `anomaly_hunter` | Охотник за аномалиями | retrieval | ✅ | Режим «Аномалии», L4 HDBSCAN |
| `viewer` | Наблюдатель | notification | ❌ | Read-only |

Промпт роли: `GET/PUT/DELETE /api/v1/roles/{role_id}/prompt`.

Сессия: `POST /api/v1/users/session` с `{ "role_id": "...", "display_name": "..." }`.

## AI-режимы (LangGraph agents service)

Прокси gateway: `/api/v1/agents-service/*` → контейнер `agents:8010`.

| Mode ID | UI | Описание |
|---------|-----|----------|
| *(null)* | **Диалог** | Быстрый ответ: dual Qdrant search + graph traversal + LLM |
| `hypothesis_mode` | Гипотезы | Гипотезы и связи между фактами |
| `audit_mode` | Аудит | Противоречия, issue/severity |
| `anomaly_mode` | Аномалии | Обход L4-выбросов (HDBSCAN + Neo4j + Qdrant) |
| `literature_review_mode` | Обзор | Структурированный обзор источников |
| `recommendation_mode` | Советы | Рекомендации по теме |

Список режимов: `GET /api/v1/agents-service/modes`.

Запуск агента: `POST /api/v1/agents-service/run`:

```json
{
  "query": "Какие аномалии в документе?",
  "mode": "anomaly_mode",
  "doc_ids": ["doc:abc123"],
  "user_role": "anomaly_hunter",
  "limit": 5
}
```

Роль `anomaly_hunter` + режим `anomaly_mode` — основной сценарий охоты за L4-аномалиями.

## Диалог vs агент

### Диалог (`POST /api/v1/chat/complete`)

```json
{
  "message": "Какие материалы упоминаются?",
  "role_id": "analyst",
  "include_graph": true,
  "include_artifacts": true,
  "document_ids": ["doc:..."]
}
```

Trace steps:

1. `chat_role` — выбранная роль
2. `qdrant_search` — dual search L3+L4 (`mkg_chunks` + `mkg_claims`)
3. `graph_traversal` — расширение контекста (`GRAPH_TRAVERSAL_MAX_HOPS`)
4. `llm_compose` — ответ YandexGPT

Ответ содержит: `reply`, `trace`, `graph`, `artifacts`, `sources`, `timing_ms`.

### Программный API без UI

`POST /api/v1/query` — тестовый endpoint для сложных вопросов:

- `mode: "dialog"` (или omit) → тот же `run_chat_query`
- `mode: "anomaly_mode"` / `audit_mode` / … → прокси в agents service

## Загрузка файлов в чате

При выборе 📎 появляется модальное окно:

| Кнопка | `processing_mode` | Пайплайн |
|--------|-------------------|----------|
| **Загрузить и обработать** | `full` | OCR → MD → L1–L6 → Neo4j → Qdrant → L4 |
| **Только для ответов** | `answers_only` | OCR → MD → Qdrant (chunks из MD) |

Карточка загрузки показывает этапы пайплайна; по завершении — **Открыть MD**.

## Trace и reasoning chain

В UI раскрывается блок **Trace** / **Reasoning**:

- **Диалог** — шаги `qdrant_search`, `graph_traversal`, `llm_compose` с таймингами.
- **Agent modes** — шаги LangGraph: planner, retrieval, analyzer, mode_builder, final_report.
- **anomaly_mode** — дополнительно список `anomalies` с `node_id`, `anomaly_reason`, `severity`, `related_neighbors`.

## Источники и экспорт MD

- **Источники** — кликабельные ссылки на `GET /api/v1/documents/{id}/markdown` (variant clean/marked).
- **Сохранить как MD** — клиентский экспорт ответа + список источников в `.md`.

## Права по ролям (кратко)

| Действие | Роли |
|----------|------|
| Upload | admin, researcher, engineer |
| Extraction / граф | admin, researcher, engineer |
| AI-агенты | admin, researcher, analyst, validator, anomaly_hunter |
| Админ / очистка | admin |

## Связанные API

| Метод | Путь | Назначение |
|-------|------|------------|
| POST | `/api/v1/chat/complete` | Диалог с RAG |
| POST | `/api/v1/query` | Программный query / agent mode |
| GET | `/api/v1/roles` | Список ролей |
| GET | `/api/v1/agents-service/modes` | AI-режимы |
| POST | `/api/v1/agents-service/run` | Запуск LangGraph |
| GET | `/api/v1/graph/anomalies` | L4-аномалии |
| POST | `/api/v1/graph/l4/cluster` | HDBSCAN L4 |

См. также: [`21_pipeline_and_layers.md`](21_pipeline_and_layers.md), [`19_user_guide.md`](19_user_guide.md).
