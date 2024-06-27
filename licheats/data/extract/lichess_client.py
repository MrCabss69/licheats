import berserk
from licheats.shared.constants import lichess_api_token

class LichessClient:
    def __init__(self, token):
        session = berserk.TokenSession(token)
        self.client = berserk.Client(session)

    def get_games(self, username, max_games=None, since=None, until=None, perf_type=None):
        """Fetch games of a player from Lichess."""
        # Converting datetime to timestamps if not None
        since_ts = berserk.utils.to_millis(since) if since else None
        until_ts = berserk.utils.to_millis(until) if until else None

        # Retrieve games using berserk
        games = self.client.games.export_by_player(
            username,
            max=max_games,
            since=since_ts,
            until=until_ts,
            perf_type=perf_type
        )
        return list(games)

    def get_profile(self, username):
        """Fetch profile of a player from Lichess."""
        return self.client.users.get_public_data(username)

    def get_player_stats(self, username):
        """Fetch performance statistics of a player for all game types."""
        return self.client.users.get_public_data(username)

    def get_cloud_evaluation(self, fen, num_variations=1, variant='standard'):
        """Get the cloud evaluation for a chess position."""
        try:
            evaluation = self.client.analysis.get_cloud_evaluation(
                fen=fen,
                num_variations=num_variations,
                variant=variant
            )
            return evaluation
        except Exception as e:
            print(f"Failed to retrieve cloud evaluation: {str(e)}")
            return None


if __name__ == '__main__':
    # Ejemplo de uso:
    client = LichessClient(lichess_api_token)
    profile = client.get_profile('DrNykterstein')
    games = client.get_games('DrNykterstein', max_games=10, perf_type='blitz')
    evaluation = client.get_cloud_evaluation('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',num_variations=5)

    print(profile)
    print(games)
    print(evaluation)
