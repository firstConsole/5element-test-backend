async def test_list_models(client, auth_headers):
    headers = await auth_headers("a@e.com")
    resp = await client.get("/models", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "fake"
    assert body["default"] == "fake-model"
    assert "fake-model" in body["models"]


async def test_models_require_auth(client):
    assert (await client.get("/models")).status_code in (401, 403)


async def test_list_tools(client, auth_headers):
    headers = await auth_headers("a@e.com")
    resp = await client.get("/tools", headers=headers)
    assert resp.status_code == 200
    names = {t["name"] for t in resp.json()}
    assert names == {"get_current_time", "calculate"}


async def test_message_with_tools(client, auth_headers):
    headers = await auth_headers("a@e.com")
    chat_id = (await client.post("/chats", json={"title": "C"}, headers=headers)).json()["id"]

    resp = await client.post(
        f"/chats/{chat_id}/messages/tools",
        json={"content": "сколько будет 2+2*10?"},
        headers=headers,
    )
    assert resp.status_code == 201
    # Fake-провайдер вызывает calculate -> реальный инструмент считает 22.
    body = resp.json()
    assert body["content"] == "Итог: 22"
    assert body["tools_used"] == ["calculate"]
