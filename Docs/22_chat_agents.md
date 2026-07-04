# Чат, роли и AI-агенты

## Обзор

Вкладка **Чат** объединяет:

- **Роль пользователя** — права и системный промпт (8 ролей). Это *стиль ответа*, не слой графа.
- **Режим скорости** — переключатель **Быстрый** (~5 с, RAG) / **Подробный** (оркестратор + trace).
- **Автоматический пайплайн агентов** — в режиме «Подробный»: оркестратор L1–L6 + RAG + обход графа.
- **Межслойные агенты L1–L6** — оценка вопроса по слоям графа; см. [`24_layer_agents.md`](24_layer_agents.md).
- **Загрузку файлов** (кнопка прикрепления) с выбором полного пайплайна или «только для ответов».
- **Trace** — цепочка reasoning: поиск → граф → LLM / шаги агента.
- **Источники** и **Сохранить как MD** — экспорт ответа с ссылками на документы.

UI cache: `?v=137` (при странном поведении — **Ctrl+F5**).

> **Безопасность MVP:** UI на `localhost:8000` без серверной аутентификации. Роль — клиентский выбор; не деплойте публично без auth.

## Режимы скорости ответа

Переключатель над полем ввода: **Быстрый** | **Подробный · с рассуждениями**. Предпочтение хранится в `localStorage` (`mkg_chat_speed_mode`).

| Режим | `speed_mode` | Поведение | Целевое время |
|-------|--------------|-----------|---------------|
| **Быстрый** | `fast` | Qdrant L3+L4 → короткий ответ LLM; без оркестратора, обхода графа и L1–L6 | ~5 с |
| **Подробный** | `full` | Оркестратор + agent loop + graph walk + trace (по умолчанию) | без жёсткого лимита |

На ответе показывается badge режима. Trace в быстром режиме — свёрнутый минимальный блок.

## Межслойные агенты в чате

**Межслойный агент** (`l1_agent` … `l6_agent`) — не роль. Это узел, который оценивает вопрос **с точки зрения одного слоя** MKG. В оркестраторе они работают **гибким циклом с JSON-шиной** — см. [`24_layer_agents.md`](24_layer_agents.md).

| Где видны | Что происходит |
|-----------|----------------|
| Ответ в чате (роли с `can_run_agents`) | Оркестратор: гибкий цикл + шина (`orchestrator_graph.py`) |
| Роли без агентов (engineer, viewer…) | Облегчённый layer trace в `chat_engine.py` |
| Trace в ответе | `agent_question`, `situation_evaluation`, `round`, `bus_messages` |

