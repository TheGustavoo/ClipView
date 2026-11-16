from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "ClipView API"
    secret_key: str = "development-only-change-this-secret-before-deploy"
    access_token_minutes: int = 60
    database_url: str = "sqlite:///./clipview.db"
    upload_dir: str = "./var/uploads"
    max_upload_bytes: int = 524288000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
