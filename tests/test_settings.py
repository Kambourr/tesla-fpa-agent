"""Settings stay empty and unpublished unless the environment says otherwise."""

from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from agent.settings import Settings

SETTING_NAMES = (
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "SEC_USER_AGENT",
    "PUBLISH_FORWARD_FORECAST",
)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in SETTING_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_defaults_leave_secrets_empty_and_forward_forecast_off(clean_env: None) -> None:
    settings = Settings(_env_file=None)
    assert settings.openai_api_key.get_secret_value() == ""
    assert settings.openai_model == ""
    assert settings.sec_user_agent.get_secret_value() == ""
    assert settings.publish_forward_forecast is False


def test_env_file_matches_the_template(tmp_path: Path, clean_env: None) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "OPENAI_API_KEY=from-env-file",
                "OPENAI_MODEL=from-env-file-model",
                "SEC_USER_AGENT=from-env-file-agent",
                "PUBLISH_FORWARD_FORECAST=false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    settings = Settings(_env_file=env_file)
    assert settings.openai_api_key.get_secret_value() == "from-env-file"
    assert settings.openai_model == "from-env-file-model"
    assert settings.sec_user_agent.get_secret_value() == "from-env-file-agent"
    assert settings.publish_forward_forecast is False


def test_forward_forecast_parses_explicit_false(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PUBLISH_FORWARD_FORECAST", "false")
    settings = Settings(_env_file=None)
    assert settings.publish_forward_forecast is False


def test_forward_forecast_can_be_turned_on(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PUBLISH_FORWARD_FORECAST", "true")
    settings = Settings(_env_file=None)
    assert settings.publish_forward_forecast is True


def test_forward_forecast_rejects_unknown_values(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PUBLISH_FORWARD_FORECAST", "maybe")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_repr_does_not_include_secret_values(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    api_key = "test-openai-key-value"
    user_agent = "test-sec-user-agent-value"
    monkeypatch.setenv("OPENAI_API_KEY", api_key)
    monkeypatch.setenv("SEC_USER_AGENT", user_agent)
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    settings = Settings(_env_file=None)
    rendered = repr(settings)
    assert api_key not in rendered
    assert user_agent not in rendered
    assert isinstance(settings.openai_api_key, SecretStr)
    assert isinstance(settings.sec_user_agent, SecretStr)
    assert settings.openai_model == "gpt-test"
