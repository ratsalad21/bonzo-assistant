import hashlib
import re
from typing import Any, Optional

import chromadb
from chromadb.config import Settings

from config import CHROMA_DB_PATH, EMBEDDING_MODEL, MOCK_MODE
from openai_client import get_openai_client

client: Optional[chromadb.PersistentClient] = None
collection: Optional[chromadb.Collection] = None

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
COLLECTION_NAME = "documents"
EMBED_BATCH_SIZE = 64
DEFAULT_QUERY_K = 5
QUERY_CANDIDATE_MULTIPLIER = 3
MAX_RESULTS_PER_SOURCE = 2
MAX_DISTANCE = 1.1


def init_rag(path: str | None = None) -> None:
    """Initialize the local Chroma client and collection once per process."""
    global client, collection

    if client is not None and collection is not None:
        return

    # Chroma is a good learning choice because the vector store lives on disk
    # and is easy to inspect without adding another hosted service.
    db_path = path or str(CHROMA_DB_PATH)
    client = chromadb.PersistentClient(
        path=db_path,
        settings=Settings(allow_reset=False),
    )
    collection = client.get_or_create_collection(name=COLLECTION_NAME)


def _stable_chunk_id(doc_id: str, chunk_index: int, chunk_text: str) -> str:
    """Build a repeatable chunk id so re-indexing can replace prior chunks cleanly."""
    digest = hashlib.sha1(chunk_text.encode("utf-8", errors="ignore")).hexdigest()[:12]
    safe_doc_id = doc_id.replace(" ", "_")
    return f"{safe_doc_id}_{chunk_index}_{digest}"


def _similarity_from_distance(distance: Optional[float]) -> Optional[float]:
    """Convert Chroma distance values into a friendlier 0-1 similarity score."""
    if distance is None:
        return None
    return max(0.0, min(1.0, 1.0 - (distance / 2.0)))


def _normalize_lookup_text(text: str) -> str:
    """Normalize text for cheap filename/query matching."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _source_match_score(query: str, source: str) -> int:
    """Score how strongly a filename appears to match the user's query text."""
    normalized_query = _normalize_lookup_text(query)
    normalized_source = _normalize_lookup_text(source)

    if not normalized_query or not normalized_source:
        return 0

    if normalized_source in normalized_query:
        return 3

    source_tokens = [token for token in normalized_source.split() if len(token) > 2]
    if not source_tokens:
        return 0

    matched_tokens = sum(1 for token in source_tokens if token in normalized_query)
    if matched_tokens == len(source_tokens):
        return 2
    if matched_tokens > 0:
        return 1
    return 0


def _embed_texts(texts: list[str]) -> list[list[float]]:
    """Create embeddings for a batch of texts using the configured OpenAI model."""
    if not texts:
        return []

    if MOCK_MODE:
        dimensions = 64
        embeddings: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).digest()
            vector = [((digest[index % len(digest)] / 255.0) * 2.0) - 1.0 for index in range(dimensions)]
            embeddings.append(vector)
        return embeddings

    # Using the hosted embeddings API keeps retrieval aligned with the same
    # provider model as chat, which simplifies the architecture for learning.
    response = get_openai_client().embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]


def _filename_matches(query: str, max_per_source: int) -> list[dict[str, Any]]:
    """Return top chunk candidates based on filename hints before vector search.

    This is a lightweight lexical helper layered on top of semantic retrieval.
    """
    assert collection is not None

    results = collection.get(include=["documents", "metadatas"])
    docs = results.get("documents", []) or []
    metadatas = results.get("metadatas", []) or []

    grouped: dict[str, list[dict[str, Any]]] = {}
    for index, doc in enumerate(docs):
        metadata = metadatas[index] if index < len(metadatas) and metadatas[index] else {}
        source = metadata.get("source")
        if not source:
            continue

        grouped.setdefault(source, []).append(
            {
                "source": source,
                "chunk": metadata.get("chunk", -1),
                "total_chunks": metadata.get("total_chunks"),
                "text": doc,
                "distance": None,
                "similarity": None,
            }
        )

    # This is a cheap lexical hint that helps queries where the filename itself
    # is the strongest clue, which pure semantic search can miss.
    matched_sources = sorted(
        ((source, _source_match_score(query, source)) for source in grouped),
        key=lambda item: (-item[1], item[0].lower()),
    )

    matches: list[dict[str, Any]] = []
    for source, score in matched_sources:
        if score <= 0:
            continue

        source_chunks = sorted(grouped[source], key=lambda item: item.get("chunk", -1))
        matches.extend(source_chunks[:max_per_source])

    return matches


def chunk_text(text: str) -> list[str]:
    """Split a document into overlapping word chunks for embedding and retrieval."""
    # Word-based chunking is simple and easy to reason about, which makes it a
    # good baseline before experimenting with smarter chunking strategies.
    words = text.split()
    if not words:
        return []

    step = max(1, CHUNK_SIZE - CHUNK_OVERLAP)
    chunks: list[str] = []

    for index in range(0, len(words), step):
        chunk_words = words[index : index + CHUNK_SIZE]
        chunk = " ".join(chunk_words).strip()
        if len(chunk) > 50:
            chunks.append(chunk)

    return chunks


