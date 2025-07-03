"""
The Outsider - A Social Deduction Game

A Flask-SocketIO application where players try to identify the AI "outsider"
who doesn't know the secret location. Built from the ground up with modern
architecture and clean code practices.
"""

import os
import logging
import random
from typing import Optional, List
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from werkzeug.middleware.proxy_fix import ProxyFix

# Import our database components
from database import (
    init_database, get_db_session, create_lobby, get_lobby_by_code,
    add_player_to_lobby, remove_player_from_lobby, disconnect_player,
    start_game_session, end_game_session, reset_lobby, get_game_statistics
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Flask configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# ProxyFix for deployment behind reverse proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# SocketIO configuration
socketio = SocketIO(
    app,
    cors_allowed_origins=os.getenv('CORS_ORIGINS', '*'),
    async_mode='eventlet',
    ping_timeout=60,
    ping_interval=25,
    logger=True,
    engineio_logger=True
)

# Game constants
LOCATIONS = [
    "Airport", "Bank", "Beach", "Casino", "Cathedral", "Circus Tent",
    "Corporate Party", "Crusader Army", "Day Spa", "Embassy", "Hospital",
    "Hotel", "Military Base", "Movie Studio", "Museum", "Ocean Liner",
    "Passenger Train", "Pirate Ship", "Polar Station", "Police Station",
    "Restaurant", "School", "Service Station", "Space Station", "Submarine",
    "Supermarket", "Theater", "University", "World War II Squad", "Zoo"
]

AI_NAMES = [
    "Alex", "Blake", "Casey", "Drew", "Ellis", "Finley", "Gray", "Harper",
    "Indigo", "Jules", "Kai", "Lane", "Morgan", "Nova", "Ocean", "Parker"
]

# Global game state
active_lobbies = {}  # In-memory cache for quick access

class GameManager:
    """Manages game state and logic for a lobby."""
    
    def __init__(self, lobby_code: str):
        self.lobby_code = lobby_code
        self.current_asker = None
        self.current_target = None
        self.turn_order = []
        
    def get_lobby_data(self):
        """Get current lobby data for frontend."""
        with get_db_session() as session:
            lobby = get_lobby_by_code(session, self.lobby_code)
            if not lobby:
                return None
                
            players_data = []
            for player in lobby.active_players:
                players_data.append({
                    'id': player.id,
                    'username': player.username,
                    'is_ai': player.is_ai,
                    'is_outsider': player.is_outsider,
                    'questions_asked': player.questions_asked,
                    'questions_answered': player.questions_answered
                })
            
            return {
                'code': lobby.code,
                'name': lobby.name,
                'state': lobby.state,
                'location': lobby.location,
                'current_turn': lobby.current_turn,
                'question_count': lobby.question_count,
                'max_questions': lobby.max_questions,
                'players': players_data,
                'current_asker': self.current_asker,
                'current_target': self.current_target
            }
    
    def start_game(self):
        """Start a new game session."""
        with get_db_session() as session:
            lobby = get_lobby_by_code(session, self.lobby_code)
            if not lobby or lobby.state != 'waiting':
                return False
                
            # Need at least 2 players (1 human + 1 AI)
            if len(lobby.active_players) < 2:
                return False
            
            # Add AI player if needed
            if len(lobby.ai_players) == 0:
                ai_name = random.choice(AI_NAMES)
                ai_player = add_player_to_lobby(
                    session, lobby, f"ai_{random.randint(1000, 9999)}", 
                    ai_name, is_ai=True
                )
                logger.info(f"Added AI player {ai_name} to lobby {self.lobby_code}")
            
            # Select random location
            location = random.choice(LOCATIONS)
            
            # Choose outsider (always AI for now)
            ai_players = lobby.ai_players
            if ai_players:
                outsider = random.choice(ai_players)
                outsider.is_outsider = True
                logger.info(f"Selected {outsider.username} as outsider")
            
            # Set up turn order
            all_players = lobby.active_players
            random.shuffle(all_players)
            self.turn_order = [p.session_id for p in all_players]
            
            # Start game session
            start_game_session(session, lobby, location)
            
            # Notify all players
            self.broadcast_game_update("Game started! Try to identify the outsider.")
            
            # Start first turn
            self.start_next_turn()
            
            return True
    
    def start_next_turn(self):
        """Start the next player's turn."""
        with get_db_session() as session:
            lobby = get_lobby_by_code(session, self.lobby_code)
            if not lobby or lobby.state != 'playing':
                return
            
            if lobby.question_count >= lobby.max_questions:
                self.start_voting_phase()
                return
            
            # Get current turn player
            if lobby.current_turn < len(self.turn_order):
                asker_sid = self.turn_order[lobby.current_turn]
                
                # Find asker player
                asker = None
                for player in lobby.active_players:
                    if player.session_id == asker_sid:
                        asker = player
                        break
                
                if asker:
                    self.current_asker = asker.username
                    
                    # Choose random target (not the asker)
                    possible_targets = [p for p in lobby.active_players if p.id != asker.id]
                    if possible_targets:
                        target = random.choice(possible_targets)
                        self.current_target = target.username
                        
                        logger.info(f"Turn {lobby.current_turn + 1}: {asker.username} asks {target.username}")
                        
                        self.broadcast_game_update(
                            f"Turn {lobby.current_turn + 1}: {asker.username}, ask {target.username} a question!"
                        )
                        
                        # If it's an AI's turn, generate a question
                        if asker.is_ai:
                            self.handle_ai_question(asker, target)
    
    def handle_ai_question(self, asker, target):
        """Handle AI asking a question."""
        # Simple AI question generation for now
        questions = [
            f"{target.username}, what's the first thing you notice when you arrive here?",
            f"{target.username}, what would you typically wear in this place?",
            f"{target.username}, who else would you expect to see here?",
            f"{target.username}, what sounds do you hear in this environment?",
            f"{target.username}, what's the most important rule to follow here?"
        ]
        
        question = random.choice(questions)
        
        # Add delay to make it feel more natural
        def delayed_question():
            socketio.emit('new_question', {
                'asker': asker.username,
                'target': target.username,
                'question': question
            }, room=self.lobby_code)
            
            # If target is also AI, generate answer
            if target.is_ai:
                self.handle_ai_answer(target, question)
        
        socketio.start_background_task(lambda: socketio.sleep(2) or delayed_question())
    
    def handle_ai_answer(self, player, question):
        """Handle AI answering a question."""
        # Simple AI answer generation
        if player.is_outsider:
            # Outsider tries to blend in without knowing the location
            answers = [
                "I think the atmosphere is quite nice here.",
                "It depends on the situation, really.",
                "I'd say it's pretty typical for a place like this.",
                "You have to adapt to your surroundings.",
                "I prefer to observe first before acting."
            ]
        else:
            # Regular AI knows the location but gives vague answers
            answers = [
                "The environment definitely shapes how you behave.",
                "I always try to respect the space I'm in.",
                "It's important to follow the established protocols.",
                "You can usually tell a lot by watching others.",
                "I think common sense applies in most situations."
            ]
        
        answer = random.choice(answers)
        
        def delayed_answer():
            self.handle_answer(player.session_id, answer)
        
        socketio.start_background_task(lambda: socketio.sleep(3) or delayed_answer())
    
    def handle_question(self, asker_sid: str, target_username: str, question: str):
        """Handle a question being asked."""
        with get_db_session() as session:
            lobby = get_lobby_by_code(session, self.lobby_code)
            if not lobby:
                return False
                
            # Verify it's the asker's turn
            if lobby.current_turn >= len(self.turn_order):
                return False
                
            expected_asker_sid = self.turn_order[lobby.current_turn]
            if asker_sid != expected_asker_sid:
                return False
            
            # Find players
            asker = None
            target = None
            for player in lobby.active_players:
                if player.session_id == asker_sid:
                    asker = player
                elif player.username == target_username:
                    target = player
            
            if not asker or not target:
                return False
            
            # Update question count
            asker.questions_asked += 1
            
            # Broadcast question
            socketio.emit('new_question', {
                'asker': asker.username,
                'target': target.username,
                'question': question
            }, room=self.lobby_code)
            
            # If target is AI, generate answer
            if target.is_ai:
                self.handle_ai_answer(target, question)
            
            return True
    
    def handle_answer(self, answerer_sid: str, answer: str):
        """Handle an answer being given."""
        with get_db_session() as session:
            lobby = get_lobby_by_code(session, self.lobby_code)
            if not lobby:
                return False
            
            # Find answerer
            answerer = None
            for player in lobby.active_players:
                if player.session_id == answerer_sid:
                    answerer = player
                    break
            
            if not answerer:
                return False
            
            # Update stats
            answerer.questions_answered += 1
            lobby.question_count += 1
            lobby.current_turn += 1
            
            # Broadcast answer
            socketio.emit('new_answer', {
                'answerer': answerer.username,
                'answer': answer
            }, room=self.lobby_code)
            
            # Start next turn
            socketio.start_background_task(lambda: socketio.sleep(2) or self.start_next_turn())
            
            return True
    
    def start_voting_phase(self):
        """Start the voting phase."""
        with get_db_session() as session:
            lobby = get_lobby_by_code(session, self.lobby_code)
            if not lobby:
                return
                
            lobby.state = 'voting'
            
            self.broadcast_game_update("Voting phase! Choose who you think is the outsider.")
            
            socketio.emit('voting_started', {
                'players': [{'username': p.username, 'id': p.id} for p in lobby.active_players]
            }, room=self.lobby_code)
    
    def handle_vote(self, voter_sid: str, target_username: str):
        """Handle a vote being cast."""
        with get_db_session() as session:
            lobby = get_lobby_by_code(session, self.lobby_code)
            if not lobby or lobby.state != 'voting':
                return False
            
            # Find voter and target
            voter = None
            target = None
            for player in lobby.active_players:
                if player.session_id == voter_sid:
                    voter = player
                elif player.username == target_username:
                    target = player
            
            if not voter or not target:
                return False
            
            # Record vote (this would use the Vote model)
            # For now, we'll use a simple counting system
            
            return True
    
    def broadcast_game_update(self, message: str):
        """Broadcast a game update to all players."""
        lobby_data = self.get_lobby_data()
        if lobby_data:
            socketio.emit('game_update', {
                'message': message,
                'lobby': lobby_data
            }, room=self.lobby_code)

# Socket.IO Event Handlers

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {request.sid}")
    
    # Find and disconnect player
    with get_db_session() as session:
        # This is a simplified version - in real implementation,
        # we'd need to track which lobby the player is in
        pass

@socketio.on('create_lobby')
def handle_create_lobby(data):
    """Handle lobby creation."""
    try:
        lobby_name = data.get('name', 'New Game')
        lobby_code = data.get('code') or f"GAME{random.randint(1000, 9999)}"
        
        with get_db_session() as session:
            # Check if lobby already exists
            existing_lobby = get_lobby_by_code(session, lobby_code)
            if existing_lobby:
                emit('error', {'message': 'Lobby code already exists'})
                return
            
            # Create new lobby
            lobby = create_lobby(session, lobby_code, lobby_name)
            active_lobbies[lobby_code] = GameManager(lobby_code)
            
            emit('lobby_created', {
                'code': lobby.code,
                'name': lobby.name
            })
            
            logger.info(f"Created lobby: {lobby_code}")
            
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
        
        with get_db_session() as session:
            lobby = get_lobby_by_code(session, lobby_code)
            if not lobby:
                emit('error', {'message': 'Lobby not found'})
                return
            
            # Add player to lobby
            try:
                player = add_player_to_lobby(session, lobby, request.sid, username)
                
                # Join socket room
                join_room(lobby_code)
                
                # Initialize game manager if needed
                if lobby_code not in active_lobbies:
                    active_lobbies[lobby_code] = GameManager(lobby_code)
                
                # Send lobby data
                lobby_data = active_lobbies[lobby_code].get_lobby_data()
                emit('joined_lobby', lobby_data)
                
                # Notify other players
                emit('player_joined', {
                    'username': username,
                    'message': f"{username} joined the game"
                }, room=lobby_code, include_self=False)
                
                logger.info(f"Player {username} joined lobby {lobby_code}")
                
            except ValueError as e:
                emit('error', {'message': str(e)})
                
    except Exception as e:
        logger.error(f"Error joining lobby: {e}")
        emit('error', {'message': 'Failed to join lobby'})

@socketio.on('start_game')
def handle_start_game(data):
    """Handle game start request."""
    try:
        lobby_code = data.get('code')
        
        if lobby_code in active_lobbies:
            game_manager = active_lobbies[lobby_code]
            if game_manager.start_game():
                logger.info(f"Started game in lobby {lobby_code}")
            else:
                emit('error', {'message': 'Cannot start game'})
        else:
            emit('error', {'message': 'Lobby not found'})
            
    except Exception as e:
        logger.error(f"Error starting game: {e}")
        emit('error', {'message': 'Failed to start game'})

@socketio.on('ask_question')
def handle_ask_question(data):
    """Handle question being asked."""
    try:
        lobby_code = data.get('lobby_code')
        target_username = data.get('target')
        question = data.get('question')
        
        if lobby_code in active_lobbies:
            game_manager = active_lobbies[lobby_code]
            success = game_manager.handle_question(request.sid, target_username, question)
            if not success:
                emit('error', {'message': 'Invalid question'})
        else:
            emit('error', {'message': 'Game not found'})
            
    except Exception as e:
        logger.error(f"Error handling question: {e}")
        emit('error', {'message': 'Failed to ask question'})

@socketio.on('give_answer')
def handle_give_answer(data):
    """Handle answer being given."""
    try:
        lobby_code = data.get('lobby_code')
        answer = data.get('answer')
        
        if lobby_code in active_lobbies:
            game_manager = active_lobbies[lobby_code]
            success = game_manager.handle_answer(request.sid, answer)
            if not success:
                emit('error', {'message': 'Invalid answer'})
        else:
            emit('error', {'message': 'Game not found'})
            
    except Exception as e:
        logger.error(f"Error handling answer: {e}")
        emit('error', {'message': 'Failed to give answer'})

@socketio.on('cast_vote')
def handle_cast_vote(data):
    """Handle vote being cast."""
    try:
        lobby_code = data.get('lobby_code')
        target_username = data.get('target')
        
        if lobby_code in active_lobbies:
            game_manager = active_lobbies[lobby_code]
            success = game_manager.handle_vote(request.sid, target_username)
            if not success:
                emit('error', {'message': 'Invalid vote'})
        else:
            emit('error', {'message': 'Game not found'})
            
    except Exception as e:
        logger.error(f"Error handling vote: {e}")
        emit('error', {'message': 'Failed to cast vote'})

# Flask Routes

@app.route('/')
def index():
    """Main game page."""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return {'status': 'healthy', 'message': 'The Outsider game server is running'}

@app.route('/stats')
def stats():
    """Game statistics endpoint."""
    try:
        with get_db_session() as session:
            stats = get_game_statistics(session)
            if stats:
                return {
                    'human_wins': stats.human_wins,
                    'ai_wins': stats.ai_wins,
                    'total_games': stats.total_games,
                    'human_win_rate': stats.human_win_rate,
                    'avg_game_duration': stats.avg_game_duration
                }
            else:
                return {'message': 'No statistics available'}
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return {'error': 'Failed to get statistics'}, 500

# Application initialization

def create_app():
    """Application factory."""
    # Initialize database
    init_database()
    logger.info("Database initialized")
    
    return app

if __name__ == '__main__':
    # Development server
    app = create_app()
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'production') == 'development'
    
    logger.info(f"Starting The Outsider game server on port {port}")
    socketio.run(app, debug=debug, port=port, host='0.0.0.0')