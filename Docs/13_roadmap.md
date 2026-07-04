# Дорожная карта

## Этап 0 — Проектирование (этот коммит)
- [x] Архитектурный разбор ТЗ, фиксация ошибок и правок.
- [x] Документация в `Docs/`.
- [x] Скелет репозитория, `docker-compose`, `.env.example`.
- [x] Core: конфиг, синглтоны (Yandex LLM, Neo4j, Qdrant).
- [x] Доменные промпты в реестре.
- [x] Схема Neo4j (constraints/indexes).
- [x] Gateway: загрузка + библиотека (скелет).

## Этап 1 — Ingestion (обработка файла)
- [x] Очередь задач `arq` + Redis (ingestion/extraction запускаются асинхронно).
- [x] Vision OCR → Markdown (базовый путь для OCR-форматов подключён).
- [x] Чанкинг, очистка мусора, ремонт кодировки (`ftfy`), базовый LLM-фильтр чанков.
- [x] Экран превью (исходник / markdown / кнопка «Отправить»).
- [~] Парсеры форматов (MD/TXT/CSV/JSON/YAML/XML работают в базовом режиме как text-decode; DOCX/XLSX требуют отдельный парсер-конвертер).
- [ ] Фото → Mermaid-диаграмма (vision-агент + reduce) — запланировано, не доведено до production.
- [x] Статусы документов в Postgres (минимальный контур + fallback).

## Этап 2 — Extraction + граф
- [x] Извлечение L2/L1+L4/L6 (LLM-first JSON-first) + fallback.
- [x] L3/L5 формируются детерминированно в extraction-пайплайне.
- [x] `_bridge_text_to_layers` — межслойные связи L3 ↔ L1–L6.
- [~] map-reduce для длинных документов: базовая chunk-first стратегия есть, полноценный reduce-агрегатор ещё в доработке.
- [ ] Entity Resolution + нормализация единиц (`pint`) — в бэклоге.
- [x] Загрузчик JSON → Cypher MERGE (идемпотентно).
- [x] GUI-вывод сформированных нод/связей (`/api/v1/graph/documents/{id}`).
- [x] Agent API: layers, graph, search, embeddings index, **capabilities**, **embeddings/points**.
- [x] Qdrant: индексация TextParagraph / Claim, semantic search в UI.
- [x] UI v3: навигация Главная | Граф | Полный граф | Qdrant | Настройки; preview bar; resize graph canvas.

## Этап 3 — Достоверность и противоречия
- [~] Расчёт композитного доверия + пересчёт по событиям (конфиг в Postgres, логика — в backlog).
- [ ] Детекторы: norm_violation, value_mismatch, stage_violation → `:FOUND_ANOMALY`.
- [x] Qdrant L4: HDBSCAN → cluster_id / is_anomaly в graph + Qdrant payload — см. `22_pipeline_layers.md`.
- [ ] Связь HDBSCAN anomalies с Contradiction engine L5.
- [ ] Очередь перепроверки, KnowledgeGap.

## Этап 4 — Поиск (запрос-ответ)
- [x] Semantic search по документу (Qdrant + keyword fallback) — Agent API + UI Qdrant.
- [x] Dual search L3+L4 + graph traversal в чате (`POST /chat/complete`).
- [x] LangGraph agents service: audit, hypothesis, anomaly, review, recommend.
- [x] Объяснимые ответы: sources, trace, Save MD в UI.
- [ ] Гибридный retrieval с фильтром грифов и полным confidence в ответе.

## Этап 5 — Визуализация и доступ
- [~] UI графа: vis-network компактный/полный, resize, preview bar (v3).
- [ ] Визуальный конструктор графа.
- [ ] RBAC UI, аудит, дашборды сравнения технологий (L6).

## Принятые решения
- Очередь задач: **arq** (async-native, Redis-брокер). Реализован worker `arq app.main.WorkerSettings`.
- Кластеризация L4: **HDBSCAN** (GLOSH outlier score) — реализовано в `mkg_core.l4_clustering`, API `/graph/l4/cluster`.
- LLM: **Yandex Responses API** (OpenAI-совместимый) с полным набором параметров.
- Локальный контур по умолчанию: `neo4j + qdrant + postgres + redis` внутри `docker-compose`.
- Rule-based fallback extraction не использует доменные хардкоды: Process/Material словарь читается из Neo4j (`name_ru`, `name_en`, `aliases`), при недоступности Neo4j остаются только generic-эвристики.
- Конфигурация модели достоверности (`confidence_weights`, `source_reliability_config`) хранится в Postgres и загружается runtime с безопасным fallback.
