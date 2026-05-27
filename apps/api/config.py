from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://quazar:quazar@localhost:5432/quazar"
    database_url_sync: str = "postgresql://quazar:quazar@localhost:5432/quazar"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "quazar"
    minio_secret_key: str = "quazarsecret"
    minio_bucket: str = "quazar-files"
    minio_secure: bool = False

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    gigachat_client_id: str = ""
    gigachat_client_secret: str = ""
    gigachat_scope: str = "GIGACHAT_API_PERS"

    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    web_url: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000"

    secrets_encryption_key: str = "change-me-32-byte-key-here!!!!"

    oidc_enabled: bool = False
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""

    ocr_language: str = "rus+eng"
    ingest_vision_fallback: bool = True
    ingest_vision_model: str = "gpt-4o-mini"
    mpxj_jar_path: str = "/app/lib/mpxj.jar"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
