from fastapi.testclient import TestClient

from emporio.agent import Reply, ToolCall
from emporio.api import app, get_agent
from emporio.store import Store


class StubAgent:
    def __init__(self):
        self.store = Store(":memory:")

    def chat(self, message, session_id=None):
        session_id = session_id or "s1"
        self.store.append(session_id, [{"role": "user", "content": message},
                                       {"role": "assistant", "content": "Olá!"}])
        return Reply(session_id, "Olá!", [ToolCall("list_active_promotions", {}, {})])


def test_chat_endpoint():
    stub = StubAgent()
    app.dependency_overrides[get_agent] = lambda: stub
    client = TestClient(app)
    try:
        assert client.get("/health").json() == {"status": "ok"}
        body = client.post("/chat", json={"message": "oi"}).json()
        assert body == {"session_id": "s1", "reply": "Olá!",
                        "tool_calls": [{"name": "list_active_promotions", "arguments": {}}]}
        assert len(client.get("/sessions/s1/messages").json()) == 2
        assert client.post("/chat", json={"message": ""}).status_code == 422
    finally:
        app.dependency_overrides.clear()
