import pandas as pd
from licheats.services import LichessApiService, DataService, StatService
from licheats.shared import Player, Game

class Client:

    def __init__(self) -> None:
        self.api_service  = LichessApiService()
        self.data_service = DataService()
        self.stat_service = StatService()
        
    def resume_stats(self, player:Player, games:list[Game]) -> pd.DataFrame:
        self.stat_service.resume_stats(player, games)
    
    def get_player(self, username:str) -> Player:
        player = self.data_service.get_player(username)
        return self.api_service.get_player(username) if player is None else player

    def get_games(self, username:str, max_games:int=None) -> list[Game]:
        games = self.data_service.get_player_games(username, max_games)
        return self.api_service.get_games(username, max_games) if games is None else games

    def save_player(self, player:Player) -> None:
        self.data_service.save_player(player)

    def save_games(self, games:list[Game]) -> None:
        self.data_service.save_games(games)
