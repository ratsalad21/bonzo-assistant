from pathlib import Path

import streamlit as st
from pypdf import PdfReader

from config import DOC_PREVIEW_CHARS, DOC_SEARCH_RESULTS, DOCS_DIR, MAX_FILE_SIZE, SAMPLE_DOC_NAME
from rag import add_document


def get_sample_document_name() -> str:
    """Return the bundled sample document name used for first-run demos."""
    return SAMPLE_DOC_NAME


def humanize_document_error(exc: Exception) -> str:
    """Convert raw document-processing failures into beginner-friendly messages."""
    message = str(exc).strip() or "Unknown document error."
    lowered = message.lower()

    if "password" in lowered or "encrypted" in lowered:
        return "This PDF is password protected, so the app cannot read it yet."
    if "no readable text" in lowered:
        return "The file did not contain readable text, so there was nothing to index."
    if "no valid chunks" in lowered:
        return "The file was too short or too empty to turn into searchable chunks."
    if "utf" in lowered or "decode" in lowered:
        return "The app could not read the file text cleanly. Try saving it as UTF-8 text or PDF."
    return f"Something went wrong while processing the document: {message}"


def save_uploaded_file(uploaded_file) -> Path:
    """Persist an uploaded file into the configured docs directory."""
    file_path = DOCS_DIR / uploaded_file.name
    file_path.write_bytes(uploaded_file.getbuffer())
    return file_path


def delete_saved_file(doc_id: str) -> bool:
    """Delete one saved source document from disk if it exists."""
    file_path = DOCS_DIR / doc_id
    if file_path.exists():
        file_path.unlink()
        return True
    return False


def extract_text_from_pdf(file_path: Path) -> str:
    """Read text from a PDF while rejecting encrypted or unreadable files."""
    with open(file_path, "rb") as handle:
        reader = PdfReader(handle)

        if reader.is_encrypted:
            raise ValueError("PDF is password protected")

        texts = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                texts.append(text)

        if not texts:
            raise ValueError("No readable text found in PDF")

        return "\n\n".join(texts)


def extract_text(file_path: Path) -> str:
    """Read text from either a plain-text file or a PDF."""
    if file_path.suffix.lower() == ".pdf":
        return extract_text_from_pdf(file_path)

    with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
        return handle.read()


def process_uploaded_file(uploaded_file) -> None:
    """Save, extract, embed, and index one uploaded document for retrieval."""
    file_size = len(uploaded_file.getbuffer())
    if file_size > MAX_FILE_SIZE:
        st.error("That file is too large for this demo app right now. The current limit is 10 MB.")
        return

    try:
        with st.spinner("Saving document..."):
            file_path = save_uploaded_file(uploaded_file)

        with st.spinner("Extracting text..."):
            text = extract_text(file_path)

        if len(text) > 100000:
            st.warning("Large document detected. Processing may take longer.")

        with st.spinner("Generating embeddings..."):
            chunk_count = add_document(text, doc_id=uploaded_file.name)

        st.success(f"{uploaded_file.name} added to the knowledge base ({chunk_count} chunks)")
    except Exception as exc:
        st.error(humanize_document_error(exc))


def reindex_document(doc_id: str) -> bool:
    """Re-run extraction and indexing for an already saved document."""
    file_path = DOCS_DIR / doc_id
    if not file_path.exists():
        st.error(f"Could not find `{doc_id}` in the local docs folder.")
        return False

    try:
        with st.spinner(f"Re-indexing {doc_id}..."):
            text = extract_text(file_path)
            chunk_count = add_document(text, doc_id=doc_id)
        st.success(f"Re-indexed {doc_id} ({chunk_count} chunks)")
        return True
    except Exception as exc:
        st.error(humanize_document_error(exc))
        return False


def list_saved_documents() -> list[str]:
    """List saved document filenames for explorer and management controls."""
    return sorted(
        [path.name for path in DOCS_DIR.iterdir() if path.is_file() and not path.name.startswith(".")],
        key=str.lower,
    )


def get_document_preview(doc_id: str, max_chars: int = DOC_PREVIEW_CHARS) -> str:
    """Load a short preview snippet for one saved document."""
    file_path = DOCS_DIR / doc_id
    if not file_path.exists():
        return ""

    try:
        text = extract_text(file_path)
    except Exception as exc:
        return f"Failed to preview document: {exc}"

    text = text.strip()
    if not text:
        return "Document is empty."
    return text[:max_chars]


def search_document_text(doc_id: str, query: str, max_results: int = DOC_SEARCH_RESULTS) -> list[str]:
    """Run a simple substring search inside one saved document.

    This is a local text search for the explorer UI, not the embedding-based
    retrieval path used for answering questions.
    """
    if not query.strip():
        return []

    file_path = DOCS_DIR / doc_id
    if not file_path.exists():
        return []

    try:
        text = extract_text(file_path)
    except Exception:
        return []

    lower_text = text.lower()
    lower_query = query.lower()
    matches: list[str] = []
    start = 0

    while len(matches) < max_results:
        index = lower_text.find(lower_query, start)
        if index == -1:
            break
        snippet_start = max(0, index - 120)
        snippet_end = min(len(text), index + len(query) + 180)
        snippet = text[snippet_start:snippet_end].replace("\n", " ").strip()
        matches.append(snippet)
        start = index + len(query)

    return matches
