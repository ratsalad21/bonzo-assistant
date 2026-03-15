import re
from typing import Any

import streamlit as st

from config import SAMPLE_DOC_NAME


def _render_agent_activity(activity: dict[str, Any], debug: bool) -> None:
    """Render a high-level execution summary for one assistant response."""
    # Show a high-level execution summary rather than hidden reasoning text.
    # That keeps the UI useful for learning without pretending to expose internals we should not show.
    primary_agent = activity.get("primary_agent", "orchestrator")
    specialists = activity.get("specialists", [])
    tools_used = activity.get("tools_used", [])
    route_label = activity.get("route_label")
    route_reason = activity.get("route_reason")
    timeline = activity.get("timeline", [])
    available_agents = activity.get("available_agents", [])
    specialist_outputs = activity.get("specialist_outputs", [])
    execution_mode = activity.get("execution_mode")
    max_specialist_steps = activity.get("max_specialist_steps")

    summary_parts = [f"Answered by `{primary_agent}`"]
    if route_label:
        summary_parts.append(f"Route: `{route_label}`")
    if specialists:
        summary_parts.append("Specialists: " + ", ".join(f"`{name}`" for name in specialists))
    if tools_used:
        summary_parts.append("Tools: " + ", ".join(f"`{name}`" for name in tools_used))

    st.caption(" | ".join(summary_parts))

    if debug:
        with st.expander("Agent Activity"):
            st.markdown("**Primary agent:** " + f"`{primary_agent}`")
            if route_reason:
                st.markdown("**Route reason:** " + route_reason)
            if execution_mode:
                execution_summary = f"`{execution_mode}`"
                if max_specialist_steps:
                    execution_summary += f" with up to `{max_specialist_steps}` specialist steps"
                st.markdown("**Execution mode:** " + execution_summary)
            st.markdown(
                "**Specialists used:** "
                + (", ".join(f"`{name}`" for name in specialists) if specialists else "none")
            )
            st.markdown(
                "**Tools used:** "
                + (", ".join(f"`{name}`" for name in tools_used) if tools_used else "none")
            )
            if available_agents:
                st.markdown("**Available agents:** " + ", ".join(f"`{name}`" for name in available_agents))
            if specialist_outputs:
                st.markdown("**Specialist handoffs:**")
                for output in specialist_outputs:
                    st.markdown(f"- `{output['agent']}`: {output['summary']}")
                    for point in output.get("key_points", []):
                        st.caption(point)
            if timeline:
                st.markdown("**Timeline:**")
                for step in timeline:
                    st.markdown(f"- `{step['agent']}` {step['action']}: {step['detail']}")


def render_message_with_code(content: str) -> None:
    """Render markdown content while preserving fenced code blocks separately."""
    parts = re.split(r"```(\w+)?\n?(.*?)\n?```", content, flags=re.DOTALL)

    language = ""
    for index, part in enumerate(parts):
        if index % 3 == 0:
            if part.strip():
                st.markdown(part)
        elif index % 3 == 1:
            language = part or ""
        elif index % 3 == 2:
            if part.strip():
                st.code(part, language=language if language else None)


