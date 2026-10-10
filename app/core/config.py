from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "AEREO Geospatial Measurement API"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    max_upload_size_bytes: int = 25 * 1024 * 1024
    max_archive_uncompressed_bytes: int = 100 * 1024 * 1024
    max_archive_members: int = 500
    log_level: str = "INFO"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
