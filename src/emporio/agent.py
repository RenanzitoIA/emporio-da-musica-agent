"""The agent loop: plain OpenAI function calling, no framework.

    user message -> model -> (tool calls -> tools -> model)* -> answer

The loop is ~60 lines on purpose: every step is visible, easy to debug and
easy to port to another provider.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from openai import OpenAI

from emporio.config import Settings
from emporio.data import StoreData
from emporio.prompts import build_system_prompt
from emporio.store import Store
from emporio.tools import StoreTools, dispatch, tool_schemas

log = logging.getLogger("emporio.agent")

MAX_TOOL_ROUNDS = 6       # guard against tool-call loops
HISTORY_MESSAGES = 40     # sliding window sent to the model


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]


@dataclass
class Reply:
    session_id: str
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)


class Agent:
    def __init__(self, settings: Settings | None = None, client: OpenAI | None = None,
                 store: Store | None = None, data: StoreData | None = None):
        self.settings = settings or Settings.from_env()
        self.client = client or OpenAI()
        self.store = store or Store(self.settings.history_db)
        self.tools = StoreTools(data or StoreData.load(), now=self.settings.now, tickets=self.store)
        self.schemas = tool_schemas(self.tools.categories)

    def chat(self, message: str, session_id: str | None = None,
             on_tool_call: Callable[[str, dict[str, Any]], None] | None = None) -> Reply:
        """Answer one user message. `on_tool_call(name, args)` fires before each tool
        runs, so a UI can show live progress ("searching the catalog...")."""
        session_id = session_id or Store.new_session_id()
        history = _trim(self.store.load(session_id))
        new: list[dict[str, Any]] = [{"role": "user", "content": message}]
        calls: list[ToolCall] = []

        for _ in range(MAX_TOOL_ROUNDS):
            response = self.client.chat.completions.create(
                model=self.settings.model,
                messages=[{"role": "system", "content": build_system_prompt(self.settings.now())},
                          *history, *new],
                tools=self.schemas,
                **self._model_options(),
            )
            msg = response.choices[0].message
            if not msg.tool_calls:
                text = (msg.content or "").strip()
                new.append({"role": "assistant", "content": text})
                break

            new.append(msg.model_dump(include={"role", "content", "tool_calls"}, exclude_none=True))
            for tc in msg.tool_calls:
                if on_tool_call:
                    on_tool_call(tc.function.name, _loads(tc.function.arguments))
                output = dispatch(self.tools, tc.function.name, tc.function.arguments, session_id)
                log.info("tool %s(%s) -> %s", tc.function.name, tc.function.arguments, output[:200])
                calls.append(ToolCall(tc.function.name, _loads(tc.function.arguments), _loads(output)))
                new.append({"role": "tool", "tool_call_id": tc.id, "content": output})
        else:
            text = ("Desculpe, me enrolei aqui para encontrar essa informação. "
                    "Posso chamar alguém da equipe para te ajudar?")
            new.append({"role": "assistant", "content": text})

        self.store.append(session_id, new)
        return Reply(session_id=session_id, text=text, tool_calls=calls)

    def _model_options(self) -> dict[str, Any]:
        # Reasoning models (gpt-5*, o*) take reasoning_effort and reject temperature.
        if self.settings.model.startswith(("gpt-5", "o")):
            return {"reasoning_effort": self.settings.reasoning_effort}
        return {"temperature": 0.3}


def _trim(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the last N messages without starting in the middle of a tool exchange."""
    if len(history) <= HISTORY_MESSAGES:
        return history
    cut = history[-HISTORY_MESSAGES:]
    while cut and cut[0]["role"] != "user":
        cut = cut[1:]
    return cut


def _loads(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {"raw": raw}
