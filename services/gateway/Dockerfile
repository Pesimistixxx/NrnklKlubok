FROM python:3.11-slim

WORKDIR /app

COPY packages/core ./packages/core
COPY packages/ingestion ./packages/ingestion
COPY packages/prompts ./packages/prompts
COPY packages/extraction ./packages/extraction

RUN pip install --no-cache-dir ./packages/core ./packages/ingestion ./packages/prompts ./packages/extraction

COPY services/gateway/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/gateway/app ./app
COPY Docs ./Docs

# Исходники monorepo важнее site-packages — иначе pip-кэш и agent_api расходятся.
ENV PYTHONPATH=/app/packages/core/src:/app/packages/ingestion/src:/app/packages/prompts/src:/app/packages/extraction/src:/app

RUN python -c "\
from mkg_core.comparison import merge_repo_comparison, run_comparison_analysis; \
from mkg_core.embeddings import compute_embedding_viz, embedding_status, index_document_graph, list_indexed_points, reindex_corpus, reindex_corpus_entities, search_document, search_entities, search_global; \
from mkg_extraction.loader import load_graph; \
from mkg_core.document_extraction import run_document_extraction; \
from app.main import app; \
import numpy; \
print('gateway import ok:', app.title)"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
