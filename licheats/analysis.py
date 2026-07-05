from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

import chess

from .schemas import AnalysisSummary, GameRecord, PlayerAnalysis, PlayerProfile, RatingPoint, ResultBucket

BucketDict = dict[str, int]
Result = Literal["win", "loss", "draw", "unknown"]
UNKNOWN_GAME_STATUSES = {"aborted", "noStart"}


def _new_bucket() -> BucketDict:
    return {"total": 0, "wins": 0, "losses": 0, "draws": 0, "unknown": 0}


def _add(bucket: BucketDict, result: Result) -> None:
    bucket["total"] += 1
    if result == "win":
        bucket["wins"] += 1
    elif result == "loss":
        bucket["losses"] += 1
    elif result == "draw":
        bucket["draws"] += 1
    else:
        bucket["unknown"] += 1


def _freeze(bucket: BucketDict) -> ResultBucket:
    decisive = bucket["wins"] + bucket["losses"] + bucket["draws"]
    win_rate = round((bucket["wins"] / decisive) * 100, 2) if decisive else 0.0
    return ResultBucket(**bucket, win_rate=win_rate)


def _color_for_player(player: PlayerProfile, game: GameRecord) -> str:
    username = player.username.lower()
    if game.white_id == username:
        return "white"
    if game.black_id == username:
        return "black"
    return "unknown"


def _result_for_color(game: GameRecord, color: str) -> Result:
    if color not in {"white", "black"}:
        return "unknown"
    if game.winner == color:
        return "win"
    if game.winner in {"white", "black"}:
        return "loss"
    if game.status in UNKNOWN_GAME_STATUSES:
        return "unknown"
    if game.status:
        return "draw"
    return "unknown"


def _opening_key(game: GameRecord) -> str:
    if game.opening_eco and game.opening_name:
        return f"{game.opening_eco} {game.opening_name}"
    if game.opening_eco:
        return game.opening_eco
    if game.opening_name:
        return game.opening_name
    return "unknown"


def _time_control(game: GameRecord) -> str | None:
    if game.clock_initial is None or game.clock_increment is None:
        return None
    return f"{game.clock_initial // 60}+{game.clock_increment}"


def _rating_for_color(game: GameRecord, color: str) -> int | None:
    if color == "white":
        return game.white_rating
    if color == "black":
        return game.black_rating
    return None


def _opponent_rating(game: GameRecord, color: str) -> int | None:
    if color == "white":
        return game.black_rating
    if color == "black":
        return game.white_rating
    return None


def _queen_category(board: chess.Board, color: str) -> str:
    if color not in {"white", "black"}:
        return "unknown"
    player_color = chess.WHITE if color == "white" else chess.BLACK
    opponent_color = not player_color
    player_has_queen = bool(board.pieces(chess.QUEEN, player_color))
    opponent_has_queen = bool(board.pieces(chess.QUEEN, opponent_color))
    if player_has_queen and opponent_has_queen:
        return "both_queens_present_final"
    if not player_has_queen and not opponent_has_queen:
        return "both_queens_missing_final"
    if not player_has_queen:
        return "player_queen_missing_final"
    return "opponent_queen_missing_final"


def _scan_board_features(game: GameRecord, color: str) -> tuple[set[str], str, bool]:
    if not game.moves:
        return set(), "unknown", False
    try:
        board = chess.Board(game.initial_fen) if game.initial_fen else chess.Board()
    except ValueError:
        return set(), "unknown", True

    castling: set[str] = set()
    invalid = False
    for ply, san in enumerate(game.moves.split()):
        moving_color = "white" if ply % 2 == 0 else "black"
        try:
            move = board.parse_san(san)
        except ValueError:
            invalid = True
            break
        if moving_color == color and board.is_castling(move):
            castling.add("kingside" if chess.square_file(move.to_square) > chess.square_file(move.from_square) else "queenside")
        board.push(move)
    return castling, _queen_category(board, color), invalid


