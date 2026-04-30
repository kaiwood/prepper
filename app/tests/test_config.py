import pytest

from prepper_cli.config import DEFAULT_OPENROUTER_MODEL, load_config, resolve_model_name


def test_resolve_model_name_prefers_explicit_model(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "local-default")
    monkeypatch.setenv("OPENROUTER_MODEL", "openrouter-default")

    assert resolve_model_name("explicit-model") == "explicit-model"


def test_resolve_model_name_prefers_generic_env(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "local-model")
    monkeypatch.setenv("OPENROUTER_MODEL", "openrouter-model")

    assert resolve_model_name() == "local-model"


def test_resolve_model_name_falls_back_to_openrouter_env(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "")
    monkeypatch.setenv("OPENROUTER_MODEL", "openrouter-model")

    assert resolve_model_name() == "openrouter-model"


def test_resolve_model_name_uses_default_when_env_is_missing(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "")
    monkeypatch.setenv("OPENROUTER_MODEL", "")

    assert resolve_model_name() == DEFAULT_OPENROUTER_MODEL


def test_load_config_prefers_generic_llm_env(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "local-key")
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:8080/v1")
    monkeypatch.setenv("LLM_MODEL", "ministral")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENROUTER_MODEL", "openrouter-model")

    config = load_config()

    assert config.api_key == "local-key"
    assert config.base_url == "http://127.0.0.1:8080/v1"
    assert config.model == "ministral"


def test_load_config_falls_back_to_openrouter_env(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_BASE_URL", "")
    monkeypatch.setenv("LLM_MODEL", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("OPENROUTER_MODEL", "openrouter-model")

    config = load_config()

    assert config.api_key == "openrouter-key"
    assert config.base_url == "https://example.test/v1"
    assert config.model == "openrouter-model"


def test_load_config_requires_api_key(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")

    with pytest.raises(ValueError, match="LLM_API_KEY or OPENROUTER_API_KEY is required"):
        load_config()
