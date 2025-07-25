import os
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings


class BaseAppSettings(BaseSettings):
    BASE_DIR: Path = Path(__file__).parent.parent
    PATH_TO_DB: str = str(BASE_DIR / "database" / "source" / "theater.db")
    PATH_TO_MOVIES_CSV: str = str(
        BASE_DIR / "database" / "seed_data" / "imdb_movies.csv"
    )
    LOGIN_TIME_DAYS: int = 7


def get_settings() -> BaseAppSettings:
    """
    Retrieve the application settings based on the current environment.

    This function reads the 'ENVIRONMENT' environment variable (defaulting to 'developing' if not set)
    and returns a corresponding settings instance. If the environment is 'testing', it returns an instance
    of TestingSettings; otherwise, it returns an instance of Settings.

    Returns:
        BaseAppSettings: The settings instance appropriate for the current environment.
    """
    environment = os.getenv("ENVIRONMENT", "developing")
    if environment == "testing":
        return TestingSettings()
    return Settings()


class Settings(BaseAppSettings):
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "test_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "test_password")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "test_host")
    POSTGRES_DB_PORT: int = int(os.getenv("POSTGRES_DB_PORT", 5432))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "test_db")

    SECRET_KEY_ACCESS: str = os.getenv("SECRET_KEY_ACCESS", os.urandom(32).hex())
    SECRET_KEY_REFRESH: str = os.getenv("SECRET_KEY_REFRESH", os.urandom(32).hex())
    JWT_SIGNING_ALGORITHM: str = os.getenv("JWT_SIGNING_ALGORITHM", "HS256")


class TestingSettings(BaseAppSettings):
    SECRET_KEY_ACCESS: str = "SECRET_KEY_ACCESS"
    SECRET_KEY_REFRESH: str = "SECRET_KEY_REFRESH"
    JWT_SIGNING_ALGORITHM: str = "HS256"
    S3_STORAGE_ENDPOINT: str = os.getenv("S3_STORAGE_ENDPOINT", "http://localhost:9000")
    S3_STORAGE_ACCESS_KEY: str = os.getenv("S3_STORAGE_ACCESS_KEY", "minioadmin")
    S3_STORAGE_SECRET_KEY: str = os.getenv("S3_STORAGE_SECRET_KEY", "some_password")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "theater-storage")
    EMAIL_HOST: str = os.getenv("EMAIL_HOST", "localhost")
    EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", "1025"))
    EMAIL_HOST_USER: str = os.getenv("EMAIL_HOST_USER", "testuser@mate.com")
    EMAIL_HOST_PASSWORD: str = os.getenv("EMAIL_HOST_PASSWORD", "test_password")
    EMAIL_USE_TLS: bool = os.getenv("EMAIL_USE_TLS", "False").lower() == "true"
    MAILHOG_API_PORT: int = int(os.getenv("MAILHOG_API_PORT", "8025"))

    def model_post_init(self, __context: dict[str, Any] | None = None) -> None:
        object.__setattr__(
            self, 'PATH_TO_DB', str(self.BASE_DIR / "database" / "source" / "test.db")
        )
        object.__setattr__(
            self,
            'PATH_TO_MOVIES_CSV',
            str(self.BASE_DIR / "database" / "seed_data" / "test_data.csv"),
        )
        object.__setattr__(
            self,
            'PATH_TO_EMAIL_TEMPLATES_DIR',
            str(self.BASE_DIR / "notifications" / "templates"),
        )
        object.__setattr__(
            self, 'ACTIVATION_EMAIL_TEMPLATE_NAME', "activation_request.html"
        )
        object.__setattr__(
            self, 'ACTIVATION_COMPLETE_EMAIL_TEMPLATE_NAME', "activation_complete.html"
        )
        object.__setattr__(
            self, 'PASSWORD_RESET_TEMPLATE_NAME', "password_reset_request.html"
        )
        object.__setattr__(
            self,
            'PASSWORD_RESET_COMPLETE_TEMPLATE_NAME',
            "password_reset_complete.html",
        )
