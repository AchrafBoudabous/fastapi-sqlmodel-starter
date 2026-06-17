"""Admin user-management endpoints: list, get, and role promotion."""

from httpx import AsyncClient

from tests.conftest import ADMIN_EMAIL, USER_EMAIL, bearer

# ── GET /users ────────────────────────────────────────────────────────────────


async def test_list_users_requires_admin(client: AsyncClient, user_token: str) -> None:
    r = await client.get("/api/v1/users/", headers=bearer(user_token))
    assert r.status_code == 403


async def test_list_users_returns_all(
    client: AsyncClient, registered_user: dict, admin_token: str
) -> None:
    r = await client.get("/api/v1/users/", headers=bearer(admin_token))
    assert r.status_code == 200
    emails = [u["email"] for u in r.json()]
    assert USER_EMAIL in emails
    assert ADMIN_EMAIL in emails


async def test_list_users_pagination(client: AsyncClient, admin_token: str) -> None:
    # Register extra users
    for i in range(3):
        await client.post(
            "/api/v1/auth/register",
            json={"email": f"extra{i}@example.com", "password": "password123"},
        )

    r = await client.get("/api/v1/users/?limit=2&offset=0", headers=bearer(admin_token))
    assert r.status_code == 200
    assert len(r.json()) == 2


# ── GET /users/{id} ───────────────────────────────────────────────────────────


async def test_get_user_by_id(
    client: AsyncClient, registered_user: dict, admin_token: str
) -> None:
    user_id = registered_user["id"]
    r = await client.get(f"/api/v1/users/{user_id}", headers=bearer(admin_token))
    assert r.status_code == 200
    assert r.json()["email"] == USER_EMAIL


async def test_get_user_nonexistent_returns_404(
    client: AsyncClient, admin_token: str
) -> None:
    r = await client.get(
        "/api/v1/users/00000000-0000-0000-0000-000000000000",
        headers=bearer(admin_token),
    )
    assert r.status_code == 404


async def test_get_user_requires_admin(
    client: AsyncClient, registered_user: dict, user_token: str
) -> None:
    user_id = registered_user["id"]
    r = await client.get(f"/api/v1/users/{user_id}", headers=bearer(user_token))
    assert r.status_code == 403


# ── PATCH /users/{id}/role ────────────────────────────────────────────────────


async def test_promote_user_to_admin(
    client: AsyncClient, registered_user: dict, admin_token: str
) -> None:
    user_id = registered_user["id"]

    r = await client.patch(
        f"/api/v1/users/{user_id}/role",
        params={"role": "admin"},
        headers=bearer(admin_token),
    )
    assert r.status_code == 200
    assert r.json()["role"] == "admin"

    # Promoted user can now call admin endpoints
    promoted_token = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": USER_EMAIL, "password": "userpass1"},
        )
    ).json()["access_token"]

    r2 = await client.get("/api/v1/users/", headers=bearer(promoted_token))
    assert r2.status_code == 200


async def test_demote_admin_to_user(
    client: AsyncClient, registered_user: dict, admin_token: str
) -> None:
    user_id = registered_user["id"]

    # Promote first
    await client.patch(
        f"/api/v1/users/{user_id}/role",
        params={"role": "admin"},
        headers=bearer(admin_token),
    )

    # Then demote
    r = await client.patch(
        f"/api/v1/users/{user_id}/role",
        params={"role": "user"},
        headers=bearer(admin_token),
    )
    assert r.status_code == 200
    assert r.json()["role"] == "user"


async def test_set_role_requires_admin(
    client: AsyncClient, registered_user: dict, user_token: str
) -> None:
    user_id = registered_user["id"]
    r = await client.patch(
        f"/api/v1/users/{user_id}/role",
        params={"role": "admin"},
        headers=bearer(user_token),
    )
    assert r.status_code == 403


async def test_set_role_invalid_value_returns_422(
    client: AsyncClient, registered_user: dict, admin_token: str
) -> None:
    user_id = registered_user["id"]
    r = await client.patch(
        f"/api/v1/users/{user_id}/role",
        params={"role": "superuser"},
        headers=bearer(admin_token),
    )
    assert r.status_code == 422
