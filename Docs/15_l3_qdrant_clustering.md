# L3: текстовая матрица, Qdrant и кластеризация

Отдельное окно в UI: **Документ → L3 / Qdrant**.  
Здесь — всё про слой L3, векторный индекс и планируемую аналитику аномалий.

---

## 1. Что такое L3 в целевой модели

**L3 — текстовая матрица:** структурированное содержимое документов с эмбеддингами для гибридного поиска.

| Узел (целевая модель) | Назначение | Статус в MVP |
|----------------------|------------|--------------|
| `TextParagraph` | Абзац RU/EN, позиция в документе, эмбеддинг | ✅ из Markdown |
| `TableMatrix` | Таблица в JSON + эмбеддинг | ⬜ не извлекается |
| `HeadingContext` | Заголовок H1–H6 для группировки | ✅ |
| `LangContext` | Язык документа / абзаца | ✅ |
| `SynonymMap` | Жаргон → L1-сущность | ⬜ не извлекается |

**Связи L3 (целевая модель vs код):**

| Связь | От → К | MVP |
|-------|--------|-----|
| `:HAS_PARAGRAPH` | Document → TextParagraph | ✅ |
| `:NEXT_PARAGRAPH` | TextParagraph → TextParagraph | ✅ |
| `:STRUCTURING` | HeadingContext → TextParagraph | ✅ |
| `:TAGGED_WITH` | TextParagraph → LangContext | ✅ |
| `:CONTEXT_FOR` | TextParagraph → L2/L4/L5/L6 | ✅ `_bridge_text_to_layers` |
| `:DATA_SOURCE_FOR` | TextParagraph → L1/L4 | ✅ |
| `:MAPS_TO` | SynonymMap → L1 | ⬜ |

---

## 2. Где хранятся эмбеддинги

| Хранилище | Что | Когда пишется |
|-----------|-----|---------------|
| **Neo4j** | Узлы и связи графа (в т.ч. L3 без вектора в свойствах) | После extraction → `load_graph` |
| **Qdrant** | Векторы `TextParagraph` и `Claim` | По запросу: UI «Индексировать», Agent API, auto после extraction в UI |

**Коллекции Qdrant:**

- `mkg_chunks` — L3 `TextParagraph` (256-dim, Yandex `text-search-doc`)
- `mkg_claims` — L4 `Claim` (256-dim)

**Код:** `packages/core/src/mkg_core/embeddings.py`, `llm.py::YandexLLMClient.embed`  
**API:** `GET /api/v1/agents/embeddings/status`, `POST .../documents/{id}/embeddings/index`, `POST .../search`

---

## 3. UI: вкладка «L3 / Qdrant»

1. **Статистика L3** — число абзацев, заголовков, межслойных связей, флаг индексации.
2. **Qdrant** — статус Yandex-ключа, URL Qdrant, счётчики точек, кнопки индексации.
3. **Кластеризация** — описание планируемого контура (см. §4).

Вкладка **«Поиск»** использует проиндексированные векторы; без индекса — keyword-fallback по графу.

**Настройки** — выбор модели для каждого сервиса: LLM (extraction + фильтр чанков), OCR, embedding doc/query (Qdrant). API: `GET/PUT /api/v1/config/models`.

---

## 4. Открытый вопрос: аномалии и кластеры (из ТЗ)

> Можно вытащить данные с **низкой достоверностью**, сравнить с другими факторами и сформировать **кластеры аномальности** в Qdrant для поддержки слоя L5?

### Какие факторы сравнивать (гипотеза)

| Фактор | Источник в графе |
|--------|------------------|
| Низкая `confidence` | L4 Measurement, Effect, ExperimentRun, Claim |
| Расхождение с нормативом | `:EVALUATED_AGAINST` → StandardMetric → `:FOUND_ANOMALY` |
| Противоречие между источниками | Contradiction (value_mismatch, stage_violation) |
| Неполнота | KnowledgeGap, отсутствие обязательных параметров Process/Material |
| Контекст | Location, EnvironmentalCondition, TechStage (`:USES_MAT` stage) |
| Текстовая близость | Qdrant: соседние абзацы / claims в других кластерах |

### На каком уровне кластеризовать?

| Уровень | Плюсы | Минусы |
|---------|-------|--------|
| **L3 TextParagraph** | Близко к цитате, RAG, семантика | Шум OCR, дубли абзацев |
| **L4 Claim / Measurement** | Числовые факты, confidence | Мало точек на документ |
| **Гибрид** | Вектор L3 + payload confidence/stage из Neo4j | Сложнее пайплайн |

**План (этап 3 roadmap):** сервис `analytics` → HDBSCAN по отфильтрованным точкам Qdrant (низкий confidence / открытые Contradiction) → метки кластера и outlier-score → запись в Neo4j (`Contradiction`, снижение confidence).

**Статус:** исследование; в MVP реализованы только индексация и semantic search.

---

## 5. Agent API (кратко)

```bash
# Статус Qdrant
curl -s http://localhost:8000/api/v1/agents/embeddings/status | jq .

# Индексация документа (doc_id с двоеточием → %3A)
curl -s -X POST "http://localhost:8000/api/v1/agents/documents/doc%3Aabc/embeddings/index" | jq .

# Semantic search
curl -s -X POST "http://localhost:8000/api/v1/agents/documents/doc%3Aabc/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "выщелачивание никеля", "limit": 5, "index_if_missing": true}' | jq .
```

Полная спецификация: [`14_agent_api.md`](14_agent_api.md).
