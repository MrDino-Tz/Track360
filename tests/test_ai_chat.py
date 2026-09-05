from types import SimpleNamespace

import app.routers.ai_chat as ai_chat


def test_ai_chat_returns_503_when_client_unavailable(monkeypatch, client):
    monkeypatch.setattr(ai_chat, "_client", lambda: None)
    resp = client.post("/api/ai/chat", json={"message": "hello"})
    assert resp.status_code == 503


def test_ai_chat_returns_reply(monkeypatch, client):
    class FakeCompletions:
        def create(self, **kwargs):
            return type("C", (), {"choices": [type("Ch", (), {"message": SimpleNamespace(content="Check the belt tension and lubricate the rollers.")})()]})()

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setattr(ai_chat, "_client", lambda: fake_client)

    resp = client.post(
        "/api/ai/chat",
        json={"message": "help", "history": [{"role": "user", "content": "earlier"}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "Check the belt tension and lubricate the rollers."
    assert body["model"] == "groq/compound-mini"


def test_ai_chat_requires_message(client):
    resp = client.post("/api/ai/chat", json={"history": []})
    assert resp.status_code == 422


def test_ai_chat_strips_markdown_asterisks(monkeypatch, client):
    class FakeCompletions:
        def create(self, **kwargs):
            content = (
                "**Top Tips**\n\n1. Check *oil* level\n- Change filter\n"
                "# Season\nManual check: ok"
            )
            return type("C", (), {"choices": [type("Ch", (), {"message": SimpleNamespace(content=content)})()]})()

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setattr(ai_chat, "_client", lambda: fake_client)

    resp = client.post("/api/ai/chat", json={"message": "tips"})
    assert resp.status_code == 200
    reply = resp.json()["reply"]
    assert "*" not in reply
    assert "**" not in reply
    assert "\n- " not in reply
    assert "Season" in reply
    assert "Manual check: ok" in reply