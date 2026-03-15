"""Simple multi-agent orchestration for one chat turn.

This module is the "manager brain" of the app. It decides which specialist
roles should help, runs them in a bounded sequence, and packages their outputs
into handoff notes for the final answer call. The design is intentionally small
so the orchestration stays teachable.
"""

import re
from typing import Any

from agent_tools import (
    list_uploaded_documents_tool,
    preview_uploaded_document_tool,
    search_uploaded_documents_tool,
)
from config import MAX_SPECIALIST_STEPS, RETRIEVAL_K

WRITING_KEYWORDS = {
    "rewrite": "rewrite",
    "rephrase": "rewrite",
    "polish": "rewrite",
    "improve": "rewrite",
    "edit": "rewrite",
    "summarize": "summary",
    "summary": "summary",
    "outline": "outline",
    "bullet": "bullets",
    "bullets": "bullets",
    "email": "email",
    "draft": "draft",
    "tone": "tone",
}
# These keyword maps are deliberately lightweight. They are not meant to be a
# perfect intent-classification system, just a readable first step that shows
# how routing decisions can be encoded in plain Python.
CODING_KEYWORDS = {
    "code": "code",
    "bug": "debug",
    "debug": "debug",
    "error": "debug",
    "exception": "debug",
    "traceback": "debug",
    "python": "python",
    "streamlit": "streamlit",
    "function": "function",
    "class": "class",
    "refactor": "refactor",
    "test": "test",
    "tests": "test",
    "api": "api",
    "yaml": "config",
    "json": "config",
    "docker": "infrastructure",
    "compose": "infrastructure",
    "sql": "data",
    "javascript": "javascript",
    "typescript": "typescript",
}
DOC_HINTS = (
    "document",
    "documents",
    "doc",
    "docs",
    "file",
    "files",
    "pdf",
    "knowledge base",
    "uploaded",
    "source",
    "sources",
)


def _make_specialist_output(
    agent: str,
    purpose: str,
    summary: str,
    key_points: list[str] | None = None,
    recommendation: str | None = None,
) -> dict[str, Any]:
    """Build a consistent specialist payload for orchestrator handoffs."""
    return {
        "agent": agent,
        "purpose": purpose,
        "summary": summary,
        "key_points": key_points or [],
        "recommendation": recommendation or "",
    }


def _normalize_text(text: str) -> str:
    """Lowercase and simplify text for lightweight intent matching."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _append_timeline(activity: dict[str, Any], agent: str, action: str, detail: str) -> None:
    """Add one high-level step to the activity trail shown in the UI."""
    activity.setdefault("timeline", []).append(
        {
            "agent": agent,
            "action": action,
            "detail": detail,
        }
    )


def _record_specialist_output(activity: dict[str, Any], output: dict[str, Any]) -> None:
    """Attach a specialist payload to the activity trace for debug viewing."""
    activity.setdefault("specialist_outputs", []).append(output)


def _has_specialist_output(specialist_outputs: list[dict[str, Any]], agent: str) -> bool:
    """Check whether a given specialist has already run in this turn."""
    return any(output.get("agent") == agent for output in specialist_outputs)


def _detect_writing_goal(prompt: str) -> str | None:
    """Infer whether the user's request sounds like a writing/editing task."""
    normalized_prompt = _normalize_text(prompt)

    for keyword, goal in WRITING_KEYWORDS.items():
        if keyword in normalized_prompt:
            return goal
    return None


def _detect_coding_goal(prompt: str) -> str | None:
    """Infer whether the prompt sounds like a coding or debugging request."""
    normalized_prompt = _normalize_text(prompt)
    tokens = set(normalized_prompt.split())

    for keyword, goal in CODING_KEYWORDS.items():
        if " " in keyword and keyword in normalized_prompt:
            return goal
        if keyword in tokens and keyword not in {"test", "tests"}:
            return goal

    if "tests" in tokens:
        return "test"
    if "test" in tokens and tokens.intersection({"code", "python", "function", "class", "api", "bug", "debug"}):
        return "test"
    return None


def _match_named_document(prompt: str, documents: list[str]) -> str | None:
    """Return the first saved document that appears to be named in the prompt."""
    normalized_prompt = _normalize_text(prompt)
    for doc_name in documents:
        stem = _normalize_text(doc_name.rsplit(".", 1)[0])
        if stem and stem in normalized_prompt:
            return doc_name
    return None


