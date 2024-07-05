from licheats.shared import Player

class PlayerProcessor:
    @staticmethod
    def process(data):
        print(data)
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
            streamer_info=data.get('streamer', {}),
            ultraBullet_games=data['perfs']['ultraBullet']['games'],
            ultraBullet_rating=data['perfs']['ultraBullet']['rating'],
            bullet_games=data['perfs']['bullet']['games'],
            bullet_rating=data['perfs']['bullet']['rating'],
            blitz_games=data['perfs']['blitz']['games'],
            blitz_rating=data['perfs']['blitz']['rating'],
            rapid_games=data['perfs']['rapid']['games'],
            rapid_rating=data['perfs']['rapid']['rating'],
            classical_games=data['perfs']['classical']['games'],
            classical_rating=data['perfs']['classical']['rating'],
            all_games=data['count']['all'],
            rated_games=data['count']['rated'],
            ai_games=data['count']['ai'],
            draw_games=data['count']['draw'],
            loss_games=data['count']['loss'],
            win_games=data['count']['win'],
        )
        return player