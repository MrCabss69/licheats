import logging
from licheats.shared import Player, Game
from collections import defaultdict, Counter
from typing import List, Dict, Any
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class GamesAnalyzer:
    @staticmethod
    def analyze(player: Player, games: List[Game]) -> Dict[str, Any]:
        stats = {
            'rating_progression': [],
            'game_duration': [],
            'win_rate_by_color': {'white': Counter(), 'black': Counter()},
            'preferred_opening_distribution': Counter(),
            'opening_win_distribution': defaultdict(Counter),
            'win_status_distribution': Counter(),
            'win_reasons': Counter(),
            'loss_reasons': Counter(),
            'castling_side_distribution': Counter(),
            'castling_win_distribution': defaultdict(Counter),
            'piece_movement_distribution': Counter(),
            'time_control_distribution': Counter(),
            'performance_with_queens': defaultdict(Counter),
            'time_pressure_performance': defaultdict(Counter)
        }

        for game in games:
            try:
                GamesAnalyzer._update_stats(game, stats, player)
            except Exception as e:
                logger.error(f"Error processing game {game.id}: {str(e)}")

        logger.debug(f"Final stats: {stats}")
        return dict(stats)

    @staticmethod
    def _update_stats(game: Game, stats: Dict[str, Any], player: Player):
        logger.debug(f"Processing game {game.id}")
        player_color = 'white' if game.players_white_id == player.username else 'black'
        is_winner = game.winner == player_color if game.winner else False

        GamesAnalyzer._update_game_based_stats(game, stats, player, player_color, is_winner)
        GamesAnalyzer._update_castling_stats(game, stats, player, player_color, is_winner)
        GamesAnalyzer._update_opening_stats(game, stats, player_color, is_winner)
        GamesAnalyzer._update_piece_movement_stats(game, stats, player, player_color)
        GamesAnalyzer._update_time_control_stats(game, stats)
        GamesAnalyzer._update_performance_stats(game, stats, player, player_color, is_winner)

    @staticmethod
    def _update_game_based_stats(game: Game, stats: Dict[str, Any], player: Player, player_color: str, is_winner: bool):
        stats['win_status_distribution'][game.status] += 1
        stats['win_rate_by_color'][player_color]['total'] += 1
        if is_winner:
            stats['win_rate_by_color'][player_color]['wins'] += 1
            stats['win_reasons'][game.status] += 1
        elif game.winner:
            stats['loss_reasons'][game.status] += 1

        player_rating = game.players_white_rating if player_color == 'white' else game.players_black_rating
        if player_rating is not None:
            stats['rating_progression'].append((game.created_at, player_rating))
        
        if game.last_move_at and game.created_at:
            duration = (game.last_move_at - game.created_at).total_seconds()
            stats['game_duration'].append(duration)

    @staticmethod
    def _update_opening_stats(game: Game, stats: Dict[str, Any], player_color: str, is_winner: bool):
        if game.opening_eco:
            eco = game.opening_eco
            stats['preferred_opening_distribution'][eco] += 1
            stats['opening_win_distribution'][eco]['total'] += 1
            stats['opening_win_distribution'][eco]['wins' if is_winner else 'losses'] += 1

    @staticmethod
    def _update_castling_stats(game: Game, stats: Dict[str, Any], player: Player, player_color: str, is_winner: bool):
        moves = game.moves.split() if game.moves else []
        player_moves = moves[::2] if player_color == 'white' else moves[1::2]
        for move in player_moves:
            if 'O-O-O' in move:
                stats['castling_side_distribution']['queenside'] += 1
                stats['castling_win_distribution']['queenside']['wins' if is_winner else 'losses'] += 1
            elif 'O-O' in move:
                stats['castling_side_distribution']['kingside'] += 1
                stats['castling_win_distribution']['kingside']['wins' if is_winner else 'losses'] += 1

    @staticmethod
    def _update_piece_movement_stats(game: Game, stats: Dict[str, Any], player: Player, player_color: str):
        moves = game.moves.split() if game.moves else []
        player_moves = moves[::2] if player_color == 'white' else moves[1::2]
        for move in player_moves:
            if move and move[0].isupper() and move[0] in 'PNBRQK':
                stats['piece_movement_distribution'][move[0]] += 1

    @staticmethod
    def _update_time_control_stats(game: Game, stats: Dict[str, Any]):
        if game.clock_initial is not None and game.clock_increment is not None:
            time_control = f"{game.clock_initial // 60}+{game.clock_increment}"
            stats['time_control_distribution'][time_control] += 1

    @staticmethod
    def _update_performance_stats(game: Game, stats: Dict[str, Any], player: Player, player_color: str, is_winner: bool):
        moves = game.moves.split() if game.moves else []
        player_moves = moves[::2] if player_color == 'white' else moves[1::2]
        has_queen = any('Q' in move for move in player_moves)
        stats['performance_with_queens']['with_queen' if has_queen else 'without_queen']['total'] += 1
        stats['performance_with_queens']['with_queen' if has_queen else 'without_queen']['wins' if is_winner else 'losses'] += 1

        if game.last_move_at and game.created_at:
            duration = (game.last_move_at - game.created_at).total_seconds()
            time_pressure = 'high' if duration < 60 else 'medium' if duration < 300 else 'low'
            stats['time_pressure_performance'][time_pressure]['total'] += 1
            stats['time_pressure_performance'][time_pressure]['wins' if is_winner else 'losses'] += 1

    @staticmethod
    def print_stats(stats: Dict[str, Any]):
        for key, value in stats.items():
            print(f"{key}:")
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    print(f"  {sub_key}: {sub_value}")
            elif isinstance(value, list):
                print(f"  {len(value)} items")
            else:
                print(f"  {value}")