Подробнее: [`24_layer_agents.md`](24_layer_agents.md) · иерархия — [`23_agent_hierarchy.md`](23_agent_hierarchy.md).

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
| `orchestrator_mode` | Координатор → гибкий цикл L1–L6 + шина → синтез (**по умолчанию в чате**) |
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
  "history": [
    {"role": "user", "content": "…"},
    {"role": "assistant", "content": "…"}
  ],
  "include_graph": true,
  "include_artifacts": true,
  "speed_mode": "full",
  "document_ids": ["doc:..."]
}
```

**`speed_mode: "fast"`** — `run_dialog_fast()`: Qdrant L3+L4 (≤5 хитов), LLM 512 токенов, timeout ~4.5 с; оркестратор и graph walk пропускаются.

**`speed_mode: "full"` (по умолчанию)** — роли с `can_run_agents`: async оркестратор (`POST /agents-service/run/async` + poll `GET .../run/{run_id}`) с **live-обновлением графа** в панели чата. Fallback при 404/503 agents — синхронный `/chat/complete` с RAG + graph walk.

История (до 16–20 реплик) передаётся в оркестратор: planner, layer agents L1–L6, synthesizer и trace `chat_memory` (число реплик). Короткие продолжения («Подумай еще раз») используют prior question для поиска.

**Роли без агентов (full):** Qdrant L3+L4 → Neo4j walk → layer trace → LLM.

Trace steps (оркестратор):

1. `orchestrator_init` → `orchestrator_plan` → `agent_loop_start`
2. **Цикл:** `orchestrator_router` ↔ `l*_agent` (раунды, `bus_messages`)
3. `discover_new_connections` → `connection_gap_analyzer` → `orchestrator_synthesize`

Trace steps (fallback-диалог):

1. `chat_role` — выбранная роль
2. `qdrant_search` — dual search L3+L4
3. `graph_traversal` — расширение контекста
4. `l1_agent` … `l6_agent` — layer trace
5. `llm_compose` — ответ YandexGPT

Ответ: `reply`, `trace`, `graph`, `artifacts`, `sources`, `layer_results`, `timing_ms`, `speed_mode`.

### Программный API без UI

`POST /api/v1/query` — явный выбор `mode: "anomaly_mode"` / `audit_mode` / …

## Загрузка файлов в чате

При нажатии кнопки прикрепления появляется модальное окно:

| Кнопка | `processing_mode` | Пайплайн |
|--------|-------------------|----------|
| **Загрузить и обработать** | `full` | OCR → MD → L1–L6 → Neo4j → Qdrant → L4 |
| **Только для ответов** | `answers_only` | OCR → MD → Qdrant (chunks из MD) |

## Trace и reasoning chain

- **Оркестратор** — `orchestrator_init` → `agent_loop_start` → router ↔ agents → discover → gap → synthesize.
- **Диалог (fallback)** — `qdrant_l3`, `graph_traversal`, layer trace, `llm_compose`.
- **Быстрый (`fast`)** — `qdrant_l3`, `qdrant_l4_cluster`, `llm_compose` (свёрнутый trace).
- **anomaly_mode** (только API) — список `anomalies` с `node_id`, `severity`, `related_neighbors`.

## История чатов и заголовки

- Threads: `POST /api/v1/chat/threads`, список в sidebar.
- Placeholder «Новый чат» → **заголовок из первого user-сообщения** (`derive_thread_title`, до ~55 символов) в `collab_db.py`.

## Источники, секции, Пояснить / Обновить

- **Источники** — блок `<details class="chat-sources">` **свёрнут по умолчанию**; chip → `GET /api/v1/documents/{id}/markdown`; badge `extraction_confidence`.
- **Структура ответа** — разделы `##` в collapsible blocks; «Сводка» открыта; см. [`25_analytics_synthesis.md`](25_analytics_synthesis.md).
- **Пояснить** — кнопка у каждого `##`-раздела и под ответом; отправляет «Поясни подробнее раздел «…»…».
- **Обновить** — повтор ответа на тот же вопрос (`regenerate` без нового user-post).
- **Экспорт** — MD, JSON-LD, Печать/PDF (см. [`27_additional_wishes.md`](27_additional_wishes.md)).

## Async graph в «Подробном»

1. UI → `POST /api/v1/agents-service/run/async` (`mode=orchestrator_mode`).
2. Poll `GET /api/v1/agents-service/run/{run_id}` (~420 ms) до `status=complete`.
3. На каждом poll: `trace` → live trace UI; `graph` → incremental mini-graph (`graph-mini.js`).
4. Индикатор «Сбор графа… L4 · N узл.» по последнему шагу trace.

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
| POST | `/api/v1/chat/complete` | Чат: fast / RAG-fallback |
| POST | `/api/v1/agents-service/run/async` | Async оркестратор (Подробный) |
| GET | `/api/v1/agents-service/run/{run_id}` | Poll trace + graph |
| POST | `/api/v1/query` | Программный query / явный agent mode |
| GET | `/api/v1/roles` | Список ролей |
| GET | `/api/v1/agents-service/modes` | AI-режимы (API) |
| POST | `/api/v1/agents-service/run` | Запуск LangGraph |
| GET | `/api/v1/graph/anomalies` | L4-аномалии |
| POST | `/api/v1/graph/l4/cluster` | HDBSCAN L4 |

См. также: [`24_layer_agents.md`](24_layer_agents.md), [`23_agent_hierarchy.md`](23_agent_hierarchy.md), [`21_pipeline_and_layers.md`](21_pipeline_and_layers.md), [`25_analytics_synthesis.md`](25_analytics_synthesis.md).
