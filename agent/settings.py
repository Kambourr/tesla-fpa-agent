"""Settings from the environment named in `.env.example`.

Secret fields stay wrapped in `SecretStr`. A repr of this model does not
include the API key or the SEC contact string. Call `get_secret_value()`
only at the moment a client needs the value, and never log the result.
"""

from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Chosen 2026-11-04 from OpenAI's model page. GPT-6 Luna lists
# structured_outputs, and its price keeps a full memo run under a dollar.
# See docs/DECISIONS.md. An empty OPENAI_MODEL uses this id.
DEFAULT_OPENAI_MODEL = "gpt-6-luna"


class Settings(BaseSettings):
    """The four project settings. Missing variables use these defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: SecretStr = Field(default=SecretStr(""))
    openai_model: str = DEFAULT_OPENAI_MODEL
    sec_user_agent: SecretStr = Field(default=SecretStr(""))
    publish_forward_forecast: bool = False

    @field_validator("openai_model", mode="before")
    @classmethod
    def blank_model_uses_default(cls, value: Any) -> Any:
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return DEFAULT_OPENAI_MODEL
        return value