def remove_document(doc_id: str) -> bool:
    """Delete all indexed chunks belonging to one source document."""
    init_rag()
    assert collection is not None

    existing = collection.get(where={"source": doc_id}, include=[])
    ids = existing.get("ids", [])
    if ids:
        collection.delete(ids=ids)
        return True
    return False


def list_indexed_documents() -> list[dict[str, Any]]:
    """Summarize indexed documents with chunk counts for the sidebar UI."""
    init_rag()
    assert collection is not None

    results = collection.get(include=["metadatas"])
    metadatas = results.get("metadatas", []) or []

    docs: dict[str, dict[str, Any]] = {}
    for metadata in metadatas:
        if not metadata:
            continue

        source = metadata.get("source")
        if not source:
            continue

        doc_entry = docs.setdefault(
            source,
            {
                "source": source,
                "chunks": 0,
                "total_chunks": metadata.get("total_chunks"),
            },
        )
        doc_entry["chunks"] += 1
        if metadata.get("total_chunks") is not None:
            doc_entry["total_chunks"] = metadata.get("total_chunks")

    return sorted(docs.values(), key=lambda item: item["source"].lower())


def clear_documents() -> int:
    """Delete all indexed chunks and return how many were removed."""
    init_rag()
    assert collection is not None

    results = collection.get(include=[])
    ids = results.get("ids", []) or []
    if ids:
        collection.delete(ids=ids)
    return len(ids)


def add_document(text: str, doc_id: str) -> int:
    """Chunk, embed, and store a document, replacing any older version first."""
    init_rag()
    assert collection is not None

    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("Document produced no valid chunks")

    remove_document(doc_id)

    # Batch embedding keeps requests smaller and mirrors the shape we'd likely
    # want even in a production pipeline.
    embeddings: list[list[float]] = []
    for start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[start : start + EMBED_BATCH_SIZE]
        embeddings.extend(_embed_texts(batch))

    ids = [_stable_chunk_id(doc_id, index, chunk) for index, chunk in enumerate(chunks)]
    metadatas = [
        {
            "source": doc_id,
            "chunk": index,
            "total_chunks": len(chunks),
        }
        for index in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return len(chunks)


def search_documents(
    query: str,
    k: int = DEFAULT_QUERY_K,
    max_distance: float = MAX_DISTANCE,
    max_per_source: int = MAX_RESULTS_PER_SOURCE,
) -> list[dict[str, Any]]:
    """Run hybrid retrieval and return ranked matches for UI and prompt assembly.

    The search first checks filename clues, then queries the vector store, and
    finally limits duplicate-heavy results from the same source.
    """
    init_rag()
    assert collection is not None

    if not query.strip():
        return []

    filename_matches = _filename_matches(query, max_per_source=max_per_source)
    query_embedding = _embed_texts([query])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=max(k * QUERY_CANDIDATE_MULTIPLIER, k),
        include=["documents", "metadatas", "distances"],
    )

    docs = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not docs:
        return []

    matches: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, int, str]] = set()
    per_source_counts: dict[str, int] = {}

    for match in filename_matches:
        dedupe_key = (match["source"], match["chunk"], match["text"])
        if dedupe_key in seen_keys:
            continue
        if per_source_counts.get(match["source"], 0) >= max_per_source:
            continue

        seen_keys.add(dedupe_key)
        per_source_counts[match["source"]] = per_source_counts.get(match["source"], 0) + 1
        matches.append(match)

        if len(matches) >= k:
            return matches

    for index, doc in enumerate(docs):
        metadata = metadatas[index] if index < len(metadatas) and metadatas[index] else {}
        distance = distances[index] if index < len(distances) else None
        source = metadata.get("source", "unknown")
        chunk_num = metadata.get("chunk", -1)
        total_chunks = metadata.get("total_chunks")

        if distance is not None and distance > max_distance:
            continue

        dedupe_key = (source, chunk_num, doc)
        if dedupe_key in seen_keys:
            continue
        if per_source_counts.get(source, 0) >= max_per_source:
            continue

        seen_keys.add(dedupe_key)
        per_source_counts[source] = per_source_counts.get(source, 0) + 1
        matches.append(
            {
                "source": source,
                "chunk": chunk_num,
                "total_chunks": total_chunks,
                "text": doc,
                "distance": distance,
                "similarity": _similarity_from_distance(distance),
            }
        )

        if len(matches) >= k:
            break

    return matches


def format_retrieval_context(matches: list[dict[str, Any]], include_sources: bool = True) -> str:
    """Flatten retrieval matches into a prompt-ready context string."""
    formatted_chunks: list[str] = []

    for match in matches:
        doc = match["text"]
        source = match.get("source", "unknown")
        chunk_num = match.get("chunk", "?")
        if include_sources:
            formatted_chunks.append(f"[Source: {source} | Chunk: {chunk_num}]\n{doc}")
        else:
            formatted_chunks.append(doc)

    return "\n\n".join(formatted_chunks)


def list_sources(matches: list[dict[str, Any]]) -> list[str]:
    """Return unique source filenames in first-seen order for display."""
    seen: set[str] = set()
    sources: list[str] = []

    for match in matches:
        source = match.get("source")
        if source and source not in seen:
            seen.add(source)
            sources.append(source)

    return sources
