from pydantic_settings import BaseSettings, SettingsConfigDict


# App settings loaded from .env file or local defaults
class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "civicfix"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
