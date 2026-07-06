FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY packages/shared /app/packages/shared
COPY packages/database /app/packages/database
COPY packages/storage /app/packages/storage
COPY packages/events /app/packages/events
COPY services/workflow-engine /app/services/workflow-engine

RUN pip install --no-cache-dir \
    -e /app/packages/shared \
    -e /app/packages/database \
    -e /app/packages/storage \
    -e /app/packages/events[postgres] \
    fastapi uvicorn[standard] celery[redis] redis httpx psycopg2-binary \
    opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc opentelemetry-instrumentation-fastapi opentelemetry-instrumentation-httpx

ENV PYTHONPATH=/app/services/workflow-engine/src:/app/packages/shared/src:/app/packages/database/src:/app/packages/storage/src:/app/packages/events/src

EXPOSE 8001
CMD ["uvicorn", "contentos_workflow.main:app", "--host", "0.0.0.0", "--port", "8001"]
