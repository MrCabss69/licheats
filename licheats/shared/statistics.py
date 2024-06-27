

def color_stats(player, games):
    results = {
        "white": {"win": 0, "loss": 0, "draw": 0},
        "black": {"win": 0, "loss": 0, "draw": 0}
    }
    for game in games:
        results[game.color][game.result] += 1
    return results