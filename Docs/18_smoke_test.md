# Smoke Test сценарии (локальный контур)

## 0) Запуск

```bash
cp .env.example .env
docker compose --project-name mkg-local up --build
```

Если запуск идёт из папки с нестандартным именем или вне git-репозитория, используйте явный fallback:

```powershell
$env:COMPOSE_PROJECT_NAME="mkg-local"
docker compose up --build
```

Ожидается:
- `gateway` доступен на `http://localhost:8000`
- Neo4j Browser на `http://localhost:7474`
- Qdrant на `http://localhost:6333`

## 1) Ingestion проверка

1. Открыть UI `http://localhost:8000`.
2. Загрузить `txt/md/pdf` файл.
3. Проверить статус в библиотеке:
   - `uploaded -> processing -> md_ready`.
4. Открыть документ:
   - в превью есть `source_text`,
   - справа есть `markdown`.

## 2) Extraction + Neo4j проверка

1. Нажать кнопку **Отправить в extraction**.
2. Проверить статус:
   - `extracting -> loaded`.
3. В карточке/таблице проверить:
   - `neo4j_synced=true`,
   - `graph_nodes > 0`,
   - `graph_relationships > 0`.

## 3) Проверка в Neo4j

В Neo4j Browser:

```cypher
MATCH (n:Document) RETURN count(n) AS docs;
MATCH (n) RETURN labels(n) AS label, count(*) AS cnt ORDER BY cnt DESC;
MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS cnt ORDER BY cnt DESC;
```

Ожидается:
- есть `Document`,
- есть `TextParagraph` и другие слои,
- есть связи (`HAS_PARAGRAPH`, `STRUCTURING`, `CONTEXT_FOR`, и др.).

## 4) Postgres статусы

```sql
SELECT id, status, step, graph_nodes, graph_relationships, neo4j_synced
FROM documents
ORDER BY upload_date DESC
LIMIT 20;
```

Ожидается:
- строки документов присутствуют,
- `status` и `step` обновляются по ходу пайплайна.

## 5) API smoke

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/documents
curl http://localhost:8000/api/v1/graph/documents/<doc_id>
curl http://localhost:8000/api/v1/agents/embeddings/status
```

## 6) Qdrant / semantic search

1. Постройте граф документа.
2. Откройте **Документ → L3 / Qdrant** → **Индексировать документ**.
3. Вкладка **Поиск** — введите запрос; ожидаются hits с `mode: semantic`.

```bash
curl -s -X POST "http://localhost:8000/api/v1/agents/documents/<doc_id>/embeddings/index"
curl -s -X POST "http://localhost:8000/api/v1/agents/documents/<doc_id>/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "тест", "limit": 3}'
```
