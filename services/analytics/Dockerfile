FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ && rm -rf /var/lib/apt/lists/*

COPY packages/core ./packages/core
RUN pip install --no-cache-dir ./packages/core

COPY services/analytics/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/analytics/app ./app

ENV PYTHONPATH=/app/packages/core/src:/app

RUN python -c "from mkg_core.embeddings import embedding_status, list_indexed_points"

CMD ["python", "-m", "app.main"]
