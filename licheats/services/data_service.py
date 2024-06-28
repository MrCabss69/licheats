from typing import Union
from licheats.data import DatabaseManager
from licheats.shared import Player, Game

class DataService:
    def __init__(self):
        self.database = DatabaseManager()
    
    def get_player(self, username: str):
        player = self.database.get_player(username)
        return player
    
    def get_player_games(self, player: Player) -> Game:
        games = self.database.get_player_games(player)
        return games
    
    def save_player(self, player: Player) -> None:
        self.database.save_player(player)
    
    def save_games(self, games: Union[Game]) -> None:
        for game in games:
            self.database.save_game(game)