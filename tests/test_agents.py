"""Small routing tests for the agent layer.

These tests focus on the highest-signal question for this module: does the
orchestrator choose the expected specialist path for a few representative
prompts?
"""

import agents


def test_direct_prompt_stays_direct(monkeypatch):
    monkeypatch.setattr(agents, "list_uploaded_documents_tool", lambda: [])

    plan = agents.build_agent_plan(
        "What do you think about this approach?",
        {
            "use_multi_agent_routing": True,
            "use_writing_agent": True,
            "use_coding_agent": True,
            "use_rag": True,
        },
        indexed_doc_count=0,
    )

    assert plan["activity"]["route_label"] == "direct"
    assert plan["specialist_outputs"] == []


def test_coding_prompt_runs_coding_then_writing(monkeypatch):
    monkeypatch.setattr(agents, "list_uploaded_documents_tool", lambda: [])

    plan = agents.build_agent_plan(
        "Can you debug this Python error and suggest a fix?",
        {
            "use_multi_agent_routing": True,
            "use_writing_agent": True,
            "use_coding_agent": True,
            "use_rag": False,
        },
        indexed_doc_count=0,
    )

    assert plan["activity"]["route_label"] == "coding + writing"
    assert [output["agent"] for output in plan["specialist_outputs"]] == ["coding_agent", "writing_agent"]


def test_retrieval_prompt_uses_uploaded_documents(monkeypatch):
    monkeypatch.setattr(agents, "list_uploaded_documents_tool", lambda: ["sample-deploy-note.md"])
    monkeypatch.setattr(
        agents,
        "search_uploaded_documents_tool",
        lambda query, k: {
            "matches": [
                {
                    "source": "sample-deploy-note.md",
                    "chunk": 0,
                    "text": "Use a custom startup command in hosted environments.",
                }
            ],
            "sources": ["sample-deploy-note.md"],
            "context": "[Source: sample-deploy-note.md | Chunk: 0]\nUse a custom startup command in hosted environments.",
        },
    )
    monkeypatch.setattr(
        agents,
        "preview_uploaded_document_tool",
        lambda doc_id: "Use a custom startup command in hosted environments.",
    )

    plan = agents.build_agent_plan(
        "What does sample-deploy-note say about startup commands?",
        {
            "use_multi_agent_routing": True,
            "use_writing_agent": False,
            "use_coding_agent": False,
            "use_rag": True,
        },
        indexed_doc_count=1,
    )

    assert plan["activity"]["route_label"] == "retrieval"
    assert [output["agent"] for output in plan["specialist_outputs"]] == ["retrieval_agent"]
    assert plan["sources"] == ["sample-deploy-note.md"]
