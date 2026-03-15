"""Sidebar UI for controls, sessions, and document tools.

The sidebar is where the app collects everything that is not the main chat
transcript: status, settings, saved sessions, document management, and learning
toggles. Keeping it in one module makes the app layout easier to reason about.
"""

from typing import Any

import streamlit as st

from config import (
    APP_MODEL_CONTEXT_WINDOW,
    DEFAULT_OUTPUT_TOKENS,
    DEFAULT_MULTI_AGENT_ROUTING,
    DEFAULT_USE_CODING_AGENT,
    DEFAULT_USE_RAG,
    DEFAULT_USE_WRITING_AGENT,
    EMBEDDING_MODEL,
    MIN_OUTPUT_TOKENS,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)
from documents import (
    delete_saved_file,
    get_document_preview,
    get_sample_document_name,
    list_saved_documents,
    process_uploaded_file,
    reindex_document,
    search_document_text,
)
from rag import clear_documents, remove_document
from sessions import (
    create_chat_session,
    delete_chat_session,
    get_chat_session_status,
    list_chat_sessions,
    load_chat_session,
    save_chat_session,
)


def render_sidebar(provider_status: dict[str, Any], indexed_docs: list[dict[str, Any]]) -> dict[str, Any]:
    """Render the full sidebar and return the settings the chat loop needs.

    The sidebar is where we collect runtime controls, session management, model
    settings, and document/RAG options in one place.
    """
    with st.sidebar:
        sessions = list_chat_sessions()
        if not sessions:
            st.session_state.current_session_id = create_chat_session()
            sessions = list_chat_sessions()

        chat_status = get_chat_session_status(st.session_state.current_session_id)

        st.header("Status")
        st.caption("Current hosted assistant health")

        if provider_status["endpoint"] == "mock://local":
            st.success("Mock mode enabled")
            st.caption("This run stays local and avoids paid API calls.")
        elif provider_status["configured"]:
            st.success("OpenAI client configured")
        else:
            st.error("OpenAI client not configured")
            if provider_status["error"]:
                st.caption(provider_status["error"])

        st.caption(f"Endpoint: {OPENAI_BASE_URL or 'https://api.openai.com/v1'}")
        st.caption(f"Embedding model: {EMBEDDING_MODEL}")
        st.caption(f"Indexed docs: {len(indexed_docs)}")
        st.caption(f"Chat sessions: {len(sessions)}")
        st.caption(
            "Agent mode: "
            + ("orchestrator + specialists" if st.session_state.get("use_multi_agent_routing", True) else "direct chat")
        )
        if chat_status["exists"]:
            st.caption(f"Saved messages: {chat_status['message_count']}")
            if chat_status["saved_at"]:
                st.caption(f"Last saved: {chat_status['saved_at']}")

        if st.button("Refresh Status", use_container_width=True):
            st.rerun()

        st.header("Sessions")
        session_options = {f"{item['title']} ({item['message_count']})": item["id"] for item in sessions}
        current_session_label = next(
            (label for label, session_id in session_options.items() if session_id == st.session_state.current_session_id),
            next(iter(session_options)),
        )
        selected_session_label = st.selectbox(
            "Chat sessions",
            list(session_options.keys()),
            index=list(session_options.keys()).index(current_session_label),
        )
        selected_session_id = session_options[selected_session_label]

        if selected_session_id != st.session_state.current_session_id:
            st.session_state.current_session_id = selected_session_id
            st.session_state.messages = load_chat_session(selected_session_id)
            st.rerun()

        if st.button("New Chat Session", use_container_width=True):
            st.session_state.current_session_id = create_chat_session()
            st.session_state.messages = []
            st.rerun()

        if st.button("Delete Current Session", use_container_width=True):
            deleted_id = st.session_state.current_session_id
            if delete_chat_session(deleted_id):
                remaining_sessions = list_chat_sessions()
                if remaining_sessions:
                    st.session_state.current_session_id = remaining_sessions[0]["id"]
                    st.session_state.messages = load_chat_session(st.session_state.current_session_id)
                else:
                    st.session_state.current_session_id = create_chat_session()
                    st.session_state.messages = []
                st.success("Deleted chat session")
                st.rerun()

        st.header("Model")
        selected_model = st.text_input("Active model", value=st.session_state.selected_model or OPENAI_MODEL)
        st.session_state.selected_model = selected_model.strip() or OPENAI_MODEL
        st.caption(f"Requests will use: {st.session_state.selected_model}")

        st.header("Document Upload")
        st.caption("Optional for learning. You can skip documents and start with plain chat.")
        uploaded_file = st.file_uploader("Upload document", type=["txt", "md", "pdf"])
        sample_doc_name = get_sample_document_name()
        sample_doc_indexed = any(doc["source"] == sample_doc_name for doc in indexed_docs)
        sample_doc_saved = sample_doc_name in list_saved_documents()

        if sample_doc_saved:
            st.caption("Bundled sample doc available for a quick first RAG demo.")
            sample_button_label = "Re-index bundled sample doc" if sample_doc_indexed else "Index bundled sample doc"
            if st.button(sample_button_label, use_container_width=True):
                if reindex_document(sample_doc_name):
                    st.success(f"{sample_doc_name} is ready for document search.")
                    st.rerun()

        if uploaded_file is not None:
            file_key = f"{uploaded_file.name}:{uploaded_file.size}"
            if file_key not in st.session_state.processed_files:
                process_uploaded_file(uploaded_file)
                st.session_state.processed_files.add(file_key)
                st.rerun()

        st.header("Knowledge Base")
        st.caption(f"{len(indexed_docs)} indexed document(s)")

        if indexed_docs:
            options = [doc["source"] for doc in indexed_docs]
            selected_doc = st.selectbox("Indexed documents", options)
            selected_entry = next(doc for doc in indexed_docs if doc["source"] == selected_doc)
            chunk_total = selected_entry.get("total_chunks") or selected_entry["chunks"]
            st.caption(f"Chunks: {selected_entry['chunks']} stored / {chunk_total} expected")

            if st.button("Re-index Selected Document", use_container_width=True):
                if reindex_document(selected_doc):
                    st.rerun()

            if st.button("Remove Selected Document", use_container_width=True):
                removed_from_index = remove_document(selected_doc)
                removed_file = delete_saved_file(selected_doc)
                st.session_state.processed_files = {
                    key for key in st.session_state.processed_files if not key.startswith(f"{selected_doc}:")
                }

                if removed_from_index or removed_file:
                    st.success(f"Removed {selected_doc}")
                    st.rerun()
                else:
                    st.warning(f"No stored data found for {selected_doc}")

            if st.button("Clear Indexed Knowledge Base", use_container_width=True):
                deleted_chunks = clear_documents()
                st.session_state.processed_files = set()
                st.success(f"Cleared indexed knowledge base ({deleted_chunks} chunks removed)")
                st.rerun()
        else:
            st.caption("No indexed documents yet.")

        st.header("Document Explorer")
        saved_docs = list_saved_documents()
        if saved_docs:
            explorer_doc = st.selectbox("Saved documents", saved_docs)
            preview_text = get_document_preview(explorer_doc)
            if preview_text:
                with st.expander("Preview document"):
                    st.text(preview_text)

            doc_search_query = st.text_input("Search inside document", key="doc_search_query")
            if doc_search_query.strip():
                matches = search_document_text(explorer_doc, doc_search_query)
                if matches:
                    st.caption(f"Found {len(matches)} match(es)")
                    for index, snippet in enumerate(matches, start=1):
                        st.markdown(f"**Match {index}**")
                        st.text(snippet)
                else:
                    st.caption("No matches found.")
        else:
            st.caption("No saved documents available for preview yet.")

        st.header("Learning Mode")
        st.caption("Start with chat-only first. Turn on RAG after the core OpenAI flow feels solid.")

        # These toggles keep the default experience simple, but let the repo grow
        # into agent-style debugging without a full UI redesign.
        use_multi_agent_routing = st.checkbox(
            "Use multi-agent orchestration",
            value=DEFAULT_MULTI_AGENT_ROUTING,
            key="use_multi_agent_routing",
        )
        use_writing_agent = st.checkbox(
            "Allow writing specialist",
            value=DEFAULT_USE_WRITING_AGENT,
            key="use_writing_agent",
        )
        use_coding_agent = st.checkbox(
            "Allow coding specialist",
            value=DEFAULT_USE_CODING_AGENT,
            key="use_coding_agent",
        )
        use_rag = st.checkbox("Use document search (RAG)", value=DEFAULT_USE_RAG, key="use_rag")
        show_context = st.checkbox("Show retrieved context", value=True, key="show_context")
        show_agent_activity = st.checkbox("Show agent activity", value=True, key="show_agent_activity")
        show_agent_debug = st.checkbox("Show agent debug details", value=False, key="show_agent_debug")

        st.header("Chat Controls")
        if st.button("Clear Chat History"):
            st.session_state.messages = []
            save_chat_session(st.session_state.current_session_id, st.session_state.messages)
            st.rerun()

        if st.button("Save Chat Snapshot", use_container_width=True):
            save_chat_session(st.session_state.current_session_id, st.session_state.messages)
            st.success("Chat saved")

        st.header("Settings")
        # These are intentionally exposed in the UI because tuning them is part
        # of the learning experience for this project.
        temperature = st.slider("Temperature", 0.0, 2.0, 0.7)
        max_tokens = st.slider(
            "Max Output Tokens",
            MIN_OUTPUT_TOKENS,
            min(4096, max(MIN_OUTPUT_TOKENS, APP_MODEL_CONTEXT_WINDOW // 2)),
            min(DEFAULT_OUTPUT_TOKENS, max(MIN_OUTPUT_TOKENS, APP_MODEL_CONTEXT_WINDOW // 6)),
        )
        custom_system_prompt = st.text_area(
            "System Prompt",
            "You are a helpful AI assistant named Bonzo. "
            "Bonzo is warm, practical, and concise.",
            height=100,
        )

    return {
        "use_multi_agent_routing": use_multi_agent_routing,
        "use_writing_agent": use_writing_agent,
        "use_coding_agent": use_coding_agent,
        "use_rag": use_rag,
        "show_context": show_context,
        "show_agent_activity": show_agent_activity,
        "show_agent_debug": show_agent_debug,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "custom_system_prompt": custom_system_prompt,
    }
