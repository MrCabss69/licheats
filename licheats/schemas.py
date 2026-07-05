from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

GameResult = Literal["win", "loss", "draw", "unknown"]
PlayerColor = Literal["white", "black", "unknown"]


class PlayerProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    username: str
    display_name: str | None = None
    title: str | None = None
    url: str | None = None
    ratings: dict[str, int | None] = Field(default_factory=dict)
    counts: dict[str, int] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)


class GameRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    rated: bool | None = None
    variant: str | None = None
    speed: str | None = None
    perf: str | None = None
    created_at: datetime | None = None
    last_move_at: datetime | None = None
    status: str | None = None
    winner: Literal["white", "black"] | None = None
    moves: str = ""
    initial_fen: str | None = None
    opening_eco: str | None = None
    opening_name: str | None = None
    opening_ply: int | None = None
    clock_initial: int | None = None
    clock_increment: int | None = None
    clock_total_time: int | None = None
    white_id: str | None = None
    black_id: str | None = None
    white_rating: int | None = None
    black_rating: int | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class SyncResult(BaseModel):
    username: str
    players_upserted: int = 0
    games_upserted: int = 0
    fetched_games: int = 0


class PlayerProfileSummary(BaseModel):
    player: PlayerProfile
    generated_at: datetime
    source: Literal["profile"] = "profile"
    total_games: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    win_rate: float = 0.0
    ratings: dict[str, int | None] = Field(default_factory=dict)
    play_time: dict[str, int] = Field(default_factory=dict)


class AnalysisCoverage(BaseModel):
    games_analyzed: int = 0
    total_known: int | None = None
    is_syncing: bool = False
    last_synced: datetime | None = None
    sample: str = "cache"


class SyncJobStatus(BaseModel):
    id: str
    username: str
    status: Literal["queued", "running", "complete", "failed"] = "queued"
    limit: int
    perf_type: str | None = None
    include_moves: bool = False
    page_size: int = 1000
    fetched_games: int = 0
    upserted_games: int = 0
    players_upserted: int = 0
    total_known: int | None = None
    batches_completed: int = 0
    error: str | None = None
    started_at: datetime | None = None
    updated_at: datetime
    finished_at: datetime | None = None


class ResultBucket(BaseModel):
    total: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    unknown: int = 0
    win_rate: float = 0.0


class RatingPoint(BaseModel):
    at: datetime
    rating: int


class AnalysisSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_games: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    unknown: int = 0
    win_rate: float = 0.0
    avg_opponent_rating: float | None = None

    def __getitem__(self, key: str) -> Any:
        try:
            return getattr(self, key)
        except AttributeError as exc:
            raise KeyError(key) from exc


class PlayerAnalysis(BaseModel):
    player: PlayerProfile
    games_count: int
    source: Literal["cache", "refresh"]
    generated_at: datetime
    coverage: AnalysisCoverage = Field(default_factory=AnalysisCoverage)
    summary: AnalysisSummary
    by_color: dict[str, ResultBucket]
    openings: dict[str, ResultBucket]
    openings_by_color: dict[str, dict[str, ResultBucket]] = Field(default_factory=dict)
    castling: dict[str, ResultBucket]
    queen_presence: dict[str, ResultBucket]
    time_controls: dict[str, int]
    rating_timeline: list[RatingPoint]
    unsupported_metrics: list[str] = Field(default_factory=list)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail
