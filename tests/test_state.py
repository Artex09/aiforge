import pytest

from aiforge.core.errors import ValidationError
from aiforge.core.state import StateManager


def test_scopes_isolated():
    sm = StateManager()
    sm.set("k", 1, scope="global")
    sm.set("k", 2, scope="agent_a")
    assert sm.get("k", scope="global") == 1
    assert sm.get("k", scope="agent_a") == 2


def test_versioning_and_rollback():
    sm = StateManager()
    sm.set("count", 1)
    v = sm.version
    sm.set("count", 2)
    assert sm.get("count") == 2
    assert sm.rollback(v) is True
    assert sm.get("count") == 1


def test_snapshot_restore():
    sm = StateManager()
    sm.set("a", 10)
    snap = sm.snapshot()
    sm.set("a", 99)
    sm.restore(snap)
    assert sm.get("a") == 10


def test_validator_rejects():
    sm = StateManager()

    def positive(key, value):
        if isinstance(value, int) and value < 0:
            raise ValueError("must be positive")

    sm.add_validator("global", positive)
    with pytest.raises(ValidationError):
        sm.set("n", -1)
