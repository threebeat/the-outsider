from flask import request
from flask_socketio import join_room, emit
from models.database import (
    SessionLocal, get_lobby, get_players, get_player_by_sid, 
    get_player_by_username, add_message, get_win_counter, 
    get_db_session, close_db_session, get_db
)
from game.logic import GameManager
from game.ai import get_random_ai_name
from config.settings import DEBUG
import logging

logger = logging.getLogger(__name__)

# Global variables to store socketio and game_manager
_socketio = None
_game_manager = None

def register_handlers(socketio, game_manager):
    global _socketio, _game_manager
    _socketio = socketio
    _game_manager = game_manager
    
    logger.info("Setting up Socket.IO event handlers...")
    
    @socketio.on_error_default
    def default_error_handler(e):
        logger.error(f"SocketIO error: {e}")
        emit('game_update', {'log': 'An internal error occurred. Please try again.'})

    @socketio.on('join_room')
    def on_join_room(data):
        logger.info(f"Join room event received: {data}")
        room = data.get('room', 'main')
        join_room(room)
        logger.info(f"Client joined room: {room}")
        # Send confirmation to the client
        emit('room_joined', {'room': room, 'status': 'success'})

    @socketio.on('test_room')
    def on_test_room(data):
        logger.info(f"Test room event received: {data}")
        # Echo back to the room to test communication
        emit('test_room_response', {'message': 'Room communication working!', 'original': data}, room='main')

    @socketio.on('join')
    def on_join(data):
        """Handle player join request."""
        logger.info(f"Join event received with data: {data}")
        username = data.get('username', '').strip()
        current_sid = request.sid
        room = 'main'
        
        logger.info(f"Processing join for username: {username}, current_sid: {current_sid}, room: {room}")
        
        if not username:
            emit('game_update', {'log': 'Username is required.'}, room=current_sid)
            return
        
        # Check if game is currently resetting
        if _game_manager.is_resetting:
            logger.info(f"Game is currently resetting, rejecting join request")
            emit('game_update', {
                'log': 'Game is currently resetting. Please wait a moment and try again.',
                'error': True
            }, room=current_sid)
            return
        
        # Use basic session management
        session = SessionLocal()
        try:
            lobby = get_lobby(session, room)
            
            # Check if a game is already in progress
            if lobby.state in ['playing', 'voting']:
                logger.info(f"Game already in progress, putting {username} in spectator mode")
                
                # Check if username is already taken by a different player
                existing_player = get_player_by_username(session, lobby, username)
                if existing_player and existing_player.sid != current_sid:
                    logger.info(f"Username {username} is already taken by different player")
                    emit('game_update', {
                        'log': f'Username "{username}" is already taken. Please choose a different name.',
                        'error': True
                    }, room=current_sid)
                    return
                
                # Don't add spectator to database - just join room and send spectator mode
                # Get current game state
                players = get_players(session, lobby)
                active_players = [p for p in players if not p.is_ai]  # Only human players for spectator view
                player_names = [p.username for p in active_players]
                
                # Join the room and send spectator mode data
                join_room(room)
                
                # Send spectator mode to the joining player
                emit('spectator_mode', {
                    'message': f'Game in progress! You are spectating as {username}.',
                    'players': player_names,
                    'question_count': lobby.question_count,
                    'questions_until_vote': max(0, 5 - lobby.question_count)
                }, room=current_sid)
                
                # Only send a chat message notification, don't update the player list for active players
                emit('game_update', {
                    'log': f"{username} joined as a spectator."
                }, room=room)
                
                # Add spectator join message to game chat
                add_message(session, lobby, f"{username} joined as a spectator.")
                
                logger.info(f"Spectator {username} joined the game in progress")
                return
            
            # Check if username is already taken by a different player
            existing_player = get_player_by_username(session, lobby, username)
            if existing_player and existing_player.sid != current_sid:
                logger.info(f"Username {username} is already taken by different player")
                emit('game_update', {
                    'log': f'Username "{username}" is already taken. Please choose a different name.',
                    'error': True
                }, room=current_sid)
                return
            
            # Check if current SID already has a player
            existing_sid_player = get_player_by_sid(session, lobby, current_sid)
            if existing_sid_player:
                # Update username if it changed
                if existing_sid_player.username != username:
                    existing_sid_player.username = username
                    session.commit()
                    logger.info(f"Updated username for existing player: {username}")
            else:
                # Create new player
                from models.database import Player
                new_player = Player(sid=current_sid, username=username, is_ai=False, lobby=lobby)
                session.add(new_player)
                session.commit()
                logger.info(f"Created new player: {username} with SID: {current_sid}")
            
            # Create AI player if this is the first human player
            players = get_players(session, lobby)
            logger.info(f"Current players: {[p.username for p in players]}")
            if len(players) == 1 and not any(p.is_ai for p in players):
                # Create AI player
                ai_name = get_random_ai_name()
                ai_player = Player(sid=f"ai_{ai_name}", username=ai_name, is_ai=True, lobby=lobby)
                session.add(ai_player)
                session.commit()
                logger.info(f"Created AI player: {ai_name}")
            
            logger.info(f"{username} has joined the room {room}. Current players: {len(get_players(session, lobby))}")
            add_message(session, lobby, f"{username} has joined the room.")
            
            # Get updated player list after potential AI creation
            updated_players = get_players(session, lobby)
            player_names = [p.username for p in updated_players]
            logger.info(f"Sending game_update with players: {player_names}")
            
            # Join the room first, then emit
            join_room(room)
            
            # Broadcast updated player list to all players in the room (including the joining player)
            emit('game_update', {
                'players': player_names,
                'log': f"{username} has joined the room.",
                'can_start_game': len(updated_players) >= 2
            }, room=room)
            
            # Send current win counter to the joining player
            win_counter = get_win_counter(session, room)
            emit('win_counter_update', {
                'human_wins': win_counter.human_wins,
                'ai_wins': win_counter.ai_wins
            }, room=current_sid)
            
            # Also send win counter to all players in the room to ensure everyone has the latest count
            emit('win_counter_update', {
                'human_wins': win_counter.human_wins,
                'ai_wins': win_counter.ai_wins
            }, room=room)
            
            logger.info(f"game_update event emitted")
        except Exception as e:
            logger.error(f"Error in on_join: {e}")
            emit('game_update', {'log': 'An error occurred while joining the game.'}, room=request.sid)
        finally:
            session.close()

    @socketio.on('start_game')
    def handle_start_game(data):
        """Handle start game request."""
        print("Start game event received")
        
        # Ensure the client is in the room
        room = 'main'
        join_room(room)
        print(f"Client {request.sid} joined room {room} for start_game")
        
        # Check if game is currently resetting
        if _game_manager.is_resetting:
            print("Game is currently resetting, rejecting start game request")
            emit('game_update', {
                'log': 'Game is currently resetting. Please wait a moment and try again.',
                'error': True
            }, room=request.sid)
            return
        
        success, message = _game_manager.start_game(room=room)
        if not success:
            print(f"Failed to start game: {message}")

    @socketio.on('manual_reset')
    def handle_manual_reset():
        """Handle manual reset request."""
        print("Manual reset event received")
        _game_manager.reset_game(room="main")
        print("Manual reset completed")

    @socketio.on('ask_question')
    def on_ask_question(data):
        print(f"=== ASK QUESTION EVENT RECEIVED ===")
        print(f"Data: {data}")
        print(f"Request SID: {request.sid}")
        
        # Use improved session management
        session = None
        try:
            session = get_db_session()
            room = 'main'
            asker_sid = request.sid
            question = data.get('question')
            target_username = data.get('target')
            
            print(f"Processing question: '{question}' from {asker_sid} to {target_username}")
            
            # Find target SID from username
            lobby = get_lobby(session, room)
            players = get_players(session, lobby)
            target_player = next((p for p in players if p.username == target_username), None)
            if not target_player:
                print(f"Target player {target_username} not found")
                emit('game_update', {'log': 'Invalid target player.'}, room=request.sid)
                return
            
            target_sid = target_player.sid
            print(f"Found target SID: {target_sid}")
            _game_manager.handle_question(asker_sid, target_sid, question, room)
        except Exception as e:
            print(f"Error in ask_question: {e}")
            logger.error(f"Error in ask_question: {e}")
            emit('game_update', {'log': 'An error occurred while asking a question.'}, room=request.sid)
        finally:
            if session:
                close_db_session(session)

    @socketio.on('submit_answer')
    def on_submit_answer(data):
        session = None
        try:
            session = get_db_session()
            room = 'main'
            target_sid = request.sid
            answer = data.get('answer')
            _game_manager.handle_answer(target_sid, answer, room)
        except Exception as e:
            logger.error(f"Error in submit_answer: {e}")
            emit('game_update', {'log': 'An error occurred while submitting an answer.'}, room=request.sid)
        finally:
            if session:
                close_db_session(session)

    @socketio.on('submit_vote')
    def on_submit_vote(data):
        session = None
        try:
            session = get_db_session()
            room = 'main'
            voter_sid = request.sid
            voted_for_sid = data.get('voted_for_sid')
            _game_manager.handle_vote(voter_sid, voted_for_sid, room)
        except Exception as e:
            logger.error(f"Error in submit_vote: {e}")
            emit('game_update', {'log': 'An error occurred while submitting your vote.'}, room=request.sid)
        finally:
            if session:
                close_db_session(session)

    @socketio.on('request_vote')
    def on_request_vote(data):
        """Handle a player's request to start voting."""
        session = None
        try:
            session = get_db_session()
            room = 'main'
            requester_sid = request.sid
            success, message = _game_manager.request_vote(requester_sid, room)
            
            if not success:
                # Send error message to the requester
                emit('game_update', {'log': message, 'error': True}, room=requester_sid)
            else:
                # Send success message to all players
                emit('game_update', {'log': f"Voting initiated by a player after {_game_manager.get_question_count(room)} questions!"}, room=room)
                
        except Exception as e:
            logger.error(f"Error in request_vote: {e}")
            emit('game_update', {'log': 'An error occurred while requesting a vote.'}, room=request.sid)
        finally:
            if session:
                close_db_session(session)

    @socketio.on('typing_start')
    def on_typing_start(data):
        """Handle typing start event."""
        try:
            room = 'main'
            username = data.get('username')
            if username:
                # Broadcast typing indicator to all players in the room
                emit('typing_start', {'username': username}, room=room, include_self=False)
        except Exception as e:
            logger.error(f"Error in typing_start: {e}")

    @socketio.on('typing_stop')
    def on_typing_stop(data):
        """Handle typing stop event."""
        try:
            room = 'main'
            username = data.get('username')
            if username:
                # Broadcast typing stop to all players in the room
                emit('typing_stop', {'username': username}, room=room, include_self=False)
        except Exception as e:
            logger.error(f"Error in typing_stop: {e}")
    
    logger.info("Socket.IO event handlers registered successfully!") 