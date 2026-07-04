# L3: текстовая матрица, Qdrant и кластеризация L4

Отдельное окно в UI: **Документ → Qdrant** и блок **L4 HDBSCAN** на пайплайне.

> L3 vs L4: [`22_pipeline_layers.md`](22_pipeline_layers.md) · API: [`21_api_reference.md`](21_api_reference.md) · Agent API: [`14_agent_api.md`](14_agent_api.md)

---

## 1. Что такое L3 в целевой модели

**L3 — текстовая матрица:** структурированное содержимое документов с эмбеддингами для семантического поиска.

| Узел (целевая модель) | Назначение | Статус в MVP |
|----------------------|------------|--------------|
| `TextParagraph` | Абзац RU/EN, позиция в документе | ✅ из Markdown |
| `TableMatrix` | Таблица в JSON + эмбеддинг | ⬜ не извлекается |
| `HeadingContext` | Заголовок H1–H6 | ✅ |
| `LangContext` | Язык документа / абзаца | ✅ |
| `SynonymMap` | Жаргон → L1-сущность | ⬜ |

**L3 не кластеризуется HDBSCAN** — только semantic search.

---

## 2. L4 и HDBSCAN (реализовано)

**L4** — факты (`Claim`, `Measurement`, `Effect`, …). В Qdrant коллекция **`mkg_claims`**.

После индексации L4 worker/gateway может запустить **HDBSCAN**:

1. Векторы Claim из Qdrant.
2. `hdbscan.HDBSCAN` (`packages/core/src/mkg_core/l4_clustering.py`).
3. Метки на узлах графа и в payload Qdrant:
   - `cluster_id` (или `-1` = noise/outlier);
   - `is_anomaly`;
   - `anomaly_score` (GLOSH).

| Параметр env | Default |
|--------------|---------|
| `HDBSCAN_MIN_CLUSTER_SIZE` | 3 |
| `HDBSCAN_MIN_SAMPLES` | auto |

API:

```bash
curl -s -X POST "http://localhost:8000/api/v1/documents/<doc_id>/l4-cluster"
curl -s -X POST "http://localhost:8000/api/v1/graph/l4/cluster" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "<doc_id>", "min_cluster_size": 3}'
curl -s "http://localhost:8000/api/v1/graph/anomalies?document_id=<doc_id>"
curl -s -X POST "http://localhost:8000/api/v1/agents/analytics/l4-cluster?document_id=<doc_id>"
```

**Режим `answers_only`:** L4 и HDBSCAN пропускаются.

LangGraph **anomaly mode** использует эти метки: [`21_multiagent_system.md`](21_multiagent_system.md).

---

## 3. Где хранятся эмбеддинги

| Хранилище | Что | Когда пишется |
|-----------|-----|---------------|
| **Neo4j** | Узлы и связи (без векторов в props) | После extraction |
| **Qdrant** | L3 → `mkg_chunks`, L4 → `mkg_claims` | `POST /documents/{id}/index` |

**Код:** `packages/core/src/mkg_core/embeddings.py`  
**Модели:** Yandex `text-search-doc/latest` (index), `text-search-query/latest` (search)

---

## 4. Dual search (L3 + L4)

В чате и `search_global`:

- **L3 hits** — цитаты из текста (`mkg_chunks`).
- **L4 hits** — факты и claims (`mkg_claims`), с учётом cluster context.

Затем **graph traversal** (`GRAPH_TRAVERSAL_MAX_HOPS`) расширяет подграф в Neo4j/JSON.

---

## 5. UI

1. **Пайплайн** — этап «Кластеризация L4», retry **↺ HDBSCAN L4**.
2. **Qdrant** — индексация, карта точек по кластерам, кнопка HDBSCAN.
3. **Граф** — badge `cluster_id` / anomaly на L4-узлах.

**Настройки** — embedding doc/query: `GET/PUT /api/v1/config/models`.

---

## 6. Открытые вопросы (следующий этап)

Связать HDBSCAN outliers с:

- низкой `confidence` на Claim;
- `:FOUND_ANOMALY` и Contradiction L5;
- KnowledgeGap.

Гипотеза факторов — см. исторический § в git; приоритет: [`03_implementation_gap.md`](03_implementation_gap.md).

---

## 7. Agent API (кратко)

```bash
curl -s http://localhost:8000/api/v1/agents/embeddings/status | jq .
curl -s -X POST "http://localhost:8000/api/v1/agents/documents/doc%3Aabc/embeddings/index" | jq .
curl -s -X POST "http://localhost:8000/api/v1/agents/documents/doc%3Aabc/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "выщелачивание", "limit": 5, "mode": "semantic"}' | jq .
```

Полная спецификация: [`14_agent_api.md`](14_agent_api.md).
