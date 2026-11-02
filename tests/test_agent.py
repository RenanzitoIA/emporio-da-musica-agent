"""Agent loop tests with a scripted fake OpenAI client (no network, no API key)."""

from datetime import datetime
from types import SimpleNamespace

from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)

from emporio.agent import Agent
from emporio.config import Settings
from emporio.prompts import build_system_prompt, store_status
from emporio.store import Store


class FakeClient:
    """Returns pre-scripted messages and records what the agent sent."""

    def __init__(self, script):
        self.script = list(script)
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=self.script.pop(0))])


def tool_call(name, arguments, call_id="call_1"):
    return ChatCompletionMessage(
        role="assistant",
        content=None,
        tool_calls=[ChatCompletionMessageToolCall(
            id=call_id, type="function", function=Function(name=name, arguments=arguments))],
    )


def answer(text):
    return ChatCompletionMessage(role="assistant", content=text)


def make_agent(script):
    settings = Settings(model="gpt-5-mini", reasoning_effort="low",
                        store_now=datetime(2026, 3, 23, 10, 30), history_db=":memory:")
    client = FakeClient(script)
    return Agent(settings=settings, client=client, store=Store(":memory:")), client


def test_tool_round_trip_and_history():
    agent, client = make_agent([
        tool_call("search_products", '{"query": "Takamine GD20", "category": null, '
                  '"min_price": null, "max_price": null, "only_available": false}'),
        answer("O Takamine GD20 sai por R$ 2.199,00."),
        answer("De nada!"),
    ])
    seen = []
    reply = agent.chat("Quanto custa o Takamine GD20?", on_tool_call=lambda n, a: seen.append(n))
    assert seen == ["search_products"]
    assert reply.text.startswith("O Takamine GD20")
    assert reply.tool_calls[0].name == "search_products"
    assert reply.tool_calls[0].result["produtos"][0]["preco_tabela"] == "R$ 2.199,00"

    # Second request carried the tool result back to the model.
    tool_msg = client.requests[1]["messages"][-1]
    assert tool_msg["role"] == "tool" and "2.199,00" in tool_msg["content"]

    # Follow-up turn in the same session sees the full previous exchange.
    agent.chat("Obrigado", session_id=reply.session_id)
    roles = [m["role"] for m in client.requests[2]["messages"]]
    assert roles == ["system", "user", "assistant", "tool", "assistant", "user"]


def test_ticket_is_persisted():
    agent, _ = make_agent([
        tool_call("open_ticket", '{"kind": "reclamacao", "summary": "Pedido 8 atrasado", '
                  '"order_id": 8, "contact": null}'),
        answer("Chamado aberto!"),
    ])
    reply = agent.chat("Meu pedido está atrasado, quero reclamar")
    assert reply.tool_calls[0].result["protocolo"] == "EM-00001"
    assert agent.store.list_tickets()[0]["session_id"] == reply.session_id


def test_unknown_tool_does_not_crash():
    agent, _ = make_agent([tool_call("delete_database", "{}"), answer("Ops.")])
    reply = agent.chat("oi")
    assert "erro" in reply.tool_calls[0].result


def test_loop_guard():
    agent, _ = make_agent([tool_call("list_active_promotions", "{}")] * 6)
    assert "equipe" in agent.chat("promoções?").text


def test_store_hours():
    assert store_status(datetime(2026, 3, 23, 10, 0)).startswith("ABERTA")      # Monday
    assert "sábado às 9h" in store_status(datetime(2026, 3, 27, 19, 0))       # Fri night -> Sat
    assert "segunda-feira às 9h" in store_status(datetime(2026, 3, 28, 14, 0))  # Sat afternoon
    assert "Data e hora: segunda-feira, 23/03/2026" in build_system_prompt(datetime(2026, 3, 23, 10))


def test_feedback_roundtrip():
    store = Store(":memory:")
    store.save_feedback("s1", 1, 1)
    store.save_feedback("s1", 1, 0)  # user changed their mind
    assert store.get_feedback("s1") == {1: 0}
