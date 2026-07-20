from aiforge.memory.base import MemoryKind
from aiforge.memory.manager import MemoryManager


def make_manager(tmp_path):
    from aiforge.storage.local import LocalStorage

    return MemoryManager(backend=LocalStorage(str(tmp_path)), short_term_capacity=5)


def test_remember_and_recall(tmp_path):
    mgr = make_manager(tmp_path)
    mgr.remember_semantic("The capital of France is Paris")
    mgr.remember_semantic("Python is a programming language")
    hits = mgr.recall("What is the capital of France?", top_k=2)
    assert any("Paris" in h.content for h in hits)


def test_short_term_capacity(tmp_path):
    mgr = make_manager(tmp_path)
    for i in range(10):
        mgr.remember(f"item {i}", MemoryKind.SHORT_TERM)
    assert len(mgr.short_term.all()) <= 5


def test_compression(tmp_path):
    mgr = make_manager(tmp_path)
    mgr.compression_threshold = 4
    for i in range(6):
        mgr.remember(f"note {i}")
    # compression should have produced at least one long-term summary
    assert len(mgr.long_term.all()) >= 1


def test_working_memory_slots(tmp_path):
    mgr = make_manager(tmp_path)
    mgr.working.set("goal", "ship AIForge")
    assert mgr.working.get_slot("goal") == "ship AIForge"


def test_vector_similarity(tmp_path):
    mgr = make_manager(tmp_path)
    mgr.remember("cats are wonderful pets", MemoryKind.VECTOR)
    mgr.remember("the stock market rose today", MemoryKind.VECTOR)
    hits = mgr.vector.search("tell me about pet cats", top_k=1)
    assert hits and "cats" in hits[0].content
