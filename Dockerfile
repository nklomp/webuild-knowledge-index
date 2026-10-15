FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv==0.12.23
COPY pyproject.toml uv.lock ./
COPY gateway ./gateway
COPY config ./config
RUN uv sync --frozen --no-dev --no-editable
ENV PATH="/app/.venv/bin:$PATH" HF_HOME=/models
RUN mkdir /models && chown 65532:65532 /models
USER 65532:65532
EXPOSE 8000
CMD ["uvicorn","gateway.api:factory","--factory","--host","0.0.0.0","--port","8000"]
