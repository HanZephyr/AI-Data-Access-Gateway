FROM python:3.12-slim AS backend

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY examples ./examples
RUN pip install --no-cache-dir -e .

ENV ADG_CONTROL_PLANE_DATABASE_URL=sqlite:///./data/adg-control-plane.db
EXPOSE 8000
CMD ["uvicorn", "adg.app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
