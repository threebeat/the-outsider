"""
The Outsider - Minimal Flask-SocketIO Server

This file only initializes the server and imports handlers.
All business logic is handled by the modular game system.
"""

import os
import logging
from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

# Import database functions
from database import init_database, clean_database

# Import managers
from lobby import LobbyManager
from game import GameManager

# Import handler registration functions
from handlers.socket_handlers import register_socket_handlers
from handlers.api_handlers import register_api_handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Flask configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# CORS configuration for React frontend
CORS(app, origins=os.getenv('CORS_ORIGINS', '*').split(','))

# ProxyFix for deployment behind reverse proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# SocketIO configuration
socketio = SocketIO(
    app,
    cors_allowed_origins=os.getenv('CORS_ORIGINS', '*').split(','),
    async_mode='eventlet',
    ping_timeout=60,
    ping_interval=25,
    logger=True,
    engineio_logger=True
)

# Initialize managers
lobby_manager = LobbyManager()
game_manager = GameManager()

# Register all handlers
register_socket_handlers(socketio, lobby_manager, game_manager)
register_api_handlers(app, lobby_manager, game_manager)

# Application initialization
def create_app():
    """Application factory with database initialization."""
    # Initialize database
    init_database()
    logger.info("Database initialized")
    
    # Clean database on startup (preserves statistics)
    try:
        cleanup_results = clean_database()
        logger.info(f"Database cleaned on startup: {cleanup_results}")
    except Exception as e:
        logger.warning(f"Failed to clean database on startup: {e}")
    
    return app

if __name__ == '__main__':
    # Development server
    app = create_app()
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'production') == 'development'
    
    logger.info(f"Starting The Outsider game server on port {port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"CORS origins: {os.getenv('CORS_ORIGINS', '*')}")
    
    socketio.run(app, debug=debug, port=port, host='0.0.0.0')