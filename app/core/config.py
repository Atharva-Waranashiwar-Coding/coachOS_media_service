from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    app_name: str = Field(default="CoachOS Media Service", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    database_url: str = Field(alias="DATABASE_URL")
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    athlete_service_url: str = Field(alias="ATHLETE_SERVICE_URL")
    athlete_service_internal_url: str | None = Field(default=None, alias="ATHLETE_SERVICE_INTERNAL_URL")
    internal_service_token: str | None = Field(default=None, alias="INTERNAL_SERVICE_TOKEN")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    aws_access_key_id: str = Field(alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(alias="AWS_SECRET_ACCESS_KEY")
    s3_bucket_name: str = Field(alias="S3_BUCKET_NAME")
    s3_endpoint_url: str | None = Field(default=None, alias="S3_ENDPOINT_URL")
    s3_presigned_url_expiration_seconds: int = Field(
        default=900, alias="S3_PRESIGNED_URL_EXPIRATION_SECONDS", ge=60, le=86400
    )
    max_video_size_bytes: int = Field(default=2_147_483_648, alias="MAX_VIDEO_SIZE_BYTES", gt=0)
    allowed_video_content_types: set[str] = Field(
        default={"video/mp4", "video/quicktime", "video/webm"}, alias="ALLOWED_VIDEO_CONTENT_TYPES"
    )
    delete_storage_objects: bool = Field(default=True, alias="DELETE_STORAGE_OBJECTS")
    timeline_publishing_enabled: bool = Field(default=False, alias="TIMELINE_PUBLISHING_ENABLED")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    default_page_size: int = Field(default=20, alias="DEFAULT_PAGE_SIZE", gt=0)
    max_page_size: int = Field(default=100, alias="MAX_PAGE_SIZE", gt=0, le=500)
    cors_origins: list[str] = Field(default_factory=list, alias="CORS_ORIGINS")
    upstream_timeout_seconds: float = Field(default=5.0, alias="UPSTREAM_TIMEOUT_SECONDS", gt=0)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("allowed_video_content_types", mode="before")
    @classmethod
    def parse_content_types(cls, value: str | set[str]) -> set[str]:
        return {item.strip().lower() for item in value.split(",") if item.strip()} if isinstance(value, str) else value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: str | list[str]) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()] if isinstance(value, str) else value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
