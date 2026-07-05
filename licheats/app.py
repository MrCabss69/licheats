from __future__ import annotations

import logging
from datetime import datetime, timezone
from threading import Lock, Thread
from time import perf_counter
from typing import Any, Callable
from uuid import uuid4

from .analysis import Analyzer
from .lichess import LichessError, LichessGateway
from .schemas import (
    AnalysisCoverage,
    GameRecord,
    PlayerAnalysis,
    PlayerProfile,
    PlayerProfileSummary,
    SyncJobStatus,
    SyncResult,
)
from .settings import Settings
from .storage import Repository

MetricsCallback = Callable[[dict[str, Any]], None]
perf_logger = logging.getLogger("licheats.perf")


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000, 3)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _int_count(player: PlayerProfile, key: str) -> int:
    value = player.counts.get(key)
    return value if isinstance(value, int) else 0


def _total_known(player: PlayerProfile) -> int | None:
    total = _int_count(player, "all")
    return total if total > 0 else None


def _profile_summary(player: PlayerProfile) -> PlayerProfileSummary:
    wins = _int_count(player, "win")
    losses = _int_count(player, "loss")
    draws = _int_count(player, "draw")
    total = _int_count(player, "all") or wins + losses + draws
    decisive = wins + losses + draws
    play_time = player.raw.get("playTime") if isinstance(player.raw, dict) else None
    return PlayerProfileSummary(
        player=player,
        generated_at=_now(),
        total_games=total,
        wins=wins,
        losses=losses,
        draws=draws,
        win_rate=round((wins / decisive) * 100, 2) if decisive else 0.0,
        ratings=player.ratings,
        play_time={
            key: value
            for key, value in (play_time or {}).items()
            if isinstance(key, str) and isinstance(value, int)
        },
    )


