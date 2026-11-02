"""HTTP API: uvicorn emporio.api:app --reload

A channel like WhatsApp would call POST /chat with the phone number as
session_id; the agent itself does not change.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from emporio.agent import Agent

app = FastAPI(title="Empório da Música — Agente de Atendimento", version="1.0.0")


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000, examples=["Quanto custa o Takamine GD20?"])
    session_id: str | None = Field(default=None, max_length=64, description="Omit to start a new conversation.")


class ToolCallOut(BaseModel):
    name: str
    arguments: dict[str, Any]


class ChatOut(BaseModel):
    session_id: str
    reply: str
    tool_calls: list[ToolCallOut]


@lru_cache
def get_agent() -> Agent:
    return Agent()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatOut)
def chat(body: ChatIn, agent: Agent = Depends(get_agent)) -> ChatOut:
    # Sync endpoint: FastAPI runs it in a thread pool, so the blocking OpenAI call is fine.
    reply = agent.chat(body.message, session_id=body.session_id)
    return ChatOut(
        session_id=reply.session_id,
        reply=reply.text,
        tool_calls=[ToolCallOut(name=c.name, arguments=c.arguments) for c in reply.tool_calls],
    )


@app.get("/sessions/{session_id}/messages")
def history(session_id: str, agent: Agent = Depends(get_agent)) -> list[dict[str, Any]]:
    """Customer-visible history (tool messages omitted)."""
    return [
        {"role": m["role"], "content": m["content"]}
        for m in agent.store.load(session_id)
        if m["role"] in {"user", "assistant"} and m.get("content")
    ]


@app.get("/tickets")
def tickets(agent: Agent = Depends(get_agent)) -> list[dict[str, Any]]:
    """Tickets opened by the agent (what the human team would work on)."""
    return agent.store.list_tickets()