def _should_use_retrieval(prompt: str, use_rag: bool, documents: list[str]) -> bool:
    """Decide whether the retrieval specialist should search the knowledge base."""
    if not use_rag or not documents:
        return False

    normalized_prompt = _normalize_text(prompt)
    if not normalized_prompt:
        return False

    if _match_named_document(prompt, documents):
        return True
    if any(hint in normalized_prompt for hint in DOC_HINTS):
        return True
    source_tokens = {
        token
        for doc_name in documents
        for token in _normalize_text(doc_name.rsplit(".", 1)[0]).split()
        if len(token) > 3
    }
    prompt_tokens = set(normalized_prompt.split())
    return bool(source_tokens.intersection(prompt_tokens))


def _run_retrieval_agent(
    prompt: str,
    documents: list[str],
    activity: dict[str, Any],
) -> tuple[list[dict[str, Any]], str, list[str], dict[str, Any]]:
    """Search the knowledge base and package the retrieval result for handoff."""
    named_document = _match_named_document(prompt, documents) if documents else None
    retrieval_result = search_uploaded_documents_tool(prompt, k=RETRIEVAL_K)
    retrieval_matches = retrieval_result["matches"]
    context = retrieval_result["context"]
    sources = retrieval_result["sources"]

    activity["specialists"].append("retrieval_agent")
    activity["tools_used"].append("search_uploaded_documents")
    _append_timeline(
        activity,
        "retrieval_agent",
        "search",
        f"Searched the uploaded documents and found {len(retrieval_matches)} relevant chunk(s).",
    )

    key_points: list[str] = []
    for match in retrieval_matches[:3]:
        key_points.append(f"{match['source']} chunk {match['chunk']}: {match['text'][:140].strip()}")

    if named_document:
        preview_text = preview_uploaded_document_tool(named_document)
        if preview_text:
            context = (
                f"[Document preview: {named_document}]\n{preview_text}\n\n{context}".strip()
                if context
                else f"[Document preview: {named_document}]\n{preview_text}"
            )
            if named_document not in sources:
                sources.insert(0, named_document)
            activity["tools_used"].append("preview_uploaded_document")
            _append_timeline(
                activity,
                "retrieval_agent",
                "preview",
                f"Loaded a short preview for `{named_document}` because the prompt named that file directly.",
            )
            key_points.insert(0, f"Previewed named document `{named_document}` to give the orchestrator quick local context.")

    if retrieval_matches:
        output = _make_specialist_output(
            agent="retrieval_agent",
            purpose="Ground the answer in uploaded documents.",
            summary=f"Found {len(retrieval_matches)} relevant chunk(s) from {len(sources)} source document(s).",
            key_points=key_points,
            recommendation="Use retrieved context when it is clearly relevant and mention source file names naturally.",
        )
    else:
        output = _make_specialist_output(
            agent="retrieval_agent",
            purpose="Ground the answer in uploaded documents.",
            summary="No strong document matches were found for this prompt.",
            key_points=["Avoid inventing document-backed claims."],
            recommendation="Answer cautiously without pretending the knowledge base supported the answer.",
        )

    _record_specialist_output(activity, output)
    return retrieval_matches, context, sources, output


def _run_writing_agent(writing_goal: str, activity: dict[str, Any]) -> dict[str, Any]:
    """Produce a writing-focused specialist handoff for the orchestrator."""
    _append_timeline(
        activity,
        "writing_agent",
        "shape",
        f"Prepared a `{writing_goal}` style response with extra attention to clarity and tone.",
    )
    activity["specialists"].append("writing_agent")

    key_points = [
        "Keep the answer easy to scan.",
        "Prefer crisp wording over filler.",
    ]
    recommendation = "Return a polished answer that stays faithful to the user's intent."

    if writing_goal == "summary":
        key_points.append("Lead with the key takeaway and compress secondary details.")
    elif writing_goal == "bullets":
        key_points.append("Use bullets if they improve readability.")
    elif writing_goal == "email":
        key_points.append("Shape the answer like a concise email draft.")
    elif writing_goal == "outline":
        key_points.append("Structure the answer like a short outline.")
    elif writing_goal == "rewrite":
        key_points.append("Preserve meaning while improving wording and flow.")
    elif writing_goal == "polish":
        key_points.append("Blend prior specialist findings into one clean final answer.")

    output = _make_specialist_output(
        agent="writing_agent",
        purpose="Improve structure, tone, and presentation.",
        summary=f"Prepared a writing plan for a `{writing_goal}` style response.",
        key_points=key_points,
        recommendation=recommendation,
    )
    _record_specialist_output(activity, output)
    return output


