"""
Socket.IO Event Handlers for The Outsider.

Pure routing layer that delegates to appropriate business logic modules.
Contains no business logic - only event routing and response formatting.
"""

import logging
from flask import request
from flask_socketio import emit, join_room, leave_room

logger = logging.getLogger(__name__)

def register_socket_handlers(socketio, lobby_manager, game_manager):
    """
    Register all Socket.IO event handlers.
    
    Args:
        socketio: SocketIO instance
        lobby_manager: Lobby management instance
        game_manager: Game management instance
    """

    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        logger.info(f"Client connected: {request.sid}")
        emit('connected', {'message': 'Connected to server successfully'})

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        logger.info(f"Client disconnected: {request.sid}")
        
        try:
            # Delegate to lobby manager for player disconnection
            success, message, lobby_code = lobby_manager.disconnect_player(request.sid)
            
            if success and lobby_code:
                # Get updated lobby data
                lobby = lobby_manager.get_lobby(lobby_code)
                if lobby:
                    # Convert to dictionary format
                    lobby_data = {
                        'code': lobby.code,
                        'name': lobby.name,
                        'players': [{'username': p.username, 'is_ai': p.is_ai} for p in lobby.players],
                        'max_players': lobby.max_players
                    }
                    # Notify other players in the lobby
                    socketio.emit('player_disconnected', {
                        'message': message,
                        'lobby': lobby_data
                    }, room=lobby_code)
                    
        except Exception as e:
            logger.error(f"Error handling disconnect: {e}")

    @socketio.on('create_lobby')
    def handle_create_lobby(data):
        """Handle lobby creation request."""
        try:
            lobby_name = data.get('name', 'New Game')
            lobby_code = data.get('code')  # Optional custom code
            creator_sid = request.sid
            
            # Delegate to lobby manager
            success, message, lobby = lobby_manager.create_lobby(
                name=lobby_name,
                custom_code=lobby_code
            )
            
            if success and lobby:
                # Convert to dictionary format
                lobby_data = {
                    'code': lobby.code,
                    'name': lobby.name,
                    'players': [],
                    'max_players': lobby.max_players
                }
                
                emit('lobby_created', {
                    'success': True,
                    'lobby': lobby_data,
                    'message': message
                })
                logger.info(f"Created lobby: {lobby.code}")
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
            player_sid = request.sid
            
            if not lobby_code or not username:
                emit('error', {'message': 'Missing lobby code or username'})
                return
            
            # Delegate to lobby manager
            success, message, player_data = lobby_manager.join_lobby(
                lobby_code=lobby_code,
                session_id=player_sid,
                username=username
            )
            
            if success:
                # Join the socket room
                join_room(lobby_code)
                
                # Get updated lobby data
                lobby = lobby_manager.get_lobby(lobby_code)
                
                # Convert to dictionary format
                lobby_data = {
                    'code': lobby.code,
                    'name': lobby.name,
                    'players': [{'username': p.username, 'is_ai': p.is_ai} for p in lobby.players],
                    'max_players': lobby.max_players
                }
                
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
            player_sid = request.sid
            
            # Delegate to lobby manager
            success, message, lobby_code = lobby_manager.leave_lobby(player_sid)
            
            if success and lobby_code:
                # Leave the socket room
                leave_room(lobby_code)
                
                # Get updated lobby data
                lobby = lobby_manager.get_lobby(lobby_code)
                
                # Send success response
                emit('left_lobby', {
                    'success': True,
                    'message': message
                })
                
                # Notify other players
                if lobby:
                    lobby_data = {
                        'code': lobby.code,
                        'name': lobby.name,
                        'players': [{'username': p.username, 'is_ai': p.is_ai} for p in lobby.players],
                        'max_players': lobby.max_players
                    }
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
            
            # Delegate to game manager
            success, message, game_data = game_manager.start_new_game(lobby_code)
            
            if success:
                # Get updated lobby data
                lobby = lobby_manager.get_lobby(lobby_code)
                
                if lobby:
                    lobby_data = {
                        'code': lobby.code,
                        'name': lobby.name,
                        'players': [{'username': p.username, 'is_ai': p.is_ai} for p in lobby.players],
                        'max_players': lobby.max_players
                    }
                    
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
            asker_sid = request.sid
            
            if not target_username or not question:
                emit('error', {'message': 'Missing target or question'})
                return
            
            # Delegate to game manager
            success, message, result_data = game_manager.handle_player_question(
                asker_sid=asker_sid,
                target_username=target_username,
                question=question
            )
            
            if success and result_data:
                lobby_code = result_data['lobby_code']
                
                # Broadcast question to all players
                socketio.emit('question_asked', {
                    'question': result_data['question'],
                    'target': result_data['target'],
                    'asker': result_data['asker'],
                    'message': f"Question asked: {result_data['question']}"
                }, room=lobby_code)
                
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
            answerer_sid = request.sid
            
            if not answer:
                emit('error', {'message': 'Missing answer'})
                return
            
            # Delegate to game manager
            success, message, result_data = game_manager.handle_player_answer(
                answerer_sid=answerer_sid,
                answer=answer
            )
            
            if success and result_data:
                lobby_code = result_data['lobby_code']
                
                # Broadcast answer to all players
                answer_event = {
                    'answer': result_data['answer'],
                    'answerer': result_data['answerer'],
                    'message': f"Answer given: {result_data['answer']}"
                }
                
                # Check if game state changed
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
            voter_sid = request.sid
            
            if not target_username:
                emit('error', {'message': 'Missing vote target'})
                return
            
            # Delegate to game manager
            success, message, result_data = game_manager.handle_player_vote(
                voter_sid=voter_sid,
                target_username=target_username
            )
            
            if success and result_data:
                lobby_code = result_data['lobby_code']
                
                vote_event = {
                    'vote_result': result_data['vote_result'],
                    'voter': result_data['voter'],
                    'target': target_username,
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
            
            # Delegate to lobby manager
            lobby = lobby_manager.get_lobby(lobby_code)
            
            if lobby:
                # Convert to dictionary format for client
                lobby_data = {
                    'code': lobby.code,
                    'name': lobby.name,
                    'players': [{'username': p.username, 'is_ai': p.is_ai} for p in lobby.players],
                    'max_players': lobby.max_players,
                    'created_at': lobby.created_at.isoformat()
                }
                emit('lobby_data', {'lobby': lobby_data})
            else:
                emit('error', {'message': 'Lobby not found'})
                
        except Exception as e:
            logger.error(f"Error getting lobby data: {e}")
            emit('error', {'message': 'Failed to get lobby data'})
    
    logger.info("Socket.IO handlers registered successfully")