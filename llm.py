"""Prompt assembly, lightweight token budgeting, and response streaming.

This module is where the app turns chat state plus orchestration output into a
provider request. It also owns mock-mode replies so the rest of the app can
exercise the same flow whether calls are local or real.
"""

from typing import Any

from config import (
    APP_MODEL_CONTEXT_WINDOW,
    APPROX_CHARS_PER_TOKEN,
    MAX_CONTEXT_CHARS,
    MAX_HISTORY_MESSAGES,
    MIN_OUTPUT_TOKENS,
    MOCK_MODE,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)
from openai_client import get_openai_client


def get_provider_status() -> dict[str, Any]:
    """Return lightweight provider status for the sidebar.

    This does not ping the API. It simply reports whether the app is configured
    to talk to OpenAI and which endpoint/model settings are active.
    """
    # For a hosted API, config presence is the cheapest status signal to show on every rerun.
    endpoint = OPENAI_BASE_URL or "https://api.openai.com/v1"
    configured = MOCK_MODE or bool(OPENAI_API_KEY)
    return {
        "configured": configured,
        "reachable": configured,
        "endpoint": "mock://local" if MOCK_MODE else endpoint,
        "model": OPENAI_MODEL if not MOCK_MODE else f"{OPENAI_MODEL} (mock)",
        "error": None if configured else "OPENAI_API_KEY is not set.",
    }


