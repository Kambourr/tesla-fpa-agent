"""Settings from the environment named in `.env.example`.

Secret fields stay wrapped in `SecretStr`. A repr of this model does not
include the API key or the SEC contact string. Call `get_secret_value()`
only at the moment a client needs the value, and never log the result.
"""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """The four project settings. Missing variables use these defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: SecretStr = Field(default=SecretStr(""))
    openai_model: str = ""
    sec_user_agent: SecretStr = Field(default=SecretStr(""))
    publish_forward_forecast: bool = False
