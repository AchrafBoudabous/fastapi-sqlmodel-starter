"""Auth flow: registration, login, /me, token refresh, and error cases."""

from httpx import AsyncClient

from tests.conftest import (
    ADMIN_EMAIL,
    USER_EMAIL,
    USER_PASSWORD,
    bearer,
)

# ── Registration ──────────────────────────────────────────────────────────────


async def test_register_returns_user_read(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "supersecret"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "new@example.com"
    assert body["role"] == "user"
    assert body["is_active"] is True
    assert "id" in body
    assert "created_at" in body
    assert "hashed_password" not in body  # never leak this


async def test_register_duplicate_email_returns_409(
    client: AsyncClient, registered_user: dict
) -> None:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": USER_EMAIL, "password": "otherpass"},
    )
    assert r.status_code == 409


async def test_register_invalid_email_returns_422(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "password123"},
    )
    assert r.status_code == 422


async def test_register_short_password_returns_422(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "short"},
    )
    assert r.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────


async def test_login_returns_both_tokens(
    client: AsyncClient, registered_user: dict
) -> None:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": USER_EMAIL, "password": USER_PASSWORD},
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


async def test_login_wrong_password_returns_401(
    client: AsyncClient, registered_user: dict
) -> None:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": USER_EMAIL, "password": "wrong"},
    )
    assert r.status_code == 401


async def test_login_unknown_email_returns_401(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "pass"},
    )
    assert r.status_code == 401


# ── /me ───────────────────────────────────────────────────────────────────────


async def test_me_returns_current_user(
    client: AsyncClient, user_token: str, registered_user: dict
) -> None:
    r = await client.get("/api/v1/auth/me", headers=bearer(user_token))
    assert r.status_code == 200
    assert r.json()["email"] == USER_EMAIL
    assert r.json()["id"] == registered_user["id"]


async def test_me_without_token_returns_401(client: AsyncClient) -> None:
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


async def test_me_with_garbage_token_returns_401(client: AsyncClient) -> None:
    r = await client.get("/api/v1/auth/me", headers=bearer("not.a.jwt"))
    assert r.status_code == 401


# ── Token refresh ─────────────────────────────────────────────────────────────


async def test_refresh_issues_new_access_token(
    client: AsyncClient, user_refresh_token: str
) -> None:
    r = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": user_refresh_token},
    )
    assert r.status_code == 200
    assert "access_token" in r.json()


async def test_access_token_rejected_as_refresh(
    client: AsyncClient, user_token: str
) -> None:
    r = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": user_token},
    )
    assert r.status_code == 401


async def test_garbage_refresh_token_returns_401(client: AsyncClient) -> None:
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": "garbage"})
    assert r.status_code == 401


# ── Admin token smoke test ────────────────────────────────────────────────────


async def test_admin_can_login(client: AsyncClient, admin_token: str) -> None:
    r = await client.get("/api/v1/auth/me", headers=bearer(admin_token))
    assert r.status_code == 200
    assert r.json()["role"] == "admin"
    assert r.json()["email"] == ADMIN_EMAIL
