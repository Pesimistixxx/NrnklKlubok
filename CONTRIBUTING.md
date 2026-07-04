# Руководство для участников

Спасибо за интерес к **MKG** — платформе карты знаний (Neo4j, Qdrant, LangGraph) для R&D-документов.

## Что можно улучшить

- пайплайн ingestion / extraction (L1–L6);
- gateway API, UI, чат и агенты;
- документацию в [`Docs/`](./Docs/).

Перед крупными изменениями загляните в [`Docs/13_roadmap.md`](./Docs/13_roadmap.md) и [`Docs/03_implementation_gap.md`](./Docs/03_implementation_gap.md).

## Локальная разработка

### 1. Клонирование

```bash
git clone https://github.com/Pesimistixxx/NrnklKlubok.git
cd NrnklKlubok
```

### 2. Переменные окружения

```bash
cp .env.example .env
```

Обязательно заполните `YANDEX_API_KEY` и `YANDEX_FOLDER_ID`. Остальные значения по умолчанию подходят для Docker Compose.

### 3. Запуск через Docker Compose

```bash
docker compose --project-name mkg-local up --build
```

| Сервис | URL |
|--------|-----|
| UI + gateway | http://localhost:8000 |
| Agents | http://localhost:8010/health |
| Neo4j Browser | http://localhost:7474 |

Подробнее: [`Docs/18_smoke_test.md`](./Docs/18_smoke_test.md).

### 4. Локально без Docker (опционально)

```bash
pip install -e packages/core -e packages/ingestion -e packages/extraction
pip install -r services/gateway/requirements.txt
uvicorn app.main:app --app-dir services/gateway --reload
```

Worker и agents — см. [`README.md`](./README.md).

## Проверка изменений

Автотестов в репозитории пока нет. Перед PR пройдите smoke-сценарии:

1. `curl http://localhost:8000/health` — gateway жив.
2. Загрузка документа через UI или `POST /api/v1/documents`.
3. При изменениях чата/агентов — запрос в `/api/v1/chat/complete` или agents API.

Чеклист: [`Docs/18_smoke_test.md`](./Docs/18_smoke_test.md).

## Процесс Pull Request

1. Создайте ветку от `master`: `feature/…`, `fix/…`, `docs/…`.
2. Делайте небольшие, сфокусированные коммиты.
3. Обновите документацию в `Docs/`, если меняется API или поведение пайплайна.
4. Откройте PR с описанием **что** и **зачем** (шаблон подставится автоматически).
5. Дождитесь ревью maintainer'а.

## Стиль кода

- Python 3.11, существующие паттерны в `packages/` и `services/`.
- Минимальный diff: не рефакторите несвязанный код в том же PR.
- Комментарии — только для неочевидной бизнес-логики.

## Документация

| Раздел | Файл |
|--------|------|
| Обзор | [`Docs/00_overview.md`](./Docs/00_overview.md) |
| Соответствие ТЗ | [`Docs/01_tz_compliance.md`](./Docs/01_tz_compliance.md) |
| Архитектура | [`Docs/02_architecture.md`](./Docs/02_architecture.md) |
| Пайплайн L1–L6 | [`Docs/21_pipeline_and_layers.md`](./Docs/21_pipeline_and_layers.md) |
| API | [`Docs/21_api_reference.md`](./Docs/21_api_reference.md) |

## Вопросы и баги

- **Баг** — issue с шаблоном *Bug report*.
- **Идея** — issue с шаблоном *Feature request*.
- **Уязвимость** — см. [`SECURITY.md`](./SECURITY.md), не публикуйте детали публично.

## Кодекс поведения

Участвуя в проекте, вы соглашаетесь с [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md).
