"""One-turn chat orchestration and persistence.

This module is the bridge between the UI and the backend helpers. It takes a
user prompt, runs orchestration, streams the answer into the interface, and
saves the finished assistant message. Keeping that lifecycle in one place makes
the app easier to trace from input to saved output.
"""

from typing import Any

import streamlit as st

from config import MAX_CONTEXT_CHARS
from agents import build_agent_plan
from llm import build_turn_instructions, fit_messages_to_budget, format_provider_error, stream_response
from sessions import now_eastern, save_chat_session
from ui import render_retrieval_matches


def handle_chat_turn(prompt: str, sidebar_settings: dict[str, Any], indexed_doc_count: int) -> None:
    """Handle one full user turn from prompt entry through saved assistant reply.

    This function appends the user message, optionally runs retrieval, trims the
    prompt to fit budget, streams the model response, and persists the result.
    """
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt,
            "timestamp": now_eastern(),
        }
    )

    retrieval_matches = []
    context = ""
    sources: list[str] = []
    activity: dict[str, Any] = {
        "primary_agent": "orchestrator",
        "specialists": [],
        "tools_used": [],
        "route_label": "direct",
        "route_reason": "The orchestrator answered directly without delegating.",
        "timeline": [],
        "specialist_outputs": [],
    }
    agent_notes = ""
    specialist_outputs: list[dict[str, Any]] = []

    # Agent planning happens before the final model call so the UI can explain
    # which specialist roles were chosen and why.
    try:
        agent_plan = build_agent_plan(prompt, sidebar_settings, indexed_doc_count=indexed_doc_count)
        retrieval_matches = agent_plan["retrieval_matches"]
        context = agent_plan["context"]
        sources = agent_plan["sources"]
        activity = agent_plan["activity"]
        agent_notes = agent_plan["agent_notes"]
        specialist_outputs = agent_plan["specialist_outputs"]
    except Exception as exc:
        st.warning(f"Agent planning fell back to direct chat mode: {exc}")

    if retrieval_matches and sidebar_settings["show_context"]:
        render_retrieval_matches(retrieval_matches, sources, MAX_CONTEXT_CHARS)

    instructions = build_turn_instructions(
        sidebar_settings["custom_system_prompt"],
        context=context,
        agent_notes=agent_notes,
        specialist_outputs=specialist_outputs,
    )
    # The final instruction block is where the app combines system prompt,
    # specialist handoffs, and retrieved context into one model-facing request.

    # Trim locally before sending the request so the app can explain the change
    # instead of failing with a token-limit error from the API.
    api_messages, adjusted_max_tokens = fit_messages_to_budget(
        instructions,
        st.session_state.messages,
        sidebar_settings["max_tokens"],
    )

    if adjusted_max_tokens != sidebar_settings["max_tokens"]:
        st.caption(f"Adjusted max output tokens to {adjusted_max_tokens} to fit the current context budget.")

    trimmed_message_count = len(st.session_state.messages) - len(api_messages)
    if trimmed_message_count > 0:
        st.caption(f"Trimmed {trimmed_message_count} earlier message(s) to fit the current context budget.")

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        try:
            # Stream partial text to keep the chat responsive and make the flow
            # feel like a modern assistant UI.
            for partial_response in stream_response(
                model=st.session_state.selected_model,
                instructions=instructions,
                messages=api_messages,
                temperature=sidebar_settings["temperature"],
                max_output_tokens=adjusted_max_tokens,
                agent_activity=activity,
                sources=sources,
                specialist_outputs=specialist_outputs,
            ):
                full_response = partial_response
                placeholder.markdown(full_response)
        except Exception as exc:
            full_response = format_provider_error(exc)
            placeholder.error(full_response)

        if full_response.strip():
            placeholder.markdown(full_response)
            if sources:
                st.caption("Sources: " + ", ".join(sources))

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": full_response,
                    "timestamp": now_eastern(),
                    "sources": sources,
                    "model": st.session_state.selected_model,
                    "activity": activity,
                }
            )
            save_chat_session(st.session_state.current_session_id, st.session_state.messages)
