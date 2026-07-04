# MKG — Единая карта знаний R&D (горно-металлургия)

Платформа на Neo4j + Qdrant + Postgres + Yandex AI Studio: загрузка документов,
OCR → Markdown → извлечение сущностей в граф, объяснимая достоверность и RAG.

## Документация


| Файл                                                                 | Содержание                                      |
| -------------------------------------------------------------------- | ----------------------------------------------- |
| [Docs/00_overview.md](./Docs/00_overview.md)                         | Зачем система, карта документов, где что в коде |
| [Docs/02_architecture.md](./Docs/02_architecture.md)                 | Архитектура и сервисы                           |
| [Docs/03_implementation_gap.md](./Docs/03_implementation_gap.md)     | Целевая модель L1–L6 vs MVP                     |
| [Docs/13_roadmap.md](./Docs/13_roadmap.md)                           | Этапы: что сделано / в работе                   |
| [Docs/15_l3_qdrant_clustering.md](./Docs/15_l3_qdrant_clustering.md) | L3, Qdrant, кластеризация, аномалии             |
| [Docs/18_smoke_test.md](./Docs/18_smoke_test.md)                     | Запуск docker compose и проверка                |
| [Docs/19_user_guide.md](./Docs/19_user_guide.md)                     | UI v3 (Главная, Граф, Qdrant…)                  |
| [Docs/20_project_status.md](./Docs/20_project_status.md)             | Текущий этап MVP-2                              |
| [Docs/14_agent_api.md](./Docs/14_agent_api.md)                       | Agent REST API (+ capabilities, Qdrant points)  |


## Структура репозитория (по файлам)

```
Docs/                          # 4 основных md-файла
infra/postgres/init.sql        # схема Postgres: documents, confidence_*
packages/
  core/src/mkg_core/
    config.py                  # Settings из .env
    llm.py                     # YandexLLMClient (Responses API, vision, embed)
    meta_db.py                 # Postgres: статусы документов
    queue.py                   # arq enqueue → Redis
    store.py                   # локальное хранилище source/md/graph
  ingestion/src/mkg_ingestion/
    formats.py                 # реестр форматов + validate_upload
    ocr.py                     # Yandex OCR sync/async + PyMuPDF fallback
    parsers.py                 # DOCX, XLSX, CSV, JSON, YAML, XML, text
    pipeline.py                # orchestrator → markdown
  extraction/src/mkg_extraction/
    extractor.py               # LLM extraction L1–L6 → graph payload
    loader.py                  # MERGE в Neo4j (schema.cypher)
  graph/
    schema.cypher              # онтология 6 слоёв
    init_schema.py             # ручное применение схемы
  prompts/                     # mkg_prompts — реестр промптов
    catalog/                   # ingestion/, extraction/ по этапам пайплайна
services/
  gateway/app/main.py          # REST API + UI, upload → очередь
  gateway/app/static/index.html
  worker/app/tasks.py          # run_ingestion, run_extraction (arq)
  worker/app/main.# WorkerSettings
  analytics/app/confidence.py  # веса достоверности из Postgres
docker-compose.yml             # name: mkg-local, neo4j/postgres/redis/qdrant/...
.env.example
```

## Архитектура: цель vs текущее состояние

### Целевая (полная) архитектура

```
UI (gateway) → upload → Redis/arq worker
                ↓
         ingestion: OCR → markdown → Qdrant chunks
                ↓
         extraction: LLM L1–L6 → entity resolve → Neo4j MERGE
                ↓
         analytics: confidence, contradictions, HDBSCAN anomalies
                ↓
         RAG: semantic search + answer synthesis
```

Хранилища: **Neo4j** (граф знаний), **Qdrant** (векторы), **Postgres** (метаданные, конфиг),
**Redis** (очередь), **локальный storage** (артефакты пайплайна).

### Что реализовано сейчас


| Компонент                                               | Статус                                     |
| ------------------------------------------------------- | ------------------------------------------ |
| Upload + validation                                     | ✅ все форматы, лимит 50 МБ, batch          |
| Парсеры DOCX/XLSX/CSV/JSON/YAML/XML                     | ✅                                          |
| arq worker (ingestion/extraction)                       | ✅                                          |
| Yandex OCR (sync + async PDF)                           | ✅ многостраничные PDF через async          |
| PyMuPDF fallback                                        | ✅ если OCR недоступен                      |
| Markdown + chunk filter                                 | ✅ базово                                   |
| LLM extraction → graph payload                          | ✅ L2/L1/L4/L6 LLM, L3/L5 детерминированно  |
| Neo4j load (MERGE)                                      | ✅                                          |
| Postgres document status                                | ✅                                          |
| Confidence config в Postgres                            | ✅ загрузка в analytics                     |
| Qdrant indexing + semantic search                       | ✅ Agent API + UI «Qdrant» + preview search |
| UI v4 (Граф / Полный граф / Qdrant / настройки моделей) | ✅ static `?v=4`                            |
| Межсл. связи L3 bridge                                  | ✅ `_bridge_text_to_layers`                 |
| Entity resolution + pint                                | ⬜                                          |
| Contradictions / HDBSCAN                                | ⬜ см. Docs/15, 03                          |
| RAG answer synthesis                                    | ⬜                                          |
| RBAC / визуальный конструктор графа                     | ⬜                                          |


### API загрузки


| Метод | Путь                               | Описание                        |
| ----- | ---------------------------------- | ------------------------------- |
| GET   | `/api/v1/formats`                  | Список форматов и лимит размера |
| POST  | `/api/v1/documents`                | Один файл (multipart `file`)    |
| POST  | `/api/v1/documents/batch`          | Несколько файлов (`files[]`)    |
| POST  | `/api/v1/documents/{id}/reprocess` | Повторный ingestion             |
| POST  | `/api/v1/documents/{id}/submit`    | Запуск extraction → Neo4j       |


Поддерживаемые расширения: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, `.tiff`, `.md`, `.txt`, `.csv`, `.json`, `.yaml`, `.yml`, `.xml`, `.docx`, `.xlsx`.

### Поток обработки одного файла

1. **gateway** `POST /api/v1/documents` — сохраняет source, ставит `run_ingestion` в Redis.
2. **worker** `run_ingestion` — `mkg_ingestion.process()`:
  - PDF → `ocr.py` (async OCR для >1 стр., иначе sync; fallback PyMuPDF);
  - chunking, junk-filter, сборка `.md`.
3. UI показывает Markdown (не сырой `%PDF-1.5`).
4. Кнопка «В граф» → `run_extraction`:
  - `extract_from_markdown()` → JSON graph;
  - `load_graph()` → Neo4j.

## Стек

Python 3.11 · FastAPI · Neo4j · Qdrant · Postgres · Redis · arq · YandexGPT 5.x · Vision OCR · PyMuPDF

## Быстрый старт

```bash
cp .env.example .env   # YANDEX_API_KEY + YANDEX_FOLDER_ID для LLM и OCR
docker compose --project-name mkg-local up --build
# UI: http://localhost:8000
```

Локально без Docker:

```bash
pip install -e packages/core -e packages/ingestion -e packages/extraction
pip install -r services/gateway/requirements.txt
uvicorn app.main:app --app-dir services/gateway --reload
cd services/worker && arq app.main.WorkerSettings
```

Проверка OCR/PDF: загрузите многостраничный PDF — статус должен стать `md_ready`, в блоке «Результат» появится текст, не бинарник.

Схема Neo4j применяется автоматически при первой загрузке. Вручную:

```bash
python packages/graph/init_schema.py
```

