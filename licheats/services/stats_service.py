from licheats.shared import GamesAnalyzer  # Asumiendo que GameAnalysis tiene los métodos necesarios

class StatService:
    @staticmethod
    def resume_stats(player, games):
        analysis = GamesAnalyzer(player.username, games)
        
        enroque_king, enroque_queen = analysis.enroque_preference()
        with_queen, without_queen = analysis.performance_with_queens()
        defeat_causes = analysis.common_causes_of_defeat()
        win_methods = analysis.game_wins()
        performance_by_color = analysis.performance_by_color()
        time_pressure_effects = analysis.time_pressure_performance()
        game_pace_preference = analysis.game_pace_preference()

        stats_summary = {
            "Enroques": {
                "Rey": enroque_king,
                "Dama": enroque_queen
            },
            "Rendimiento con Damas": {
                "Con Dama": with_queen,
                "Sin Dama": without_queen
            },
            "Causas de Derrota": defeat_causes,
            "Métodos de Victoria": win_methods,
            "Rendimiento por Color": performance_by_color,
            "Efecto de la Presión de Tiempo": time_pressure_effects,
            "Preferencia de Ritmo de Juego": game_pace_preference
        }

        return stats_summary
