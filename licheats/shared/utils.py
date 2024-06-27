import pandas as pd
from typing import Dict, Any
import datetime 
import re 

def _format_date(date_string: str) -> str:
        # Remove the 'Z' if present and ensure the string ends with '+00:00'
        date_string = date_string.replace('Z', '')
        if not date_string.endswith('+00:00'):
            date_string += '+00:00'
        
        # Use regex to handle varying decimal places in seconds
        date_string = re.sub(r'(\d{2}:\d{2}:\d{2})\.(\d+)', r'\1', date_string)

        try:
            date = datetime.fromisoformat(date_string)
            return date.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError as e:
            print(f"Warning: Could not parse date '{date_string}'. Error: {e}")
            return date_string


def preprocess_player_games(games_):
    df = pd.DataFrame(games_)
    df = df.join(df['players'].apply(pd.Series).add_prefix('players_'))
    df = df.join(df['opening'].apply(pd.Series).add_prefix('opening_'))
    df = df.join(df['clock'].apply(pd.Series).add_prefix('clock_'))

    for col in ['players_white', 'players_black']:
        for detail in ['user', 'rating', 'ratingDiff']:
            df[f'{col}_{detail}'] = df[col].apply(lambda x: x.get(detail, {}).get('name') if detail == 'user' else x.get(detail))
        df.drop(col, axis=1, inplace=True)

    df['createdAt'] = pd.to_datetime(df['createdAt'], unit='ms')
    df['lastMoveAt'] = pd.to_datetime(df['lastMoveAt'], unit='ms')
    df.drop(['players', 'opening', 'clock'], axis=1, inplace=True)

    return df

def process_player_stats(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    processed_data = {
        'username': raw_data['user']['name'],
        'performance_type': raw_data['stat']['perfType']['name'],
        'rating': {
            'current': raw_data['perf']['glicko']['rating'],
            'deviation': raw_data['perf']['glicko']['deviation'],
            'progress': raw_data['perf'].get('progress'),
            'highest': {
                'rating': raw_data['stat']['highest']['int'],
                'date': _format_date(raw_data['stat']['highest']['at']),
                'game_id': raw_data['stat']['highest']['gameId']
            },
            'lowest': {
                'rating': raw_data['stat']['lowest']['int'],
                'date': _format_date(raw_data['stat']['lowest']['at']),
                'game_id': raw_data['stat']['lowest']['gameId']
            }
        },
        'games': {
            'total': raw_data['stat']['count']['all'],
            'rated': raw_data['stat']['count']['rated'],
            'wins': raw_data['stat']['count']['win'],
            'losses': raw_data['stat']['count']['loss'],
            'draws': raw_data['stat']['count']['draw'],
            'berserks': raw_data['stat']['count']['berserk'],
            'disconnects': raw_data['stat']['count']['disconnects'],
            'total_time': raw_data['stat']['count']['seconds']
        },
        'streaks': {
            'win': {
                'current': raw_data['stat']['resultStreak']['win']['cur']['v'],
                'max': raw_data['stat']['resultStreak']['win']['max']['v']
            },
            'loss': {
                'current': raw_data['stat']['resultStreak']['loss']['cur']['v'],
                'max': raw_data['stat']['resultStreak']['loss']['max']['v']
            }
        },
        'best_wins': [
            {
                'opponent': win['opId']['name'],
                'opponent_rating': win['opRating'],
                'date': _format_date(win['at']),
                'game_id': win['gameId']
            } for win in raw_data['stat']['bestWins']['results']
        ],
        'worst_losses': [
            {
                'opponent': loss['opId']['name'],
                'opponent_rating': loss['opRating'],
                'date': _format_date(loss['at']),
                'game_id': loss['gameId']
            } for loss in raw_data['stat']['worstLosses']['results']
        ],
        'last_played': _format_date(raw_data['stat']['playStreak']['lastDate'])
    }
    return processed_data
