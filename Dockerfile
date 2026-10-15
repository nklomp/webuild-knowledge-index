# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base
WORKDIR /app
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install --no-cache-dir uv==0.12.23
COPY pyproject.toml uv.lock ./
COPY gateway ./gateway
COPY config ./config
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export SSL_CERT_FILE=/run/secrets/proxy_ca; fi; \
    uv sync --frozen --no-dev --no-editable
ENV PATH="/app/.venv/bin:$PATH" HF_HOME=/models
RUN chmod -R a+rX /app/gateway /app/config && \
    groupadd --gid 65532 gateway && \
    useradd --uid 65532 --gid 65532 --create-home --shell /usr/sbin/nologin gateway && \
    mkdir /models && chown 65532:65532 /models
USER 65532:65532
EXPOSE 8000
CMD ["uvicorn","gateway.api:factory","--factory","--host","0.0.0.0","--port","8000"]

FROM base AS ingestion
USER root
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export SSL_CERT_FILE=/run/secrets/proxy_ca; fi; \
    apt-get update && apt-get install -y --no-install-recommends git ca-certificates && \
    rm -rf /var/lib/apt/lists/*
COPY scripts ./scripts
COPY sql ./sql
RUN chmod -R a+rX /app/scripts /app/sql && \
    mkdir /app/artifacts /app/site && chown 65532:65532 /app/artifacts /app/site
USER 65532:65532
CMD ["python","-m","gateway.cli","run"]

FROM base AS retrieval
