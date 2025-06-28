# app.py

import os
import logging
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from werkzeug.middleware.proxy_fix import ProxyFix
from config.settings import SECRET_KEY, CORS_ORIGINS, DEBUG
from game.logic import GameManager
from socket_handlers.handlers import register_handlers
from models.database import Base, engine, SessionLocal, get_win_counter, WinCounter

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Initialization ---
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
socketio = SocketIO(
    app,
    cors_allowed_origins=CORS_ORIGINS,
    async_mode="eventlet" if os.environ.get("RENDER", "") == "true" else None,
    ping_timeout=60,
    ping_interval=25
)

# Reset database on startup
print("Resetting database on startup...")

# Preserve win counter before reset
session = SessionLocal()
try:
    win_counter_data = None
    try:
        win_counter = get_win_counter(session, "main")
        win_counter_data = {
            'human_wins': win_counter.human_wins,
            'ai_wins': win_counter.ai_wins
        }
        print(f"Preserving win counter: {win_counter_data}")
    except Exception as e:
        print(f"Could not preserve win counter: {e}")
        win_counter_data = {'human_wins': 0, 'ai_wins': 0}
finally:
    session.close()

# Drop and recreate all tables
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

# Restore win counter
if win_counter_data:
    session = SessionLocal()
    try:
        new_counter = WinCounter(
            room="main",
            human_wins=win_counter_data['human_wins'],
            ai_wins=win_counter_data['ai_wins']
        )
        session.add(new_counter)
        session.commit()
        print(f"Win counter restored: {win_counter_data}")
    except Exception as e:
        print(f"Error restoring win counter: {e}")
    finally:
        session.close()

print("Database reset complete!")

game_manager = GameManager(socketio)

# Test event to verify Socket.IO is working
@socketio.on('test')
def test_event(data):
    logger.info(f"Test event received: {data}")
    emit('test_response', {'message': 'Test successful!'})

@socketio.on('connect')
def handle_connect():
    logger.info("Client connected!")

@socketio.on('*')
def catch_all(event, data):
    logger.info(f"Unhandled event received: {event} with data: {data}")

# Register the main event handlers
logger.info("Registering event handlers...")
register_handlers(socketio, game_manager)
logger.info("Event handlers registered!")

# Send win counter to all connected players on startup
def send_win_counter_on_startup():
    session = SessionLocal()
    try:
        win_counter = get_win_counter(session, "main")
        socketio.emit('win_counter_update', {
            'human_wins': win_counter.human_wins,
            'ai_wins': win_counter.ai_wins
        }, room="main")
        print(f"Sent win counter on startup: {win_counter.human_wins} humans, {win_counter.ai_wins} AI")
    except Exception as e:
        print(f"Error sending win counter on startup: {e}")
    finally:
        session.close()

# Schedule win counter broadcast after a short delay to ensure all clients are connected
import threading
import time
def delayed_win_counter_broadcast():
    time.sleep(2)  # Wait 2 seconds for clients to connect
    send_win_counter_on_startup()

startup_timer = threading.Timer(2.0, delayed_win_counter_broadcast)
startup_timer.daemon = True
startup_timer.start()

@app.route('/')
def index():
    return render_template('game.html')

if __name__ == '__main__':
    logger.info("Starting Flask-SocketIO app...")
    socketio.run(app, debug=DEBUG, port=5000)