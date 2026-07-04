# Аналитика и синтез ответов

UI cache: `?v=95` (при странном поведении — **Ctrl+F5**).

## Назначение

Все пользовательские ответы чата MKG (быстрый RAG, fallback-диалог, оркестратор L1–L6, programmatic modes) формируются **структурированным обзором литературы** с явными разделами на русском.

Слайд «АНАЛИТИКА И СИНТЕЗ ОТВЕТОВ» реализован в:

| Компонент | Файл | Что делает |
|-----------|------|------------|
| Шаблон разделов | `packages/core/src/mkg_core/answer_structure.py` | `ANSWER_STRUCTURE_TEMPLATE`, `CHAT_STRUCTURE_RULES`, `SYNTH_STRUCTURE_RULES`, `extract_synthesis_entities()` |
| Роли чата | `services/gateway/app/role_prompts.py` | `CHAT_OUTPUT_RULES` + акценты researcher / analyst / validator / anomaly_hunter |
| Оркестратор | `services/agents/app/orchestrator_graph.py` | `_SYNTH_PROMPT`, payload: layer_results, sources, knowledge_gaps, experts, anomalies, gaps |
| Fallback-диалог | `services/gateway/app/chat_engine.py` | system prompt + `FAST_STRUCTURE_NOTE` в быстром режиме |
| Programmatic modes | `services/agents/app/nodes.py` | `_ANSWER_STYLE`, `_BUILDER_PROMPT` |
| UI | `static/js/chats.js`, `static/css/app.css` | Markdown-рендер, collapsible ##-разделы, «Пояснить» на раздел |

## Шаблон ответа (Markdown)

```markdown
## Сводка
## Источники по группам (метод / год / география)
## Консенсус и разногласия
## Уверенность (N источников, уровень достоверности)
## Пробелы в знаниях
## Рекомендации (кейсы, эксперты, темы)
## Уточняющий вопрос
```

Последний раздел опускается, если ответ полный.

### 1. Structured answers

- **Источники по группам** — метод/процесс, год, география (РФ/зарубеж), уровень детализации.
- **Консенсус и разногласия** — согласованные выводы vs расхождения / противоречия.
- **Уверенность** — число опорных источников + уровень (высокая/средняя/низкая) по `extraction_confidence`.

### 2. Knowledge gaps

- Непокрытые комбинации material–mode–condition.
- Технологии только в отечественной или только в зарубежной литературе.
- Узлы `KnowledgeGap` из Neo4j → раздел «Пробелы в знаниях».
- `connection_gap_analyzer` → поле `gaps` в synthesizer payload.

### 3. Recommendations

- Похожие кейсы и смежные решения.
- Узлы `Expert`, `Organization`, `Facility` → «Рекомендации».
- Темы для углублённого изучения.

## Backend: данные synthesizer

`orchestrator_synthesize` передаёт в LLM:

| Поле | Источник |
|------|----------|
| `layer_results` | L1–L6 agent loop |
| `sources` | `extract_synthesis_entities()` — Claim, Material, Process, TextParagraph |
| `knowledge_gaps` | Neo4j `KnowledgeGap` |
| `experts` | Neo4j `Expert` |
| `anomalies` | L4 с `cluster_id=-1` (HDBSCAN noise) |
| `gaps` | `connection_gap_analyzer` JSON |
| `new_connections` | `discover_new_connections` |

## UI

- Ответ рендерится через `marked` + DOMPurify (`md-render-view`).
- Если в ответе ≥2 заголовков `##`, разделы оборачиваются в `<details class="chat-answer-section">`.
- Первый раздел («Сводка») открыт по умолчанию.
- Кнопка **Пояснить** у каждого раздела отправляет: «Поясни подробнее раздел «…» предыдущего ответа…».
- Общая кнопка **Пояснить** под сообщением поясняет весь ответ.
- Кнопка **Обновить** — повтор генерации на исходный вопрос пользователя (`regenerate`).

## Режимы скорости

| Режим | Структура |
|-------|-----------|
| **Быстрый** | Те же заголовки `##`, содержание короче; «Рекомендации» и «Уточняющий вопрос» — по необходимости |
| **Подробный** | Полный шаблон; оркестратор + gap analyzer + graph entities |

## Связь с key requirements

Пересекается с агентом key requirements (19851921):

- Гео-фильтр RU/зарубеж → раздел «Источники по группам».
- `query_facets` (materials, processes, year, geography) → planner и layer agents.
- Верификация / `extraction_confidence` → «Уверенность».
- Числовые диапазоны и синонимы → поиск и facets, отражаются в группировке источников.

## Связанные документы

- [`22_chat_agents.md`](22_chat_agents.md) — чат, роли, пайплайн
- [`24_layer_agents.md`](24_layer_agents.md) — L1–L6 и шина
- [`21_multiagent_system.md`](21_multiagent_system.md) — Recommendation / Expert Finder agents
