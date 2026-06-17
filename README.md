# FastAPI SQLModel Starter

A production-ready, batteries-included template for building REST APIs with
**FastAPI**, **SQLModel**, and **PostgreSQL**. Clone it, rename the models, and
ship — everything from JWT auth to GitHub Actions CI is already wired up.

[![CI](https://github.com/AchrafBoudabous/fastapi-sqlmodel-starter/actions/workflows/ci.yml/badge.svg)](https://github.com/AchrafBoudabous/fastapi-sqlmodel-starter/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

---

## What's included

| Layer | Choice | Why |
|---|---|---|
| API framework | FastAPI 0.111+ | async-native, automatic OpenAPI docs, excellent DX |
| ORM / schema | SQLModel | one model definition for both DB table and Pydantic validation |
| Settings | pydantic-settings | `.env` file support with full type validation at startup |
| Database | PostgreSQL (asyncpg) | production target; SQLite (aiosqlite) in tests |
| Migrations | Alembic | async-capable env, sequential numbered migrations |
| Auth | JWT (python-jose) + bcrypt (passlib) | stateless access + refresh tokens, role field on User |
| Testing | pytest-asyncio + httpx | full async test suite, no live DB required |
| Containers | Docker (multi-stage) + docker-compose | slim runtime image, Postgres service, hot-reload in dev |
| CI | GitHub Actions | lint → type-check → test running in parallel |
| Code quality | ruff + pre-commit | format + lint in one tool, enforced before every commit |

---

## Project structure

```
fastapi-sqlmodel-starter/
├── app/
│   ├── main.py              # FastAPI app, middleware, router registration
│   ├── core/
│   │   ├── config.py        # Settings (pydantic-settings, reads .env)
│   │   ├── deps.py          # get_current_user, CurrentUser, require_role
│   │   └── security.py      # password hashing, JWT creation/decoding
│   ├── models/
│   │   ├── user.py          # User SQLModel table + Role enum
│   │   └── item.py          # Item SQLModel table (FK → users)
│   ├── schemas/
│   │   ├── token.py         # LoginRequest, RefreshRequest, Token
│   │   ├── user.py          # UserCreate, UserRead
│   │   └── item.py          # ItemCreate, ItemUpdate, ItemRead
│   ├── api/v1/
│   │   ├── router.py        # APIRouter aggregator for /api/v1
│   │   ├── auth.py          # /auth/register, /login, /refresh, /me
│   │   ├── items.py         # /items CRUD (ownership-gated)
│   │   └── users.py         # /users admin endpoints
│   └── db/
│       ├── session.py       # async engine, AsyncSessionLocal, get_session
│       └── base.py          # imports all models → Alembic metadata discovery
├── alembic/
│   ├── env.py               # async-capable Alembic env
│   ├── script.py.mako       # migration file template
│   └── versions/
│       ├── 0001_create_users_table.py
│       └── 0002_create_items_table.py
├── tests/
│   ├── conftest.py          # engine, session, client, user/admin fixtures
│   ├── test_health.py
│   ├── test_auth.py
│   ├── test_items.py
│   └── test_users.py
├── .github/workflows/ci.yml
├── Dockerfile               # multi-stage: builder + slim runtime
├── docker-compose.yml       # app + postgres, hot-reload mounts
├── alembic.ini
├── pyproject.toml           # deps, ruff, mypy, pytest config
├── .pre-commit-config.yaml
└── .env.example
```

---

## Quick start

### Option A — local development (no Docker)

**Prerequisites:** Python 3.11+, a running PostgreSQL instance.

```bash
# 1. Clone and enter the repo
git clone https://github.com/AchrafBoudabous/fastapi-sqlmodel-starter.git
cd fastapi-sqlmodel-starter

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install project + dev dependencies
pip install -e ".[dev]"

# 4. Configure environment
cp .env.example .env
# Edit .env — at minimum set DATABASE_URL and SECRET_KEY

# 5. Run migrations
alembic upgrade head

# 6. Start the server
uvicorn app.main:app --reload
```

The API is now at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

### Option B — Docker Compose (app + Postgres, no local install needed)

**Prerequisites:** Docker Desktop running.

```bash
cp .env.example .env          # uses sensible defaults for docker-compose

docker compose up --build     # first run: builds the image
docker compose up             # subsequent runs
```

The app runs migrations automatically on startup then binds to `http://localhost:8000`.

---

## Environment variables

All variables are read from `.env` via `pydantic-settings`. See `.env.example` for the full list.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async SQLAlchemy connection string |
| `SECRET_KEY` | *(must set)* | JWT signing key — generate with `python -c "import secrets; print(secrets.token_hex(32))"`. App refuses to start in production (`DEBUG=false`) if the default value is used. |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `DEBUG` | `true` | Enables SQLAlchemy query logging. Set to `false` in production. |
| `CORS_ORIGINS` | `["http://localhost:3000","http://localhost:8000"]` | JSON array of allowed origins for the CORS middleware. In production, list only your actual frontend URLs. |

---

## API overview

```
GET  /health                       # liveness check

POST /api/v1/auth/register         # create account → UserRead
POST /api/v1/auth/login            # email + password → Token
POST /api/v1/auth/refresh          # refresh_token → Token
GET  /api/v1/auth/me               # current user's profile 🔒

GET  /api/v1/items/                # list items (own only; admin: all) 🔒
POST /api/v1/items/                # create item 🔒
GET  /api/v1/items/{id}            # get item (own only; admin: any) 🔒
PUT  /api/v1/items/{id}            # update item (own only; admin: any) 🔒
DELETE /api/v1/items/{id}          # delete item (own only; admin: any) 🔒

GET  /api/v1/users/                # list all users 🔒👑
GET  /api/v1/users/{id}            # get user 🔒👑
PATCH /api/v1/users/{id}/role      # promote / demote 🔒👑

🔒 requires Bearer token   👑 requires role=admin
```

---

## Running tests

Tests use an **in-memory SQLite** database — no Postgres required.

```bash
pytest tests/ -v                  # run all tests
pytest tests/test_auth.py -v      # single file
pytest -k "admin" -v              # filter by name
pytest --tb=short -q              # quiet output
```

The test suite covers:
- Auth flow: register, login, `/me`, token refresh, error cases (401, 409, 422)
- Items CRUD: create, list, get, update, delete — including ownership isolation
- Role-based access: user sees own items, admin sees all, 403 on missing permissions
- Admin user management: list, get, promote, demote

---

## Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1

# Show migration history
alembic history

# Generate a new migration after editing models
alembic revision --autogenerate -m "add tags table"
```

> **Note:** `alembic revision --autogenerate` compares your SQLModel models
> against the live database schema. It requires a running Postgres connection
> (use the `DATABASE_URL` in your `.env`). Inspect the generated file before
> running it — autogenerate occasionally misses index changes on complex models.

---

## Architectural decisions

### Why SQLModel instead of SQLAlchemy + separate Pydantic models?

The traditional FastAPI pattern uses SQLAlchemy models for the ORM layer and
separate Pydantic models for request/response validation. This works but creates
friction: two class hierarchies that mirror each other, requiring explicit
mapping between them.

SQLModel collapses these into one: a class decorated with `table=True` is both
a valid SQLAlchemy mapped class *and* a Pydantic model. You write the field once
and get DB column definition, validation, and serialization for free.

The trade-off: SQLModel is younger than SQLAlchemy + Pydantic independently, and
its type stubs are imperfect. We mitigate this by keeping separate Pydantic
`*Read`/`*Create` schema classes in `app/schemas/` — these control exactly what
goes in and out of the API, while the SQLModel table classes stay focused on the
DB layer.

### Why server-managed timestamps?

`created_at` and `updated_at` use `server_default=func.now()` and
`onupdate=func.now()` (SQLAlchemy column-level). The **database server** sets
them, not the application.

This avoids timezone drift between app servers in a multi-node deployment, is
immune to clock skew on the application host, and means you never need to pass
timestamps in your `INSERT` statements.

The Python field type is `datetime | None` (None before the first DB flush);
after `session.refresh(obj)` they're always populated.

### Why access + refresh tokens instead of just access tokens?

Short-lived access tokens (30 min) limit the blast radius of a stolen token —
after expiry, it's useless. Refresh tokens (7 days) let clients stay logged in
without re-entering credentials. Each token carries a `"type"` claim
(`"access"` or `"refresh"`) that is checked in every handler, preventing a
refresh token from being used to authenticate API calls (and vice versa).

No refresh token rotation is implemented in this starter — that's appropriate
for most apps. If you need it, add a `refresh_token` table and invalidate old
tokens on use.

### Why 404 instead of 403 for ownership violations?

When a user requests another user's item, the API returns `404 Not Found`, not
`403 Forbidden`. A `403` tells the caller "this resource exists but you can't
have it." A `404` reveals nothing. This is the standard pattern for
ownership-gated resources.

### Why a model registry file (`app/db/base.py`)?

Alembic's `env.py` needs all SQLModel table classes to be imported before it
reads `SQLModel.metadata`. Rather than importing them directly in `env.py`
(which becomes a merge-conflict target every time you add a model), we have a
single file — `app/db/base.py` — that imports every model. `env.py` imports
this one file. When you add a new model, you add one line to `base.py` and
nothing else changes.

### Why multi-stage Docker?

The `builder` stage has gcc, python3-dev, and libffi-dev — necessary to compile
C extensions (asyncpg, bcrypt, cryptography). The `runtime` stage is a clean
`python:3.11-slim` with only the compiled venv copied in. No build tools in
production → smaller image, smaller attack surface.

A stub `app/__init__.py` is created in the builder so `pip install .` can
resolve dependencies without the full source. The real source is copied as a
separate `COPY` layer, so changing a `.py` file doesn't trigger a full
`pip install`.

---

## Adding a new resource end-to-end

This walks through adding a **`Tag`** resource (users can tag items). Follow
these steps in order.

### 1 — Define the model (`app/models/tag.py`)

```python
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, SQLModel


class Tag(SQLModel, table=True):
    __tablename__ = "tags"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=64, index=True)
    owner_id: uuid.UUID = Field(foreign_key="users.id", index=True, nullable=False)

    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
```

### 2 — Register it for Alembic (`app/db/base.py`)

```python
from app.models.item import Item  # noqa: F401
from app.models.tag import Tag    # noqa: F401  ← add this line
from app.models.user import User  # noqa: F401
```

Also export from `app/models/__init__.py`:

```python
from app.models.tag import Tag
```

### 3 — Write the schemas (`app/schemas/tag.py`)

```python
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    created_at: datetime
```

### 4 — Write the router (`app/api/v1/tags.py`)

```python
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.core.deps import CurrentUser, SessionDep
from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagRead

router = APIRouter(prefix="/tags", tags=["tags"])


@router.post("/", response_model=TagRead, status_code=status.HTTP_201_CREATED)
async def create_tag(body: TagCreate, session: SessionDep, current_user: CurrentUser) -> Tag:
    tag = Tag(**body.model_dump(), owner_id=current_user.id)
    session.add(tag)
    await session.commit()
    await session.refresh(tag)
    return tag


@router.get("/", response_model=list[TagRead])
async def list_tags(session: SessionDep, current_user: CurrentUser) -> list[Tag]:
    result = await session.exec(select(Tag).where(Tag.owner_id == current_user.id))
    return list(result.all())


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(tag_id: uuid.UUID, session: SessionDep, current_user: CurrentUser) -> None:
    tag = await session.get(Tag, tag_id)
    if tag is None or tag.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    await session.delete(tag)
    await session.commit()
```

### 5 — Register the router (`app/api/v1/router.py`)

```python
from app.api.v1 import auth, items, tags, users  # ← add tags

router.include_router(tags.router)               # ← add this line
```

### 6 — Generate the migration

```bash
alembic revision --autogenerate -m "create tags table"
```

Inspect the generated file in `alembic/versions/`. Verify the `upgrade()` and
`downgrade()` functions look correct, then apply:

```bash
alembic upgrade head
```

### 7 — Write tests (`tests/test_tags.py`)

```python
from httpx import AsyncClient
from tests.conftest import bearer


async def test_create_tag(client: AsyncClient, user_token: str) -> None:
    r = await client.post("/api/v1/tags/", json={"name": "python"}, headers=bearer(user_token))
    assert r.status_code == 201
    assert r.json()["name"] == "python"


async def test_list_tags(client: AsyncClient, user_token: str) -> None:
    await client.post("/api/v1/tags/", json={"name": "fastapi"}, headers=bearer(user_token))
    r = await client.get("/api/v1/tags/", headers=bearer(user_token))
    assert r.status_code == 200
    assert any(t["name"] == "fastapi" for t in r.json())
```

Run `pytest tests/test_tags.py -v` to confirm everything works. The test client
uses in-memory SQLite — no migration needed in the test environment since
`SQLModel.metadata.create_all()` in the fixture creates all tables from the
current model definitions.

---

## Pre-commit hooks

```bash
pip install pre-commit
pre-commit install                 # install git hook
pre-commit run --all-files         # run fast hooks now
pre-commit run mypy --all-files    # run mypy (manual stage)
```

Hooks that run on every commit:
- `ruff-format` — enforces consistent formatting
- `ruff` — linting with auto-fix
- Standard file checks (trailing whitespace, YAML/TOML validity, no debug statements, no commits to `main`)

Mypy is on `stages: [manual]` so it doesn't slow down every commit. It always
runs in the `type-check` CI job.

---

## CI pipeline

Three jobs run in parallel on every push to `main` and every pull request:

```
push / PR
    ├── lint        ruff format --check && ruff check
    ├── type-check  mypy app/
    └── test        pytest tests/ -v
```

The `lint` job installs only `ruff` (no project deps), so it starts in seconds.
`type-check` and `test` install the full dep tree, cached by `pyproject.toml`
hash.

---

## License

MIT — use this as the foundation for your own projects.
