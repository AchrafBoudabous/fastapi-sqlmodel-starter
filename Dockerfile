# ─── Stage 1: dependency builder ──────────────────────────────────────────────
# Installs all packages into an isolated venv.  The source is NOT baked here —
# keeping it separate gives us a cached dep layer that only rebuilds when
# pyproject.toml changes, not every time app/ code changes.
FROM python:3.11-slim AS builder

WORKDIR /build

# C extensions (asyncpg, bcrypt/cffi, cryptography) require a compiler.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./

# Stub the app package so pip can resolve metadata without the real source.
# The stub is never shipped to the runtime image.
RUN mkdir app && touch app/__init__.py

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip --no-cache-dir && \
    /opt/venv/bin/pip install --no-cache-dir .


# ─── Stage 2: runtime image ───────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Non-root user — defence-in-depth against container escapes.
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup --no-create-home appuser

# Compiled dependencies from the builder stage.
COPY --from=builder /opt/venv /opt/venv

# Application source (separate COPY so this layer only rebuilds on code changes).
COPY app/      ./app/
COPY alembic/  ./alembic/
COPY alembic.ini ./

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
