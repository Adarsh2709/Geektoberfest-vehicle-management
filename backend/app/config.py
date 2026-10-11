from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/vehicle_maintenance"
    secret_key: str = "change-this-development-secret-before-deployment"
    frontend_origin: str = "http://localhost:5173"
    receipt_dir: str = "uploads/receipts"
    max_receipt_mb: int = 5
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
