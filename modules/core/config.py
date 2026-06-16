from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://ribcage:ribcage@localhost:5432/ribcage"
    redis_url: str = "redis://localhost:6379/0"
    meilisearch_url: str = "http://localhost:7700"
    meilisearch_key: str = "ribcage-dev-key"
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "ribcage"
    s3_secret_key: str = "ribcage-secret"
    s3_bucket: str = "ribcage"
    cors_origins: str = "http://localhost:3000"
    jwt_secret: str = "ribcage-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    prometheus_enabled: bool = True
    outbox_publisher_enabled: bool = True


settings = Settings()
