import pytest

from aiforge.storage.cache import TTLCache
from aiforge.storage.local import LocalStorage
from aiforge.storage.vector_store import InMemoryVectorStore, cosine_similarity


def test_local_kv_roundtrip(tmp_path):
    s = LocalStorage(str(tmp_path))
    s.set("ns", "key", {"a": 1})
    assert s.get("ns", "key") == {"a": 1}
    assert "key" in s.keys("ns")
    s.delete("ns", "key")
    assert not s.exists("ns", "key")


def test_local_collections(tmp_path):
    s = LocalStorage(str(tmp_path))
    s.append("logs", {"msg": "a"})
    s.append("logs", {"msg": "b"})
    records = s.query("logs")
    assert [r["msg"] for r in records] == ["a", "b"]


def test_sqlite_backend(tmp_path):
    from aiforge.storage.sqlite_store import SQLiteStorage

    s = SQLiteStorage(str(tmp_path / "db.sqlite"))
    s.set("ns", "k", [1, 2, 3])
    assert s.get("ns", "k") == [1, 2, 3]
    s.append("c", {"v": 1})
    assert len(s.query("c")) == 1
    s.close()


def test_cache_ttl():
    c = TTLCache(default_ttl=0.01)
    c.set("k", "v")
    assert c.get("k") == "v"
    import time

    time.sleep(0.02)
    assert c.get("k") is None


def test_vector_search():
    store = InMemoryVectorStore()
    store.add([1.0, 0.0], text="east")
    store.add([0.0, 1.0], text="north")
    hits = store.search([0.9, 0.1], top_k=1)
    assert hits[0][0].text == "east"


def test_cosine():
    assert cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)
