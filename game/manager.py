"""
Main Game Manager for The Outsider.

This module coordinates all game subsystems and provides a unified interface
for managing game state, progression, and player interactions.
"""

import logging
from typing import Optional, Dict, Any, List
from .lobby import LobbyManager
from .turns import TurnManager  
from .voting import VotingManager
from ai.questions import QuestionGenerator
from utils.constants import GAME_STATES, LOCATIONS, WINNER_TYPES
from database import get_db_session, get_lobby_by_code

logger = logging.getLogger(__name__)

class GameManager:
    """Main game coordinator that manages all aspects of the game."""
    
    def __init__(self):
        # Initialize subsystem managers
        self.lobby_manager = LobbyManager()
        self.turn_manager = TurnManager()
        self.voting_manager = VotingManager()
        self.question_generator = QuestionGenerator()
        
        # Track active games
        self.active_games: Dict[str, Dict[str, Any]] = {}
        self.player_lobby_map: Dict[str, str] = {}  # session_id -> lobby_code
    
    # Lobby Management Methods
    
    def create_lobby(self, lobby_name: str, lobby_code: Optional[str] = None) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """Create a new game lobby."""
        return self.lobby_manager.create_lobby(lobby_name, lobby_code)
    
    def join_lobby(self, lobby_code: str, session_id: str, username: str) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """Add a player to a lobby."""
        success, message, player_data = self.lobby_manager.join_lobby(lobby_code, session_id, username)
        
        if success:
            self.player_lobby_map[session_id] = lobby_code
            
        return success, message, player_data
    
    def leave_lobby(self, session_id: str) -> tuple[bool, str, Optional[str]]:
        """Remove a player from their lobby."""
        success, message, lobby_code = self.lobby_manager.leave_lobby(session_id)
        
        if success and session_id in self.player_lobby_map:
            del self.player_lobby_map[session_id]
            
        return success, message, lobby_code
    
    def disconnect_player(self, session_id: str) -> tuple[bool, str, Optional[str]]:
        """Mark a player as disconnected."""
        success, message, lobby_code = self.lobby_manager.disconnect_player(session_id)
        
        if success and session_id in self.player_lobby_map:
            del self.player_lobby_map[session_id]
            
        return success, message, lobby_code
    
    def get_lobby_data(self, lobby_code: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive lobby data including game state."""
        lobby_data = self.lobby_manager.get_lobby_data(lobby_code)
        
        if lobby_data:
            # Add turn information if game is active
            if lobby_data['state'] == GAME_STATES['PLAYING']:
                turn_info = self.turn_manager.get_turn_summary(lobby_code)
                if turn_info:
                    lobby_data.update(turn_info)
            
            # Add voting information if in voting phase
            elif lobby_data['state'] == GAME_STATES['VOTING']:
                voting_status = self.voting_manager.get_voting_status(lobby_code)
                if voting_status:
                    lobby_data['voting_status'] = voting_status
                    
        return lobby_data
    
    # Game Flow Methods
    
    def start_game(self, lobby_code: str) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """Start a new game in the lobby."""
        try:
            # Get lobby data
            lobby_data = self.lobby_manager.get_lobby_data(lobby_code)
            if not lobby_data:
                return False, "Lobby not found", None
            
            if lobby_data['state'] != GAME_STATES['WAITING']:
                return False, "Game already in progress", None
            
            # Check if we need to add an AI player
            if lobby_data['ai_players'] == 0:
                success, message, ai_data = self.lobby_manager.add_ai_player(lobby_code)
                if not success:
                    return False, f"Failed to add AI player: {message}", None
            
            # Select random location
            import random
            location = random.choice(LOCATIONS)
            
            # Initialize game session in database
            with get_db_session() as session:
                lobby = get_lobby_by_code(session, lobby_code)
                if not lobby:
                    return False, "Lobby not found in database", None
                
                from database import start_game_session
                
                human_count = len(lobby.human_players)
                ai_count = len(lobby.ai_players)
                
                game_session = start_game_session(session, lobby, location)
                
                # Choose outsider (always AI for now)
                ai_players = lobby.ai_players
                if ai_players:
                    outsider = random.choice(ai_players)
                    outsider.is_outsider = True
                    lobby.outsider_player_id = outsider.id
                    logger.info(f"Selected {outsider.username} as outsider in lobby {lobby_code}")
            
            # Initialize turn order
            if not self.turn_manager.initialize_turn_order(lobby_code):
                return False, "Failed to initialize turn order", None
            
            # Start first turn
            turn_info = self.turn_manager.start_next_turn(lobby_code)
            if not turn_info:
                return False, "Failed to start first turn", None
            
            # Track active game
            self.active_games[lobby_code] = {
                'location': location,
                'started_at': game_session.started_at,
                'session_id': game_session.id
            }
            
            result_data = {
                'location': location,
                'turn_info': turn_info,
                'message': 'Game started! Try to identify the outsider.'
            }
            
            logger.info(f"Started game in lobby {lobby_code} with location '{location}'")
            return True, "Game started successfully", result_data
            
        except Exception as e:
            logger.error(f"Error starting game: {e}")
            return False, "Failed to start game", None
    
    def handle_question(self, session_id: str, target_username: str, question: str) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """Handle a player asking a question."""
        try:
            lobby_code = self.player_lobby_map.get(session_id)
            if not lobby_code:
                return False, "Player not in any lobby", None
            
            # Validate and process the question
            success, error_msg = self.turn_manager.handle_question_asked(
                lobby_code, session_id, target_username, question
            )
            
            if not success:
                return False, error_msg, None
            
            result_data = {
                'question': question,
                'target': target_username,
                'lobby_code': lobby_code
            }
            
            return True, "Question asked successfully", result_data
            
        except Exception as e:
            logger.error(f"Error handling question: {e}")
            return False, "Failed to process question", None
    
    def handle_answer(self, session_id: str, answer: str) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """Handle a player giving an answer."""
        try:
            lobby_code = self.player_lobby_map.get(session_id)
            if not lobby_code:
                return False, "Player not in any lobby", None
            
            # Process the answer
            success, error_msg = self.turn_manager.handle_answer_given(
                lobby_code, session_id, answer
            )
            
            if not success:
                return False, error_msg, None
            
            # Check if we should advance to voting
            if self.turn_manager.should_advance_to_voting(lobby_code):
                voting_success, voting_msg, voting_data = self.voting_manager.start_voting_phase(lobby_code)
                if voting_success:
                    # Handle AI votes automatically
                    self.voting_manager.handle_ai_votes(lobby_code)
                    
                    result_data = {
                        'answer': answer,
                        'advance_to_voting': True,
                        'voting_data': voting_data
                    }
                else:
                    result_data = {
                        'answer': answer,
                        'advance_to_voting': False,
                        'error': voting_msg
                    }
            else:
                # Continue with next turn
                turn_info = self.turn_manager.start_next_turn(lobby_code)
                result_data = {
                    'answer': answer,
                    'next_turn': turn_info
                }
            
            return True, "Answer processed successfully", result_data
            
        except Exception as e:
            logger.error(f"Error handling answer: {e}")
            return False, "Failed to process answer", None
    
    def handle_vote(self, session_id: str, target_username: str) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """Handle a player casting a vote."""
        try:
            lobby_code = self.player_lobby_map.get(session_id)
            if not lobby_code:
                return False, "Player not in any lobby", None
            
            # Cast the vote
            success, message, vote_result = self.voting_manager.cast_vote(
                lobby_code, session_id, target_username
            )
            
            if not success:
                return False, message, None
            
            # Check if voting is complete
            if vote_result and vote_result.get('voting_complete'):
                game_result = self.voting_manager.get_game_result(lobby_code)
                if game_result:
                    # End the game session
                    self._end_game_session(lobby_code, game_result)
                    
                    result_data = {
                        'vote_result': vote_result,
                        'game_result': game_result
                    }
                else:
                    result_data = {'vote_result': vote_result}
            else:
                result_data = {'vote_result': vote_result}
            
            return True, "Vote cast successfully", result_data
            
        except Exception as e:
            logger.error(f"Error handling vote: {e}")
            return False, "Failed to cast vote", None
    
    def generate_ai_question(self, lobby_code: str, ai_session_id: str, target_username: str) -> Optional[str]:
        """Generate a question for an AI player."""
        try:
            # Get AI player data
            with get_db_session() as session:
                lobby = get_lobby_by_code(session, lobby_code)
                if not lobby:
                    return None
                
                ai_player = None
                for player in lobby.active_players:
                    if player.session_id == ai_session_id and player.is_ai:
                        ai_player = player
                        break
                
                if not ai_player:
                    return None
                
                ai_player_data = {
                    'username': ai_player.username,
                    'is_outsider': ai_player.is_outsider,
                    'questions_asked': ai_player.questions_asked,
                    'personality': ai_player.ai_personality or 'curious'
                }
                
                game_context = {
                    'location': lobby.location
                } if lobby.location else None
                
                return self.question_generator.generate_question(
                    ai_player_data, target_username, game_context
                )
                
        except Exception as e:
            logger.error(f"Error generating AI question: {e}")
            return None
    
    def reset_game(self, lobby_code: str) -> bool:
        """Reset a game to allow for a new round."""
        try:
            # Reset all subsystems
            success = self.lobby_manager.reset_lobby(lobby_code)
            if success:
                self.turn_manager.reset_turns(lobby_code)
                self.voting_manager.reset_voting(lobby_code)
                
                # Clean up active game tracking
                if lobby_code in self.active_games:
                    del self.active_games[lobby_code]
                
                logger.info(f"Reset game in lobby {lobby_code}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error resetting game: {e}")
            return False
    
    def _end_game_session(self, lobby_code: str, game_result: Dict[str, Any]):
        """End the current game session and update statistics."""
        try:
            with get_db_session() as session:
                lobby = get_lobby_by_code(session, lobby_code)
                if not lobby:
                    return
                
                from database import end_game_session, increment_human_wins, increment_ai_wins
                
                winner = game_result.get('winner')
                reason = game_result.get('reason')
                eliminated_username = game_result.get('eliminated_player')
                
                # Find eliminated player
                eliminated_player = None
                if eliminated_username:
                    for player in lobby.active_players:
                        if player.username == eliminated_username:
                            eliminated_player = player
                            break
                
                # End the session
                end_game_session(session, lobby, winner, reason, eliminated_player)
                
                # Update win statistics
                if winner == WINNER_TYPES['HUMANS']:
                    increment_human_wins(session, lobby.code)
                elif winner == WINNER_TYPES['AI']:
                    increment_ai_wins(session, lobby.code)
                
                logger.info(f"Ended game session in lobby {lobby_code}: {winner} won")
                
        except Exception as e:
            logger.error(f"Error ending game session: {e}")
    
    def get_player_lobby(self, session_id: str) -> Optional[str]:
        """Get the lobby code for a player's session."""
        return self.player_lobby_map.get(session_id)
    
    def is_player_turn(self, session_id: str) -> bool:
        """Check if it's a specific player's turn."""
        lobby_code = self.player_lobby_map.get(session_id)
        if not lobby_code:
            return False
            
        return self.turn_manager.is_player_turn(lobby_code, session_id)
    
    def get_active_lobbies(self) -> List[Dict[str, Any]]:
        """Get all active lobbies."""
        return self.lobby_manager.get_active_lobbies()
    
    def cleanup_inactive_lobbies(self) -> int:
        """Clean up inactive lobbies."""
        return self.lobby_manager.cleanup_inactive_lobbies()