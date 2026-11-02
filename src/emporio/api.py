"""HTTP API + web chat: uvicorn emporio.api:app --reload  ->  http://localhost:8000

A channel like WhatsApp would call POST /chat with the phone number as
session_id; the agent itself does not change. The web UI (web/) uses
POST /chat/stream to show each tool call live while the agent works.
"""

from __future__ import annotations

import json
import queue
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from emporio.agent import Agent
from emporio.prompts import ASSISTANT_NAME, store_status

WEB = Path(__file__).resolve().parents[2] / "web"

app = FastAPI(title="Empório da Música — Agente de Atendimento", version="1.1.0")
app.mount("/static", StaticFiles(directory=WEB), name="static")


# ------------------------------------------------------------------ models
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


class FeedbackIn(BaseModel):
    session_id: str = Field(max_length=64)
    turn: int = Field(ge=1)
    score: int = Field(ge=0, le=1, description="1 = helpful, 0 = not helpful")


@lru_cache
def get_agent() -> Agent:
    return Agent()


# ------------------------------------------------------------------ labels
def describe(name: str, args: dict[str, Any]) -> str:
    """Customer-friendly label for a tool call (never includes personal data)."""
    if name == "search_products":
        parts = []
        if args.get("query"):
            parts.append(f"“{args['query']}”")
        if args.get("category"):
            parts.append(str(args["category"]).lower())
        if args.get("max_price"):
            parts.append(f"até R$ {args['max_price']:,.0f}".replace(",", "."))
        return "Buscando no catálogo" + (": " + ", ".join(parts) if parts else "")
    return {
        "get_product_details": "Conferindo detalhes e estoque",
        "list_active_promotions": "Verificando promoções ativas",
        "calculate_payment_options": "Calculando Pix, parcelamento e frete",
        "lookup_order": f"Verificando identidade · pedido #{args.get('order_id', '?')}",
        "open_ticket": "Registrando chamado para a equipe",
    }.get(name, name)


def _turns(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group raw OpenAI messages into UI turns: user text, tool calls, answer."""
    turns: list[dict[str, Any]] = []
    for m in messages:
        if m["role"] == "user":
            turns.append({"user": m["content"], "tools": [], "answer": ""})
        elif not turns:
            continue
        elif m["role"] == "assistant" and m.get("tool_calls"):
            for tc in m["tool_calls"]:
                try:
                    args = json.loads(tc["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {}
                name = tc["function"]["name"]
                turns[-1]["tools"].append({"name": name, "label": describe(name, args), "arguments": args})
        elif m["role"] == "assistant":
            turns[-1]["answer"] = m.get("content") or ""
    return turns


# ------------------------------------------------------------------ routes
@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/store")
def store_info(agent: Agent = Depends(get_agent)) -> dict[str, Any]:
    now = agent.settings.now()
    status = store_status(now)
    return {
        "assistant": ASSISTANT_NAME,
        "model": agent.settings.model,
        "now": now.isoformat(timespec="minutes"),
        "is_open": status.startswith("ABERTA"),
        "status": status,
    }


@app.post("/chat", response_model=ChatOut)
def chat(body: ChatIn, agent: Agent = Depends(get_agent)) -> ChatOut:
    # Sync endpoint: FastAPI runs it in a thread pool, so the blocking OpenAI call is fine.
    reply = agent.chat(body.message, session_id=body.session_id)
    return ChatOut(
        session_id=reply.session_id,
        reply=reply.text,
        tool_calls=[ToolCallOut(name=c.name, arguments=c.arguments) for c in reply.tool_calls],
    )


@app.post("/chat/stream")
def chat_stream(body: ChatIn, agent: Agent = Depends(get_agent)) -> StreamingResponse:
    """Server-Sent Events: `tool` events while the agent works, then `done` (or `error`)."""
    events: queue.Queue = queue.Queue()

    def on_tool(name: str, args: dict[str, Any]) -> None:
        events.put(("tool", {"name": name, "label": describe(name, args), "arguments": args}))

    def work() -> None:
        try:
            reply = agent.chat(body.message, session_id=body.session_id, on_tool_call=on_tool)
            events.put(("done", {"session_id": reply.session_id, "reply": reply.text}))
        except Exception as exc:  # surface API/network errors to the UI
            events.put(("error", {"message": f"{type(exc).__name__}: {exc}"}))

    threading.Thread(target=work, daemon=True).start()

    def stream() -> Iterator[str]:
        while True:
            kind, data = events.get()
            yield f"event: {kind}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            if kind in {"done", "error"}:
                break

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/sessions/{session_id}/turns")
def turns(session_id: str, agent: Agent = Depends(get_agent)) -> dict[str, Any]:
    """Conversation grouped by turn, with friendly tool labels and saved feedback."""
    return {
        "turns": _turns(agent.store.load(session_id)),
        "feedback": agent.store.get_feedback(session_id),
    }


@app.get("/sessions/{session_id}/messages")
def history(session_id: str, agent: Agent = Depends(get_agent)) -> list[dict[str, Any]]:
    """Customer-visible history (tool messages omitted)."""
    return [
        {"role": m["role"], "content": m["content"]}
        for m in agent.store.load(session_id)
        if m["role"] in {"user", "assistant"} and m.get("content")
    ]


@app.post("/feedback")
def feedback(body: FeedbackIn, agent: Agent = Depends(get_agent)) -> dict[str, str]:
    agent.store.save_feedback(body.session_id, body.turn, body.score)
    return {"status": "ok"}


@app.get("/tickets")
def tickets(agent: Agent = Depends(get_agent)) -> list[dict[str, Any]]:
    """Tickets opened by the agent (what the human team would work on)."""
    return agent.store.list_tickets()
