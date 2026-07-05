from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections.abc import Callable, Iterable
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from licheats import Licheats, Settings
from licheats.analysis import Analyzer
from licheats.lichess import LichessGateway, normalize_game, normalize_player
from licheats.storage import GameRow, Repository


FixtureFactory = Callable[[int], list[Any]]


def now_ms() -> float:
    return time.perf_counter() * 1000


def elapsed_ms(start_ms: float) -> float:
    return round(now_ms() - start_ms, 3)


def emit(record: dict[str, Any]) -> None:
    print(json.dumps(record, sort_keys=True), flush=True)


@contextmanager
def db_url_context(explicit_db_url: str | None):
    if explicit_db_url:
        yield explicit_db_url
        return
    with NamedTemporaryFile(prefix="licheats-perf-", suffix=".sqlite3") as tmp:
        yield f"sqlite:///{tmp.name}"


def response_size(payload: Any) -> int:
    if hasattr(payload, "model_dump_json"):
        return len(payload.model_dump_json())
    return len(json.dumps(payload, default=str))


def run_service_call(
    *,
    operation: str,
    call: Callable[[], Any],
    metric_records: list[dict[str, Any]],
) -> Any:
    metric_records.clear()
    start = now_ms()
    status = "ok"
    error = None
    result = None
    try:
        result = call()
        return result
    except Exception as exc:
        status = "error"
        error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        record = {
            "kind": "service_call",
            "operation": operation,
            "status": status,
            "wall_ms": elapsed_ms(start),
            "response_bytes": response_size(result) if result is not None else 0,
            "internal_metrics": list(metric_records),
        }
        if error:
            record["error"] = error
        if hasattr(result, "fetched_games"):
            record["games_count"] = result.fetched_games
        elif hasattr(result, "games_count"):
            record["games_count"] = result.games_count
        emit(record)


def run_http_call(method: str, url: str) -> None:
    start = now_ms()
    status = "ok"
    error = None
    response = None
    try:
        response = httpx.request(method, url, timeout=300)
        response.raise_for_status()
    except Exception as exc:
        status = "error"
        error = f"{type(exc).__name__}: {exc}"
    record = {
        "kind": "http_call",
        "method": method,
        "url": url,
        "status": status,
        "wall_ms": elapsed_ms(start),
        "status_code": response.status_code if response is not None else None,
        "response_bytes": len(response.content) if response is not None else 0,
    }
    if error:
        record["error"] = error
    emit(record)


def run_endpoint_probe(args: argparse.Namespace) -> None:
    if args.base_url:
        base_url = args.base_url.rstrip("/")
        for limit in args.limit:
            run_http_call("GET", f"{base_url}/players/{args.username}/analysis?limit={limit}&refresh=false")
        run_http_call("POST", f"{base_url}/players/{args.username}/sync?limit={max(args.limit)}")
        return

    records: list[dict[str, Any]] = []
    with db_url_context(args.db_url) as db_url:
        settings = Settings.from_env()
        settings = Settings(
            db_url=db_url,
            lichess_api_token=settings.lichess_api_token,
            lichess_base_url=settings.lichess_base_url,
            request_timeout=settings.request_timeout,
            cors_origins=settings.cors_origins,
            cors_origin_regex=settings.cors_origin_regex,
        )
        service = Licheats(settings, metrics_callback=records.append)
        seed_limit = max(args.limit)
        run_service_call(
            operation=f"sync_player limit={seed_limit}",
            call=lambda: service.sync_player(args.username, limit=seed_limit),
            metric_records=records,
        )
        for limit in args.limit:
            run_service_call(
                operation=f"analyze_player cache limit={limit}",
                call=lambda limit=limit: service.analyze_player(
                    args.username,
                    limit=limit,
                    refresh=False,
                ),
                metric_records=records,
            )
        run_service_call(
            operation=f"sync_player repeat limit={seed_limit}",
            call=lambda: service.sync_player(args.username, limit=seed_limit),
            metric_records=records,
        )


