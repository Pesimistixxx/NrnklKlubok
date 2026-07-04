# Дополнительные пожелания — MVP и roadmap

UI cache: `?v=95` (при странном поведении — **Ctrl+F5**).

## Обзор

Слайд «ДОПОЛНИТЕЛЬНЫЕ ПОЖЕЛАНИЯ» — что реализовано в hackathon MVP и что остаётся в roadmap.

| # | Пожелание | MVP (сейчас) | Roadmap |
|---|-----------|--------------|---------|
| 1 | Multilingual RU/EN | Расширение поиска по `aliases` / `name_ru` / `name_en`; заметка в промптах чата | Полный term mapping UI, авто-детект языка документа |
| 2 | Export | MD + **JSON-LD** + **Печать/PDF** в чате | Серверный PDF, шаблоны презентаций |
| 3 | Notifications | `localStorage` watchlist + toast при новом документе | Push/email, подписка на темы в Postgres |
| 4 | Expert graph edit | Комментарий к связи (admin/engineer), `expert_edits` в JSON + Neo4j props | Полный audit trail, merge в extraction |
| 5 | Manager dashboards | Карточки в **Настройки → Обзор** | Командная активность, drill-down по доменам |
| 6 | Comparative analysis | Панель **Сравнение** на графе (2–3 Process/Material) | CAPEX, cold climate, eco limits из L6 |

## Export (чат)

На ответе ассистента:

- **Сохранить как MD** — как раньше.
- **JSON-LD** — `@type: Answer`, источники как `citation`, дата, автор роли.
- **Печать / PDF** — HTML-предпросмотр + `@media print` (Ctrl+P → «Сохранить как PDF»).

## Expert graph edit

**Роли:** `admin`, `engineer`.

На панели детали связи (Documents → граф → клик по ребру):

- Поле «Комментарий эксперта» + кнопка «Сохранить».
- API: `PATCH /api/v1/graph/documents/{doc_id}/relationship?from=&to=&type=`
- Body: `{ "expert_comment", "edited_by", "role_id" }`
- Хранение: `relationship.props.expert_comment`, `edited_by`, `edited_at`; журнал `graph.expert_edits[]`; Neo4j `SET r += props`.

## Dashboard (обзор)

**Настройки → Обзор знаний** (или секция на вкладке Настройки):

- API: `GET /api/v1/dashboard/stats`
- Карточки: число документов, L4-аномалии, узлы `Contradiction`, домены (гидромет / экология / отходы по заголовкам файлов).
- **Зоны риска:** противоречия, разреженные L4-кластеры (≤2 факта), L4-noise.

## Сравнительный анализ

На вкладке **Документы → граф**:

- Кнопка **Сравнение** в toolbar.
- Выбор до 3 узлов `Process` / `Material`.
- Таблица Measurement: параметр, значение, единица, документ-источник.

## Multilingual

- `mkg_core.alias_expansion` — токены запроса дополняются синонимами из графов (Material, Process, Equipment, ChemicalReagent).
- `effective_search_query()` — alias expansion после учёта истории чата.
- Промпты: `MULTILINGUAL_NOTE` в `role_prompts.py`.

## Notifications (лёгкий MVP)

- **Настройки → Подписки:** ключевые слова (через запятую), хранение `localStorage` (`mkg_topic_watchlist`).
- При обновлении списка документов — toast, если `file_name` совпал с watchlist.
- **Roadmap:** серверные подписки, digest по email, Neo4j `Event` / pub alerts.

## Связанные API

| Метод | Путь | Назначение |
|-------|------|------------|
| GET | `/api/v1/dashboard/stats` | Обзор для менеджера |
| PATCH | `/api/v1/graph/documents/{id}/relationship` | Комментарий эксперта к связи |
| GET | `/api/v1/docs/additional-wishes` | Этот документ в UI |

См. также: [`22_chat_agents.md`](22_chat_agents.md), [`13_roadmap.md`](13_roadmap.md).
