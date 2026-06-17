"""Items CRUD: ownership enforcement, role-based visibility, and validation."""

from httpx import AsyncClient

from tests.conftest import bearer

# ── Create ────────────────────────────────────────────────────────────────────


async def test_create_item_returns_201(client: AsyncClient, user_token: str) -> None:
    r = await client.post(
        "/api/v1/items/",
        json={"title": "My note", "description": "Hello"},
        headers=bearer(user_token),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "My note"
    assert body["description"] == "Hello"
    assert "id" in body
    assert "owner_id" in body


async def test_create_item_requires_auth(client: AsyncClient) -> None:
    r = await client.post("/api/v1/items/", json={"title": "x"})
    assert r.status_code == 401


async def test_create_item_empty_title_returns_422(
    client: AsyncClient, user_token: str
) -> None:
    r = await client.post(
        "/api/v1/items/", json={"title": ""}, headers=bearer(user_token)
    )
    assert r.status_code == 422


async def test_create_item_description_is_optional(
    client: AsyncClient, user_token: str
) -> None:
    r = await client.post(
        "/api/v1/items/", json={"title": "no desc"}, headers=bearer(user_token)
    )
    assert r.status_code == 201
    assert r.json()["description"] is None


# ── List ──────────────────────────────────────────────────────────────────────


async def test_list_returns_only_own_items(
    client: AsyncClient, user_token: str, admin_token: str
) -> None:
    await client.post(
        "/api/v1/items/", json={"title": "user item"}, headers=bearer(user_token)
    )
    await client.post(
        "/api/v1/items/", json={"title": "admin item"}, headers=bearer(admin_token)
    )

    r = await client.get("/api/v1/items/", headers=bearer(user_token))
    assert r.status_code == 200
    titles = [i["title"] for i in r.json()]
    assert "user item" in titles
    assert "admin item" not in titles


async def test_admin_list_returns_all_items(
    client: AsyncClient, user_token: str, admin_token: str
) -> None:
    await client.post(
        "/api/v1/items/", json={"title": "user item"}, headers=bearer(user_token)
    )
    await client.post(
        "/api/v1/items/", json={"title": "admin item"}, headers=bearer(admin_token)
    )

    r = await client.get("/api/v1/items/", headers=bearer(admin_token))
    titles = [i["title"] for i in r.json()]
    assert "user item" in titles
    assert "admin item" in titles


async def test_list_pagination(client: AsyncClient, user_token: str) -> None:
    for i in range(5):
        await client.post(
            "/api/v1/items/", json={"title": f"item {i}"}, headers=bearer(user_token)
        )

    r = await client.get("/api/v1/items/?limit=3&offset=0", headers=bearer(user_token))
    assert len(r.json()) == 3

    r2 = await client.get("/api/v1/items/?limit=3&offset=3", headers=bearer(user_token))
    assert len(r2.json()) == 2


# ── Get by id ─────────────────────────────────────────────────────────────────


async def test_get_own_item(client: AsyncClient, user_token: str) -> None:
    r = await client.post(
        "/api/v1/items/", json={"title": "mine"}, headers=bearer(user_token)
    )
    item_id = r.json()["id"]

    r2 = await client.get(f"/api/v1/items/{item_id}", headers=bearer(user_token))
    assert r2.status_code == 200
    assert r2.json()["title"] == "mine"


async def test_get_other_users_item_returns_404(
    client: AsyncClient, user_token: str, admin_token: str
) -> None:
    r = await client.post(
        "/api/v1/items/", json={"title": "admin's"}, headers=bearer(admin_token)
    )
    item_id = r.json()["id"]

    # Regular user cannot see admin's item — 404 not 403 to avoid leaking existence
    r2 = await client.get(f"/api/v1/items/{item_id}", headers=bearer(user_token))
    assert r2.status_code == 404


async def test_admin_can_get_any_item(
    client: AsyncClient, user_token: str, admin_token: str
) -> None:
    r = await client.post(
        "/api/v1/items/", json={"title": "user's secret"}, headers=bearer(user_token)
    )
    item_id = r.json()["id"]

    r2 = await client.get(f"/api/v1/items/{item_id}", headers=bearer(admin_token))
    assert r2.status_code == 200
    assert r2.json()["title"] == "user's secret"


async def test_get_nonexistent_item_returns_404(
    client: AsyncClient, user_token: str
) -> None:
    r = await client.get(
        "/api/v1/items/00000000-0000-0000-0000-000000000000",
        headers=bearer(user_token),
    )
    assert r.status_code == 404


# ── Update ────────────────────────────────────────────────────────────────────


async def test_update_own_item(client: AsyncClient, user_token: str) -> None:
    r = await client.post(
        "/api/v1/items/",
        json={"title": "old", "description": "keep"},
        headers=bearer(user_token),
    )
    item_id = r.json()["id"]

    r2 = await client.put(
        f"/api/v1/items/{item_id}",
        json={"title": "new"},
        headers=bearer(user_token),
    )
    assert r2.status_code == 200
    assert r2.json()["title"] == "new"
    assert (
        r2.json()["description"] == "keep"
    )  # exclude_unset preserves untouched fields


async def test_update_other_users_item_returns_404(
    client: AsyncClient, user_token: str, admin_token: str
) -> None:
    r = await client.post(
        "/api/v1/items/", json={"title": "admin item"}, headers=bearer(admin_token)
    )
    item_id = r.json()["id"]

    r2 = await client.put(
        f"/api/v1/items/{item_id}", json={"title": "hacked"}, headers=bearer(user_token)
    )
    assert r2.status_code == 404


async def test_admin_can_update_any_item(
    client: AsyncClient, user_token: str, admin_token: str
) -> None:
    r = await client.post(
        "/api/v1/items/", json={"title": "original"}, headers=bearer(user_token)
    )
    item_id = r.json()["id"]

    r2 = await client.put(
        f"/api/v1/items/{item_id}",
        json={"title": "admin edit"},
        headers=bearer(admin_token),
    )
    assert r2.status_code == 200
    assert r2.json()["title"] == "admin edit"


# ── Delete ────────────────────────────────────────────────────────────────────


async def test_delete_own_item(client: AsyncClient, user_token: str) -> None:
    r = await client.post(
        "/api/v1/items/", json={"title": "bye"}, headers=bearer(user_token)
    )
    item_id = r.json()["id"]

    r2 = await client.delete(f"/api/v1/items/{item_id}", headers=bearer(user_token))
    assert r2.status_code == 204

    r3 = await client.get(f"/api/v1/items/{item_id}", headers=bearer(user_token))
    assert r3.status_code == 404


async def test_delete_other_users_item_returns_404(
    client: AsyncClient, user_token: str, admin_token: str
) -> None:
    r = await client.post(
        "/api/v1/items/", json={"title": "protected"}, headers=bearer(admin_token)
    )
    item_id = r.json()["id"]

    r2 = await client.delete(f"/api/v1/items/{item_id}", headers=bearer(user_token))
    assert r2.status_code == 404


async def test_admin_can_delete_any_item(
    client: AsyncClient, user_token: str, admin_token: str
) -> None:
    r = await client.post(
        "/api/v1/items/", json={"title": "removable"}, headers=bearer(user_token)
    )
    item_id = r.json()["id"]

    r2 = await client.delete(f"/api/v1/items/{item_id}", headers=bearer(admin_token))
    assert r2.status_code == 204
