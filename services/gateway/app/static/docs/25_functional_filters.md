# Функциональные требования — фильтрация

> UI cache: `?v=95` (при странном поведении — **Ctrl+F5**).

Полная версия: `Docs/25_functional_filters.md`.

## Граф — расширенные фильтры

Тип документа, тип связи, язык, география, практика RU/foreign, Measurement min/max, material/process + синонимы, entity type, год, confidence, Contradiction/KnowledgeGap.

Состояние: `sessionStorage` (`mkg_graph_adv_filters`). Работает на графе документа и **«Все документы»**.

## Qdrant — chip-фильтры

После corpus search: патент/статья/отчёт/справочник, L3/L4, min score ≥50/70/85%.

## Roadmap

Передача facet-пресетов в `POST /chat/complete`.
