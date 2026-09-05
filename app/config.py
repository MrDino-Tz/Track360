from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "PlantDesk"
    database_url: str = "sqlite:///./data/plant.db"

    africastalking_username: str = ""
    africastalking_api_key: str = ""
    africastalking_sender_id: str = ""
    africastalking_sandbox: bool = True
    africastalking_send_ack: bool = False

    default_phone_country_code: str = "255"


@lru_cache
def get_settings() -> Settings:
    return Settings()
