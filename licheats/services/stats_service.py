from licheats.shared import Player, GamesAnalyzer, StatsVisualizer
from .data_service import DataService
from typing import Union, Dict, Any

class StatService:
    @staticmethod
    def analyze_player_games(data_service: DataService, username:str, max_games:int=None) -> Dict[str, Any]:
        player = data_service.get_player(username)
        games = data_service.get_player_games(username, max_games)
        print(player)
        print()
        print(games)
        return GamesAnalyzer.analyze(player, games)

    @staticmethod
    def visualize_stats(stats: Dict[str, Any]) -> None:
        StatsVisualizer.plot_all(stats)