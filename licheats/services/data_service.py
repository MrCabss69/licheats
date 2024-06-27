from typing import Union
from licheats.data import DatabaseManager
from licheats.shared import Player, Game

class DataService:
    def __init__(self):
        self.data_manager = DatabaseManager()
    
    def get_username_data(self, username: str):
        player = self.data_manager.find_player_by_username(username)
        if player:
            games = self.data_manager.find_games_by_player(player.id)
            return player, games
        return None
    
    def add_player_data(self, player: Player, games: Union[Game]) -> None:
        
        self.data_manager.add_player(player)
        for game in games:
            try:
                self.data_manager.add_game(game)
            except:
                pass

    def add_games(self, games: Union[Game])-> None:
        for game in games:
            self.data_manager.add_game(game)