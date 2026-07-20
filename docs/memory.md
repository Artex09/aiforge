# Memory

The `MemoryManager` unifies five stores behind one API and adds retrieval,
ranking, and compression.

## Store types

| Store | Kind | Description |
|-------|------|-------------|
| `ShortTermMemory` | `short_term` | Bounded rolling buffer (recent context) |
| `WorkingMemory` | `working` | Named scratchpad slots (active variables) |
| `SessionMemory` | `session` | Per-session history, persisted |
| `LongTermMemory` | `long_term` | Durable keyword-searchable memory |
| `VectorMemory` | `vector` | Semantic recall via embeddings + cosine |

## Writing

```python
engine.memory.remember("a transient note")                 # short-term
engine.memory.remember_semantic("Paris is the capital of France")  # long-term + vector
engine.memory.working.set("goal", "ship v1")
```

## Recall (retrieval + ranking)

```python
hits = engine.memory.recall("what is the capital of France?", top_k=5)
for h in hits:
    print(h.score, h.content)
```

`recall` searches across stores and ranks results by a blend of **relevance**
(similarity / keyword overlap) and **recency**, de-duplicating by content.

## Embeddings

`Embedder` prefers the configured provider's `embed`, and falls back to a
deterministic hash-based embedding — so semantic memory works offline. Enable
NumPy (`pip install -e ".[vector]"`) to accelerate similarity math.

## Compression

When short-term memory exceeds `memory.compression.threshold`, the oldest half is
summarised (via the provider, or extractively offline) into a single long-term
record — keeping prompts small while retaining knowledge. Emits `MEMORY_COMPRESS`.

## Injecting memory into prompts

Agents automatically call `memory.context_messages(query)` to prepend relevant
memories as a system message when `use_memory=True`.

## Persistence

Long-term and session stores persist through the configured storage backend
(local JSON or SQLite). Vector memory can persist to a `StorageBackend` too.
