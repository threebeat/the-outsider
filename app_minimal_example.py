"""
The Outsider - Minimal Flask Application Example

This demonstrates how clean app.py becomes after proper separation of concerns.
All business logic has been moved to dedicated modules.
"""

import os
import logging
from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from dotenv import load_dotenv

# Import our clean, separated systems
from lobby import LobbyManager
from game import GameManager
from handlers import register_socket_handlers, register_api_handlers
from database import init_database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def create_app():
    """Application factory - completely minimal setup."""
    
    # Flask setup
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # CORS for React frontend
    CORS(app, origins=os.getenv('CORS_ORIGINS', '*').split(','))
    
    # SocketIO setup
    socketio = SocketIO(app, cors_allowed_origins=os.getenv('CORS_ORIGINS', '*').split(','))
    
    # Initialize database
    init_database()
    
    # Initialize business logic managers (dependency injection)
    lobby_manager = LobbyManager()
    game_manager = GameManager()
    
    # Register all handlers (no logic in app.py - pure delegation)
    register_socket_handlers(socketio, lobby_manager, game_manager)
    register_api_handlers(app, lobby_manager, game_manager)
    
    logger.info("The Outsider server initialized successfully")
    return app, socketio

if __name__ == '__main__':
    app, socketio = create_app()
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    logger.info(f"Starting server on port {port}")
    socketio.run(app, debug=debug, port=port, host='0.0.0.0')

"""
Key Benefits of This Minimal Structure:

1. ZERO BUSINESS LOGIC in app.py
   - Pure web server setup
   - Dependency injection pattern
   - Clean separation of concerns

2. EASY TO TEST
   - Mock lobby_manager and game_manager
   - Test handlers independently
   - Test business logic without web layer

3. EASY TO MAINTAIN
   - Change game rules? → Edit game/ modules
   - Change lobby logic? → Edit lobby/ modules  
   - Change API format? → Edit handlers/ modules
   - Change database? → Edit database.py

4. PRODUCTION READY
   - Clean error handling at appropriate layers
   - Proper logging throughout
   - Environment-based configuration
   - Dependency injection for testing

5. FRONTEND FRIENDLY
   - Clear API boundaries
   - Predictable event structure
   - Easy to mirror structure in React components
"""