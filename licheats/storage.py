from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .schemas import GameRecord, PlayerProfile


class Base(DeclarativeBase):
    pass


class PlayerRow(Base):
    __tablename__ = "players"

    username: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    ratings: Mapped[dict] = mapped_column(JSON, default=dict)
    counts: Mapped[dict] = mapped_column(JSON, default=dict)
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GameRow(Base):
    __tablename__ = "games"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    rated: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    variant: Mapped[str | None] = mapped_column(String, nullable=True)
    speed: Mapped[str | None] = mapped_column(String, nullable=True)
    perf: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_move_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    winner: Mapped[str | None] = mapped_column(String, nullable=True)
    moves: Mapped[str] = mapped_column(String, default="")
    initial_fen: Mapped[str | None] = mapped_column(String, nullable=True)
    opening_eco: Mapped[str | None] = mapped_column(String, nullable=True)
    opening_name: Mapped[str | None] = mapped_column(String, nullable=True)
    opening_ply: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clock_initial: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clock_increment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clock_total_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    white_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    black_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    white_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    black_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _ensure_sqlite_parent(db_url: str) -> None:
    if not db_url.startswith("sqlite:///"):
        return
    path = db_url.removeprefix("sqlite:///")
    if path in {":memory:", ""}:
        return
    Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Repository:
    def __init__(self, db_url: str):
        _ensure_sqlite_parent(db_url)
        self.engine = create_engine(db_url, future=True)
        Base.metadata.create_all(self.engine)
        self._session = sessionmaker(self.engine, expire_on_commit=False, future=True)

    def upsert_player(self, player: PlayerProfile) -> int:
        row = PlayerRow(
            username=player.username.lower(),
            display_name=player.display_name,
            title=player.title,
            url=player.url,
            ratings=player.ratings,
            counts=player.counts,
            raw_json=player.raw,
            updated_at=_now(),
        )
        with self.session() as session:
            session.merge(row)
            session.commit()
        return 1

    def upsert_games(self, games: Iterable[GameRecord]) -> int:
        count = 0
        with self.session() as session:
            for game in games:
                session.merge(self._game_to_row(game))
                count += 1
            session.commit()
        return count

    def get_player(self, username: str) -> PlayerProfile | None:
        with self.session() as session:
            row = session.get(PlayerRow, username.lower())
            return self._row_to_player(row) if row else None

    def get_games_for_player(self, username: str, limit: int = 100) -> list[GameRecord]:
        user = username.lower()
        statement = (
            select(GameRow)
            .where((GameRow.white_id == user) | (GameRow.black_id == user))
            .order_by(GameRow.created_at.desc())
            .limit(limit)
        )
        with self.session() as session:
            return [self._row_to_game(row) for row in session.scalars(statement).all()]

    def session(self) -> Session:
        return self._session()

    @staticmethod
    def _game_to_row(game: GameRecord) -> GameRow:
        return GameRow(
            id=game.id,
            rated=game.rated,
            variant=game.variant,
            speed=game.speed,
            perf=game.perf,
            created_at=game.created_at,
            last_move_at=game.last_move_at,
            status=game.status,
            winner=game.winner,
            moves=game.moves,
            initial_fen=game.initial_fen,
            opening_eco=game.opening_eco,
            opening_name=game.opening_name,
            opening_ply=game.opening_ply,
            clock_initial=game.clock_initial,
            clock_increment=game.clock_increment,
            clock_total_time=game.clock_total_time,
            white_id=game.white_id.lower() if game.white_id else None,
            black_id=game.black_id.lower() if game.black_id else None,
            white_rating=game.white_rating,
            black_rating=game.black_rating,
            raw_json=game.raw,
            updated_at=_now(),
        )

    @staticmethod
    def _row_to_player(row: PlayerRow) -> PlayerProfile:
        return PlayerProfile(
            username=row.username,
            display_name=row.display_name,
            title=row.title,
            url=row.url,
            ratings=row.ratings or {},
            counts=row.counts or {},
            raw=row.raw_json or {},
        )

    @staticmethod
    def _row_to_game(row: GameRow) -> GameRecord:
        return GameRecord(
            id=row.id,
            rated=row.rated,
            variant=row.variant,
            speed=row.speed,
            perf=row.perf,
            created_at=row.created_at,
            last_move_at=row.last_move_at,
            status=row.status,
            winner=row.winner if row.winner in {"white", "black"} else None,
            moves=row.moves or "",
            initial_fen=row.initial_fen,
            opening_eco=row.opening_eco,
            opening_name=row.opening_name,
            opening_ply=row.opening_ply,
            clock_initial=row.clock_initial,
            clock_increment=row.clock_increment,
            clock_total_time=row.clock_total_time,
            white_id=row.white_id,
            black_id=row.black_id,
            white_rating=row.white_rating,
            black_rating=row.black_rating,
            raw=row.raw_json or {},
        )
