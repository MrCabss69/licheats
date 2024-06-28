import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from typing import Dict, Any

class StatsVisualizer:
    @staticmethod
    def plot_all(stats: Dict[str, Any]):
        # Diccionario de funciones para cada tipo de gráfico
        plot_functions = {
            'opening_distribution': StatsVisualizer._plot_opening_distribution,
            'win_rate_by_color': StatsVisualizer._plot_win_rate_by_color,
            'piece_movement': StatsVisualizer._plot_piece_movement,
            'castling_results': StatsVisualizer._plot_castling_results,
            'rating_progression': StatsVisualizer._plot_rating_progression,
            'time_control_distribution': StatsVisualizer._plot_time_control_distribution,
            'performance_with_queens': StatsVisualizer._plot_performance_with_queens,
            'time_pressure_performance': StatsVisualizer._plot_time_pressure_performance
        }
        for plot_func in plot_functions.values():
            plot_func(stats)  # Llamar a cada función de ploteo
        plt.show()

    @staticmethod
    def plot(stats: Dict[str, Any], plot_type: str):
        # Diccionario de funciones para cada tipo de gráfico
        plot_functions = {
            'opening_distribution': StatsVisualizer._plot_opening_distribution,
            'win_rate_by_color': StatsVisualizer._plot_win_rate_by_color,
            'piece_movement': StatsVisualizer._plot_piece_movement,
            'castling_results': StatsVisualizer._plot_castling_results,
            'rating_progression': StatsVisualizer._plot_rating_progression,
            'time_control_distribution': StatsVisualizer._plot_time_control_distribution,
            'performance_with_queens': StatsVisualizer._plot_performance_with_queens,
            'time_pressure_performance': StatsVisualizer._plot_time_pressure_performance
        }
        if plot_type in plot_functions:
            plot_functions[plot_type](stats)  # Llamar a la función específica
            plt.show()
        else:
            print(f"Plot type '{plot_type}' not found.")

    @staticmethod
    def _plot_opening_distribution(stats: Dict[str, Any]):
        data = pd.DataFrame(list(stats['preferred_opening_distribution'].items()), 
                            columns=['Opening', 'Count'])
        data = data.sort_values('Count', ascending=False).head(10)
        
        plt.figure(figsize=(12, 6))
        sns.barplot(x='Count', y='Opening', data=data)
        plt.title('Top 10 Preferred Openings')
        plt.tight_layout()

    @staticmethod
    def _plot_win_rate_by_color(stats: Dict[str, Any]):
        data = []
        for color, stats in stats['win_rate_by_color'].items():
            win_rate = stats['wins'] / stats['total'] * 100 if stats['total'] > 0 else 0
            data.append({'Color': color.capitalize(), 'Win Rate': win_rate})
        
        df = pd.DataFrame(data)
        plt.figure(figsize=(8, 6))
        sns.barplot(x='Color', y='Win Rate', data=df)
        plt.title('Win Rate by Color')
        plt.ylabel('Win Rate (%)')
        plt.ylim(0, 100)

    @staticmethod
    def _plot_piece_movement(stats: Dict[str, Any]):
        data = pd.DataFrame(list(stats['piece_movement_distribution'].items()), 
                            columns=['Piece', 'Moves'])
        
        plt.figure(figsize=(10, 6))
        sns.barplot(x='Piece', y='Moves', data=data)
        plt.title('Piece Movement Distribution')
        plt.ylabel('Number of Moves')

    @staticmethod
    def _plot_castling_results(stats: Dict[str, Any]):
        data = [
            {'Side': 'Kingside', 'Result': 'Win', 'Count': stats['castling_win_distribution']['king_win']},
            {'Side': 'Kingside', 'Result': 'Loss', 'Count': stats['castling_win_distribution']['king_loss']},
            {'Side': 'Queenside', 'Result': 'Win', 'Count': stats['castling_win_distribution']['queen_win']},
            {'Side': 'Queenside', 'Result': 'Loss', 'Count': stats['castling_win_distribution']['queen_loss']}
        ]
        df = pd.DataFrame(data)
        
        plt.figure(figsize=(10, 6))
        sns.barplot(x='Side', y='Count', hue='Result', data=df)
        plt.title('Castling Results')
        plt.ylabel('Number of Games')

    @staticmethod
    def _plot_rating_progression(stats: Dict[str, Any]):
        data = pd.DataFrame(stats['rating_progression'], columns=['Date', 'Rating'])
        plt.figure(figsize=(12, 6))
        plt.plot(data['Date'], data['Rating'])
        plt.title('Rating Progression Over Time')
        plt.xlabel('Date')
        plt.ylabel('Rating')
        plt.xticks(rotation=45)

    @staticmethod
    def _plot_time_control_distribution(stats: Dict[str, Any]):
        data = pd.DataFrame(list(stats['time_control_distribution'].items()), 
                            columns=['Time Control', 'Count'])
        
        plt.figure(figsize=(10, 6))
        sns.barplot(x='Time Control', y='Count', data=data)
        plt.title('Time Control Distribution')
        plt.ylabel('Number of Games')
        plt.xticks(rotation=45)

    @staticmethod
    def _plot_performance_with_queens(stats: Dict[str, Any]):
        data = []
        for category, stats in stats['performance_with_queens'].items():
            win_rate = stats['wins'] / stats['total'] * 100 if stats['total'] > 0 else 0
            data.append({'Category': category.replace('_', ' ').title(), 'Win Rate': win_rate})
        
        df = pd.DataFrame(data)
        plt.figure(figsize=(8, 6))
        sns.barplot(x='Category', y='Win Rate', data=df)
        plt.title('Win Rate With and Without Queens')
        plt.ylabel('Win Rate (%)')
        plt.ylim(0, 100)

    @staticmethod
    def _plot_time_pressure_performance(stats: Dict[str, Any]):
        data = []
        for category, stats in stats['time_pressure_performance'].items():
            win_rate = stats['wins'] / stats['total'] * 100 if stats['total'] > 0 else 0
            data.append({'Category': category.replace('_', ' ').title(), 'Win Rate': win_rate})
        
        df = pd.DataFrame(data)
        plt.figure(figsize=(8, 6))
        sns.barplot(x='Category', y='Win Rate', data=df)
        plt.title('Win Rate Under Time Pressure')
        plt.ylabel('Win Rate (%)')
        plt.ylim(0, 100)
