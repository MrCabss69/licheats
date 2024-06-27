import datetime
from licheats.shared import Player

class PlayerProcessor:
    @staticmethod
    def process(data):
        """Transforms Lichess API data into an ORM format."""
        player = Player(
            username=data['username'],
            title=data.get('title'),
            flair=data.get('flair'),
            patron=data.get('patron', False),
            created_at=data['createdAt'],
            seen_at=data['seenAt'],
            play_time_total=data['playTime']['total'],
            play_time_tv=data['playTime']['tv'],
            url=data['url'],
            followable=data.get('followable', False),
            following=data.get('following', False),
            blocking=data.get('blocking', False),
            follows_you=data.get('followsYou', False),
            perfs=data['perfs'],
            counts=data['count'],
            streamer_info=data.get('streamer', {})
        )
        return player