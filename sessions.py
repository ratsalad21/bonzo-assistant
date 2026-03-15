import datetime
import json
import re
from pathlib import Path
from typing import Any

from config import CHAT_HISTORY_DIR, EASTERN


def now_eastern() -> datetime.datetime:
    """Return the current timestamp in the app's display timezone."""
    return datetime.datetime.now(EASTERN)


def slugify_session_name(name: str) -> str:
    """Convert a title into a filesystem-friendly session id fragment."""
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip().lower()).strip("-")
    return slug or "chat"


def session_file_path(session_id: str) -> Path:
    """Map a session id to its JSON file on disk."""
    return CHAT_HISTORY_DIR / f"{session_id}.json"


def derive_session_title(messages: list[dict[str, Any]], fallback: str) -> str:
    """Choose a human-friendly chat title from the first user message."""
    for message in messages:
        if message.get("role") == "user" and message.get("content"):
            title = " ".join(str(message["content"]).split())[:60].strip()
            return title or fallback
    return fallback


def serialize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert in-memory messages into JSON-safe dictionaries for saving."""
    serialized: list[dict[str, Any]] = []
    for message in messages:
        item = dict(message)
        timestamp = item.get("timestamp")
        if isinstance(timestamp, datetime.datetime):
            item["timestamp"] = timestamp.isoformat()
        serialized.append(item)
    return serialized


def deserialize_messages(raw_messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert saved JSON message payloads back into runtime message objects."""
    messages: list[dict[str, Any]] = []
    for raw in raw_messages:
        item = dict(raw)
        timestamp = item.get("timestamp")
        if isinstance(timestamp, str):
            try:
                item["timestamp"] = datetime.datetime.fromisoformat(timestamp)
            except ValueError:
                item["timestamp"] = None
        messages.append(item)
    return messages


def list_chat_sessions() -> list[dict[str, Any]]:
    """Read session files from disk and return sidebar-friendly session metadata."""
    sessions: list[dict[str, Any]] = []
    for path in sorted(CHAT_HISTORY_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            sessions.append(
                {
                    "id": path.stem,
                    "title": payload.get("title") or path.stem,
                    "saved_at": payload.get("saved_at"),
                    "created_at": payload.get("created_at"),
                    "message_count": len(payload.get("messages", [])),
                }
            )
        except Exception:
            sessions.append(
                {
                    "id": path.stem,
                    "title": path.stem,
                    "saved_at": None,
                    "created_at": None,
                    "message_count": 0,
                }
            )

    sessions.sort(
        key=lambda item: item.get("saved_at") or item.get("created_at") or "",
        reverse=True,
    )
    return sessions


def create_chat_session(title: str | None = None) -> str:
    """Create a new empty chat session file and return its generated id."""
    timestamp = now_eastern()
    base = slugify_session_name(title or timestamp.strftime("chat-%Y%m%d-%H%M%S"))
    session_id = base
    counter = 2

    while session_file_path(session_id).exists():
        session_id = f"{base}-{counter}"
        counter += 1

    payload = {
        "title": title or f"Chat {timestamp.strftime('%Y-%m-%d %H:%M')}",
        "created_at": timestamp.isoformat(),
        "saved_at": timestamp.isoformat(),
        "messages": [],
    }
    session_file_path(session_id).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return session_id


def ensure_active_session() -> str:
    """Return the newest existing session, or create one if none exist."""
    sessions = list_chat_sessions()
    if sessions:
        return sessions[0]["id"]
    return create_chat_session()


def load_chat_session(session_id: str) -> list[dict[str, Any]]:
    """Load one saved chat transcript from disk into memory."""
    path = session_file_path(session_id)
    if not path.exists():
        return []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return deserialize_messages(payload.get("messages", []))
    except Exception:
        return []


def save_chat_session(session_id: str, messages: list[dict[str, Any]]) -> None:
    """Persist the latest message list for a session back to its JSON file."""
    path = session_file_path(session_id)
    previous_payload: dict[str, Any] = {}
    if path.exists():
        try:
            previous_payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            previous_payload = {}

    title = derive_session_title(messages, previous_payload.get("title") or session_id)
    payload = {
        "title": title,
        "created_at": previous_payload.get("created_at") or now_eastern().isoformat(),
        "saved_at": now_eastern().isoformat(),
        "messages": serialize_messages(messages),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def delete_chat_session(session_id: str) -> bool:
    """Delete a session file and report whether anything was removed."""
    path = session_file_path(session_id)
    if path.exists():
        path.unlink()
        return True
    return False


def get_chat_session_status(session_id: str) -> dict[str, Any]:
    """Return lightweight session metadata for the sidebar status block."""
    path = session_file_path(session_id)
    if not path.exists():
        return {"exists": False, "message_count": 0, "saved_at": None}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {
            "exists": True,
            "message_count": len(payload.get("messages", [])),
            "saved_at": payload.get("saved_at"),
            "title": payload.get("title"),
        }
    except Exception:
        return {
            "exists": True,
            "message_count": 0,
            "saved_at": None,
            "title": session_id,
        }
