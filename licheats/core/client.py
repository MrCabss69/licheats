from licheats.services import LichessApiService, DataService, StatService
from licheats.shared import Player, Game
from typing import List, Dict, Any, Union

class Client:
    
    def __init__(self):
        self.api_service = LichessApiService()
        self.data_service = DataService()

    def get_player(self, username: str, autosave: bool = False) -> Player:
        """Retrieves or registers a player by username."""
        player = self.data_service.get_player(username)
        if player is None:
            player = self.api_service.get_player(username)
            if player and autosave:
                self.data_service.save_player(player)
        return player

    def get_player_stats(self, player: Union[str, Player]) -> Dict:
        return self.data_service.get_player_stats(player)

    def get_player_games(self, player: Union[str, Player], max_games: int = None, autosave: bool = True) -> List[Game]:
        """Retrieves or fetches games for a given player."""
        games = self.data_service.get_player_games(player, max_games)
        if not games:
            games = self.api_service.get_games(player, max_games)
            if games and autosave:
                self.data_service.save_games(games)
        return games

    def get_player_resume(self, player: Union[str, Player]) -> Dict:
        return self.data_service.get_player_stats(player)

    def player_games_analysis(self, username: str, max_games: int = None) -> Dict[str, Any]:
        """Analyzes games for a specific player."""
        return StatService.analyze_player_games(self.data_service,username,max_games)

    def visualize_stats(self, stats: Dict[str, Any]):
        """Visualizes statistics from game analysis."""
        StatService.visualize_stats(stats)

    def save_player(self, player: Player) -> None:
        self.data_service.save_player(player)

    def save_games(self, games: list[Game]) -> None:
        self.data_service.save_games(games)