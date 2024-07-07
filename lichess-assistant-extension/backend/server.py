
from flask import Flask, request, jsonify
from flask_cors import CORS
from licheats import Client
app = Flask(__name__)
CORS(app)

@app.route('/get_player_stats', methods=['POST'])
def player_stats():
    print(request.json)
    username = request.json.get('username')
    if not username:
        return jsonify({'error': 'Username is required'}), 400
    try:
        client = Client()
        stats = client.player_games_analysis(username, 100)
        print(stats)
        return stats
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
