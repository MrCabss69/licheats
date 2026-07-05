from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_path


class SettingsError(ValueError):
    pass


def _default_db_url() -> str:
    data_dir = Path(user_data_path("licheats", "licheats"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{data_dir / 'licheats.sqlite3'}"


def _split_csv(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value:
        return default
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _positive_float_from_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError as exc:
        raise SettingsError(f"{name} must be a number.") from exc
    if parsed <= 0:
        raise SettingsError(f"{name} must be positive.")
    return parsed


def _optional_env_text(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value or None


@dataclass(frozen=True)
class Settings:
    db_url: str
    lichess_api_token: str | None = None
    lichess_base_url: str = "https://lichess.org"
    request_timeout: float = 20.0
    cors_origins: tuple[str, ...] = ("http://127.0.0.1:8000", "http://localhost:8000")
    cors_origin_regex: str | None = r"^(chrome-extension|moz-extension)://[a-z0-9-]+$"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_url=os.getenv("LICHEATS_DB_URL") or _default_db_url(),
            lichess_api_token=os.getenv("LICHESS_API_TOKEN"),
            lichess_base_url=os.getenv("LICHESS_BASE_URL", "https://lichess.org").rstrip("/"),
            request_timeout=_positive_float_from_env("LICHEATS_REQUEST_TIMEOUT", 20.0),
            cors_origins=_split_csv(
                os.getenv("LICHEATS_CORS_ORIGINS"),
                ("http://127.0.0.1:8000", "http://localhost:8000"),
            ),
            cors_origin_regex=_optional_env_text(
                "LICHEATS_CORS_ORIGIN_REGEX", r"^(chrome-extension|moz-extension)://[a-z0-9-]+$"
            ),
        )
