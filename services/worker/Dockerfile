FROM python:3.11-slim
WORKDIR /app

COPY packages/core ./packages/core
COPY packages/ingestion ./packages/ingestion
COPY packages/extraction ./packages/extraction
COPY packages/prompts ./packages/prompts
RUN pip install --no-cache-dir ./packages/core ./packages/ingestion ./packages/extraction ./packages/prompts

COPY services/worker/app ./app

ENV PYTHONPATH=/app/packages/core/src:/app/packages/ingestion/src:/app/packages/extraction/src:/app/packages/prompts/src:/app

RUN python -c "from mkg_core.embeddings import embedding_status, list_indexed_points, search_global, reindex_corpus"

CMD ["arq", "app.main.WorkerSettings"]