def render_app_chrome(provider_status: dict[str, Any], indexed_doc_count: int) -> None:
    """Render the top-of-page hero section and shared app styling."""
    status_label = "ONLINE" if provider_status["configured"] else "CONFIG NEEDED"
    status_class = "online" if provider_status["configured"] else "offline"

    st.markdown(
        f"""
        <style>
        :root {{
            --bonzo-bg-top: #c9b193;
            --bonzo-bg-mid: #a98967;
            --bonzo-bg-bottom: #725a45;
            --bonzo-hero-text: #e8dac7;
            --bonzo-subtle-text: rgba(229, 216, 198, 0.82);
            --bonzo-card-bg: rgba(42, 37, 31, 0.28);
            --bonzo-card-border: rgba(242, 222, 194, 0.14);
            --bonzo-card-label: rgba(226, 212, 194, 0.78);
            --bonzo-card-value: #eedfcb;
            --bonzo-banner-bg: rgba(72, 57, 42, 0.9);
            --bonzo-banner-border: rgba(230, 199, 159, 0.16);
            --bonzo-banner-text: #eadbc7;
            --bonzo-sidebar-bg: rgba(38, 31, 24, 0.74);
            --bonzo-sidebar-border: rgba(237, 212, 181, 0.1);
            --bonzo-panel-bg: rgba(48, 39, 30, 0.62);
            --bonzo-panel-border: rgba(233, 206, 174, 0.12);
            --bonzo-panel-text: #f0e2cf;
            --bonzo-input-bg: rgba(34, 28, 22, 0.84);
            --bonzo-input-border: rgba(229, 200, 164, 0.18);
            --bonzo-input-text: #f1e4d2;
            --bonzo-muted-text: rgba(233, 218, 198, 0.76);
            --bonzo-button-bg: linear-gradient(135deg, rgba(98, 69, 42, 0.95), rgba(55, 40, 28, 0.98));
            --bonzo-button-border: rgba(237, 208, 177, 0.14);
            --bonzo-button-text: #f4e7d6;
            --bonzo-retrieval-bg: rgba(45, 36, 27, 0.95);
            --bonzo-retrieval-border: rgba(222, 191, 145, 0.2);
            --bonzo-retrieval-meta: #e0c59d;
            --bonzo-retrieval-text: #efe1ce;
        }}
        .stApp {{
            background:
                radial-gradient(circle at top left, rgba(255, 196, 128, 0.12), transparent 24%),
                radial-gradient(circle at top right, rgba(88, 123, 161, 0.12), transparent 22%),
                linear-gradient(
                    180deg,
                    var(--bonzo-bg-top) 0%,
                    var(--bonzo-bg-mid) 42%,
                    var(--bonzo-bg-bottom) 100%
                );
        }}
        .stApp,
        .stApp p,
        .stApp label,
        .stApp li,
        .stApp span:not([data-baseweb="tag"]) {{
            color: var(--bonzo-panel-text);
        }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, rgba(26, 22, 17, 0.92), var(--bonzo-sidebar-bg));
            border-right: 1px solid var(--bonzo-sidebar-border);
        }}
        [data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
            background: transparent;
        }}
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span {{
            color: var(--bonzo-panel-text);
        }}
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
            color: var(--bonzo-muted-text);
        }}
        [data-testid="stChatMessage"] {{
            background: var(--bonzo-panel-bg);
            border: 1px solid var(--bonzo-panel-border);
            border-radius: 22px;
            box-shadow: 0 14px 30px rgba(29, 20, 14, 0.14);
            padding: 0.2rem 0.2rem 0.35rem;
            backdrop-filter: blur(10px);
            margin-bottom: 0.75rem;
        }}
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] span {{
            color: var(--bonzo-panel-text);
        }}
        [data-testid="stChatMessage"] pre {{
            background: rgba(26, 22, 17, 0.84);
            border: 1px solid rgba(235, 208, 175, 0.12);
            border-radius: 14px;
        }}
        [data-testid="stChatInput"] {{
            background: rgba(31, 26, 21, 0.7);
            border: 1px solid rgba(235, 205, 171, 0.12);
            border-radius: 18px;
            padding: 0.2rem;
            box-shadow: 0 10px 24px rgba(26, 19, 13, 0.18);
        }}
        [data-testid="stChatInput"] textarea,
        .stTextInput input,
        .stTextArea textarea,
        .stNumberInput input,
        [data-baseweb="select"] > div,
        [data-baseweb="base-input"] > div {{
            background: var(--bonzo-input-bg) !important;
            color: var(--bonzo-input-text) !important;
            border: 1px solid var(--bonzo-input-border) !important;
            border-radius: 14px !important;
        }}
        .stTextInput input::placeholder,
        .stTextArea textarea::placeholder,
        [data-testid="stChatInput"] textarea::placeholder {{
            color: rgba(233, 218, 198, 0.46) !important;
        }}
        .stButton > button,
        [data-testid="baseButton-secondary"],
        [data-testid="baseButton-primary"] {{
            background: var(--bonzo-button-bg);
            color: var(--bonzo-button-text);
            border: 1px solid var(--bonzo-button-border);
            border-radius: 14px;
            box-shadow: 0 10px 18px rgba(34, 24, 17, 0.18);
        }}
        .stButton > button:hover,
        [data-testid="baseButton-secondary"]:hover,
        [data-testid="baseButton-primary"]:hover {{
            border-color: rgba(245, 221, 195, 0.22);
            filter: brightness(1.04);
        }}
        .stCheckbox {{
            background: rgba(41, 33, 26, 0.38);
            border: 1px solid rgba(231, 203, 171, 0.08);
            border-radius: 14px;
            padding: 0.35rem 0.55rem;
        }}
        .stSlider [data-baseweb="slider"] {{
            padding-top: 0.35rem;
        }}
        .stSlider [role="slider"] {{
            background: #e0c59d;
            box-shadow: 0 0 0 0.2rem rgba(224, 197, 157, 0.18);
        }}
        .stSlider [data-testid="stTickBar"] {{
            background: rgba(44, 35, 28, 0.4);
        }}
        .stAlert {{
            background: rgba(51, 41, 32, 0.78);
            border: 1px solid rgba(233, 205, 170, 0.12);
            color: var(--bonzo-panel-text);
        }}
        .bonzo-shell {{
            padding: 0 0 1.5rem;
        }}
        .bonzo-hero {{
            overflow: hidden;
            border-radius: 30px;
            padding: 2rem 2.1rem 1.75rem;
            background:
                radial-gradient(circle at 20% 20%, rgba(255, 219, 171, 0.16), transparent 24%),
                linear-gradient(135deg, rgba(24, 37, 49, 0.98), rgba(54, 36, 23, 0.97));
            box-shadow: 0 18px 44px rgba(38, 27, 16, 0.28);
            color: var(--bonzo-hero-text);
            margin-bottom: 1rem;
        }}
        .bonzo-kicker {{
            display: inline-block;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.14);
            font-size: 0.73rem;
            letter-spacing: 0.12em;
            font-weight: 700;
        }}
        .bonzo-title {{
            margin: 0.85rem 0 0.25rem;
            font-size: 2.4rem;
            line-height: 1;
            font-weight: 800;
            letter-spacing: -0.04em;
        }}
        .bonzo-subtitle {{
            margin: 0;
            max-width: 48rem;
            color: var(--bonzo-subtle-text);
            font-size: 1rem;
        }}
        .bonzo-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.75rem;
            margin-top: 1.15rem;
        }}
        .bonzo-card {{
            background: var(--bonzo-card-bg);
            border: 1px solid var(--bonzo-card-border);
            border-radius: 18px;
            padding: 0.85rem 0.95rem;
            backdrop-filter: blur(8px);
        }}
        .bonzo-label {{
            font-size: 0.72rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--bonzo-card-label);
            margin-bottom: 0.35rem;
        }}
        .bonzo-value {{
            font-size: 1rem;
            font-weight: 700;
            color: var(--bonzo-card-value);
            word-break: break-word;
        }}
        .bonzo-status::before {{
            content: "";
            width: 0.65rem;
            height: 0.65rem;
            border-radius: 999px;
            display: inline-block;
            margin-right: 0.45rem;
        }}
        .bonzo-status.online::before {{
            background: #73f0ac;
            box-shadow: 0 0 0 0.18rem rgba(115, 240, 172, 0.18);
        }}
        .bonzo-status.offline::before {{
            background: #ff8f7d;
            box-shadow: 0 0 0 0.18rem rgba(255, 143, 125, 0.16);
        }}
        .bonzo-banner {{
            border-radius: 18px;
            padding: 0.9rem 1rem;
            background: var(--bonzo-banner-bg);
            border: 1px solid var(--bonzo-banner-border);
            color: var(--bonzo-banner-text);
            margin-bottom: 0.75rem;
        }}
        .bonzo-retrieval-card {{
            background: var(--bonzo-retrieval-bg);
            border: 1px solid var(--bonzo-retrieval-border);
            border-radius: 16px;
            padding: 0.85rem 0.95rem;
            margin: 0.75rem 0;
        }}
        .bonzo-retrieval-meta {{
            color: var(--bonzo-retrieval-meta);
            font-size: 0.92rem;
            font-weight: 700;
            margin-bottom: 0.55rem;
        }}
        .bonzo-retrieval-text {{
            color: var(--bonzo-retrieval-text);
            white-space: pre-wrap;
            line-height: 1.5;
            font-size: 0.96rem;
        }}
        @media (max-width: 900px) {{
            .bonzo-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
            .bonzo-title {{
                font-size: 2rem;
            }}
        }}
        </style>
        <div class="bonzo-shell">
          <div class="bonzo-hero">
            <div class="bonzo-kicker">HOSTED OPENAI ASSISTANT</div>
            <div class="bonzo-title">Bonzo Assistant</div>
            <p class="bonzo-subtitle">
              Streamlit chat with OpenAI responses, persistent sessions, and optional document-aware retrieval.
            </p>
            <div class="bonzo-grid">
              <div class="bonzo-card">
                <div class="bonzo-label">Provider Status</div>
                <div class="bonzo-value bonzo-status {status_class}">{status_label}</div>
              </div>
              <div class="bonzo-card">
                <div class="bonzo-label">Active Model</div>
                <div class="bonzo-value">{st.session_state.selected_model}</div>
              </div>
              <div class="bonzo-card">
                <div class="bonzo-label">Indexed Docs</div>
                <div class="bonzo-value">{indexed_doc_count}</div>
              </div>
              <div class="bonzo-card">
                <div class="bonzo-label">Stack</div>
                <div class="bonzo-value">OpenAI + Chroma + Agents</div>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state_banner(indexed_doc_count: int) -> str | None:
    """Render the first-run empty state and return an optional starter prompt."""
    st.markdown(
        """
        <div class="bonzo-banner">
          <strong>System ready.</strong> Start with one of the guided prompts below, then try the bundled sample document when you want to learn the RAG path.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Starter prompts help you see plain chat, writing help, and coding help without guessing what to ask.")

    prompt_options = [
        "What can you help me learn in this app?",
        "Rewrite this into a friendlier update for the team.",
        "Can you debug this Python error and suggest a fix?",
    ]
    if indexed_doc_count > 0:
        prompt_options.append(f"What does {SAMPLE_DOC_NAME} say about startup commands?")

    starter_prompt = None
    columns = st.columns(len(prompt_options))
    for index, prompt_text in enumerate(prompt_options):
        if columns[index].button(prompt_text, key=f"starter_prompt_{index}", use_container_width=True):
            starter_prompt = prompt_text

    if indexed_doc_count == 0:
        st.caption(
            f"Tip: use `Index bundled sample doc` in the sidebar to add `{SAMPLE_DOC_NAME}` and try a document-aware question."
        )
    return starter_prompt


def render_chat_history(messages: list[dict[str, Any]]) -> None:
    """Render the saved conversation transcript in chat-message components."""
    show_agent_activity = st.session_state.get("show_agent_activity", True)
    show_agent_debug = st.session_state.get("show_agent_debug", False)

    for message in messages:
        with st.chat_message(message["role"]):
            render_message_with_code(message["content"])
            if message.get("timestamp"):
                st.caption(f"_{message['timestamp'].strftime('%I:%M %p')}_")
            if message.get("sources"):
                st.caption("Sources: " + ", ".join(message["sources"]))
            if message.get("role") == "assistant" and show_agent_activity and message.get("activity"):
                _render_agent_activity(message["activity"], debug=show_agent_debug)


def render_retrieval_matches(
    retrieval_matches: list[dict[str, Any]],
    sources: list[str],
    max_context_chars: int,
) -> None:
    """Render retrieved document chunks in an expandable debug-friendly panel."""
    expander_label = f"Retrieved {len(retrieval_matches)} chunks from {len(sources)} document(s)"
    with st.expander(expander_label):
        if sources:
            st.markdown("**Sources:** " + ", ".join(sources))

        for match in retrieval_matches:
            similarity = match.get("similarity")
            similarity_text = f"{similarity * 100:.0f}% match" if isinstance(similarity, float) else "match"
            st.markdown(
                f"""
                <div class="bonzo-retrieval-card">
                  <div class="bonzo-retrieval-meta">{match['source']} | chunk {match['chunk']} | {similarity_text}</div>
                  <div class="bonzo-retrieval-text">{match["text"][:max_context_chars]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
