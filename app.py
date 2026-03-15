"""Streamlit entry point for the Bonzo Assistant app.

This file stays intentionally small. Streamlit reruns the script top-to-bottom
on every interaction, so keeping the entry point thin makes the app easier to
follow and easier to debug. Most of the real behavior lives in helper modules.
"""

import streamlit as st

from app_state import initialize_app_state
from chat_flow import handle_chat_turn
from llm import get_provider_status
from rag import list_indexed_documents
from sidebar import render_sidebar
from ui import render_app_chrome, render_chat_history, render_empty_state_banner

# Streamlit reruns this file top-to-bottom on every interaction, so this file
# stays intentionally thin and delegates most behavior to helper modules.
st.set_page_config(page_title="Bonzo Assistant", page_icon=":material/pets:", layout="wide")

initialize_app_state()

provider_status = get_provider_status()
indexed_docs = list_indexed_documents()

render_app_chrome(provider_status, len(indexed_docs))

sidebar_settings = render_sidebar(provider_status, indexed_docs)

starter_prompt = None
if not st.session_state.messages:
    starter_prompt = render_empty_state_banner(len(indexed_docs))

render_chat_history(st.session_state.messages)

chat_prompt = st.chat_input("Ask Bonzo anything...")
# Starter prompts share the same chat handler as typed prompts so the app only
# has one path for processing user turns.
prompt = chat_prompt or starter_prompt

if prompt:
    handle_chat_turn(prompt, sidebar_settings, len(indexed_docs))
