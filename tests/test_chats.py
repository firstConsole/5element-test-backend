async def test_chat_crud(client, auth_headers):
    headers = await auth_headers("a@e.com")

    assert (await client.get("/chats", headers=headers)).json() == []

    created = await client.post("/chats", json={"title": "Первый"}, headers=headers)
    assert created.status_code == 201
    chat_id = created.json()["id"]

    renamed = await client.patch(
        f"/chats/{chat_id}", json={"title": "Переименован"}, headers=headers
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Переименован"

    assert (await client.delete(f"/chats/{chat_id}", headers=headers)).status_code == 204
    assert (
        await client.patch(f"/chats/{chat_id}", json={"title": "x"}, headers=headers)
    ).status_code == 404


async def test_chats_require_auth(client):
    assert (await client.get("/chats")).status_code in (401, 403)


async def test_empty_title_rejected(client, auth_headers):
    headers = await auth_headers("a@e.com")
    resp = await client.post("/chats", json={"title": ""}, headers=headers)
    assert resp.status_code == 422


async def test_user_isolation(client, auth_headers):
    alice = await auth_headers("alice@e.com")
    bob = await auth_headers("bob@e.com")

    chat_id = (await client.post("/chats", json={"title": "A"}, headers=alice)).json()["id"]

    # Bob не видит и не может трогать чат Alice.
    assert (await client.get("/chats", headers=bob)).json() == []
    assert (
        await client.patch(f"/chats/{chat_id}", json={"title": "hack"}, headers=bob)
    ).status_code == 404
    assert (await client.delete(f"/chats/{chat_id}", headers=bob)).status_code == 404

    # У Alice чат на месте.
    assert len((await client.get("/chats", headers=alice)).json()) == 1
