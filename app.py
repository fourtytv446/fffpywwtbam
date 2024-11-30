import os
import sqlite3
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import time
import eventlet

eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback_secret_key')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
CORS(app)

# Database path for Render
DATABASE_PATH = '/tmp/game.db'

def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
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

# [Rest of the previous server code remains the same]

# Add routes to serve HTML files
@app.route('/')
def serve_player_page():
    return send_from_directory('templates', 'player.html')

@app.route('/admin')
def serve_admin_page():
    return send_from_directory('templates', 'admin.html')

if __name__ == '__main__':
    init_db()
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
