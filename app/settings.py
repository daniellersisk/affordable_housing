from __future__ import annotations

import os
from dataclasses import dataclass, field

TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}


def _get_str(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    return value


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(f"Invalid boolean for {name}: {value!r}")


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid integer for {name}: {value!r}") from exc


@dataclass(frozen=True)
class Settings:
    # Non-secret runtime config
    app_env: str = field(default_factory=lambda: _get_str("APP_ENV", "local"))
    app_host: str = field(default_factory=lambda: _get_str("APP_HOST", "0.0.0.0"))
    app_port: int = field(default_factory=lambda: _get_int("APP_PORT", 8000))

    # Database config
    database_url: str = field(
        default_factory=lambda: _get_str(
            "DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@db:5432/affordable_housing",
        )
    )

    # Ingestion config (non-secret + secret token)
    nyc_open_data_url: str = field(
        default_factory=lambda: _get_str("NYC_OPEN_DATA_URL", "")
    )
    nyc_open_data_base_url: str = field(
        default_factory=lambda: _get_str(
            "NYC_OPEN_DATA_BASE_URL",
            "https://data.cityofnewyork.us",
        )
    )
    nyc_open_data_view_id: str = field(
        default_factory=lambda: _get_str("NYC_OPEN_DATA_VIEW_ID", "hg8x-zxpr")
    )
    soda_app_token: str = field(default_factory=lambda: _get_str("SODA_APP_TOKEN", ""))
    ingest_page_size: int = field(
        default_factory=lambda: _get_int("INGEST_PAGE_SIZE", 2000)
    )
    ingest_timeout_seconds: int = field(
        default_factory=lambda: _get_int("INGEST_TIMEOUT_SECONDS", 30)
    )
    ingest_max_retries: int = field(
        default_factory=lambda: _get_int("INGEST_MAX_RETRIES", 3)
    )

    # API auth config (contains secret key)
    api_auth_enabled: bool = field(
        default_factory=lambda: _get_bool("API_AUTH_ENABLED", True)
    )
    write_api_key: str = field(default_factory=lambda: _get_str("WRITE_API_KEY", ""))
    write_api_key_header: str = field(
        default_factory=lambda: _get_str("WRITE_API_KEY_HEADER", "X-API-Key")
    )

    # Non-secret API config
    cors_allowed_origins: str = field(
        default_factory=lambda: _get_str(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:8000",
        )
    )

    @property
    def resolved_open_data_url(self) -> str:
        if self.nyc_open_data_url:
            return self.nyc_open_data_url
        return (
            f"{self.nyc_open_data_base_url}/resource/"
            f"{self.nyc_open_data_view_id}.json"
        )


def load_settings() -> Settings:
    return Settings()


settings = load_settings()
