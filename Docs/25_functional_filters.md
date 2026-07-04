# Функциональные требования — фильтрация

> UI cache: `?v=95` (при странном поведении — **Ctrl+F5**).

Соответствие требованиям импорта/нормализации данных и реализации в MKG.

## Импорт и нормализация (источник требований)

| Требование | Реализация в MKG |
|------------|------------------|
| Типы документов: статьи RU/EN, отчёты, патенты, справочники | Heuristic `inferDocCategory()` по имени файла и метаданным; фильтр «Тип документа» на графе и Qdrant |
| NLP: Materials, Processes, Parameters | Фильтры «Материал» / «Процесс» + диапазон Measurement (конц., temp, flow) |
| Relations: method→material, experiment→effect, author→field | Multi-select типов связей: `USES_MAT`, `SHOWED_EFFECT`, `AUTHORED` (EXPERT_IN) и др. |
| Numeric constraints (sulfates ≤ 300 mg/l) | min/max по `Measurement.numeric_value` + поле параметра |
| Synonyms (электроэкстракция/electrowinning, ПВП/fluidized bed) | `aliases[]` на узлах + `SYNONYM_PAIRS` в клиентском поиске |

## Фильтры графа (Документы → Граф, все документы)

Панель **Расширенные фильтры** в тулбаре графа (`app.js` → `applyAdvancedGraphFilters`).

| Фильтр | Поле состояния | Поведение |
|--------|----------------|-----------|
| Тип документа | `docCategories[]` | patent / article / report / handbook — по `Document` и `source_doc_id` |
| Тип связи | `relationTypes[]` | Multi-select: USES_MAT, SHOWED_EFFECT, AUTHORED, … — скрывает прочие рёбра |
| Параметр (число) | `numericMin`, `numericMax`, `numericParam` | Узлы `Measurement` в диапазоне |
| Язык | `language` | RU / EN / both — `LangContext`, `props.lang`, эвристика текста |
| Материал / процесс | `materialKeyword`, `processKeyword` | Поиск по имени + `aliases[]` + `SYNONYM_PAIRS` |
| География | `geographyNodes[]` | Multi-select Location-узлов корпуса |
| Практика | `practiceFilter` | `domestic` (RU) / `foreign` — по `Location.country` |
| Тип сущности | `entityTypes[]` | Фильтр по label узла |
| Год публикации | `yearMin`, `yearMax` | `Document.publication_year` |
| Достоверность | `minConfidence` | `extraction_confidence` на узлах |
| Противоречия / пробелы | `showContradictions`, `showGaps` | Узлы `Contradiction`, `KnowledgeGap` |

Состояние сохраняется в `sessionStorage` (`mkg_graph_adv_filters`).

## Qdrant — пост-фильтры поиска

Вкладка **Qdrant** → строка chip-фильтров под полем поиска.

| Chip | Эффект |
|------|--------|
| Патент / Статья / Отчёт / Справочник | `inferDocCategory()` по `document_id` hit |
| L3 / L4 | `hit.layer` |
| ≥50% / ≥70% / ≥85% | `hit.score` (min confidence) |

Фильтрация клиентская после `POST /api/v1/agents/search`.

## Chat retrieval (roadmap)

MVP: facet-фильтры из пресета графа **не** передаются в `search_chat_retrieval` автоматически.

Планируется:
- «Закрепить фильтры» → передача `document_ids`, `layers`, `min_score` в `POST /api/v1/chat/complete`
- Синхронизация chip-пресетов Qdrant с быстрым режимом чата

## Связанные файлы

| Файл | Изменения |
|------|-----------|
| `services/gateway/app/static/index.html` | UI фильтров, Qdrant chips |
| `services/gateway/app/static/js/app.js` | Логика фильтрации |
| `services/gateway/app/static/css/app.css` | Chips, param range |
| `Docs/21_pipeline_and_layers.md` | Ссылка на dual search + фильтры |

См. также: [`21_pipeline_and_layers.md`](21_pipeline_and_layers.md), [`22_chat_agents.md`](22_chat_agents.md).
