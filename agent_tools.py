"""Tool-style wrappers used by the agent layer.

The agents work more cleanly when they call narrow helper functions with simple
inputs and outputs. This module provides that thin wrapper layer around the
document and retrieval code so orchestration stays easier to read.
"""

from typing import Any

from documents import get_document_preview, list_saved_documents
from rag import format_retrieval_context, list_sources, search_documents


def list_uploaded_documents_tool() -> list[str]:
    """Return saved document names so agents can inspect the local knowledge base."""
    return list_saved_documents()


def search_uploaded_documents_tool(query: str, k: int) -> dict[str, Any]:
    """Run retrieval and package matches in a tool-friendly shape.

    The orchestrator and retrieval specialist both benefit from one shared tool
    contract that includes the raw matches plus prompt-ready context.
    """
    matches = search_documents(query, k=k)
    sources = list_sources(matches)
    return {
        "matches": matches,
        "sources": sources,
        "context": format_retrieval_context(matches) if matches else "",
    }


def preview_uploaded_document_tool(doc_id: str, max_chars: int = 800) -> str:
    """Return a short preview snippet for one saved document."""
    return get_document_preview(doc_id, max_chars=max_chars)
