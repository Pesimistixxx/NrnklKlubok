# Единая карта знаний R&D для горно-металлургической отрасли

> Рабочее название: **MKG** (Mining Knowledge Graph).

## Суть системы одним абзацем

Платформа собирает разрозненные R&D-источники (отчёты, статьи, патенты, протоколы,
книги, таблицы), приводит их к единому размеченному виду, извлекает сущности и факты,
раскладывает их по **6 онтологическим слоям** в граф Neo4j, а параллельно строит
векторный индекс в Qdrant. Поверх этого работают движки **достоверности**,
**выявления противоречий** и **пробелов в знаниях**. Итог — система, которая отвечает
на сложные многопараметрические запросы, показывает источник каждого факта, его
уровень доверия и конфликтующие данные.

## Ключевые боли, которые решаем

| Боль | Как решаем |
|------|-----------|
| Знания разрознены, теряется институциональная память | Единый граф + текстовая матрица + версионирование |
| Дублирование экспериментов | Entity Resolution + поиск похожих фактов через Qdrant |
| Противоречивые выводы | Движок противоречий (`Contradiction`) + объяснимая достоверность |
| «Поверхностная» достоверность (боль заказчика) | **Композитная модель доверия** вместо одного числа |
| Слабый текстовый слой | Иерархический чанкинг, OCR→Markdown, поддержка книг (map-reduce) |

## Минимальный комплект документации

| Файл | Что внутри |
|------|-----------|
| `00_overview.md` | Краткая суть проекта и текущий статус |
| `02_architecture.md` | Архитектура, ingestion/extraction/Neo4j/Qdrant |
| `03_implementation_gap.md` | **Целевая модель vs MVP** (6 слоёв, связи, ТЗ) |
| `13_roadmap.md` | Что реализовано и что в доработке |
| `15_l3_qdrant_clustering.md` | L3, Qdrant, кластеризация, открытый вопрос аномалий |
| `18_smoke_test.md` | Пошаговая проверка локального запуска |
| `19_user_guide.md` | UI v3: Главная, Граф, Полный граф, Qdrant, Настройки |
| `20_project_status.md` | Текущий этап MVP-2 и матрица готовности |
| `14_agent_api.md` | Agent REST API для интеграций |

## Где что происходит (по коду)

1. **Upload**: `services/gateway/app/main.py` (`POST /api/v1/documents`).
2. **Ingestion**: `services/worker/app/tasks.py::run_ingestion` и `packages/ingestion/.../pipeline.py`.
3. **Extraction/разметка**: `services/worker/app/tasks.py::run_extraction` и `packages/extraction/.../extractor.py`.
4. **Заполнение Neo4j**: `packages/extraction/.../loader.py::load_graph` (`MERGE` узлов/связей).
5. **Эмбеддинги → Qdrant**: `packages/core/.../embeddings.py` — по запросу UI / Agent API; UI: вкладка **Qdrant**, превью документа (Markdown, поиск).
6. **Межслойный bridge L3**: `extractor.py::_bridge_text_to_layers` — `CONTEXT_FOR`, `DATA_SOURCE_FOR`, `ABOUT`.

## Текущий статус MVP (кратко)

| Готово | В работе / не сделано |
|--------|------------------------|
| Upload, OCR, MD, extraction L1–L6, Neo4j, GUI графа | Contradiction engine, композитный confidence |
| Agent API, semantic search, Qdrant indexing, capabilities registry | TableMatrix, SynonymMap, HDBSCAN-анomalies |
| UI v3: компактный/полный граф, resize canvas, preview bar | RAG synthesis, RBAC, визуальный конструктор |

Подробное сравнение с целевой моделью: [`03_implementation_gap.md`](03_implementation_gap.md).

## Что делаем на текущем этапе (MVP-2)

1. **Главная** — загрузка файла; документы только в **боковой панели**; превью (▼) — Markdown, поиск, логи.
2. Конвейер: OCR → Markdown → extraction L1–L6 → Neo4j + bridge L3.
3. **Граф** / **Полный граф** — vis-network (компактный vs все L3); resize canvas.
4. **Qdrant** — индексация, точки, лог; **Настройки** — модели LLM / OCR / embedding.
5. **Agent API** — 8 ролей, `GET /capabilities`, `GET /embeddings/points`.

Полный RAG «запрос-ответ», кластеризация аномалий (L5) и визуальный конструктор — **следующий этап**.
