FROM python:3.11-slim



WORKDIR /app



COPY packages/core ./packages/core

COPY packages/ingestion ./packages/ingestion

COPY packages/prompts ./packages/prompts

RUN pip install --no-cache-dir ./packages/core ./packages/ingestion ./packages/prompts



COPY services/gateway/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt



COPY services/gateway/app ./app



ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

