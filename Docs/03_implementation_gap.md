# Соответствие целевой графовой модели и MVP

Сравнение **исходной архитектуры** (6 слоёв, связи, ТЗ) с текущей реализацией в репозитории MKG.

---

## Слои L1–L6: узлы

| Слой | Целевые узлы | Реализовано | Не реализовано / частично |
|------|--------------|-------------|---------------------------|
| **L1** | Material, Process, Equipment, ChemicalReagent, StandardMetric, PhaseState, Property | Material, Process, Equipment, ChemicalReagent, StandardMetric (LLM + fallback из Neo4j) | PhaseState, Property как отдельные узлы |
| **L2** | Document, Expert, Organization, Location, Event, Timeline, Facility | Document, Expert, Organization, Location, Timeline (частично Event, Facility) | Event, Facility — редко извлекаются |
| **L3** | TextParagraph, TableMatrix, HeadingContext, LangContext, SynonymMap | TextParagraph, HeadingContext, LangContext (детерминированно из MD) | TableMatrix, SynonymMap, поле `embedding` в Neo4j (векторы только в Qdrant) |
| **L4** | ExperimentRun, TechStage, Measurement, Deviation, TrendVector, Formula, EnvironmentalCondition, Effect | ExperimentRun, TechStage, Measurement, Claim, Effect, Formula (LLM) | Deviation, TrendVector, EnvironmentalCondition; версионирование Measurement (`PREVIOUS_VERSION`) |
| **L5** | VerificationStatus, SecurityRole, Contradiction, AuditTrail, KnowledgeGap | SecurityRole, VerificationStatus (базово) | Contradiction engine, AuditTrail, KnowledgeGap, жизненный цикл противоречий |
| **L6** | TechnologySolution, EconomicIndicator, EnvironmentalIndicator | TechnologySolution, EconomicIndicator, EnvironmentalIndicator (LLM) | Связи `:COMPARABLE_TO`, `:REGION`, `:YEAR_CALC` — не все |

---

## Связи: ключевые цепочки ТЗ

| Цепочка | Целевая модель | MVP |
|---------|----------------|-----|
| Документ → текст | `:HAS_PARAGRAPH`, `:HAS_TABLE`, `:HAS_HEADER` | ✅ HAS_PARAGRAPH, HAS_HEADER; ⬜ HAS_TABLE |
| Текст → факт | `:CONTEXT_FOR`, `:DATA_SOURCE_FOR` + confidence | ✅ через `_bridge_text_to_layers` |
| Стадия → материал | `:USES_MAT` с атрибутом `stage` | ⬜ частично в промпте, не валидируется жёстко |
| Измерение → норма → противоречие | `:EVALUATED_AGAINST` → `:FOUND_ANOMALY` | ⬜ не автоматизировано |
| Противоречие → эксперт | `:RESOLVED_BY` | ⬜ |
| L6 сравнение | `:COMPARABLE_TO`, экономика/экология | ⬜ частично узлы без полного набора связей |

**Межслойный bridge (добавлен в MVP):** `DATA_SOURCE_FOR`, `CONTEXT_FOR`, `ABOUT` — TextParagraph ↔ L1/L2/L4/L5/L6.

---

## Инфраструктура и агенты (ТЗ §5)

| Компонент ТЗ | Статус |
|--------------|--------|
| Ingestion (OCR, MD, чанки) | ✅ worker + `mkg_ingestion` |
| Extraction (NER, 6 слоёв) | ✅ `mkg_extraction` |
| Graph Fusion / Neo4j load | ✅ `loader.py` MERGE |
| Validation (противоречия, confidence) | ⬜ `analytics` — скелет |
| Retrieval (гибридный поиск) | ✅ Agent API + Qdrant semantic; ⬜ полный RAG-орchestrator |
| Synthesis (отчёты) | ⬜ |
| Security / Audit | ⬜ RBAC UI |
| Notification | ⬜ |

---

## Достоверность (боль заказчика)

**Цель:** композитная модель confidence на связях L3→L4, L4-узлах, Contradiction с пересчётом.

**Сейчас:**

- Поля `confidence` в промптах extraction для части L4-узлов.
- Конфиг весов в Postgres (`confidence_weights`) — загрузка в `analytics`.
- Нет автоматического детектора `:FOUND_ANOMALY` и пересчёта по событиям.

---

## Qdrant и кластеризация

| Функция | Статус |
|---------|--------|
| Индексация L3/L4 в Qdrant | ✅ |
| Semantic search по документу | ✅ Agent API + UI «Поиск» |
| HDBSCAN / аномалии → Neo4j | ⬜ см. [`15_l3_qdrant_clustering.md`](15_l3_qdrant_clustering.md) |

---

## UI vs ТЗ

| Требование ТЗ | MVP |
|---------------|-----|
| Загрузка + библиотека | ✅ Главная + sidebar |
| Превью MD + «отправить» | ✅ «Построить граф» |
| GUI графа | ✅ vis-network, фильтры слоёв, межсл. связи |
| Запрос на естественном языке | ✅ вкладка «Поиск» (semantic + keyword) |
| Визуальный конструктор | ⬜ |
| RBAC | ⬜ |

---

## Что делать дальше (приоритет)

1. **Contradiction + `:EVALUATED_AGAINST`** — analytics, замыкание цепочки L4→L5.
2. **TableMatrix + SynonymMap** — расширение L3/L1.
3. **Entity resolution + pint** — нормализация единиц.
4. **HDBSCAN по low-confidence** — ответ на открытый вопрос кластеризации.
5. **RAG synthesis** — мульти-агентный ответ с цитатами и confidence.
