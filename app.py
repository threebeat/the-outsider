"""
The Outsider - A Social Deduction Game Backend

Clean Flask-SocketIO application that serves as an API backend for a React frontend.
All game logic is modularized into separate components.
"""

import os
import logging
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

# Import our modular game system
from game.manager import GameManager
from database import init_database, get_game_statistics, get_db_session

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

# Initialize game manager
game_manager = GameManager()

# Socket.IO Event Handlers

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to server successfully'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {request.sid}")
    
    # Handle player disconnection
    success, message, lobby_code = game_manager.disconnect_player(request.sid)
    if success and lobby_code:
        # Notify other players in the lobby
        lobby_data = game_manager.get_lobby_data(lobby_code)
        if lobby_data:
            socketio.emit('player_disconnected', {
                'message': message,
                'lobby': lobby_data
            }, room=lobby_code)

@socketio.on('create_lobby')
def handle_create_lobby(data):
    """Handle lobby creation."""
    try:
        lobby_name = data.get('name', 'New Game')
        lobby_code = data.get('code')  # Optional custom code
        
        success, message, lobby_data = game_manager.create_lobby(lobby_name, lobby_code)
        
        if success:
            emit('lobby_created', {
                'success': True,
                'lobby': lobby_data,
                'message': message
            })
            logger.info(f"Created lobby: {lobby_data['code']}")
        else:
            emit('error', {'message': message})
            
    except Exception as e:
        logger.error(f"Error creating lobby: {e}")
        emit('error', {'message': 'Failed to create lobby'})

@socketio.on('join_lobby')
def handle_join_lobby(data):
    """Handle player joining a lobby."""
    try:
        lobby_code = data.get('code')
        username = data.get('username')
        
        if not lobby_code or not username:
            emit('error', {'message': 'Missing lobby code or username'})
            return
        
        success, message, player_data = game_manager.join_lobby(lobby_code, request.sid, username)
        
        if success:
            # Join the socket room
            join_room(lobby_code)
            
            # Get updated lobby data
            lobby_data = game_manager.get_lobby_data(lobby_code)
            
            # Send success response to player
            emit('joined_lobby', {
                'success': True,
                'player': player_data,
                'lobby': lobby_data,
                'message': message
            })
            
            # Notify other players
            emit('player_joined', {
                'player': player_data,
                'lobby': lobby_data,
                'message': f"{username} joined the game"
            }, room=lobby_code, include_self=False)
            
            logger.info(f"Player {username} joined lobby {lobby_code}")
        else:
            emit('error', {'message': message})
            
    except Exception as e:
        logger.error(f"Error joining lobby: {e}")
        emit('error', {'message': 'Failed to join lobby'})

@socketio.on('leave_lobby')
def handle_leave_lobby():
    """Handle player leaving a lobby."""
    try:
        success, message, lobby_code = game_manager.leave_lobby(request.sid)
        
        if success and lobby_code:
            # Leave the socket room
            leave_room(lobby_code)
            
            # Get updated lobby data
            lobby_data = game_manager.get_lobby_data(lobby_code)
            
            # Send success response
            emit('left_lobby', {
                'success': True,
                'message': message
            })
            
            # Notify other players
            if lobby_data:
                emit('player_left', {
                    'lobby': lobby_data,
                    'message': message
                }, room=lobby_code)
            
        else:
            emit('error', {'message': message or 'Failed to leave lobby'})
            
    except Exception as e:
        logger.error(f"Error leaving lobby: {e}")
        emit('error', {'message': 'Failed to leave lobby'})

@socketio.on('start_game')
def handle_start_game(data):
    """Handle game start request."""
    try:
        lobby_code = data.get('code')
        if not lobby_code:
            emit('error', {'message': 'Missing lobby code'})
            return
        
        success, message, game_data = game_manager.start_game(lobby_code)
        
        if success:
            # Get updated lobby data
            lobby_data = game_manager.get_lobby_data(lobby_code)
            
            # Notify all players that game started
            socketio.emit('game_started', {
                'success': True,
                'game_data': game_data,
                'lobby': lobby_data,
                'message': message
            }, room=lobby_code)
            
            logger.info(f"Started game in lobby {lobby_code}")
        else:
            emit('error', {'message': message})
            
    except Exception as e:
        logger.error(f"Error starting game: {e}")
        emit('error', {'message': 'Failed to start game'})

@socketio.on('ask_question')
def handle_ask_question(data):
    """Handle question being asked."""
    try:
        target_username = data.get('target')
        question = data.get('question')
        
        if not target_username or not question:
            emit('error', {'message': 'Missing target or question'})
            return
        
        success, message, result_data = game_manager.handle_question(request.sid, target_username, question)
        
        if success and result_data:
            lobby_code = result_data['lobby_code']
            
            # Broadcast question to all players
            socketio.emit('question_asked', {
                'question': result_data['question'],
                'target': result_data['target'],
                'message': f"Question asked: {result_data['question']}"
            }, room=lobby_code)
            
            # Check if target is AI and generate response
            # This would be handled by AI system in a background task
            
        else:
            emit('error', {'message': message})
            
    except Exception as e:
        logger.error(f"Error handling question: {e}")
        emit('error', {'message': 'Failed to ask question'})

