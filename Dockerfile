FROM python:3.12-slim AS backend

WORKDIR /app
COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY examples ./examples
RUN pip install --no-cache-dir -e ".[all]"
RUN addgroup --system adg && adduser --system --ingroup adg --home /app adg \
    && mkdir -p /app/data \
    && chown -R adg:adg /app

ENV ADG_CONTROL_PLANE_DATABASE_URL=sqlite:///./data/adg-control-plane.db
EXPOSE 8000
USER adg
CMD ["uvicorn", "adg.app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
