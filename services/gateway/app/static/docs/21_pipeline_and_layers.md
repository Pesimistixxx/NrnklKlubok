# Пайплайн документов и слои L1–L6

> L3 = семантический поиск (Qdrant). L4 = HDBSCAN-кластеры и аномалии.

UI cache: `?v=95` (при странном поведении — **Ctrl+F5**).

## Полный пайплайн (`processing_mode=full`)

```
Upload → OCR → Markdown (clean + marked) → Extraction L1–L6 → Graph JSON
  → Neo4j MERGE → Qdrant (mkg_chunks + mkg_claims) → L4 HDBSCAN
```

## Лёгкий путь (`processing_mode=answers_only`)

```
Upload → OCR → Markdown → Qdrant (только mkg_chunks из MD)
```

- **Upgrade в full:** `POST /api/v1/documents/{id}/reprocess-full` или кнопка «↺ Построить полный граф».

## Граф «Все документы»

Пункт **«Все документы»** → объединённый vis-network корпуса; расширенные фильтры, **Сравнение** Process/Material.

## Qdrant — корпус

- Статистика **N / M документов**; поиск по корпусу без обязательного `document_id`.
- Карта L4-кластеров: **клик по кластеру** → панель состава.

## Шесть слоёв L1–L6

| Слой | Содержание |
|------|------------|
| L1 | Материалы, процессы, оборудование |
| L2 | Стадии, условия, контекст |
| L3 | TextParagraph, HeadingContext |
| L4 | Claim, Measurement, ExperimentRun |
| L5 | Verification, AuditTrail |
| L6 | Document, Author, ТЭП |

## Dual search в чате

Qdrant L3+L4 → graph traversal → LLM. См. **Чат, роли и AI-агенты**.

## Фильтрация

См. **Функциональные фильтры** — граф и Qdrant chip-фильтры.
