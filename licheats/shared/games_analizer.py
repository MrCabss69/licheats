from collections import defaultdict, Counter
from typing import List, Dict, Any
from licheats.shared.models import Game, Player

class GamesAnalyzer:
    @staticmethod
    def analyze(player: Player, games: List[Game]) -> Dict[str, Any]:
        stats = defaultdict(lambda: defaultdict(Counter))
        stats.update({
            'rating_progression': [],
            'game_duration': [],
            'win_rate_by_color': {'white': Counter(), 'black': Counter()}
        })

        for game in games:
            GamesAnalyzer._update_stats(game, stats, player)

        return dict(stats)

    @staticmethod
    def _update_stats(game: Game, stats: Dict[str, Any], player: Player):
        player_color = 'white' if game.players_white_id == player.username else 'black'
        is_winner = game.winner == player_color

        GamesAnalyzer._update_opening_stats(game, stats, is_winner)
        GamesAnalyzer._update_game_stats(game, stats, player_color, is_winner)
        GamesAnalyzer._update_castling_stats(game, stats, is_winner)
        GamesAnalyzer._update_piece_movement_stats(game, stats)
        GamesAnalyzer._update_time_control_stats(game, stats)
        GamesAnalyzer._update_queen_performance_stats(game, stats, is_winner)
        GamesAnalyzer._update_time_pressure_stats(game, stats, is_winner)

    @staticmethod
    def _update_opening_stats(game: Game, stats: Dict[str, Any], is_winner: bool):
        stats['preferred_opening_distribution'][game.opening_eco] += 1
        stats['opening_win_distribution'][game.opening_eco]['total'] += 1
        stats['opening_win_distribution'][game.opening_eco]['wins' if is_winner else 'losses'] += 1

    @staticmethod
    def _update_game_stats(game: Game, stats: Dict[str, Any], player_color: str, is_winner: bool):
        stats['win_status_distribution'][game.status] += 1
        stats['win_rate_by_color'][player_color]['total'] += 1
        if is_winner:
            stats['win_rate_by_color'][player_color]['wins'] += 1
            stats['win_reasons'][game.status] += 1
        elif game.winner:
            stats['loss_reasons'][game.status] += 1

        player_rating = game.players_white_rating if player_color == 'white' else game.players_black_rating
        stats['rating_progression'].append((game.created_at, player_rating))

        if game.last_move_at and game.created_at:
            stats['game_duration'].append((game.last_move_at - game.created_at).total_seconds())

    @staticmethod
    def _update_castling_stats(game: Game, stats: Dict[str, Any], is_winner: bool):
        moves = game.moves.split()
        for move in moves:
            if 'O-O-O' in move:
                stats['castling_side_distribution']['queen'] += 1
                stats['castling_win_distribution']['queen_win' if is_winner else 'queen_loss'] += 1
            elif 'O-O' in move:
                stats['castling_side_distribution']['king'] += 1
                stats['castling_win_distribution']['king_win' if is_winner else 'king_loss'] += 1

    @staticmethod
    def _update_piece_movement_stats(game: Game, stats: Dict[str, Any]):
        moves = game.moves.split()
        for move in moves:
            if move[0].isupper() and move[0] in 'PNBRQK':
                stats['piece_movement_distribution'][move[0]] += 1

    @staticmethod
    def _update_time_control_stats(game: Game, stats: Dict[str, Any]):
        stats['time_control_distribution'][game.speed] += 1

    @staticmethod
    def _update_queen_performance_stats(game: Game, stats: Dict[str, Any], is_winner: bool):
        moves = game.moves.split()
        queens_traded = 'Q' in moves and 'q' in moves
        category = 'with_queens' if not queens_traded else 'without_queens'
        stats['performance_with_queens'][category]['total'] += 1
        if is_winner:
            stats['performance_with_queens'][category]['wins'] += 1

    @staticmethod
    def _update_time_pressure_stats(game: Game, stats: Dict[str, Any], is_winner: bool):
        moves = game.moves.split()
        under_pressure = any('!' in move for move in moves[-10:])
        category = 'under_pressure' if under_pressure else 'not_under_pressure'
        stats['time_pressure_performance'][category]['total'] += 1
        if is_winner:
            stats['time_pressure_performance'][category]['wins'] += 1
