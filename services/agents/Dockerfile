FROM python:3.11-slim

WORKDIR /app

COPY packages/core ./packages/core
RUN pip install --no-cache-dir ./packages/core

COPY services/agents/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/agents/app ./app

ENV PYTHONPATH=/app/packages/core/src:/app
EXPOSE 8010

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
