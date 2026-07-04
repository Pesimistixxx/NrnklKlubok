FROM python:3.11-slim
WORKDIR /app

COPY packages/core ./packages/core
COPY packages/ingestion ./packages/ingestion
COPY packages/extraction ./packages/extraction
COPY packages/graph ./packages/graph
COPY packages/prompts ./packages/prompts
RUN pip install --no-cache-dir ./packages/core ./packages/ingestion ./packages/extraction ./packages/prompts

COPY services/worker/app ./app
ENV PYTHONPATH=/app
CMD ["arq", "app.main.WorkerSettings"]
