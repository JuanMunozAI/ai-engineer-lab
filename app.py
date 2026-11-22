"""app.py - a chat screen for the office-manual assistant.

Usage:
    streamlit run app.py
"""
import streamlit as st

from ask import answer
from llm import MODELS

st.set_page_config(page_title="Lakeside Front Desk Assistant", page_icon="🦷")
st.title("🦷 Lakeside Front Desk Assistant")
st.caption("Answers come only from the office manual. Fictional practice, fake data.")

model = st.sidebar.radio(
    "Model", list(MODELS), format_func=lambda m: f"{m} ({MODELS[m]})"
)
st.sidebar.write("small and big run on this PC. claude uses the API.")

if "chat" not in st.session_state:
    st.session_state.chat = []          # remembers the conversation while the page is open


def show_sources(hits):
    with st.expander("Sources"):
        for i, h in enumerate(hits, 1):
            st.markdown(f"**[{i}]** `{h['source']}` > {h['section']}")


for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["text"])
        if msg.get("hits"):
            show_sources(msg["hits"])

if question := st.chat_input("Ask about policies, insurance, codes..."):
    st.session_state.chat.append({"role": "user", "text": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner(f"Looking it up with {MODELS[model]}..."):
            reply, hits = answer(question, model)
        st.markdown(reply)
        show_sources(hits)
    st.session_state.chat.append({"role": "assistant", "text": reply, "hits": hits})
