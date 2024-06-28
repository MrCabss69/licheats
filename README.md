# Licheats - Lichess Data Retrieval and Analysis

## Resumen del Proyecto

**Licheats** es un sistema avanzado para la visualización y análisis de estadísticas de partidas de ajedrez, centrado especialmente en las aperturas. Este sistema no solo permite almacenar y gestionar información sobre partidas de ajedrez en una base de datos estructurada, sino que también proporciona herramientas analíticas para explorar estrategias de aperturas, evaluar el rendimiento de los jugadores y predecir resultados basados en el historial de juego.

### Objetivos del Proyecto

El objetivo principal del proyecto es desarrollar un sistema integral que permita:
- Analizar y visualizar estadísticas de partidas de ajedrez.
- Investigar las preferencias y efectividad de diferentes aperturas de ajedrez.
- Prever las mejores estrategias de apertura para enfrentamientos específicos entre jugadores.

### Preguntas Clave a Responder

El sistema está diseñado para responder a preguntas específicas relacionadas con el comportamiento y el rendimiento de los jugadores:
- ¿El jugador tiende a enrocarse? Si es así, ¿hacia qué lado prefiere?
- ¿El jugador tiene un mejor rendimiento con damas en el tablero o sin ellas?
- ¿Cuáles son las causas más comunes de las derrotas del jugador (tiempo, abandono, jaque mate)?
- ¿Cómo suele ganar el jugador sus partidas (por tiempo, por abandono del oponente, por jaque mate)?
- ¿El jugador tiene un mejor rendimiento con las piezas blancas o negras?
- ¿Cómo afecta la presión del tiempo al rendimiento del jugador?
- ¿Cuál es la preferencia del jugador respecto al ritmo de juego (rápidas, blitz, estándar)?


### Uso

```python
from licheats import Client
client = Client()

player = client.get_player('Fieber69')
player


games = client.get_games('Fieber69')
games

client.save_player(player)
client.save_games(games)
``````