from __future__ import annotations

from .analysis import Analyzer
from .lichess import LichessGateway
from .schemas import PlayerAnalysis, PlayerProfile, SyncResult
from .settings import Settings
from .storage import Repository


class Licheats:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        repository: Repository | None = None,
        gateway: LichessGateway | None = None,
        analyzer: Analyzer | None = None,
    ):
        self.settings = settings or Settings.from_env()
        self.repository = repository or Repository(self.settings.db_url)
        self.gateway = gateway or LichessGateway(self.settings)
        self.analyzer = analyzer or Analyzer()

    def get_player(self, username: str) -> PlayerProfile | None:
        return self.repository.get_player(username)

    def sync_player(
        self,
        username: str,
        *,
        limit: int = 100,
        perf_type: str | None = None,
    ) -> SyncResult:
        normalized = username.lower()
        player = self.gateway.get_player(normalized)
        games = self.gateway.get_games(normalized, limit=limit, perf_type=perf_type)
        return SyncResult(
            username=normalized,
            players_upserted=self.repository.upsert_player(player),
            games_upserted=self.repository.upsert_games(games),
            fetched_games=len(games),
        )

    def analyze_player(
        self,
        username: str,
        *,
        limit: int = 100,
        refresh: bool = False,
        perf_type: str | None = None,
    ) -> PlayerAnalysis:
        normalized = username.lower()
        source = "refresh" if refresh else "cache"
        player = self.repository.get_player(normalized)
        games = self.repository.get_games_for_player(normalized, limit=limit)

        if refresh or player is None or not games:
            self.sync_player(normalized, limit=limit, perf_type=perf_type)
            player = self.repository.get_player(normalized)
            games = self.repository.get_games_for_player(normalized, limit=limit)
            source = "refresh"

        if player is None:
            raise RuntimeError(f"Player {username!r} was not available after sync")
        return self.analyzer.analyze(player, games, source=source)
