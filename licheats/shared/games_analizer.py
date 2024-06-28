

class GamesAnalyzer:
    def __init__(self, player_username, games):
        self.username = player_username  # Usuario del jugador que estamos analizando
        self.games = games  # Lista de partidas

    def is_player_white(self, game):
        return game.players_white_id == self.username

    def enroque_preference(self):
        king_side, queen_side = 0, 0
        for game in self.games:
            moves = game.moves.split()
            is_white = self.is_player_white(game)
            # Asignar el lado correcto del enroque según el color del jugador
            king_rook = 'O-O' if is_white else 'O-O-O'
            queen_rook = 'O-O-O' if is_white else 'O-O'
            if king_rook in moves:
                king_side += 1
            if queen_rook in moves:
                queen_side += 1
        return king_side, queen_side

    def performance_with_queens(self):
        with_queen, without_queen = 0, 0
        for game in self.games:
            moves = game.moves.split()
            is_white = self.is_player_white(game)
            # Considerar solo las jugadas donde participa el jugador
            queen_moves = [move for move in moves if ('Q' in move.upper() and is_white) or ('q' in move.lower() and not is_white)]
            if queen_moves:
                with_queen += 1
            else:
                without_queen += 1
        return with_queen, without_queen

    def common_causes_of_defeat(self):
        results = {'time': 0, 'resign': 0, 'checkmate': 0}
        for game in self.games:
            if game.winner != game.players_black_id == self.username or game.players_white_id == self.username:
                if 'time' in game.status:
                    results['time'] += 1
                elif 'resign' in game.status:
                    results['resign'] += 1
                elif 'checkmate' in game.status:
                    results['checkmate'] += 1
        return results

    def game_wins(self):
        by_time, by_resignation, by_checkmate = 0, 0, 0
        for game in self.games:
            if game.result == 'win' and game.players_black_id == self.username or game.players_white_id == self.username:
                if 'time' in game.status:
                    by_time += 1
                elif 'resign' in game.status:
                    by_resignation += 1
                elif 'checkmate' in game.status:
                    by_checkmate += 1
        return by_time, by_resignation, by_checkmate
