# app.py

import os
import logging
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from werkzeug.middleware.proxy_fix import ProxyFix
from config.settings import SECRET_KEY, CORS_ORIGINS, DEBUG, OPENAI_API_KEY
from game.logic import GameManager
from socket_handlers.handlers import register_handlers
from models.database import Base, engine, SessionLocal, get_win_counter, WinCounter, get_player_by_sid, remove_player, get_players, get_lobby

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Initialization ---
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# SocketIO configuration with eventlet for Render compatibility
socketio = SocketIO(
    app,
    cors_allowed_origins=CORS_ORIGINS,
    async_mode="eventlet",
    ping_timeout=60,
    ping_interval=25,
    logger=True,
    engineio_logger=True
)

# Reset database on startup
logger.info("Resetting database on startup...")

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
        logger.info(f"Preserving win counter: {win_counter_data}")
    except Exception as e:
        logger.error(f"Could not preserve win counter: {e}")
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
        logger.info(f"Win counter restored: {win_counter_data}")
    except Exception as e:
        logger.error(f"Error restoring win counter: {e}")
    finally:
        session.close()

logger.info("Database reset complete!")

# Verify OpenAI API key is configured
if not OPENAI_API_KEY:
    logger.warning("WARNING: OPENAI_API_KEY is not set! AI responses will use fallback messages.")
else:
    logger.info("OpenAI API key is configured.")

game_manager = GameManager(socketio)

# Test event to verify Socket.IO is working
@socketio.on('test')
def test_event(data):
    logger.info(f"Test event received: {data}")
    emit('test_response', {'message': 'Test successful!'})

@socketio.on('connect')
def handle_connect(sid):
    logger.info(f"Client connected: {sid}")
    # Send a simple test message to verify connection
    emit('connection_test', {'message': 'Connection established successfully!'})

@socketio.on('disconnect')
def handle_disconnect(sid):
    logger.info(f"Client disconnected: {sid}")
    
    # Clean up the player from the game state
    try:
        # Find the player with this SID
        session = SessionLocal()
        try:
            lobby = get_lobby(session, "main")
            player = get_player_by_sid(session, lobby, sid)
            if player:
                logger.info(f"Removing player {player.username} (SID: {sid}) from game")
                
                # Remove the player from the database
                remove_player(session, player)
                
                # Get updated player list
                players = get_players(session, lobby)
                player_names = [p.username for p in players]
                
                # Emit game update to remaining players
                socketio.emit('game_update', {
                    'players': player_names,
                    'log': f"{player.username} has left the game."
                }, room="main")
                
                logger.info(f"Player {player.username} removed successfully. Remaining players: {player_names}")
            else:
                logger.info(f"No player found for SID: {sid}")
                
        except Exception as e:
            logger.error(f"Error cleaning up disconnected player {sid}: {e}")
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error in disconnect handler: {e}")

@socketio.on_error_default
def default_error_handler(e):
    logger.error(f"SocketIO default error: {e}")
    emit('error', {'message': 'An error occurred. Please try again.'})

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
        logger.info(f"Sent win counter on startup: {win_counter.human_wins} humans, {win_counter.ai_wins} AI")
    except Exception as e:
        logger.error(f"Error sending win counter on startup: {e}")
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

@app.route('/health')
def health_check():
    return {'status': 'healthy', 'message': 'The Outsider game server is running'}

if __name__ == '__main__':
    logger.info("Starting Flask-SocketIO app...")
    socketio.run(app, debug=DEBUG, port=5000)