def _run_coding_agent(coding_goal: str, activity: dict[str, Any]) -> dict[str, Any]:
    """Produce a coding-focused specialist handoff for the orchestrator."""
    _append_timeline(
        activity,
        "coding_agent",
        "analyze",
        f"Prepared a `{coding_goal}`-focused technical answer with extra attention to implementation details.",
    )
    activity["specialists"].append("coding_agent")

    key_points = [
        "Be concrete about implementation details.",
        "State assumptions when they matter.",
        "Prefer correct low-risk steps over vague suggestions.",
    ]
    recommendation = "Answer like a careful technical teammate."

    if coding_goal == "debug":
        key_points.append("Highlight likely failure points and the smallest safe fix first.")
    elif coding_goal == "refactor":
        key_points.append("Favor maintainability and clear boundaries.")
    elif coding_goal == "test":
        key_points.append("Include validation or test ideas where useful.")
    elif coding_goal == "infrastructure":
        key_points.append("Call out environment and deployment concerns clearly.")

    output = _make_specialist_output(
        agent="coding_agent",
        purpose="Improve technical accuracy and implementation guidance.",
        summary=f"Prepared a technical response plan focused on `{coding_goal}`.",
        key_points=key_points,
        recommendation=recommendation,
    )
    _record_specialist_output(activity, output)
    return output


def _route_label_from_specialists(activity: dict[str, Any]) -> str:
    """Convert the chosen specialist set into a readable route label."""
    specialists = activity.get("specialists", [])
    if not specialists:
        return "direct"
    return " + ".join(name.replace("_agent", "") for name in specialists)


def _route_reason_from_outputs(outputs: list[dict[str, Any]]) -> str:
    """Summarize why the orchestrator used the chosen specialists."""
    if not outputs:
        return "The orchestrator answered directly without delegating."
    summaries = [f"{output['agent']} ({output['purpose'].rstrip('.')})" for output in outputs]
    return "The orchestrator combined " + ", ".join(summaries) + "."


def _build_orchestrator_notes(
    specialist_outputs: list[dict[str, Any]],
    retrieval_used: bool,
) -> str:
    """Turn specialist payloads into compact handoff notes for the final answer call."""
    notes = [
        "You are the orchestrator for a small learning-oriented multi-agent demo.",
        "Return one polished final answer to the user rather than exposing internal hidden reasoning.",
    ]

    if retrieval_used:
        notes.append("A retrieval specialist already searched the knowledge base. Use the grounded evidence when it is relevant.")

    if specialist_outputs:
        notes.append("You have structured handoff notes from specialist agents. Use them to shape the final answer.")

    return "\n".join(notes)


def _choose_next_specialist(
    prompt: str,
    sidebar_settings: dict[str, Any],
    documents: list[str],
    writing_goal: str | None,
    coding_goal: str | None,
    specialist_outputs: list[dict[str, Any]],
) -> tuple[str | None, str, str | None]:
    """Pick the next specialist to run based on the current orchestration state."""
    # The sequential loop is intentionally rule-based instead of model-driven so
    # the learning flow is easier to inspect and reason about.
    retrieval_ran = _has_specialist_output(specialist_outputs, "retrieval_agent")
    coding_ran = _has_specialist_output(specialist_outputs, "coding_agent")
    writing_ran = _has_specialist_output(specialist_outputs, "writing_agent")

    if (
        not retrieval_ran
        and _should_use_retrieval(prompt, sidebar_settings.get("use_rag", False), documents)
    ):
        return "retrieval_agent", "the prompt appears to depend on uploaded documents", None

    if (
        not coding_ran
        and coding_goal
        and sidebar_settings.get("use_coding_agent", True)
    ):
        return "coding_agent", "the prompt looks technical and benefits from implementation-focused guidance", coding_goal

    if not writing_ran and sidebar_settings.get("use_writing_agent", True):
        if writing_goal:
            return "writing_agent", "the prompt explicitly asks for shaping or rewriting", writing_goal
        if coding_ran:
            return "writing_agent", "a final polishing pass will make the technical answer easier to read", "polish"

    return None, "no additional specialist adds enough value", None