def run_moves_experiment(args: argparse.Namespace) -> None:
    settings = Settings.from_env()
    timeout = httpx.Timeout(args.timeout, read=args.timeout)
    gateway = LichessGateway(settings, client=httpx.Client(timeout=timeout))
    limit = max(args.limit)
    for include_moves in [True, False]:
        start = now_ms()
        games = list(
            gateway.iter_games(
                args.username,
                limit=limit,
                include_moves=include_moves,
                page_size=args.page_size,
            )
        )
        emit(
            {
                "kind": "gateway_moves_experiment",
                "username": args.username,
                "limit": limit,
                "include_moves": include_moves,
                "page_size": args.page_size,
                "games_count": len(games),
                "wall_ms": elapsed_ms(start),
                "normalized_response_bytes": sum(len(game.model_dump_json()) for game in games),
                "games_with_moves": sum(1 for game in games if game.moves),
            }
        )


def iter_labeled_games(lines: Iterable[str]) -> Iterable[Any]:
    for line in lines:
        if line.strip():
            yield normalize_game(json.loads(line))


def run_full_history(args: argparse.Namespace) -> None:
    settings = Settings.from_env()
    timeout = httpx.Timeout(args.timeout, read=args.timeout)
    gateway = LichessGateway(settings, client=httpx.Client(timeout=timeout))
    player = gateway.get_player(args.username)
    reported_total = player.counts.get("all") or args.full_history_max
    target = min(reported_total, args.full_history_max)

    games_by_id: dict[str, Any] = {}
    started = now_ms()

    for game in gateway.iter_games(args.username, limit=target, page_size=args.page_size):
        games_by_id.setdefault(game.id, game)
        if len(games_by_id) % args.page_size == 0:
            emit(
                {
                    "kind": "full_history_progress",
                    "fetched_games": len(games_by_id),
                    "chunk_games": args.page_size,
                    "elapsed_ms": elapsed_ms(started),
                }
            )

    games = sorted(
        games_by_id.values(),
        key=lambda game: (game.created_at or game.last_move_at).timestamp()
        if game.created_at or game.last_move_at
        else 0,
        reverse=True,
    )
    step = now_ms()
    analysis = Analyzer().analyze(player, games, source="refresh")
    analyzer_ms = elapsed_ms(step)
    emit(
        {
            "kind": "full_history_summary",
            "username": args.username,
            "streaming": True,
            "reported_total": reported_total,
            "fetched_games": len(games),
            "games_count": analysis.games_count,
            "analyzer_ms": analyzer_ms,
            "response_bytes": response_size(analysis),
            "elapsed_ms": elapsed_ms(started),
        }
    )


def fixture_player_and_games() -> tuple[Any, list[Any]]:
    fixtures = Path("tests/fixtures")
    player = normalize_player(json.loads((fixtures / "player.json").read_text()))
    games = [normalize_game(json.loads(line)) for line in (fixtures / "games.ndjson").read_text().splitlines()]
    return player, games


def make_fixture_games(count: int) -> list[Any]:
    _, base_games = fixture_player_and_games()
    games = []
    for index in range(count):
        base = base_games[index % len(base_games)]
        games.append(
            base.model_copy(
                update={
                    "id": f"{base.id}-{index}",
                    "perf": "blitz" if index % 3 else "rapid",
                }
            )
        )
    return games


def bench(label: str, call: Callable[[], Any], reps: int = 3) -> dict[str, Any]:
    samples = []
    last = None
    for _ in range(reps):
        start = now_ms()
        last = call()
        samples.append(now_ms() - start)
    return {
        "label": label,
        "min_ms": round(min(samples), 3),
        "median_ms": round(statistics.median(samples), 3),
        "max_ms": round(max(samples), 3),
        "last_result": last,
    }


def row_values(row: GameRow) -> dict[str, Any]:
    return {column.name: getattr(row, column.name) for column in GameRow.__table__.columns}


def bulk_upsert_games(repo: Repository, games: list[Any], chunk_size: int = 500) -> int:
    rows = [row_values(repo._game_to_row(game)) for game in games]
    if not rows:
        return 0
    total = 0
    with repo.session() as session:
        for start in range(0, len(rows), chunk_size):
            chunk = rows[start : start + chunk_size]
            statement = sqlite_insert(GameRow).values(chunk)
            update_columns = {
                column.name: getattr(statement.excluded, column.name)
                for column in GameRow.__table__.columns
                if column.name != "id"
            }
            statement = statement.on_conflict_do_update(
                index_elements=[GameRow.id],
                set_=update_columns,
            )
            session.execute(statement)
            total += len(chunk)
        session.commit()
    return total