class Licheats:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        repository: Repository | None = None,
        gateway: LichessGateway | None = None,
        analyzer: Analyzer | None = None,
        metrics_callback: MetricsCallback | None = None,
    ):
        self.settings = settings or Settings.from_env()
        self.repository = repository or Repository(self.settings.db_url)
        self.gateway = gateway or LichessGateway(self.settings)
        self.analyzer = analyzer or Analyzer()
        self.metrics_callback = metrics_callback
        self._sync_jobs: dict[str, SyncJobStatus] = {}
        self._sync_jobs_lock = Lock()

    def _emit_metrics(self, metrics: dict[str, Any]) -> None:
        perf_logger.info("licheats_perf", extra={"licheats_perf": metrics})
        if self.metrics_callback:
            self.metrics_callback(metrics)

    def get_player(self, username: str) -> PlayerProfile | None:
        return self.repository.get_player(username)

    def profile_summary(self, username: str) -> PlayerProfileSummary:
        normalized = username.lower()
        metrics: dict[str, Any] = {
            "operation": "profile_summary",
            "username": normalized,
        }
        operation_start = perf_counter()
        try:
            step_start = perf_counter()
            player = self.gateway.get_player(normalized)
            metrics["fetch_player_ms"] = _elapsed_ms(step_start)
            summary = _profile_summary(player)
            metrics["total_known"] = summary.total_games
            return summary
        except LichessError as exc:
            metrics["lichess_error_code"] = exc.code
            raise
        finally:
            metrics["total_ms"] = _elapsed_ms(operation_start)
            self._emit_metrics(metrics)

    def sync_player(
        self,
        username: str,
        *,
        limit: int = 100,
        perf_type: str | None = None,
        include_moves: bool = True,
        page_size: int = 1000,
    ) -> SyncResult:
        normalized = username.lower()
        metrics: dict[str, Any] = {
            "operation": "sync_player",
            "username": normalized,
            "limit": limit,
            "perf_type": perf_type,
            "include_moves": include_moves,
            "page_size": page_size,
        }
        operation_start = perf_counter()
        try:
            step_start = perf_counter()
            player = self.gateway.get_player(normalized)
            metrics["fetch_player_ms"] = _elapsed_ms(step_start)

            step_start = perf_counter()
            games = self.gateway.get_games(
                normalized,
                limit=limit,
                perf_type=perf_type,
                include_moves=include_moves,
                page_size=page_size,
            )
            metrics["fetch_games_ms"] = _elapsed_ms(step_start)
            metrics["fetched_games"] = len(games)

            step_start = perf_counter()
            players_upserted = self.repository.upsert_player(player)
            metrics["upsert_player_ms"] = _elapsed_ms(step_start)

            step_start = perf_counter()
            games_upserted = self.repository.upsert_games(
                games,
                preserve_existing_moves=not include_moves,
            )
            metrics["upsert_games_ms"] = _elapsed_ms(step_start)

            return SyncResult(
                username=normalized,
                players_upserted=players_upserted,
                games_upserted=games_upserted,
                fetched_games=len(games),
            )
        except LichessError as exc:
            metrics["lichess_error_code"] = exc.code
            raise
        finally:
            metrics["total_ms"] = _elapsed_ms(operation_start)
            self._emit_metrics(metrics)

    def analyze_player(
        self,
        username: str,
        *,
        limit: int = 100,
        refresh: bool = False,
        perf_type: str | None = None,
    ) -> PlayerAnalysis:
        normalized = username.lower()
        metrics: dict[str, Any] = {
            "operation": "analyze_player",
            "username": normalized,
            "limit": limit,
            "refresh": refresh,
            "perf_type": perf_type,
        }
        operation_start = perf_counter()
        source = "refresh" if refresh else "cache"

        step_start = perf_counter()
        player = self.repository.get_player(normalized)
        metrics["initial_get_player_ms"] = _elapsed_ms(step_start)

        step_start = perf_counter()
        games = self.repository.get_games_for_player(normalized, limit=limit, perf_type=perf_type)
        metrics["query_games_ms"] = _elapsed_ms(step_start)
        metrics["initial_cached_games"] = len(games)

        if refresh or player is None or not games:
            step_start = perf_counter()
            self.sync_player(normalized, limit=limit, perf_type=perf_type)
            metrics["sync_ms"] = _elapsed_ms(step_start)

            step_start = perf_counter()
            player = self.repository.get_player(normalized)
            metrics["post_sync_get_player_ms"] = _elapsed_ms(step_start)

            step_start = perf_counter()
            games = self.repository.get_games_for_player(normalized, limit=limit, perf_type=perf_type)
            metrics["post_sync_query_ms"] = _elapsed_ms(step_start)
            source = "refresh"

        if player is None:
            metrics["games_count"] = len(games)
            metrics["source"] = source
            metrics["total_ms"] = _elapsed_ms(operation_start)
            self._emit_metrics(metrics)
            raise RuntimeError(f"Player {username!r} was not available after sync")

        step_start = perf_counter()
        analysis = self.analyzer.analyze(player, games, source=source)
        analysis.coverage = AnalysisCoverage(
            games_analyzed=len(games),
            total_known=_total_known(player),
            is_syncing=self._is_syncing(normalized),
            sample=f"last_{limit}",
        )
        metrics["analyzer_ms"] = _elapsed_ms(step_start)
        metrics["games_count"] = len(games)
        metrics["source"] = source
        metrics["total_ms"] = _elapsed_ms(operation_start)
        self._emit_metrics(metrics)
        return analysis

    def start_sync_job(
        self,
        username: str,
        *,
        limit: int = 5000,
        perf_type: str | None = None,
        include_moves: bool = False,
        page_size: int = 1000,
    ) -> SyncJobStatus:
        normalized = username.lower()
        now = _now()
        cached_player = self.repository.get_player(normalized)
        job = SyncJobStatus(
            id=str(uuid4()),
            username=normalized,
            limit=limit,
            perf_type=perf_type,
            include_moves=include_moves,
            page_size=page_size,
            total_known=_total_known(cached_player) if cached_player is not None else None,
            updated_at=now,
        )
        with self._sync_jobs_lock:
            self._sync_jobs[job.id] = job

        thread = Thread(target=self._run_sync_job, args=(job.id,), daemon=True)
        thread.start()
        return self.get_sync_job(job.id) or job

    def get_sync_job(self, job_id: str) -> SyncJobStatus | None:
        with self._sync_jobs_lock:
            job = self._sync_jobs.get(job_id)
            return job.model_copy(deep=True) if job is not None else None

    def _is_syncing(self, username: str) -> bool:
        with self._sync_jobs_lock:
            return any(
                job.username == username and job.status in {"queued", "running"}
                for job in self._sync_jobs.values()
            )

    def _update_sync_job(self, job_id: str, **changes: Any) -> SyncJobStatus:
        with self._sync_jobs_lock:
            job = self._sync_jobs[job_id]
            for key, value in changes.items():
                setattr(job, key, value)
            job.updated_at = _now()
            return job.model_copy(deep=True)

    def _run_sync_job(self, job_id: str) -> None:
        job = self._update_sync_job(job_id, status="running", started_at=_now())
        metrics: dict[str, Any] = {
            "operation": "sync_job",
            "job_id": job.id,
            "username": job.username,
            "limit": job.limit,
            "perf_type": job.perf_type,
            "include_moves": job.include_moves,
            "page_size": job.page_size,
        }
        operation_start = perf_counter()
        try:
            step_start = perf_counter()
            player = self.gateway.get_player(job.username)
            metrics["fetch_player_ms"] = _elapsed_ms(step_start)

            step_start = perf_counter()
            players_upserted = self.repository.upsert_player(player)
            metrics["upsert_player_ms"] = _elapsed_ms(step_start)
            self._update_sync_job(
                job_id,
                players_upserted=players_upserted,
                total_known=_total_known(player),
            )

            fetch_start = perf_counter()
            batch: list[GameRecord] = []
            for game in self.gateway.iter_games(
                job.username,
                limit=job.limit,
                perf_type=job.perf_type,
                include_moves=job.include_moves,
                page_size=job.page_size,
            ):
                batch.append(game)
                if len(batch) >= job.page_size:
                    self._flush_sync_batch(job_id, batch)
                    batch = []

            if batch:
                self._flush_sync_batch(job_id, batch)

            metrics["fetch_games_ms"] = _elapsed_ms(fetch_start)
            final = self._update_sync_job(job_id, status="complete", finished_at=_now())
            metrics["fetched_games"] = final.fetched_games
            metrics["upserted_games"] = final.upserted_games
            metrics["batches_completed"] = final.batches_completed
        except LichessError as exc:
            metrics["lichess_error_code"] = exc.code
            self._update_sync_job(
                job_id,
                status="failed",
                error=str(exc),
                finished_at=_now(),
            )
        except Exception as exc:  # pragma: no cover - defensive boundary for background jobs
            self._update_sync_job(
                job_id,
                status="failed",
                error=f"{type(exc).__name__}: {exc}",
                finished_at=_now(),
            )
        finally:
            metrics["total_ms"] = _elapsed_ms(operation_start)
            self._emit_metrics(metrics)

    def _flush_sync_batch(self, job_id: str, batch: list[GameRecord]) -> None:
        if not batch:
            return
        job = self.get_sync_job(job_id)
        if job is None:
            return

        step_start = perf_counter()
        upserted = self.repository.upsert_games(
            batch,
            preserve_existing_moves=not job.include_moves,
        )
        upsert_ms = _elapsed_ms(step_start)
        updated = self._update_sync_job(
            job_id,
            fetched_games=job.fetched_games + len(batch),
            upserted_games=job.upserted_games + upserted,
            batches_completed=job.batches_completed + 1,
        )
        self._emit_metrics(
            {
                "operation": "sync_job_batch",
                "job_id": job_id,
                "username": job.username,
                "batch_games": len(batch),
                "fetched_games": updated.fetched_games,
                "upserted_games": updated.upserted_games,
                "upsert_games_ms": upsert_ms,
            }
        )
