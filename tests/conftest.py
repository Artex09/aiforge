"""Shared pytest fixtures for the AIForge test suite."""
import os
import sys

import pytest

# Ensure the repo root is importable when tests run from anywhere.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aiforge.config.settings import Config  # noqa: E402
from aiforge.core.engine import Engine  # noqa: E402
from aiforge.sdk import AIForge  # noqa: E402


@pytest.fixture
def config(tmp_path):
    return Config.load(
        overrides={"storage": {"path": str(tmp_path / ".aiforge")},
                   "security": {"sandbox_root": str(tmp_path / "sandbox")}},
        use_env=False,
    )


@pytest.fixture
def engine(config):
    eng = Engine(config)
    yield eng
    eng.shutdown()


@pytest.fixture
def forge(config):
    return AIForge(config=config)