def explain_plan(repo: Repository, sql: str) -> list[str]:
    with repo.engine.connect() as connection:
        return [row[3] for row in connection.execute(text(f"EXPLAIN QUERY PLAN {sql}")).all()]


def run_storage_experiments(args: argparse.Namespace) -> None:
    player, _ = fixture_player_and_games()
    for count in args.storage_size:
        games = make_fixture_games(count)
        with NamedTemporaryFile(prefix="licheats-storage-current-", suffix=".sqlite3") as tmp:
            repo = Repository(f"sqlite:///{tmp.name}")
            repo.upsert_player(player)
            emit({"kind": "storage_benchmark", **bench(f"current_upsert n={count}", lambda: repo.upsert_games(games), reps=1)})
            emit(
                {
                    "kind": "storage_benchmark",
                    **bench(
                        f"current_query limit=1000 n={count}",
                        lambda: len(repo.get_games_for_player("fieber69", limit=1000)),
                    ),
                }
            )
            emit(
                {
                    "kind": "storage_plan",
                    "label": f"current_query_plan n={count}",
                    "plan": explain_plan(
                        repo,
                        "SELECT * FROM games WHERE (white_id = 'fieber69' OR black_id = 'fieber69') "
                        "ORDER BY created_at DESC LIMIT 1000",
                    ),
                }
            )

        with NamedTemporaryFile(prefix="licheats-storage-bulk-", suffix=".sqlite3") as tmp:
            repo = Repository(f"sqlite:///{tmp.name}")
            repo.upsert_player(player)
            emit({"kind": "storage_benchmark", **bench(f"bulk_upsert n={count}", lambda: bulk_upsert_games(repo, games), reps=1)})
            with repo.engine.begin() as connection:
                connection.execute(text("CREATE INDEX ix_games_white_created ON games (white_id, created_at DESC)"))
                connection.execute(text("CREATE INDEX ix_games_black_created ON games (black_id, created_at DESC)"))
                connection.execute(text("CREATE INDEX ix_games_white_perf_created ON games (white_id, perf, created_at DESC)"))
                connection.execute(text("CREATE INDEX ix_games_black_perf_created ON games (black_id, perf, created_at DESC)"))
            emit(
                {
                    "kind": "storage_benchmark",
                    **bench(
                        f"indexed_query limit=1000 n={count}",
                        lambda: len(repo.get_games_for_player("fieber69", limit=1000)),
                    ),
                }
            )
            emit(
                {
                    "kind": "storage_plan",
                    "label": f"indexed_query_plan n={count}",
                    "plan": explain_plan(
                        repo,
                        "SELECT * FROM games WHERE (white_id = 'fieber69' OR black_id = 'fieber69') "
                        "ORDER BY created_at DESC LIMIT 1000",
                    ),
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure Licheats hot paths and emit JSONL.")
    parser.add_argument("--username", default="fieber69")
    parser.add_argument("--limit", type=int, action="append", default=None)
    parser.add_argument("--db-url", default=None)
    parser.add_argument("--base-url", default=None, help="Hit a running API instead of the local service object.")
    parser.add_argument("--skip-endpoints", action="store_true", help="Skip endpoint/service probes.")
    parser.add_argument("--full-history", action="store_true")
    parser.add_argument("--moves-experiment", action="store_true")
    parser.add_argument("--full-history-max", type=int, default=20000)
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--storage-experiments", action="store_true")
    parser.add_argument("--storage-size", type=int, action="append", default=None)
    args = parser.parse_args()
    args.limit = args.limit or [100, 1000]
    args.storage_size = args.storage_size or [100, 1000, 3000]
    return args


def main() -> None:
    args = parse_args()
    try:
        if not args.skip_endpoints:
            run_endpoint_probe(args)
        if args.moves_experiment:
            run_moves_experiment(args)
        if args.full_history:
            run_full_history(args)
        if args.storage_experiments:
            run_storage_experiments(args)
    except Exception as exc:
        emit({"kind": "probe_error", "error": f"{type(exc).__name__}: {exc}"})
        raise


if __name__ == "__main__":
    sys.exit(main())
