FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install the reviewed dependency set before copying frequently changed app files.
COPY server/requirements.lock ./requirements.lock
RUN python -m pip install -r requirements.lock
COPY server/pyproject.toml ./pyproject.toml
COPY server/studio ./studio
RUN python -m pip install --no-deps . \
    && groupadd --gid 10001 studio \
    && useradd --uid 10001 --gid studio --no-create-home --shell /usr/sbin/nologin studio

COPY server/alembic.ini ./alembic.ini
COPY server/alembic ./alembic
COPY server/templates ./templates
COPY server/static ./static
COPY deploy/healthcheck.py ./healthcheck.py

USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "/app/healthcheck.py"]

# OAuth callbacks contain short-lived codes: do not record query strings in logs.
CMD ["uvicorn", "studio.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers"]
