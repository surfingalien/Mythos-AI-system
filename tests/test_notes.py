"""Tests for the notes keyword-retrieval tool."""

from jarvis.tools.notes import search_notes_dir


def test_finds_relevant_note(tmp_path):
    (tmp_path / "recipes.md").write_text(
        "Pizza dough: use 65% hydration flour and slow fermentation.",
        encoding="utf-8")
    (tmp_path / "travel.txt").write_text(
        "Flight to Tokyo leaves at 9am from gate 42.", encoding="utf-8")

    results = search_notes_dir(tmp_path, "pizza dough hydration")
    assert results
    assert results[0][0] == "recipes.md"
    assert "hydration" in results[0][1]


def test_no_match_returns_empty(tmp_path):
    (tmp_path / "a.txt").write_text("nothing relevant here", encoding="utf-8")
    assert search_notes_dir(tmp_path, "quantum blockchain") == []


def test_ignores_non_text_files(tmp_path):
    (tmp_path / "data.bin").write_bytes(b"\x00pizza\x00")
    assert search_notes_dir(tmp_path, "pizza") == []


def test_short_words_ignored(tmp_path):
    (tmp_path / "a.md").write_text("an it to of", encoding="utf-8")
    assert search_notes_dir(tmp_path, "an it to") == []
