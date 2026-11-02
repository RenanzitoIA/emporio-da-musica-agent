"""Terminal chat: python -m emporio.cli [--session ID] [--debug]"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from emporio.agent import Agent
from emporio.store import Store

HELP = "Comandos: /novo (nova conversa), /sair, /debug (mostra ferramentas usadas)"


def main() -> None:
    parser = argparse.ArgumentParser(description="Empório da Música — assistente de atendimento")
    parser.add_argument("--session", help="continua uma conversa salva")
    parser.add_argument("--debug", action="store_true", help="mostra as chamadas de ferramenta")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.WARNING)

    agent = Agent()
    session = args.session or Store.new_session_id()
    debug = args.debug
    print(f"Empório da Música — sessão {session}. {HELP}\n")

    while True:
        try:
            text = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text == "/sair":
            break
        if text == "/novo":
            session = Store.new_session_id()
            print(f"(nova sessão {session})\n")
            continue
        if text == "/debug":
            debug = not debug
            print(f"(debug {'ligado' if debug else 'desligado'})\n")
            continue

        reply = agent.chat(text, session_id=session)
        if debug:
            for call in reply.tool_calls:
                print(f"  [tool] {call.name}({json.dumps(call.arguments, ensure_ascii=False)})")
        print(f"\nLia: {reply.text}\n")


if __name__ == "__main__":
    main()