def build_api_messages(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Convert stored chat messages into the role/content format the API expects.

    Only user and assistant turns are kept, and only the most recent window of
    messages is included so requests stay manageable.
    """
    api_messages: list[dict[str, str]] = []

    for msg in messages[-MAX_HISTORY_MESSAGES:]:
        role = msg.get("role")
        content = str(msg.get("content", "")).strip()
        if role not in {"user", "assistant"} or not content:
            continue
        api_messages.append({"role": role, "content": content})

    return api_messages


def estimate_text_tokens(text: str) -> int:
    """Estimate token count from character length using a simple heuristic."""
    if not text:
        return 0
    return max(1, (len(text) + APPROX_CHARS_PER_TOKEN - 1) // APPROX_CHARS_PER_TOKEN)


def estimate_messages_tokens(system_prompt: str, messages: list[dict[str, str]]) -> int:
    """Estimate total prompt size for the system prompt plus message list."""
    # This estimate is intentionally rough and slightly conservative. We prefer
    # trimming a little early over sending an oversized request that fails hard.
    token_total = estimate_text_tokens(system_prompt) + 24
    token_total += sum(estimate_text_tokens(msg.get("content", "")) + 12 for msg in messages)
    return token_total


def fit_messages_to_budget(
    system_prompt: str,
    messages: list[dict[str, Any]],
    requested_output_tokens: int,
) -> tuple[list[dict[str, str]], int]:
    """Trim history so the prompt plus output target fits the local budget.

    The function keeps recent turns first, then drops older ones in pairs until
    the request is small enough to send.
    """
    # Reserve space for the answer first, then drop older turns until the prompt
    # fits the local context budget.
    output_tokens = max(
        MIN_OUTPUT_TOKENS,
        min(requested_output_tokens, max(MIN_OUTPUT_TOKENS, APP_MODEL_CONTEXT_WINDOW // 2)),
    )
    budget = max(MIN_OUTPUT_TOKENS, APP_MODEL_CONTEXT_WINDOW - output_tokens - 64)
    recent_messages = messages[-MAX_HISTORY_MESSAGES:]

    while recent_messages:
        api_messages = build_api_messages(recent_messages)
        if estimate_messages_tokens(system_prompt, api_messages) <= budget:
            return api_messages, output_tokens
        recent_messages = recent_messages[2:]

    fallback_messages = build_api_messages(messages[-1:])
    return fallback_messages, output_tokens


def build_turn_instructions(
    base_prompt: str,
    context: str = "",
    agent_notes: str = "",
    specialist_outputs: list[dict[str, Any]] | None = None,
) -> str:
    """Merge the base prompt with orchestrator notes and specialist handoff notes."""
    parts = [base_prompt.strip()]

    if agent_notes.strip():
        parts.append(agent_notes.strip())

    if specialist_outputs:
        # Specialists hand back structured notes so the final answer step can
        # stay one model call instead of a tangle of ad-hoc prompt strings.
        specialist_sections: list[str] = []
        for output in specialist_outputs:
            lines = [
                f"[{output.get('agent', 'specialist')}]",
                f"Purpose: {output.get('purpose', '')}",
                f"Summary: {output.get('summary', '')}",
            ]
            key_points = output.get("key_points", [])
            if key_points:
                lines.append("Key points:")
                lines.extend(f"- {point}" for point in key_points)
            recommendation = output.get("recommendation", "")
            if recommendation:
                lines.append(f"Recommendation: {recommendation}")
            specialist_sections.append("\n".join(lines))

        parts.append("Specialist handoff notes:\n" + "\n\n".join(specialist_sections))

    if context:
        # Retrieved context is inserted into instructions so the model gets one clear
        # policy block telling it how to use the extra material.
        parts.append(
            "You may use the retrieved context below if it is relevant. "
            "When the answer depends on that context, mention the source file names naturally in your answer.\n\n"
            f"Retrieved context:\n{context[:MAX_CONTEXT_CHARS]}"
        )

    return "\n\n".join(part for part in parts if part)


def build_retrieval_instructions(base_prompt: str, context: str) -> str:
    """Backward-compatible wrapper around the newer instruction builder."""
    return build_turn_instructions(base_prompt, context=context)


def format_provider_error(exc: Exception) -> str:
    """Convert raw provider failures into clearer user-facing messages."""
    message = str(exc).strip() or "Unknown provider error."
    lowered = message.lower()

    if "insufficient_quota" in lowered or "quota" in lowered:
        return "The OpenAI request reached the API, but the account does not have enough quota or billing set up."
    if "api key" in lowered or "authentication" in lowered or "unauthorized" in lowered:
        return "The OpenAI API key looks missing or invalid. Check `OPENAI_API_KEY` in `.env`."
    if "connection error" in lowered or "unsupportedprotocol" in lowered:
        return "The app could not reach the provider endpoint. Check your internet connection and `OPENAI_BASE_URL`."
    if "timeout" in lowered:
        return "The request took too long. Try a shorter prompt or try again in a moment."
    return f"Request failed: {message}"


def _pick_mock_intro(route_label: str | None, prompt: str) -> str:
    """Choose a natural-sounding opening line for mock mode."""
    if route_label == "retrieval":
        return "I checked the uploaded material and here is the clearest summary."
    if route_label and "retrieval" in route_label and "writing" in route_label:
        return "I used the uploaded notes and cleaned the answer up so it reads clearly."
    if route_label and "retrieval" in route_label and "coding" in route_label:
        return "I grounded this answer in the uploaded notes and focused on the technical details."
    if route_label and "writing" in route_label:
        return "Here is a cleaner rewrite that keeps the original intent."
    if route_label and "coding" in route_label:
        return "Here is the technical explanation with the most important implementation details first."
    if "?" in prompt:
        return "Here is the clearest answer I can give from the current app context."
    return "Here is a helpful draft answer."


def _render_mock_specialist_advice(specialist_outputs: list[dict[str, Any]]) -> list[str]:
    """Turn specialist handoffs into readable answer bullets for mock mode."""
    bullets: list[str] = []
    for output in specialist_outputs:
        summary = output.get("summary", "").strip()
        if summary:
            bullets.append(summary)

        for point in output.get("key_points", [])[:2]:
            point = str(point).strip()
            if point:
                bullets.append(point)
    return bullets[:5]


def _build_mock_response(
    latest_user_message: str,
    route_label: str | None,
    sources: list[str],
    specialist_outputs: list[dict[str, Any]],
) -> str:
    """Create a more natural mock response that feels like a real assistant reply."""
    # Mock mode is most useful when it still feels like a normal assistant.
    # That way a beginner can learn the app flow without reading raw debug text.
    intro = _pick_mock_intro(route_label, latest_user_message)
    bullets = _render_mock_specialist_advice(specialist_outputs)

    sections = [intro]

    if bullets:
        sections.append("\n".join(f"- {bullet}" for bullet in bullets))
    else:
        sections.append(
            "This mock response is local, but the app flow is real: chat state, routing, prompt assembly, and persistence are all active."
        )

    if sources:
        sections.append("Relevant source files: " + ", ".join(sources))

    sections.append(
        "Mock mode is on, so this answer is generated locally for learning without making paid API calls."
    )
    return "\n\n".join(section for section in sections if section)


def stream_response(
    model: str,
    instructions: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_output_tokens: int,
    agent_activity: dict[str, Any] | None = None,
    sources: list[str] | None = None,
    specialist_outputs: list[dict[str, Any]] | None = None,
):
    """Stream a chat response from the Responses API as incremental text.

    The caller receives progressively longer response strings so the UI can
    render a live-updating assistant message.
    """
    if MOCK_MODE:
        latest_user_message = next(
            (msg["content"] for msg in reversed(messages) if msg.get("role") == "user"),
            "",
        )
        route_label = (agent_activity or {}).get("route_label")
        cited_sources = sources or []
        specialist_notes = specialist_outputs or []
        mock_text = _build_mock_response(
            latest_user_message=latest_user_message,
            route_label=route_label,
            sources=cited_sources,
            specialist_outputs=specialist_notes,
        )
        full_response = ""
        chunk_size = 24
        for start in range(0, len(mock_text), chunk_size):
            full_response = mock_text[: start + chunk_size]
            yield full_response
        return

    client = get_openai_client()
    full_response = ""

    # Responses API streaming emits structured events; here we only surface text
    # deltas so the UI stays easy to follow.
    stream = client.responses.create(
        model=model,
        input=messages,
        instructions=instructions,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        stream=True,
    )

    for event in stream:
        event_type = getattr(event, "type", "")

        if event_type == "response.output_text.delta":
            delta = getattr(event, "delta", "")
            if delta:
                full_response += delta
                yield full_response
        elif event_type == "error":
            message = getattr(event, "message", "Unknown streaming error.")
            raise RuntimeError(message)
