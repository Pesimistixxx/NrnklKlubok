# Smoke Test сценарии (локальный контур)

> User guide: [`19_user_guide.md`](19_user_guide.md) · API: [`21_api_reference.md`](21_api_reference.md)

## 0) Запуск

```bash
cp .env.example .env
# Заполните YANDEX_API_KEY и YANDEX_FOLDER_ID
docker compose --project-name mkg-local up --build
```

Windows (нестандартная папка):

```powershell
$env:COMPOSE_PROJECT_NAME="mkg-local"
docker compose up --build
```

Ожидается:

| Сервис | URL |
|--------|-----|
| gateway + UI | http://localhost:8000 |
| agents | http://localhost:8010/health |
| Neo4j Browser | http://localhost:7474 |
| Qdrant | http://localhost:6333 |

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/agents-service/health
curl http://localhost:8000/api/v1/diagnostics
```

---

## 1) Ingestion + Markdown

1. UI → **Документы** → загрузить `txt` / `md` / `pdf` (режим **Полный пайплайн**).
2. Статус: `uploaded → processing → md_ready` (далее auto-extraction).
3. Вкладка **Markdown**:
   - **Без разметки** — текст (не `%PDF-1.5`);
   - **С разметкой** — `<!-- L3:TextParagraph … -->`;
   - **Скачать .md**.

API:

```bash
curl -s "http://localhost:8000/api/v1/documents/<doc_id>/markdown?variant=clean"
curl -s "http://localhost:8000/api/v1/documents/<doc_id>/markdown?variant=marked&download=1" -o marked.md
```

Retry OCR:

```bash
curl -s -X POST "http://localhost:8000/api/v1/documents/<doc_id>/reprocess"
```

---

## 2) Extraction + Neo4j

1. Дождаться `extracting → loaded`.
2. Карточка документа: `neo4j_synced=true`, `graph_nodes > 0`.
3. **Markdown → С разметкой** — узлы L1–L6.

Если авто-extraction выключен:

```bash
curl -s -X POST "http://localhost:8000/api/v1/documents/<doc_id>/submit"
```

Neo4j Browser:

```cypher
MATCH (n:Document) RETURN count(n) AS docs;
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS cnt ORDER BY cnt DESC LIMIT 15;
```

Postgres:

```sql
SELECT id, status, step, graph_nodes, neo4j_synced, processing_mode
FROM documents ORDER BY upload_date DESC LIMIT 10;
```

---

## 3) Qdrant + L4 HDBSCAN

1. UI → документ → **Qdrant** → **Индексировать**  
   или:

```bash
curl -s -X POST "http://localhost:8000/api/v1/documents/<doc_id>/index"
curl -s http://localhost:8000/api/v1/agents/embeddings/status
```

2. **HDBSCAN L4**:

```bash
curl -s -X POST "http://localhost:8000/api/v1/documents/<doc_id>/l4-cluster"
# или
curl -s -X POST "http://localhost:8000/api/v1/graph/l4/cluster" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "<doc_id>", "min_cluster_size": 3}'
```

3. Аномалии:

```bash
curl -s "http://localhost:8000/api/v1/graph/anomalies?document_id=<doc_id>&limit=20"
```

Ожидается: `l4_clustered=true`, `l4_clusters > 0`, записи с `is_anomaly` или `cluster_id=-1`.

4. Semantic search:

```bash
curl -s -X POST "http://localhost:8000/api/v1/agents/documents/<doc_id>/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "тест", "limit": 3, "mode": "semantic"}'
```

---

## 4) Чат (dual search)

```bash
curl -s -X POST "http://localhost:8000/api/v1/chat/complete" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "О чём документ?",
    "role_id": "analyst",
    "include_graph": true,
    "document_ids": ["<doc_id>"]
  }'
```

Ожидается: `reply`, `sources[]`, `trace[]`, опционально `graph`.

UI: **Чат** → вопрос → блок **Источники** → **Сохранить как MD**.

---

## 5) LangGraph agents

```bash
curl -s http://localhost:8000/api/v1/agents-service/modes

curl -s -X POST "http://localhost:8000/api/v1/agents-service/run" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Есть ли противоречия в числовых данных?",
    "mode": "audit",
    "doc_ids": ["<doc_id>"],
    "user_role": "validator"
  }'
```

Режимы для проверки: `audit`, `hypothesis`, `anomaly`.

UI: **Чат** → переключатель режима агента → trace шагов.

---

## 6) Режим answers_only

```bash
curl -s -X POST http://localhost:8000/api/v1/documents \
  -F "file=@note.txt" \
  -F "processing_mode=answers_only"
```

Ожидается: `md_ready` без `graph_nodes`; L4 cluster → 409.

---

## 7) Admin и config

```bash
curl -s http://localhost:8000/api/v1/config/models
curl -s http://localhost:8000/api/v1/agents/capabilities
# Очистка (осторожно!)
# curl -s -X POST "http://localhost:8000/api/v1/admin/clear?confirm=true"
```

---

## 8) Pipeline layers API

```bash
curl -s "http://localhost:8000/api/v1/documents/<doc_id>/pipeline/layers"
curl -s "http://localhost:8000/api/v1/graph/documents/<doc_id>"
curl -s "http://localhost:8000/api/v1/documents/<doc_id>/preview"
```

---

## Чек-лист «всё работает»

- [ ] `GET /health` → ok
- [ ] Upload → `md_ready` → `loaded`
- [ ] Markdown clean/marked скачивается
- [ ] Neo4j содержит TextParagraph и Claim
- [ ] Qdrant points > 0 после index
- [ ] L4 HDBSCAN: clusters + anomalies
- [ ] Chat complete возвращает sources
- [ ] Agents run (audit) возвращает summary + trace
- [ ] Retry-кнопки в UI перезапускают этапы