@dataclass(frozen=True)
class GameAnalysisContext:
    color: str
    result: Result
    opening_key: str
    time_control: str | None
    rating: int | None
    opponent_rating: int | None
    castling_sides: set[str]
    queen_category: str
    invalid_moves: bool


def _context_for_game(player: PlayerProfile, game: GameRecord) -> GameAnalysisContext:
    color = _color_for_player(player, game)
    castling_sides, queen_category, invalid_moves = _scan_board_features(game, color)
    return GameAnalysisContext(
        color=color,
        result=_result_for_color(game, color),
        opening_key=_opening_key(game),
        time_control=_time_control(game),
        rating=_rating_for_color(game, color),
        opponent_rating=_opponent_rating(game, color),
        castling_sides=castling_sides,
        queen_category=queen_category,
        invalid_moves=invalid_moves,
    )


def _add_board_feature_buckets(
    *,
    castling: dict[str, BucketDict],
    queen_presence: dict[str, BucketDict],
    context: GameAnalysisContext,
) -> None:
    if context.castling_sides:
        for side in context.castling_sides:
            _add(castling[side], context.result)
    else:
        _add(castling["none"], context.result)
    _add(queen_presence[context.queen_category], context.result)


class Analyzer:
    def analyze(
        self,
        player: PlayerProfile,
        games: list[GameRecord],
        *,
        source: Literal["cache", "refresh"] = "cache",
    ) -> PlayerAnalysis:
        by_color = defaultdict(_new_bucket)
        openings = defaultdict(_new_bucket)
        openings_by_color: dict[str, dict[str, BucketDict]] = {
            "white": defaultdict(_new_bucket),
            "black": defaultdict(_new_bucket),
        }
        castling = defaultdict(_new_bucket)
        queen_presence = defaultdict(_new_bucket)
        time_controls: dict[str, int] = defaultdict(int)
        rating_timeline: list[RatingPoint] = []
        unsupported: set[str] = set()
        opponent_ratings: list[int] = []
        summary_bucket = _new_bucket()

        for game in games:
            context = _context_for_game(player, game)
            _add(summary_bucket, context.result)
            _add(by_color[context.color], context.result)
            _add(openings[context.opening_key], context.result)
            if context.color in ("white", "black"):
                _add(openings_by_color[context.color][context.opening_key], context.result)

            if context.time_control:
                time_controls[context.time_control] += 1

            if context.rating is not None and game.created_at is not None:
                rating_timeline.append(RatingPoint(at=game.created_at, rating=context.rating))

            if context.opponent_rating is not None:
                opponent_ratings.append(context.opponent_rating)

            if context.invalid_moves:
                unsupported.add("Some games contain moves or FENs that python-chess could not parse.")
            _add_board_feature_buckets(
                castling=castling,
                queen_presence=queen_presence,
                context=context,
            )

        frozen_summary = _freeze(summary_bucket)
        avg_opponent_rating = (
            round(sum(opponent_ratings) / len(opponent_ratings), 2) if opponent_ratings else None
        )
        summary = AnalysisSummary(
            total_games=frozen_summary.total,
            wins=frozen_summary.wins,
            losses=frozen_summary.losses,
            draws=frozen_summary.draws,
            unknown=frozen_summary.unknown,
            win_rate=frozen_summary.win_rate,
            avg_opponent_rating=avg_opponent_rating,
        )

        return PlayerAnalysis(
            player=player,
            games_count=len(games),
            source=source,
            generated_at=datetime.now(timezone.utc),
            summary=summary,
            by_color={key: _freeze(value) for key, value in by_color.items()},
            openings={key: _freeze(value) for key, value in openings.items()},
            openings_by_color={
                color: {key: _freeze(bucket) for key, bucket in table.items()}
                for color, table in openings_by_color.items()
            },
            castling={key: _freeze(value) for key, value in castling.items()},
            queen_presence={key: _freeze(value) for key, value in queen_presence.items()},
            time_controls=dict(time_controls),
            rating_timeline=sorted(rating_timeline, key=lambda point: point.at),
            unsupported_metrics=sorted(unsupported),
        )
