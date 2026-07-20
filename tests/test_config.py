import os

from aiforge.config.settings import Config


def test_defaults_present():
    cfg = Config()
    assert cfg.get("provider.default") == "mock"
    assert cfg.get("memory.vector.dimension") == 256


def test_dotted_get_set():
    cfg = Config()
    cfg.set("provider.model", "custom-1")
    assert cfg.get("provider.model") == "custom-1"
    assert cfg.get("nope.here", "fallback") == "fallback"


def test_env_override(monkeypatch):
    monkeypatch.setenv("AIFORGE_PROVIDER__TEMPERATURE", "0.1")
    monkeypatch.setenv("AIFORGE_SECURITY__ALLOW_SHELL", "true")
    cfg = Config.load(use_env=True)
    assert cfg.get("provider.temperature") == 0.1
    assert cfg.get("security.allow_shell") is True


def test_file_load_json(tmp_path):
    p = tmp_path / "cfg.json"
    p.write_text('{"provider": {"model": "from-file"}}', encoding="utf-8")
    cfg = Config.load(path=str(p), use_env=False)
    assert cfg.get("provider.model") == "from-file"
    # unspecified keys still fall back to defaults
    assert cfg.get("provider.default") == "mock"


def test_set_never_mutates_module_defaults():
    """Config.set on one instance must not bleed into later instances via
    the shared DEFAULTS dict (regression: auth_token leaked across engines)."""
    from aiforge.config.settings import DEFAULTS

    a = Config()
    a.set("api.auth_token", "leak?")
    a.set("provider.openai_model", "gpt-x")
    assert DEFAULTS["api"]["auth_token"] is None
    b = Config()
    assert b.get("api.auth_token") is None
    assert b.get("provider.openai_model") is None
