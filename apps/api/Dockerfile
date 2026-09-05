FROM python:3.14-slim@sha256:cad9a2c871761c413caa6fdd6441c783451e740a48aaeba60ae62a8b53525ef6 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PORT=8000

WORKDIR /app
COPY requirements.lock ./
RUN python -m pip install --no-cache-dir --upgrade pip && python -m pip install --no-cache-dir -r requirements.lock
COPY alembic ./alembic
COPY alembic.ini ./
COPY src ./src

EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn rt_connect_api.main:app --host 0.0.0.0 --port \"${PORT:-8000}\""]
