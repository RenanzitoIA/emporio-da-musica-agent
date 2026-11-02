"""Streamlit chat UI: streamlit run app.py

Branded chat with live tool-progress, typing effect, feedback buttons and a
conversation that survives page reloads (session id lives in the URL).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st  # noqa: E402

from emporio.agent import Agent  # noqa: E402
from emporio.prompts import ASSISTANT_NAME, store_status  # noqa: E402
from emporio.store import Store  # noqa: E402

st.set_page_config(page_title="Empório da Música · Atendimento", page_icon="🎸",
                   layout="centered", initial_sidebar_state="expanded")
st.markdown(f"<style>{(ROOT / 'ui' / 'style.css').read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True)

AVATAR = {"user": "👤", "assistant": "🎸"}
SUGGESTIONS = [
    ("🎸", "Quais violões disponíveis custam até R$ 1000?"),
    ("💰", "Quanto custa o Takamine GD20? Dá pra parcelar?"),
    ("📦", "Quero saber o status do meu pedido"),
    ("↩️", "Me arrependi da compra, posso devolver?"),
]


# --------------------------------------------------------------------- helpers
@st.cache_resource
def get_agent() -> Agent:
    return Agent()


def md(text: str) -> str:
    """Escape '$' so Streamlit does not render "R$ 10 ... R$ 20" as LaTeX math."""
    return text.replace("$", r"\$")


def describe(name: str, args: dict) -> str:
    """Customer-friendly label for a tool call (no personal data)."""
    if name == "search_products":
        parts = []
        if args.get("query"):
            parts.append(f"“{args['query']}”")
        if args.get("category"):
            parts.append(args["category"].lower())
        if args.get("max_price"):
            parts.append(f"até R$ {args['max_price']:,.0f}".replace(",", "."))
        return "🔎 Buscando no catálogo" + (": " + ", ".join(parts) if parts else "")
    return {
        "get_product_details": "📦 Conferindo detalhes e estoque do produto",
        "list_active_promotions": "🏷️ Verificando promoções ativas",
        "calculate_payment_options": "💳 Calculando Pix, parcelamento e frete",
        "lookup_order": f"🔐 Verificando identidade e consultando o pedido #{args.get('order_id', '?')}",
        "open_ticket": "📝 Registrando chamado para a equipe",
    }.get(name, f"⚙️ {name}")


def turns_from_history(messages: list[dict]) -> list[dict]:
    """Group raw OpenAI messages into UI turns: user text, tool calls, answer."""
    import json

    turns: list[dict] = []
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
                turns[-1]["tools"].append((tc["function"]["name"], args))
        elif m["role"] == "assistant":
            turns[-1]["answer"] = m.get("content") or ""
    return turns


def render_tools(tools: list[tuple[str, dict]], technical: bool) -> None:
    if not tools:
        return
    label = f"Consultei o sistema {len(tools)}x" if len(tools) > 1 else "Consultei o sistema"
    with st.expander(f"✓ {label}", expanded=False):
        for name, args in tools:
            st.markdown(f"<div class='tool-row'>{describe(name, args)}</div>", unsafe_allow_html=True)
            if technical:
                st.code(f"{name}({args})", language="python")


def user_bubble(text: str) -> None:
    # The hidden marker lets the CSS style user messages (custom avatars carry no test id).
    with st.chat_message("user", avatar=AVATAR["user"]):
        st.markdown(f"<span class='msg-user'></span>{md(text)}", unsafe_allow_html=True)


def stream_words(text: str, delay: float = 0.012):
    for word in md(text).split(" "):
        yield word + " "
        time.sleep(delay)


# --------------------------------------------------------------------- state
agent = get_agent()
session_id = st.query_params.get("s")
if not session_id:
    session_id = Store.new_session_id()
    st.query_params["s"] = session_id


def new_conversation() -> None:
    st.query_params["s"] = Store.new_session_id()


def save_feedback(turn: int) -> None:
    value = st.session_state.get(f"fb_{session_id}_{turn}")
    if value is not None:
        agent.store.save_feedback(session_id, turn, int(value))


now = agent.settings.now()
status_text = store_status(now)
is_open = status_text.startswith("ABERTA")

# --------------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown(
        """
        <div class="brand">
          <div class="brand-mark">🎸</div>
          <div><div class="brand-name">Empório da Música</div>
          <div class="brand-tag">Sua música começa aqui.</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    pill = "open" if is_open else "closed"
    st.markdown(
        f"""
        <div class="side-card">
          <div class="side-label">Loja física</div>
          <span class="status-pill"><span class="status-dot {pill}"></span>
          {"Aberta agora" if is_open else "Fechada agora"}</span>
          <div style="margin-top:.55rem">{status_text.split(". ", 1)[-1] if not is_open else status_text.split("(")[-1].rstrip(").")}</div>
        </div>
        <div class="side-card">
          <div class="side-label">Horários</div>
          Seg a sex · <b>9h às 18h</b><br>Sábado · <b>9h às 13h</b><br>Domingo e feriados · fechado
        </div>
        <div class="side-card">
          <div class="side-label">Contato</div>
          Rua 14 de Maio, 3200 · Centro<br>Campo Grande · MS<br>WhatsApp <b>(67) 3321-4500</b>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.button("＋  Nova conversa", on_click=new_conversation, width="stretch")
    technical = st.toggle("Modo técnico", value=False,
                          help="Mostra o nome e os argumentos de cada ferramenta chamada.")
    st.markdown(
        f"<div class='side-foot'>Modelo {agent.settings.model} · data simulada "
        f"{now:%d/%m/%Y %H:%M}<br>Sessão {session_id}</div>",
        unsafe_allow_html=True,
    )

# --------------------------------------------------------------------- header
st.markdown(
    f"""
    <div class="topbar">
      <div class="agent">
        <div class="agent-avatar">{ASSISTANT_NAME[0]}</div>
        <div><div class="agent-name">{ASSISTANT_NAME} · Assistente virtual</div>
        <div class="agent-sub">Consulta estoque, preços e pedidos em tempo real</div></div>
      </div>
      <div class="topbar-badge">{"● Online" if is_open else "● Online · equipe volta no horário comercial"}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------- history
turns = turns_from_history(agent.store.load(session_id))
feedback = agent.store.get_feedback(session_id)
queued = st.session_state.pop("queued", None)

if not turns and not queued:
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-icon">🎶</div>
          <h1>Oi! Eu sou a {ASSISTANT_NAME}.</h1>
          <p>Te ajudo a escolher seu próximo instrumento, conferir preços e promoções,
          acompanhar pedidos e tirar dúvidas sobre trocas, pagamento e entrega.</p>
        </div>
        <div class="suggest-label">Comece por aqui</div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for i, (icon, text) in enumerate(SUGGESTIONS):
        if cols[i % 2].button(f"{icon}  {text}", key=f"sug_{i}", width="stretch"):
            st.session_state["queued"] = text
            st.rerun()

for i, turn in enumerate(turns, start=1):
    user_bubble(turn["user"])
    if turn["answer"]:
        with st.chat_message("assistant", avatar=AVATAR["assistant"]):
            render_tools(turn["tools"], technical)
            st.markdown(md(turn["answer"]))
            key = f"fb_{session_id}_{i}"
            if key not in st.session_state and i in feedback:
                st.session_state[key] = feedback[i]
            st.feedback("thumbs", key=key, on_change=save_feedback, args=(i,))

# --------------------------------------------------------------------- new turn
prompt = st.chat_input(f"Escreva para a {ASSISTANT_NAME}…") or queued
if prompt:
    user_bubble(prompt)
    with st.chat_message("assistant", avatar=AVATAR["assistant"]):
        tools_box = st.empty()
        typing = st.empty()
        typing.markdown(f"<span style='color:var(--muted)'>{ASSISTANT_NAME} está digitando…</span>",
                        unsafe_allow_html=True)
        live: dict = {"status": None}

        def on_tool(name: str, args: dict) -> None:
            if live["status"] is None:
                live["status"] = tools_box.status("Consultando o sistema…", expanded=True)
            live["status"].markdown(f"<div class='tool-row'>{describe(name, args)}</div>",
                                    unsafe_allow_html=True)

        try:
            reply = agent.chat(prompt, session_id=session_id, on_tool_call=on_tool)
        except Exception as exc:  # network / API errors: keep the UI alive
            typing.empty()
            st.error(f"Não consegui responder agora ({type(exc).__name__}). Tente de novo em instantes.")
            st.stop()

        if live["status"] is not None:
            n = len(reply.tool_calls)
            live["status"].update(label=f"✓ Consultei o sistema{f' {n}x' if n > 1 else ''}",
                                  state="complete", expanded=False)
        typing.empty()
        st.write_stream(stream_words(reply.text))
    st.rerun()