@socketio.on('give_answer')
def handle_give_answer(data):
    """Handle answer being given."""
    try:
        answer = data.get('answer')
        
        if not answer:
            emit('error', {'message': 'Missing answer'})
            return
        
        success, message, result_data = game_manager.handle_answer(request.sid, answer)
        
        if success and result_data:
            lobby_code = game_manager.get_player_lobby(request.sid)
            if lobby_code:
                # Broadcast answer to all players
                answer_event = {
                    'answer': result_data['answer'],
                    'message': f"Answer given: {result_data['answer']}"
                }
                
                # Check if advancing to voting or next turn
                if result_data.get('advance_to_voting'):
                    answer_event['advance_to_voting'] = True
                    answer_event['voting_data'] = result_data.get('voting_data')
                elif result_data.get('next_turn'):
                    answer_event['next_turn'] = result_data['next_turn']
                
                socketio.emit('answer_given', answer_event, room=lobby_code)
                
        else:
            emit('error', {'message': message})
            
    except Exception as e:
        logger.error(f"Error handling answer: {e}")
        emit('error', {'message': 'Failed to give answer'})

@socketio.on('cast_vote')
def handle_cast_vote(data):
    """Handle vote being cast."""
    try:
        target_username = data.get('target')
        
        if not target_username:
            emit('error', {'message': 'Missing vote target'})
            return
        
        success, message, result_data = game_manager.handle_vote(request.sid, target_username)
        
        if success and result_data:
            lobby_code = game_manager.get_player_lobby(request.sid)
            if lobby_code:
                vote_event = {
                    'vote_result': result_data['vote_result'],
                    'message': f"Vote cast for {target_username}"
                }
                
                # Check if game ended
                if result_data.get('game_result'):
                    vote_event['game_result'] = result_data['game_result']
                    vote_event['game_ended'] = True
                
                socketio.emit('vote_cast', vote_event, room=lobby_code)
                
        else:
            emit('error', {'message': message})
            
    except Exception as e:
        logger.error(f"Error handling vote: {e}")
        emit('error', {'message': 'Failed to cast vote'})

@socketio.on('get_lobby_data')
def handle_get_lobby_data(data):
    """Handle request for lobby data."""
    try:
        lobby_code = data.get('code')
        if not lobby_code:
            emit('error', {'message': 'Missing lobby code'})
            return
        
        lobby_data = game_manager.get_lobby_data(lobby_code)
        
        if lobby_data:
            emit('lobby_data', {
                'lobby': lobby_data
            })
        else:
            emit('error', {'message': 'Lobby not found'})
            
    except Exception as e:
        logger.error(f"Error getting lobby data: {e}")
        emit('error', {'message': 'Failed to get lobby data'})

# Flask API Routes

@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'message': 'The Outsider game server is running',
        'version': '2.0.0'
    })

@app.route('/api/stats')
def get_stats():
    """Game statistics endpoint."""
    try:
        with get_db_session() as session:
            stats = get_game_statistics(session)
            if stats:
                return jsonify({
                    'human_wins': stats.human_wins,
                    'ai_wins': stats.ai_wins,
                    'total_games': stats.total_games,
                    'human_win_rate': stats.human_win_rate,
                    'avg_game_duration': stats.avg_game_duration
                })
            else:
                return jsonify({'message': 'No statistics available'})
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({'error': 'Failed to get statistics'}), 500

@app.route('/api/lobbies/active')
def get_active_lobbies():
    """Get list of active lobbies."""
    try:
        lobbies = game_manager.get_active_lobbies()
        return jsonify({'lobbies': lobbies})
    except Exception as e:
        logger.error(f"Error getting active lobbies: {e}")
        return jsonify({'error': 'Failed to get lobbies'}), 500

@app.route('/api/cleanup')
def cleanup_inactive():
    """Clean up inactive lobbies (admin endpoint)."""
    try:
        cleaned_count = game_manager.cleanup_inactive_lobbies()
        return jsonify({
            'message': f'Cleaned up {cleaned_count} inactive lobbies'
        })
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return jsonify({'error': 'Cleanup failed'}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500

# Application initialization

def create_app():
    """Application factory."""
    # Initialize database
    init_database()
    logger.info("Database initialized")
    
    # Clean up old lobbies on startup
    try:
        cleaned = game_manager.cleanup_inactive_lobbies()
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} inactive lobbies on startup")
    except Exception as e:
        logger.warning(f"Failed to clean up lobbies on startup: {e}")
    
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