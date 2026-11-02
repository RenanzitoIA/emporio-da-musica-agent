"""Run scripted multi-turn conversations against the real model and save them
as Markdown in examples/ (including which tools were called).

    python scripts/run_examples.py            # all scenarios
    python scripts/run_examples.py 04         # only scenarios whose file starts with 04
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from emporio.agent import Agent
from emporio.store import Store

OUT = Path(__file__).resolve().parents[1] / "examples"

SCENARIOS = [
    ("01-catalogo-violoes-ate-1000", "Catalog search with price filter + installment follow-up", [
        "Oi! Quais opções de violões disponíveis custando até R$1000?",
        "Gostei do Yamaha C40. Dá pra parcelar? E o frete pra Campo Grande?",
    ]),
    ("02-informacoes-e-fora-do-escopo", "Store info from the policy manual + out-of-scope requests", [
        "Qual o endereço da loja? Vocês abrem domingo?",
        "Vocês vendem cordas e palhetas?",
        "E você me passa uma receita de bolo de cenoura?",
    ]),
    ("03-preco-promocao-e-pix", "Price lookup, expired vs. active promotion, non-cumulative Pix discount", [
        "Quanto custa o Takamine GD20?",
        "Ele não estava com promoção de Oferta Especial?",
        "E o Crafter HT-100? Se eu pagar no Pix tem os 5% em cima da promoção?",
    ]),
    ("04-devolucao-arrependimento", "Non-trivial: order lookup with identity check + return policy applied to real dates", [
        "Me arrependi da minha compra, posso devolver meu pedido?",
        "É o pedido 7",
        "Letícia Gonçalves Rocha",
        "Na verdade o ukulele começou a trastejar, acho que veio com defeito. E agora?",
    ]),
    ("05-pedido-atrasado-e-chamado", "Failed verification, late delivery, complaint ticket, out-of-stock product", [
        "Cadê meu pedido 8? Era pra ter chegado faz tempo",
        "Ana Souza",
        "Meu telefone é (67) 99654-7821",
        "Quero registrar uma reclamação, pode ser?",
        "Pode abrir sim. Aproveitando: o violão Giannini GF-3D tem em estoque?",
    ]),
]


def render(title: str, description: str, session_id: str, turns: list) -> str:
    lines = [f"# {title}", "", f"> {description}", f">", f"> Session `{session_id}`", ""]
    for user, reply in turns:
        lines += [f"**Cliente:** {user}", ""]
        for call in reply.tool_calls:
            args = json.dumps(call.arguments, ensure_ascii=False)
            lines.append(f"<sub>🔧 `{call.name}({args})`</sub>  ")
        if reply.tool_calls:
            lines.append("")
        lines += [f"**Lia:** {reply.text}", "", "---", ""]
    return "\n".join(lines)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    agent = Agent()
    OUT.mkdir(exist_ok=True)
    for slug, description, messages in SCENARIOS:
        if not slug.startswith(only):
            continue
        session = Store.new_session_id()
        turns = []
        for message in messages:
            turns.append((message, agent.chat(message, session_id=session)))
        title = slug.split("-", 1)[1].replace("-", " ").capitalize()
        text = render(title, description, session, turns)
        (OUT / f"{slug}.md").write_text(text, encoding="utf-8")
        print(text)


if __name__ == "__main__":
    main()
