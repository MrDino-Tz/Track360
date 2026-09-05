from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Thibitisha"
    database_url: str = "sqlite:///./data/plant.db"

    africastalking_username: str = ""
    africastalking_api_key: str = ""
    africastalking_sender_id: str = ""
    africastalking_sandbox: bool = True
    africastalking_send_ack: bool = False

    # Aliased to project-specific env names: a generic `GROQ_API_KEY` exported
    # in the shell would otherwise shadow the value in `.env` (env vars win in
    # pydantic-settings) and silently point at the wrong account.
    groq_api_key: str = Field(default="", validation_alias="THIBITISHA_GROQ_API_KEY")
    groq_model: str = Field(default="groq/compound-mini", validation_alias="THIBITISHA_GROQ_MODEL")

    africastalking_payments_product_name: str = ""
    reward_default_amount: int = 1000
    reward_currency: str = "TZS"

    default_phone_country_code: str = "255"


@lru_cache
def get_settings() -> Settings:
    return Settings()
