async def test_register_returns_user(client):
    resp = await client.post(
        "/auth/register", json={"email": "a@e.com", "password": "password1"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "a@e.com"
    assert "id" in body and "password" not in body


async def test_register_duplicate_conflict(client):
    await client.post("/auth/register", json={"email": "a@e.com", "password": "password1"})
    resp = await client.post(
        "/auth/register", json={"email": "a@e.com", "password": "password1"}
    )
    assert resp.status_code == 409


async def test_register_rejects_invalid_email(client):
    resp = await client.post(
        "/auth/register", json={"email": "not-email", "password": "password1"}
    )
    assert resp.status_code == 422


async def test_login_success_and_wrong_password(client):
    await client.post("/auth/register", json={"email": "a@e.com", "password": "password1"})

    ok = await client.post("/auth/login", json={"email": "a@e.com", "password": "password1"})
    assert ok.status_code == 200
    assert ok.json()["token_type"] == "bearer"

    bad = await client.post("/auth/login", json={"email": "a@e.com", "password": "wrongpass"})
    assert bad.status_code == 401


async def test_me_requires_token(client, auth_headers):
    assert (await client.get("/auth/me")).status_code in (401, 403)
    headers = await auth_headers("a@e.com")
    resp = await client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "a@e.com"
