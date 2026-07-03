from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_path


def _default_db_url() -> str:
    data_dir = Path(user_data_path("licheats", "licheats"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{data_dir / 'licheats.sqlite3'}"


def _split_csv(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value:
        return default
    return tuple(part.strip() for part in value.split(",") if part.strip())


@dataclass(frozen=True)
class Settings:
    db_url: str
    lichess_api_token: str | None = None
    lichess_base_url: str = "https://lichess.org"
    request_timeout: float = 20.0
    cors_origins: tuple[str, ...] = ("http://127.0.0.1:8000", "http://localhost:8000")
    cors_origin_regex: str | None = r"^chrome-extension://[a-z]+$"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_url=os.getenv("LICHEATS_DB_URL", _default_db_url()),
            lichess_api_token=os.getenv("LICHESS_API_TOKEN"),
            lichess_base_url=os.getenv("LICHESS_BASE_URL", "https://lichess.org").rstrip("/"),
            request_timeout=float(os.getenv("LICHEATS_REQUEST_TIMEOUT", "20")),
            cors_origins=_split_csv(
                os.getenv("LICHEATS_CORS_ORIGINS"),
                ("http://127.0.0.1:8000", "http://localhost:8000"),
            ),
            cors_origin_regex=os.getenv(
                "LICHEATS_CORS_ORIGIN_REGEX", r"^chrome-extension://[a-z]+$"
            ),
        )
