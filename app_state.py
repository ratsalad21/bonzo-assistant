"""Session-state setup for the Streamlit app.

This module exists so the rest of the app can assume certain keys already
exist in `st.session_state`. That keeps UI and chat code cleaner and makes the
Streamlit rerun model easier for a beginner to understand.
"""

import streamlit as st

from config import (
    DEFAULT_MULTI_AGENT_ROUTING,
    DEFAULT_USE_CODING_AGENT,
    DEFAULT_USE_RAG,
    DEFAULT_USE_WRITING_AGENT,
    OPENAI_MODEL,
)
from sessions import ensure_active_session, load_chat_session


def initialize_app_state() -> None:
    """Create the Streamlit session_state keys the app expects on each rerun.

    Streamlit re-executes the script frequently, so we use this helper to
    initialize chat/session fields only once per browser session.
    """
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = ensure_active_session()

    if "messages" not in st.session_state:
        st.session_state.messages = load_chat_session(st.session_state.current_session_id)

    if "processed_files" not in st.session_state:
        st.session_state.processed_files = set()

    if "selected_model" not in st.session_state:
        st.session_state.selected_model = OPENAI_MODEL

    # These UI defaults live in session state so toggles survive reruns and
    # still behave like normal application settings from the user's perspective.
    if "use_rag" not in st.session_state:
        st.session_state.use_rag = DEFAULT_USE_RAG

    if "show_context" not in st.session_state:
        st.session_state.show_context = True

    if "show_agent_activity" not in st.session_state:
        st.session_state.show_agent_activity = True

    if "show_agent_debug" not in st.session_state:
        st.session_state.show_agent_debug = False

    if "use_multi_agent_routing" not in st.session_state:
        st.session_state.use_multi_agent_routing = DEFAULT_MULTI_AGENT_ROUTING

    if "use_writing_agent" not in st.session_state:
        st.session_state.use_writing_agent = DEFAULT_USE_WRITING_AGENT

    if "use_coding_agent" not in st.session_state:
        st.session_state.use_coding_agent = DEFAULT_USE_CODING_AGENT
