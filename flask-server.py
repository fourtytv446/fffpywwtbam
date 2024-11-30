import sqlite3
from flask import Flask, request, jsonify, render_template, session
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import time
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

# Database initialization
def init_db():
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS questions
                 (id INTEGER PRIMARY KEY, 
                  question TEXT, 
                  option1 TEXT, 
                  option2 TEXT, 
                  option3 TEXT, 
                  option4 TEXT, 
                  correct_order TEXT)''')
    conn.commit()
    conn.close()

# User management
def register_user(username, password):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    hashed_password = generate_password_hash(password)
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                  (username, hashed_password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def validate_user(username, password):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    
    if result and check_password_hash(result[0], password):
        return True
    return False

# Game state management
game_state = {
    'current_question': None,
    'players': {},
    'game_active': False,
    'start_time': None,
    'max_players': 6
}

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if register_user(username, password):
        return jsonify({"status": "success"}), 201
    return jsonify({"status": "error", "message": "Username already exists"}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if validate_user(username, password):
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "error", "message": "Invalid credentials"}), 401

@socketio.on('connect_player')
def handle_player_connect(data):
    username = data.get('username')
    
    if len(game_state['players']) >= game_state['max_players']:
        emit('server_message', {'message': 'Server is full'})
        return
    
    game_state['players'][username] = {
        'response': None,
        'response_time': None
    }
    
    emit('player_list_update', list(game_state['players'].keys()), broadcast=True)

@socketio.on('admin_start_game')
def start_game(data):
    question = data.get('question')
    options = [
        data.get('option1'),
        data.get('option2'),
        data.get('option3'),
        data.get('option4')
    ]
    correct_order = data.get('correct_order')
    
    game_state['current_question'] = {
        'question': question,
        'options': options,
        'correct_order': correct_order
    }
    game_state['game_active'] = True
    game_state['start_time'] = time.time()
    
    # Broadcast question to all players
    emit('game_started', {
        'question': question,
        'options': options
    }, broadcast=True)

@socketio.on('player_response')
def handle_player_response(data):
    username = data.get('username')
    response = data.get('response')
    
    if not game_state['game_active']:
        return
    
    response_time = time.time() - game_state['start_time']
    
    game_state['players'][username]['response'] = response
    game_state['players'][username]['response_time'] = response_time

@socketio.on('admin_end_game')
def end_game():
    # Calculate and announce winners
    correct_responses = {}
    for username, player_data in game_state['players'].items():
        if player_data['response'] == game_state['current_question']['correct_order']:
            correct_responses[username] = player_data['response_time']
    
    if correct_responses:
        winner = min(correct_responses, key=correct_responses.get)
        emit('game_result', {
            'winner': winner,
            'correct_responses': correct_responses
        }, broadcast=True)
    
    # Reset game state
    game_state['game_active'] = False
    game_state['current_question'] = None
    game_state['start_time'] = None
    
    for player in game_state['players']:
        game_state['players'][player]['response'] = None
        game_state['players'][player]['response_time'] = None

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True)
