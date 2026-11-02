from datetime import datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from emporio.agent import Reply, ToolCall
from emporio.api import app, get_agent
from emporio.store import Store


class StubAgent:
    def __init__(self):
        self.store = Store(":memory:")
        self.settings = SimpleNamespace(model="stub", now=lambda: datetime(2026, 3, 23, 10, 30))

    def chat(self, message, session_id=None, on_tool_call=None):
        session_id = session_id or "s1"
        if on_tool_call:
            on_tool_call("search_products", {"query": "GD20"})
        self.store.append(session_id, [
            {"role": "user", "content": message},
            {"role": "assistant", "content": None, "tool_calls": [
                {"id": "c1", "type": "function",
                 "function": {"name": "search_products", "arguments": '{"query": "GD20"}'}}]},
            {"role": "tool", "tool_call_id": "c1", "content": "{}"},
            {"role": "assistant", "content": "Olá!"},
        ])
        return Reply(session_id, "Olá!", [ToolCall("search_products", {"query": "GD20"}, {})])


def client():
    stub = StubAgent()
    app.dependency_overrides[get_agent] = lambda: stub
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_chat_endpoint_and_history():
    c = client()
    assert c.get("/health").json() == {"status": "ok"}
    body = c.post("/chat", json={"message": "oi"}).json()
    assert body["session_id"] == "s1" and body["reply"] == "Olá!"
    assert body["tool_calls"] == [{"name": "search_products", "arguments": {"query": "GD20"}}]
    assert len(c.get("/sessions/s1/messages").json()) == 2
    assert c.post("/chat", json={"message": ""}).status_code == 422


def test_stream_emits_tool_then_done():
    c = client()
    with c.stream("POST", "/chat/stream", json={"message": "oi"}) as res:
        text = "".join(res.iter_text())
    assert text.index("event: tool") < text.index("event: done")
    assert "Buscando no catálogo" in text and '"session_id": "s1"' in text


def test_turns_feedback_store_and_index():
    c = client()
    c.post("/chat", json={"message": "oi"})
    assert c.post("/feedback", json={"session_id": "s1", "turn": 1, "score": 1}).status_code == 200
    data = c.get("/sessions/s1/turns").json()
    assert data["turns"][0]["tools"][0]["label"].startswith("Buscando no catálogo")
    assert data["feedback"] == {"1": 1}
    assert c.get("/store").json()["is_open"] is True
    assert "Empório da Música" in c.get("/").text
