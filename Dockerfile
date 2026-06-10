FROM python:3.12-slim AS backend

ARG PYPI_INDEX_URL=https://pypi.org/simple

WORKDIR /app
COPY pyproject.toml uv.lock README.md alembic.ini ./
COPY src ./src
COPY examples ./examples
RUN pip install --no-cache-dir --index-url "${PYPI_INDEX_URL}" uv \
    && uv sync --frozen --no-dev --extra all --default-index "${PYPI_INDEX_URL}"
RUN addgroup --system adg && adduser --system --ingroup adg --home /app adg \
    && mkdir -p /app/data \
    && chown -R adg:adg /app

ENV ADG_CONTROL_PLANE_DATABASE_URL=sqlite:///./data/adg-control-plane.db
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
USER adg
CMD ["uvicorn", "adg.app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
