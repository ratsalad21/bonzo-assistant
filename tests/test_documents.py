"""Small tests for local document helper behavior."""

from pathlib import Path

import documents


def test_list_saved_documents_ignores_hidden_files(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(documents, "DOCS_DIR", tmp_path)

    (tmp_path / ".gitkeep").write_text("", encoding="utf-8")
    (tmp_path / ".hidden.txt").write_text("ignore me", encoding="utf-8")
    (tmp_path / "sample-deploy-note.md").write_text("sample", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")

    assert documents.list_saved_documents() == ["notes.txt", "sample-deploy-note.md"]
