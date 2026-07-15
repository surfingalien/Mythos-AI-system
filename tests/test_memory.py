"""Tests for persistent memory."""

from jarvis.memory import Memory


def test_remember_and_reload(tmp_path):
    path = tmp_path / "mem.json"
    m = Memory(path)
    m.remember("The user's favorite city is Tokyo")
    m.remember("The user works at Acme Corp")

    m2 = Memory(path)
    assert len(m2.all_facts()) == 2
    assert "Tokyo" in m2.all_facts()[0]


def test_deduplication(tmp_path):
    m = Memory(tmp_path / "mem.json")
    m.remember("likes coffee")
    m.remember("Likes Coffee")
    assert len(m.all_facts()) == 1


def test_search_ranks_by_hits(tmp_path):
    m = Memory(tmp_path / "mem.json")
    m.remember("favorite color is blue")
    m.remember("blue blue everywhere blue")
    hits = m.search("blue")
    assert len(hits) == 2
    assert hits[0] == "blue blue everywhere blue"


def test_forget(tmp_path):
    m = Memory(tmp_path / "mem.json")
    m.remember("temporary secret")
    m.remember("permanent fact")
    assert m.forget("secret") == 1
    assert m.all_facts() == ["permanent fact"]


def test_corrupt_file_recovers(tmp_path):
    path = tmp_path / "mem.json"
    path.write_text("{not json", encoding="utf-8")
    m = Memory(path)
    assert m.all_facts() == []
    m.remember("fresh start")
    assert Memory(path).all_facts() == ["fresh start"]
