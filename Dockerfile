FROM python:3.12-slim

WORKDIR /app

RUN useradd --create-home --uid 10001 app

COPY pyproject.toml README.md LICENSE ./
COPY ingest ./ingest
COPY api ./api
COPY mcp ./mcp

RUN pip install --no-cache-dir . \
    && chown -R app:app /app

USER app

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
