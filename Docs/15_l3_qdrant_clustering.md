# L3: текстовая матрица, Qdrant и L4 HDBSCAN

В UI: вкладка **Qdrant** и этап **L4** на пайплайне документа.  
L3 = семантический поиск; L4 = кластеры и аномалии.

---

## 1. Что такое L3 в целевой модели

**L3 — текстовая матрица:** структурированное содержимое документов с эмбеддингами для гибридного поиска.

| Узел | Назначение | Статус в MVP |
|------|------------|--------------|
| `TextParagraph` | Абзац RU/EN, позиция в документе | ✅ из Markdown |
| `TableMatrix` | Таблица в JSON + эмбеддинг | ⬜ |
| `HeadingContext` | Заголовок H1–H6 | ✅ |
| `LangContext` | Язык документа / абзаца | ✅ |
| `SynonymMap` | Жаргон → L1-сущность | ⬜ |

**Связи L3 (MVP):** `HAS_PARAGRAPH`, `NEXT_PARAGRAPH`, `STRUCTURING`, `TAGGED_WITH`, `CONTEXT_FOR`, `DATA_SOURCE_FOR`, `ABOUT` — через `_bridge_text_to_layers`.

---

## 2. Где хранятся эмбеддинги

| Хранилище | Что | Когда |
|-----------|-----|-------|
| **Neo4j** | Узлы и связи (без векторов в props) | После extraction |
| **Qdrant `mkg_chunks`** | L3 TextParagraph, MD chunks (`answers_only`) | После extraction / index / answers_only |
| **Qdrant `mkg_claims`** | L4 Claim, Measurement, Effect… | После extraction / index |

**Код:** `packages/core/src/mkg_core/embeddings.py`  
Worker после extraction вызывает `index_document_graph` автоматически.

---

## 3. L3 semantic search

- Модели: Yandex `text-search-doc` (индекс), `text-search-query` (поиск).
- Размерность: 256 (`QDRANT_VECTOR_SIZE`).
- Поиск по документу: `POST /api/v1/agents/documents/{id}/search`.
- Глобальный / dual (L3+L4): `POST /api/v1/agents/search/global`.
- Чат использует `search_global()` — обе коллекции, merge по score.

---

## 4. L4 HDBSCAN — кластеры и аномалии ✅

> Реализовано в MVP-2+: `l4_clustering.py`, UI этап L4, API anomalies.

### Алгоритм

1. Scroll L4-точек из `mkg_claims` с векторами.
2. **HDBSCAN** (`hdbscan` Python) с `min_cluster_size` из env.
3. Outliers → `cluster_id = -1`, `is_anomaly = true`, `anomaly_score`.
4. Метки пишутся в payload Qdrant и props узлов графа (`l4_cluster`).

### API

```bash
# Кластеризация документа
curl -X POST http://localhost:8000/api/v1/graph/l4/cluster \
  -H "Content-Type: application/json" \
  -d '{"document_id": "doc:abc", "min_cluster_size": 3}'

# Список аномалий (auto_cluster=true по умолчанию)
curl "http://localhost:8000/api/v1/graph/anomalies?document_id=doc%3Aabc&limit=50"

# Retry через documents API
curl -X POST http://localhost:8000/api/v1/documents/doc%3Aabc/l4-cluster
```

### UI

- Пайплайн документа: этап **L4** со статусом и кнопкой **↺ HDBSCAN L4**.
- Qdrant: блок кластеризации L4, карта точек с `cluster_id`.
- Роль **Охотник за аномалиями** + AI-режим **Аномалии**.

### Env

| Переменная | Default | Описание |
|------------|---------|----------|
| `HDBSCAN_MIN_CLUSTER_SIZE` | 3 | Мин. точек в кластере |
| `HDBSCAN_MIN_SAMPLES` | null | HDBSCAN min_samples (optional) |

---

## 5. UI: вкладка «Qdrant»

1. **Статистика** — точки в `mkg_chunks` / `mkg_claims`.
2. **Индексировать** — `POST .../index` или Agent API.
3. **Семантический поиск** — hits с layer L3/L4.
4. **Карта точек** — scroll без векторов.
5. **L4 cluster** — POST analytics/l4-cluster (Agent API).

**Настройки** — LLM, OCR, embedding doc/query: `GET/PUT /api/v1/config/models`.

---

## 6. Agent API (кратко)

```bash
curl -s http://localhost:8000/api/v1/agents/embeddings/status | jq .

curl -s -X POST "http://localhost:8000/api/v1/agents/documents/doc%3Aabc/embeddings/index" | jq .

curl -s -X POST "http://localhost:8000/api/v1/agents/documents/doc%3Aabc/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "выщелачивание никеля", "limit": 5, "index_if_missing": true}' | jq .
```

Полная спецификация: [`14_agent_api.md`](14_agent_api.md).

См. также: [`21_pipeline_and_layers.md`](21_pipeline_and_layers.md).