def build_agent_plan(
    prompt: str,
    sidebar_settings: dict[str, Any],
    indexed_doc_count: int | None = None,
) -> dict[str, Any]:
    """Choose specialist agents, tools, and instruction notes for one user turn.

    The orchestrator stays in charge, but it can call specialists, collect
    their handoff payloads, and then compose one final answer.
    """
    documents = list_uploaded_documents_tool() if indexed_doc_count is None or indexed_doc_count > 0 else []
    writing_goal = _detect_writing_goal(prompt)
    coding_goal = _detect_coding_goal(prompt)
    use_multi_agent = sidebar_settings.get("use_multi_agent_routing", True)

    activity: dict[str, Any] = {
        "primary_agent": "orchestrator",
        "available_agents": ["orchestrator", "retrieval_agent", "writing_agent"],
        "specialists": [],
        "tools_used": [],
        "route_label": "direct",
        "route_reason": "The orchestrator answered directly without delegating.",
        "execution_mode": "sequential",
        "max_specialist_steps": MAX_SPECIALIST_STEPS,
        "timeline": [],
        "specialist_outputs": [],
    }
    _append_timeline(
        activity,
        "orchestrator",
        "plan",
        f"Reviewed the prompt and started a sequential orchestration loop with up to {MAX_SPECIALIST_STEPS} specialist step(s).",
    )

    if not use_multi_agent:
        _append_timeline(activity, "orchestrator", "answer", "Multi-agent routing is disabled, so Bonzo answered directly.")
        return {
        "activity": activity,
        "retrieval_matches": [],
        "context": "",
            "sources": [],
            "agent_notes": "Answer directly as Bonzo without delegating to specialist agents.",
            "coding_goal": None,
            "specialist_outputs": [],
            "writing_goal": None,
        }

    retrieval_matches: list[dict[str, Any]] = []
    context = ""
    sources: list[str] = []
    specialist_outputs: list[dict[str, Any]] = []
    activity["available_agents"].append("coding_agent")

    if documents:
        activity["tools_used"].append("list_uploaded_documents")
        _append_timeline(
            activity,
            "orchestrator",
            "inspect",
            f"Checked the local knowledge base and found {len(documents)} saved document(s).",
        )

    loop_completed = True
    for step_number in range(1, MAX_SPECIALIST_STEPS + 1):
        # The hard step limit is our simple stopping rule. It keeps the demo
        # from drifting into endless delegation loops.
        next_agent, delegate_reason, specialist_goal = _choose_next_specialist(
            prompt,
            sidebar_settings,
            documents,
            writing_goal,
            coding_goal,
            specialist_outputs,
        )
        if not next_agent:
            loop_completed = False
            _append_timeline(
                activity,
                "orchestrator",
                "stop",
                f"Stopped after reviewing the current handoff state because {delegate_reason}.",
            )
            break

        _append_timeline(
            activity,
            "orchestrator",
            "delegate",
            f"Step {step_number}: routed to `{next_agent}` because {delegate_reason}.",
        )

        if next_agent == "retrieval_agent":
            retrieval_matches, context, sources, retrieval_output = _run_retrieval_agent(
                prompt,
                documents,
                activity,
            )
            specialist_outputs.append(retrieval_output)
        elif next_agent == "coding_agent" and specialist_goal:
            specialist_outputs.append(_run_coding_agent(specialist_goal, activity))
        elif next_agent == "writing_agent" and specialist_goal:
            specialist_outputs.append(_run_writing_agent(specialist_goal, activity))

    if loop_completed:
        next_agent, _, _ = _choose_next_specialist(
            prompt,
            sidebar_settings,
            documents,
            writing_goal,
            coding_goal,
            specialist_outputs,
        )
        if next_agent:
            _append_timeline(
                activity,
                "orchestrator",
                "stop",
                f"Stopped because the loop reached the safety limit of {MAX_SPECIALIST_STEPS} specialist step(s).",
            )
        else:
            _append_timeline(
                activity,
                "orchestrator",
                "stop",
                "Stopped after using the full orchestration budget because the specialist handoffs were sufficient to compose the final answer.",
            )

    activity["route_label"] = _route_label_from_specialists(activity)
    activity["route_reason"] = _route_reason_from_outputs(specialist_outputs)

    if not activity["specialists"]:
        _append_timeline(activity, "orchestrator", "answer", "Answered directly because no specialist was needed.")
    else:
        specialist_summary = ", ".join(activity["specialists"])
        _append_timeline(
            activity,
            "orchestrator",
            "compose",
            f"Combined specialist input from {specialist_summary} into one final answer.",
        )

    activity["specialist_outputs"] = specialist_outputs

    return {
        "activity": activity,
        "retrieval_matches": retrieval_matches,
        "context": context,
        "sources": sources,
        "agent_notes": _build_orchestrator_notes(specialist_outputs, retrieval_used=bool(retrieval_matches)),
        "coding_goal": coding_goal,
        "specialist_outputs": specialist_outputs,
        "writing_goal": writing_goal,
    }
