# Чат, роли и AI-агенты

## Обзор

Вкладка **Чат** объединяет:

- **Роль пользователя** — права и системный промпт (8 ролей). Это *стиль ответа*, не слой графа.
- **Автоматический пайплайн агентов** — оркестратор L1–L6 + RAG + обход графа (без выбора «режима» в UI).
- **Межслойные агенты L1–L6** — оценка вопроса по слоям графа; см. **Межслойные агенты (L1–L6)**.
- **Загрузку файлов** (кнопка прикрепления) с выбором полного пайплайна или «только для ответов».
- **Trace** — цепочка reasoning: поиск → граф → LLM / шаги агента.
- **Источники** и **Сохранить как MD** — экспорт ответа с ссылками на документы.

UI cache: `?v=76` (при странном поведении — **Ctrl+F5**).

## Межслойные агенты в чате

**Межслойный агент** (`l1_agent` … `l6_agent`) — не роль. Это узел, который оценивает вопрос **с точки зрения одного слоя** MKG (материалы L1, текст L3, факты L4…). В оркестраторе они работают **циклом L1→L6** с накоплением контекста — см. раздел **«Цикл межслойных агентов»** в **Межслойные агенты (L1–L6)**.

| Где видны | Что происходит |
|-----------|----------------|
| Ответ в чате (роли с `can_run_agents`) | Оркестратор L1→L6 последовательно (`orchestrator_graph.py`) |
| Роли без агентов (engineer, viewer…) | Облегчённый layer trace в `chat_engine.py` |
| Trace в ответе | `agent_question`, `situation_evaluation`, `node_count`, `loop_index` (1…6) |

Подробнее: **Межслойные агенты (L1–L6)** · иерархия — **Иерархия агентов**.

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
| `anomaly_hunter` | Охотник за аномалиями | retrieval | ✅ | L4 HDBSCAN (стиль ответа) |
| `viewer` | Наблюдатель | notification | ❌ | Read-only |

Промпт роли: `GET/PUT/DELETE /api/v1/roles/{role_id}/prompt`.

Сессия: `POST /api/v1/users/session` с `{ "role_id": "...", "display_name": "..." }`.

## AI-режимы (LangGraph, программный API)

Режимы **не выбираются в UI чата**. Они доступны через API для тестов и интеграций.

Прокси gateway: `/api/v1/agents-service/*` → контейнер `agents:8010`.

| Mode ID | Назначение |
|---------|------------|
| `orchestrator_mode` | Координатор → L1→L6 → синтез (**по умолчанию в чате**, внутренне) |
| `hypothesis_mode` | Гипотезы и связи между фактами |
| `audit_mode` | Противоречия, issue/severity |
| `anomaly_mode` | L4-выбросы HDBSCAN — **внутренний**, не UI |
| `literature_review_mode` | Структурированный обзор источников |
| `recommendation_mode` | Рекомендации по теме |

Список режимов: `GET /api/v1/agents-service/modes`.

Запуск: `POST /api/v1/agents-service/run` или `POST /api/v1/query` с `mode`.

## Пайплайн ответа в чате

### `POST /api/v1/chat/complete` (единственный UI-путь)

```json
{
  "message": "Какие материалы упоминаются?",
  "role_id": "analyst",
  "include_graph": true,
  "include_artifacts": true,
  "document_ids": ["doc:..."]
}
```

**Роли с `can_run_agents`:** gateway вызывает `orchestrator_mode` в agents service (L1→L6, discover, synthesize). При недоступности agents — fallback на RAG-диалог.

**Роли без агентов:** Qdrant L3+L4 → Neo4j walk → layer trace → LLM.

Trace steps (оркестратор):

1. `orchestrator_init` → `orchestrator_plan` → `layer_loop_start`
2. **Цикл L1…L6:** `l1_agent` … `l6_agent` (каждый шаг с `loop_index`, контекст передаётся дальше)
3. `discover_new_connections` → `connection_gap_analyzer` (опциональный refinement) → `orchestrator_synthesize`

Trace steps (fallback-диалог):

1. `chat_role` — выбранная роль
2. `qdrant_search` — dual search L3+L4
3. `graph_traversal` — расширение контекста
4. `l1_agent` … `l6_agent` — layer trace
5. `llm_compose` — ответ YandexGPT

Ответ: `reply`, `trace`, `graph`, `artifacts`, `sources`, `layer_results`, `timing_ms`.

### Программный API без UI

`POST /api/v1/query` — явный выбор `mode: "anomaly_mode"` / `audit_mode` / …

## Загрузка файлов в чате

При нажатии кнопки прикрепления появляется модальное окно:

| Кнопка | `processing_mode` | Пайплайн |
|--------|-------------------|----------|
| **Загрузить и обработать** | `full` | OCR → MD → L1–L6 → Neo4j → Qdrant → L4 |
| **Только для ответов** | `answers_only` | OCR → MD → Qdrant (chunks из MD) |

## Trace и reasoning chain

- **Оркестратор** — `orchestrator_init` → `layer_loop_start` → `l1_agent` … `l6_agent` → discover → gap → synthesize.
- **Диалог (fallback)** — `qdrant_l3`, `graph_traversal`, layer trace, `llm_compose`.
- **anomaly_mode** (только API) — список `anomalies` с `node_id`, `severity`, `related_neighbors`.

## Источники и экспорт MD

- **Источники** — кликабельные ссылки на `GET /api/v1/documents/{id}/markdown`.
- **Сохранить как MD** — клиентский экспорт ответа + список источников.

## Права по ролям (кратко)

| Действие | Роли |
|----------|------|
| Upload | admin, researcher, engineer |
| Extraction / граф | admin, researcher, engineer |
| AI-агенты (оркестратор) | admin, researcher, analyst, validator, anomaly_hunter |
| Админ / очистка | admin |

## Связанные API

| Метод | Путь | Назначение |
|-------|------|------------|
| POST | `/api/v1/chat/complete` | Чат: оркестратор или RAG-fallback |
| POST | `/api/v1/query` | Программный query / явный agent mode |
| GET | `/api/v1/roles` | Список ролей |
| GET | `/api/v1/agents-service/modes` | AI-режимы (API) |
| POST | `/api/v1/agents-service/run` | Запуск LangGraph |
| GET | `/api/v1/graph/anomalies` | L4-аномалии |
| POST | `/api/v1/graph/l4/cluster` | HDBSCAN L4 |

См. также: **Межслойные агенты (L1–L6)**, **Иерархия агентов**, **Пайплайн и слои L1–L6**.
