from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "FocusPoint"
    secret_key: str = "change-me"
    session_cookie_name: str = "focuspoint_session"

    # Admin bootstrap
    admin_email: str = "admin@local"
    admin_password: str = "admin"

    # Database
    database_url: str = "postgresql+psycopg2://focuspoint:focuspoint@db:5432/focuspoint"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

