from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

import httpx

from .schemas import GameRecord, PlayerProfile
from .settings import Settings


class LichessError(RuntimeError):
    def __init__(self, message: str, *, code: str = "lichess_error", details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class LichessPayloadError(LichessError):
    pass


def _normalize_username(value: str | None) -> str | None:
    return value.lower() if value else None


def lichess_time_to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    if isinstance(value, str):
        text = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise LichessPayloadError(
                f"Invalid Lichess datetime: {value}",
                code="invalid_datetime",
                details={"value": value},
            ) from exc
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    raise LichessPayloadError(
        f"Unsupported Lichess timestamp type: {type(value).__name__}",
        code="invalid_datetime",
        details={"value": repr(value)},
    )


def normalize_player(data: dict[str, Any]) -> PlayerProfile:
    username = _normalize_username(data.get("username") or data.get("id"))
    if not username:
        raise LichessPayloadError("Player payload is missing username/id", code="invalid_player")

    perfs = data.get("perfs") or {}
    ratings = {
        name: perf.get("rating")
        for name, perf in perfs.items()
        if isinstance(perf, dict) and "rating" in perf
    }
    counts = {
        name: int(value)
        for name, value in (data.get("count") or {}).items()
        if isinstance(value, int)
    }
    return PlayerProfile(
        username=username,
        display_name=data.get("username"),
        title=data.get("title"),
        url=data.get("url"),
        ratings=ratings,
        counts=counts,
        raw=data,
    )


def _side_user_id(side: dict[str, Any]) -> str | None:
    user = side.get("user") or {}
    if isinstance(user, dict):
        return _normalize_username(user.get("id") or user.get("name"))
    return _normalize_username(side.get("name"))


def normalize_game(data: dict[str, Any]) -> GameRecord:
    game_id = data.get("id")
    if not game_id:
        raise LichessPayloadError("Game payload is missing id", code="invalid_game")

    players = data.get("players") or {}
    white = players.get("white") or {}
    black = players.get("black") or {}
    opening = data.get("opening") or {}
    clock = data.get("clock") or {}
    perf = data.get("perf")

    return GameRecord(
        id=game_id,
        rated=data.get("rated"),
        variant=data.get("variant"),
        speed=data.get("speed"),
        perf=perf if isinstance(perf, str) else None,
        created_at=lichess_time_to_datetime(data.get("createdAt")),
        last_move_at=lichess_time_to_datetime(data.get("lastMoveAt")),
        status=data.get("status"),
        winner=data.get("winner") if data.get("winner") in {"white", "black"} else None,
        moves=data.get("moves") or "",
        initial_fen=data.get("initialFen"),
        opening_eco=opening.get("eco"),
        opening_name=opening.get("name"),
        opening_ply=opening.get("ply"),
        clock_initial=clock.get("initial"),
        clock_increment=clock.get("increment"),
        clock_total_time=clock.get("totalTime"),
        white_id=_side_user_id(white),
        black_id=_side_user_id(black),
        white_rating=white.get("rating"),
        black_rating=black.get("rating"),
        raw=data,
    )


class LichessGateway:
    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self.settings = settings
        self._client = client or httpx.Client(timeout=settings.request_timeout)

    def _headers(self, accept: str = "application/json") -> dict[str, str]:
        headers = {"Accept": accept}
        if self.settings.lichess_api_token:
            headers["Authorization"] = f"Bearer {self.settings.lichess_api_token}"
        return headers

    def get_player(self, username: str) -> PlayerProfile:
        url = f"{self.settings.lichess_base_url}/api/user/{username}"
        response = self._request("GET", url, headers=self._headers())
        return normalize_player(response.json())

    def get_games(
        self,
        username: str,
        *,
        limit: int = 100,
        perf_type: str | None = None,
        include_moves: bool = True,
        page_size: int = 1000,
    ) -> list[GameRecord]:
        return list(
            self.iter_games(
                username,
                limit=limit,
                perf_type=perf_type,
                include_moves=include_moves,
                page_size=page_size,
            )
        )

    def iter_games(
        self,
        username: str,
        *,
        limit: int = 100,
        perf_type: str | None = None,
        include_moves: bool = True,
        page_size: int = 1000,
    ) -> Iterator[GameRecord]:
        remaining = max(0, limit)
        until: int | None = None
        url = f"{self.settings.lichess_base_url}/api/games/user/{username}"

        while remaining > 0:
            page_limit = min(page_size, remaining)
            params = self._game_params(
                limit=page_limit,
                perf_type=perf_type,
                include_moves=include_moves,
                until=until,
            )
            page_games = 0
            oldest_seen: datetime | None = None

            with self._stream_request(
                "GET",
                url,
                params=params,
                headers=self._headers("application/x-ndjson"),
            ) as response:
                for line in response.iter_lines():
                    if not line.strip():
                        continue
                    game = self._parse_game_line(line)
                    page_games += 1
                    remaining -= 1
                    if game.created_at is not None and (
                        oldest_seen is None or game.created_at < oldest_seen
                    ):
                        oldest_seen = game.created_at
                    yield game
                    if remaining <= 0:
                        break

            if page_games == 0 or page_games < page_limit or oldest_seen is None:
                break
            until = int(oldest_seen.astimezone(timezone.utc).timestamp() * 1000) - 1

    @staticmethod
    def _game_params(
        *,
        limit: int,
        perf_type: str | None,
        include_moves: bool,
        until: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "max": limit,
            "moves": "true" if include_moves else "false",
            "opening": "true",
            "clocks": "true",
            "evals": "false",
        }
        if perf_type:
            params["perfType"] = perf_type
        if until is not None:
            params["until"] = until
        return params

    @staticmethod
    def _parse_game_line(line: str) -> GameRecord:
        try:
            return normalize_game(json.loads(line))
        except json.JSONDecodeError as exc:
            raise LichessPayloadError(
                "Invalid NDJSON returned by Lichess",
                code="invalid_ndjson",
                details={"line": line[:200]},
            ) from exc

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        try:
            response = self._client.request(method, url, timeout=self.settings.request_timeout, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            raise LichessError(
                f"Lichess returned HTTP {exc.response.status_code}",
                code="lichess_http_error",
                details={"status_code": exc.response.status_code, "body": exc.response.text[:500]},
            ) from exc
        except httpx.HTTPError as exc:
            raise LichessError(str(exc), code="lichess_transport_error") from exc

    @contextmanager
    def _stream_request(self, method: str, url: str, **kwargs: Any) -> Iterator[httpx.Response]:
        try:
            with self._client.stream(
                method,
                url,
                timeout=self.settings.request_timeout,
                **kwargs,
            ) as response:
                response.raise_for_status()
                yield response
        except httpx.HTTPStatusError as exc:
            try:
                body = exc.response.text
            except httpx.ResponseNotRead:
                body = exc.response.read().decode("utf-8", errors="replace")
            raise LichessError(
                f"Lichess returned HTTP {exc.response.status_code}",
                code="lichess_http_error",
                details={"status_code": exc.response.status_code, "body": body[:500]},
            ) from exc
        except httpx.HTTPError as exc:
            raise LichessError(str(exc), code="lichess_transport_error") from exc
