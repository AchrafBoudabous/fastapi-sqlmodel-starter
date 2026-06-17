"""Shared pytest fixtures for the entire test suite.

Every test gets a fresh in-memory SQLite database via StaticPool so
connections are isolated between tests without needing a running Postgres.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import app.db.base  # noqa: F401 — registers all table models on SQLModel.metadata
from app.core.security import hash_password
from app.db.session import get_session
from app.main import app
from app.models.user import Role, User

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

# Fixed credentials used by the standard user/admin fixtures.
# Tests that need unique users should register ad-hoc via the client.
USER_EMAIL = "user@example.com"
USER_PASSWORD = "userpass1"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "adminpass1"


# ── Database engine (one fresh in-memory DB per test) ────────────────────────


@pytest.fixture()
async def engine():
    _engine = create_async_engine(
        _TEST_DB_URL,
        connect_args={"check_same_thread": False},
        # StaticPool keeps all async connections on the same underlying
        # SQLite connection, so data written in one session is visible in another.
        poolclass=StaticPool,
    )
    async with _engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield _engine
    await _engine.dispose()


@pytest.fixture()
async def session(engine) -> AsyncSession:
    """Direct DB session — use this for inserting seed data in tests."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s


# ── HTTP client wired to the test database ───────────────────────────────────


@pytest.fixture()
async def client(engine) -> AsyncClient:
    """Async HTTP client with the session dependency overridden to the test DB."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_session():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_session] = _override_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Standard user fixtures ────────────────────────────────────────────────────


@pytest.fixture()
async def registered_user(client: AsyncClient) -> dict:
    """Register the standard test user via the API and return the UserRead payload."""
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": USER_EMAIL, "password": USER_PASSWORD},
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture()
async def user_token(client: AsyncClient, registered_user: dict) -> str:
    """JWT access token for the standard test user."""
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": USER_EMAIL, "password": USER_PASSWORD},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture()
async def user_refresh_token(client: AsyncClient, registered_user: dict) -> str:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": USER_EMAIL, "password": USER_PASSWORD},
    )
    return r.json()["refresh_token"]


# ── Admin fixtures (seeded directly into the DB to avoid the bootstrap problem) ──


@pytest.fixture()
async def admin_user(session: AsyncSession) -> User:
    """Create an admin user directly in the DB.

    We bypass the API here because there's no public endpoint to create an admin —
    that's intentional. In production, seed the first admin via a management script.
    """
    user = User(
        email=ADMIN_EMAIL,
        hashed_password=hash_password(ADMIN_PASSWORD),
        role=Role.admin,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture()
async def admin_token(client: AsyncClient, admin_user: User) -> str:
    """JWT access token for the seeded admin user."""
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


# ── Convenience helpers ───────────────────────────────────────────────────────


def bearer(token: str) -> dict[str, str]:
    """Build an Authorization header dict from a JWT token."""
    return {"Authorization": f"Bearer {token}"}
