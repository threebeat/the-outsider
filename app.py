"""
The Outsider - A Social Deduction Game Backend

Flask-SocketIO backend API that serves a React frontend.
Handles real-time multiplayer game logic where players try to identify 
the AI "outsider" who doesn't know the secret location.
"""

import os
import logging
import random
from typing import Optional, List, Dict
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

# Import our database components
from database import (
    init_database, get_db_session, create_lobby, get_lobby_by_code,
    add_player_to_lobby, remove_player_from_lobby, disconnect_player,
    start_game_session, end_game_session, reset_lobby, get_game_statistics,
    cleanup_inactive_lobbies
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
active_lobbies: Dict[str, 'GameManager'] = {}  # In-memory cache for quick access
player_lobby_map: Dict[str, str] = {}  # Maps session_id to lobby_code

class GameManager:
    """Manages game state and logic for a lobby."""
    
    def __init__(self, lobby_code: str):
        self.lobby_code = lobby_code
        self.current_asker = None
        self.current_target = None
        self.turn_order = []
        self.votes = {}  # Track votes during voting phase
        
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
                    'questions_answered': player.questions_answered,
                    'is_connected': player.is_connected
                })
            
            return {
                'code': lobby.code,
                'name': lobby.name,
                'state': lobby.state,
                'location': lobby.location if lobby.state != 'waiting' else None,
                'current_turn': lobby.current_turn,
                'question_count': lobby.question_count,
                'max_questions': lobby.max_questions,
                'players': players_data,
                'current_asker': self.current_asker,
                'current_target': self.current_target,
                'total_players': len(players_data)
            }
    
    def start_game(self):
        """Start a new game session."""
        with get_db_session() as session:
            lobby = get_lobby_by_code(session, self.lobby_code)
            if not lobby or lobby.state != 'waiting':
                return False
                
            # Need at least 1 human player
            if len(lobby.human_players) < 1:
                return False
            
            # Add AI player if needed
            if len(lobby.ai_players) == 0:
                ai_name = random.choice([name for name in AI_NAMES 
                                       if name not in [p.username for p in lobby.active_players]])
                try:
                    ai_player = add_player_to_lobby(
                        session, lobby, f"ai_{random.randint(1000, 9999)}", 
                        ai_name, is_ai=True
                    )
                    logger.info(f"Added AI player {ai_name} to lobby {self.lobby_code}")
                except ValueError as e:
                    logger.error(f"Failed to add AI player: {e}")
                    return False
            
            # Select random location
            location = random.choice(LOCATIONS)
            
            # Choose outsider (always AI for now)
            ai_players = lobby.ai_players
            if ai_players:
                outsider = random.choice(ai_players)
                outsider.is_outsider = True
                lobby.outsider_player_id = outsider.id
                logger.info(f"Selected {outsider.username} as outsider")
            
            # Set up turn order
            all_players = lobby.active_players
            random.shuffle(all_players)
            self.turn_order = [p.session_id for p in all_players]
            
            # Start game session
            start_game_session(session, lobby, location)
            
            # Notify all players
            self.broadcast_game_update("Game started! Try to identify the outsider.", include_location=False)
            
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
            self.votes = {}  # Reset votes
            
            self.broadcast_game_update("Voting phase! Choose who you think is the outsider.")
            
            socketio.emit('voting_started', {
                'players': [{'username': p.username, 'id': p.id} for p in lobby.active_players if not p.is_ai]
            }, room=self.lobby_code)
            
            # Handle AI votes
            self.handle_ai_votes()
    
    def handle_ai_votes(self):
        """Handle AI players casting votes."""
        with get_db_session() as session:
            lobby = get_lobby_by_code(session, self.lobby_code)
            if not lobby:
                return
            
            for ai_player in lobby.ai_players:
                if not ai_player.is_outsider:  # Only non-outsider AIs vote
                    # AI votes for a random human player
                    human_players = lobby.human_players
                    if human_players:
                        target = random.choice(human_players)
                        self.votes[ai_player.session_id] = target.username
                        
                        socketio.emit('vote_cast', {
                            'voter': ai_player.username,
                            'target': target.username
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
            
            if not voter or not target or voter.is_ai:
                return False
            
            # Record vote
            self.votes[voter_sid] = target_username
            
            # Broadcast vote
            socketio.emit('vote_cast', {
                'voter': voter.username,
                'target': target_username
            }, room=self.lobby_code)
            
            # Check if all human players have voted
            human_players = lobby.human_players
            human_votes = [v for k, v in self.votes.items() 
                          if any(p.session_id == k for p in human_players)]
            
            if len(human_votes) >= len(human_players):
                self.end_voting()
            
            return True
    
    def end_voting(self):
        """End voting and determine game outcome."""
        with get_db_session() as session:
            lobby = get_lobby_by_code(session, self.lobby_code)
            if not lobby:
                return
            
            # Count votes
            vote_counts = {}
            for target_username in self.votes.values():
                vote_counts[target_username] = vote_counts.get(target_username, 0) + 1
            
            # Find most voted player
            if vote_counts:
                eliminated_username = max(vote_counts.keys(), key=lambda x: vote_counts[x])
                eliminated_player = None
                outsider_player = None
                
                for player in lobby.active_players:
                    if player.username == eliminated_username:
                        eliminated_player = player
                    if player.is_outsider:
                        outsider_player = player
                
                # Determine winner
                if eliminated_player and eliminated_player.is_outsider:
                    winner = 'humans'
                    reason = 'Outsider eliminated by vote'
                else:
                    winner = 'ai'
                    reason = 'Humans eliminated wrong player'
                
                # End game
                end_game_session(session, lobby, winner, reason, eliminated_player)
                
                # Broadcast results
                socketio.emit('game_ended', {
                    'winner': winner,
                    'reason': reason,
                    'eliminated_player': eliminated_username,
                    'outsider_was': outsider_player.username if outsider_player else 'Unknown',
                    'vote_results': vote_counts
                }, room=self.lobby_code)
                
                # Reset lobby after delay
                socketio.start_background_task(lambda: socketio.sleep(10) or self.reset_lobby())
    
    def reset_lobby(self):
        """Reset the lobby for a new game."""
        with get_db_session() as session:
            lobby = get_lobby_by_code(session, self.lobby_code)
            if lobby:
                reset_lobby(session, lobby)
                self.votes = {}
                self.current_asker = None
                self.current_target = None
                self.turn_order = []
                
                self.broadcast_game_update("Game reset. Ready for a new round!")
    
    def broadcast_game_update(self, message: str, include_location: bool = True):
        """Broadcast a game update to all players."""
        lobby_data = self.get_lobby_data()
        if lobby_data:
            update_data = {
                'message': message,
                'lobby': lobby_data
            }
            
            if include_location and lobby_data.get('location'):
                # Send location only to non-outsider players
                with get_db_session() as session:
                    lobby = get_lobby_by_code(session, self.lobby_code)
                    if lobby:
                        for player in lobby.active_players:
                            player_data = update_data.copy()
                            if player.is_outsider:
                                player_data['lobby'] = {**lobby_data, 'location': None}
                            
                            socketio.emit('game_update', player_data, 
                                        room=player.session_id)
            else:
                socketio.emit('game_update', update_data, room=self.lobby_code)

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
    if request.sid in player_lobby_map:
        lobby_code = player_lobby_map[request.sid]
        with get_db_session() as session:
            lobby = get_lobby_by_code(session, lobby_code)
            if lobby:
                for player in lobby.players:
                    if player.session_id == request.sid:
                        disconnect_player(session, player)
                        leave_room(lobby_code)
                        
                        # Notify other players
                        socketio.emit('player_left', {
                            'username': player.username,
                            'message': f"{player.username} left the game"
                        }, room=lobby_code)
                        
                        break
        
        # Clean up mapping
        del player_lobby_map[request.sid]

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
                player_lobby_map[request.sid] = lobby_code
                
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
                emit('error', {'message': 'Cannot start game - need at least 1 human player'})
        else:
            emit('error', {'message': 'Lobby not found'})
            
    except Exception as e:
        logger.error(f"Error starting game: {e}")
        emit('error', {'message': 'Failed to start game'})

@socketio.on('ask_question')
def handle_ask_question(data):
    """Handle question being asked."""
    try:
        lobby_code = player_lobby_map.get(request.sid)
        target_username = data.get('target')
        question = data.get('question')
        
        if lobby_code and lobby_code in active_lobbies:
            game_manager = active_lobbies[lobby_code]
            success = game_manager.handle_question(request.sid, target_username, question)
            if not success:
                emit('error', {'message': 'Invalid question or not your turn'})
        else:
            emit('error', {'message': 'Game not found'})
            
    except Exception as e:
        logger.error(f"Error handling question: {e}")
        emit('error', {'message': 'Failed to ask question'})

@socketio.on('give_answer')
def handle_give_answer(data):
    """Handle answer being given."""
    try:
        lobby_code = player_lobby_map.get(request.sid)
        answer = data.get('answer')
        
        if lobby_code and lobby_code in active_lobbies:
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
        lobby_code = player_lobby_map.get(request.sid)
        target_username = data.get('target')
        
        if lobby_code and lobby_code in active_lobbies:
            game_manager = active_lobbies[lobby_code]
            success = game_manager.handle_vote(request.sid, target_username)
            if not success:
                emit('error', {'message': 'Invalid vote'})
        else:
            emit('error', {'message': 'Game not found'})
            
    except Exception as e:
        logger.error(f"Error handling vote: {e}")
        emit('error', {'message': 'Failed to cast vote'})

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
        lobbies_info = []
        for code, manager in active_lobbies.items():
            lobby_data = manager.get_lobby_data()
            if lobby_data:
                lobbies_info.append({
                    'code': lobby_data['code'],
                    'name': lobby_data['name'],
                    'state': lobby_data['state'],
                    'players': lobby_data['total_players'],
                    'max_players': 8  # Default max
                })
        
        return jsonify({'lobbies': lobbies_info})
    except Exception as e:
        logger.error(f"Error getting active lobbies: {e}")
        return jsonify({'error': 'Failed to get lobbies'}), 500

@app.route('/api/cleanup')
def cleanup_inactive():
    """Clean up inactive lobbies (admin endpoint)."""
    try:
        with get_db_session() as session:
            cleaned_count = cleanup_inactive_lobbies(session)
            
            # Also clean up in-memory state
            inactive_codes = []
            for code, manager in active_lobbies.items():
                if not manager.get_lobby_data():
                    inactive_codes.append(code)
            
            for code in inactive_codes:
                del active_lobbies[code]
            
            return jsonify({
                'message': f'Cleaned up {cleaned_count} inactive lobbies',
                'memory_cleanup': len(inactive_codes)
            })
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return jsonify({'error': 'Cleanup failed'}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Application initialization

def create_app():
    """Application factory."""
    # Initialize database
    init_database()
    logger.info("Database initialized")
    
    # Clean up old lobbies on startup
    with get_db_session() as session:
        cleaned = cleanup_inactive_lobbies(session, hours_inactive=6)
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} inactive lobbies on startup")
    
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