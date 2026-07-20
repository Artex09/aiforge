"""Storage layer: local/sqlite backends, cache, and vector store."""
from .base import StorageBackend
from .cache import TTLCache
from .local import LocalStorage
from .vector_store import InMemoryVectorStore, cosine_similarity

__all__ = [
    "StorageBackend",
    "LocalStorage",
    "TTLCache",
    "InMemoryVectorStore",
    "cosine_similarity",
]


def SQLiteStorage(*args, **kwargs):  # lazy to keep import light
    from .sqlite_store import SQLiteStorage as _S

    return _S(*args, **kwargs)
