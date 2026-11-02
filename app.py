"""Streamlit chat UI: streamlit run app.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import streamlit as st  # noqa: E402

from emporio.agent import Agent  # noqa: E402
from emporio.store import Store  # noqa: E402

st.set_page_config(page_title="Empório da Música", page_icon="🎸")


def md(text: str) -> str:
    """Escape '$' so Streamlit does not render "R$ 10 ... R$ 20" as LaTeX math."""
    return text.replace("$", r"\$")


@st.cache_resource
def get_agent() -> Agent:
    return Agent()


agent = get_agent()
if "session_id" not in st.session_state:
    st.session_state.session_id = Store.new_session_id()
session_id = st.session_state.session_id

with st.sidebar:
    st.header("Empório da Música")
    st.caption("Sua música começa aqui.")
    st.write(f"Modelo: `{agent.settings.model}`")
    st.write(f"Data simulada: `{agent.settings.now():%d/%m/%Y %H:%M}`")
    st.write(f"Sessão: `{session_id}`")
    show_tools = st.toggle("Mostrar ferramentas usadas", value=True)
    if st.button("Nova conversa"):
        st.session_state.session_id = Store.new_session_id()
        st.session_state.pop("tool_log", None)
        st.rerun()
    st.divider()
    st.caption("Experimente: \"Quais violões até R$ 1000?\", \"Quanto custa o Takamine GD20?\", "
               "\"Me arrependi da compra, posso devolver?\"")

st.title("🎸 Atendimento Empório da Música")
tool_log: dict[int, list] = st.session_state.setdefault("tool_log", {})

turn = 0
for msg in agent.store.load(session_id):
    if msg["role"] == "user":
        turn += 1
        st.chat_message("user").markdown(md(msg["content"]))
    elif msg["role"] == "assistant" and msg.get("content"):
        with st.chat_message("assistant"):
            if show_tools and tool_log.get(turn):
                with st.expander(f"{len(tool_log[turn])} consulta(s) ao sistema"):
                    for call in tool_log[turn]:
                        st.code(f"{call.name}({call.arguments})", language="python")
            st.markdown(md(msg["content"]))

if prompt := st.chat_input("Escreva sua mensagem..."):
    st.chat_message("user").markdown(md(prompt))
    with st.chat_message("assistant"), st.spinner("Consultando..."):
        reply = agent.chat(prompt, session_id=session_id)
    tool_log[turn + 1] = reply.tool_calls
    st.rerun()
