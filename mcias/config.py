from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    environment: str = "development"
    bootstrap_token: str = ""

    model_config = SettingsConfigDict(env_prefix="MCIAS_", env_file=".env", extra="ignore")
