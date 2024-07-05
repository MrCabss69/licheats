from typing import Union, Dict
from licheats.shared import Player, Game
from licheats.data import DatabaseManager

class DataService:
    def __init__(self):
        self.database = DatabaseManager()
    
    def get_player(self, username: str) -> Player:
        """ Retrieve a Player instance by username. """
        player = self.database.get_player(username)
        return player
    
    def get_player_games(self, player:  Union[str, Player], max_games: int = None) -> list:
        """ Retrieve a list of Game instances associated with the player. """
        games = self.database.get_player_games(player, max_games)
        return games
    
    def save_player(self, player: Player) -> None:
        """ Save a Player instance to the database. """
        self.database.save_player(player)
    
    def save_games(self, games: Union[list, Game]) -> None:
        """ Save one or multiple Game instances to the database. """
        if isinstance(games, list):
            for game in games:
                self.database.save_game(game)
        else:
            self.database.save_game(games)

    def get_player_stats(self, player: Union[str, Player]) -> Dict:
        """ Retrieve summary statistics for a player. """
        if isinstance(player, str):
            player = self.get_player(player)
            if not player:
                return {}  # Return an empty dict if no player found

        # Collect player statistics
        stats = {
            "username": player.username,
            "games_played": player.all_games,
            "total_wins": player.win_games,
            "total_losses": player.loss_games,
            "rating_bullet": player.bullet_rating,
            "rating_blitz": player.blitz_rating,
            "rating_classical": player.classical_rating,
        }
        return stats
