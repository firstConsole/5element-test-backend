import json


async def _new_chat(client, headers):
    return (await client.post("/chats", json={"title": "C"}, headers=headers)).json()["id"]


async def test_send_message_and_history(client, auth_headers):
    headers = await auth_headers("a@e.com")
    chat_id = await _new_chat(client, headers)

    resp = await client.post(
        f"/chats/{chat_id}/messages", json={"content": "Привет"}, headers=headers
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "assistant"
    assert resp.json()["content"] == "Ответ: Привет"

    history = (await client.get(f"/chats/{chat_id}/messages", headers=headers)).json()
    assert [m["role"] for m in history] == ["user", "assistant"]


async def test_send_message_isolation(client, auth_headers):
    alice = await auth_headers("alice@e.com")
    bob = await auth_headers("bob@e.com")
    chat_id = await _new_chat(client, alice)

    assert (
        await client.post(f"/chats/{chat_id}/messages", json={"content": "x"}, headers=bob)
    ).status_code == 404


async def test_streaming(client, auth_headers):
    headers = await auth_headers("a@e.com")
    chat_id = await _new_chat(client, headers)

    deltas, done = [], None
    async with client.stream(
        "POST", f"/chats/{chat_id}/messages/stream", json={"content": "hi"}, headers=headers
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        async for line in resp.aiter_lines():
            if not line.startswith("data:"):
                continue
            event = json.loads(line[5:].strip())
            if "delta" in event:
                deltas.append(event["delta"])
            if event.get("done"):
                done = event

    assert "".join(deltas) == "часть1часть2"
    assert done and "message_id" in done

    # Ответ сохранён в истории.
    history = (await client.get(f"/chats/{chat_id}/messages", headers=headers)).json()
    assert history[-1]["content"] == "часть1часть2"


async def test_empty_content_rejected(client, auth_headers):
    headers = await auth_headers("a@e.com")
    chat_id = await _new_chat(client, headers)
    resp = await client.post(
        f"/chats/{chat_id}/messages", json={"content": ""}, headers=headers
    )
    assert resp.status_code == 422
