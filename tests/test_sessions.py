"""Small tests for chat-session save/load behavior."""

from pathlib import Path

import sessions


def test_save_and_load_chat_session_round_trip(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sessions, "CHAT_HISTORY_DIR", tmp_path)

    session_id = sessions.create_chat_session("First Test Session")
    messages = [
        {"role": "user", "content": "Hello from a test."},
        {"role": "assistant", "content": "Hi there."},
    ]

    sessions.save_chat_session(session_id, messages)
    loaded_messages = sessions.load_chat_session(session_id)
    listed_sessions = sessions.list_chat_sessions()

    assert [message["content"] for message in loaded_messages] == ["Hello from a test.", "Hi there."]
    assert listed_sessions[0]["id"] == session_id
    assert listed_sessions[0]["title"] == "Hello from a test."
