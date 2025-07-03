"""
Game Manager - Coordinator for game operations.

Provides a unified interface for game operations by coordinating
between TurnManager, QuestionManager, VoteManager, and AnswerManager.
"""

import logging
from typing import Optional, Dict, Any, Tuple
from .turn_manager import TurnManager
from .question_manager import QuestionManager
from .answer_manager import AnswerManager
from .vote_manager import VoteManager
from database import get_db_session, Lobby, GameSession, GameStatistics, create_game_session
from utils.constants import LOCATIONS

logger = logging.getLogger(__name__)

class GameManager:
    """Coordinates all game operations within lobbies."""
    
    def __init__(self):
        self.active_games: Dict[str, Dict[str, Any]] = {}  # lobby_code -> game state
        self.question_manager = QuestionManager()
        self.answer_manager = AnswerManager()
        self.vote_manager = VoteManager()
    
    def start_new_game(self, lobby_code: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Start a new game in a lobby.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            tuple: (success, message, game_data)
        """
        try:
            with get_db_session() as session:
                lobby = session.query(Lobby).filter_by(code=lobby_code).first()
                if not lobby:
                    return False, "Lobby not found", None
                
                if lobby.state != 'waiting':
                    return False, "Game already in progress", None
                
                from database import get_players_from_lobby
                if len(get_players_from_lobby(lobby.id, is_spectator=False)) < 3:
                    return False, "Need at least 3 players to start", None
                
                # Select random location
                import random
                location = random.choice(LOCATIONS)
                
                # Start game session in database
                game_session = create_game_session(lobby.id, location)
                
                # Initialize turn manager
                turn_manager = TurnManager(lobby_code)
                
                # Set up game state
                self.active_games[lobby_code] = {
                    'turn_manager': turn_manager,
                    'game_session_id': game_session.id,
                    'location': location,
                    'outsider': self._select_outsider_player(lobby),
                    'voting_session': None
                }
                
                game_data = {
                    'location': location,
                    'current_player': turn_manager.get_current_player(),
                    'turn_order': turn_manager.get_turn_order(),
                    'game_state': 'playing'
                }
                
                logger.info(f"Started game in lobby {lobby_code} with location {location}")
                return True, "Game started", game_data
                
        except Exception as e:
            logger.error(f"Error starting game: {e}")
            return False, "Failed to start game", None
    
    def handle_player_question(self, asker_sid: str, target_username: str, 
                              question: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Handle a player asking a question.
        
        Args:
            asker_sid: Session ID of asker
            target_username: Username of target
            question: The question text
            
        Returns:
            tuple: (success, message, result_data)
        """
        try:
            # Find lobby and validate
            lobby_code = self._find_player_lobby(asker_sid)
            if not lobby_code:
                return False, "Player not in any game", None
            
            if lobby_code not in self.active_games:
                return False, "No active game in lobby", None
            
            game_state = self.active_games[lobby_code]
            turn_manager = game_state['turn_manager']
            
            # Get asker username
            asker_username = self._get_player_username(asker_sid)
            if not asker_username:
                return False, "Player not found", None
            
            # Validate it's the asker's turn
            if turn_manager.get_current_player() != asker_username:
                return False, "Not your turn", None
            
            # Handle question based on player type
            is_ai = self._is_ai_player(asker_username)
            
            if is_ai and asker_username == game_state['outsider']:
                # AI outsider asking
                question_data = self.question_manager.handle_ai_question(
                    asker_username, target_username, {'location': None}
                )
            elif is_ai:
                # Regular AI asking (not implemented in new structure)
                return False, "Regular AI players not supported", None
            else:
                # Human asking
                question_data = self.question_manager.handle_human_question(
                    asker_username, target_username, question
                )
            
            if not question_data:
                return False, "Failed to process question", None
            
            # Update turn manager
            turn_manager.add_question_to_current_turn(
                asker_username, target_username, question_data.question
            )
            
            result_data = {
                'lobby_code': lobby_code,
                'question': question_data.question,
                'asker': asker_username,
                'target': target_username
            }
            
            return True, "Question asked", result_data
            
        except Exception as e:
            logger.error(f"Error handling question: {e}")
            return False, "Failed to handle question", None
    
    def handle_player_answer(self, answerer_sid: str, answer: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Handle a player giving an answer.
        
        Args:
            answerer_sid: Session ID of answerer
            answer: The answer text
            
        Returns:
            tuple: (success, message, result_data)
        """
        try:
            # Find lobby and validate
            lobby_code = self._find_player_lobby(answerer_sid)
            if not lobby_code:
                return False, "Player not in any game", None
            
            if lobby_code not in self.active_games:
                return False, "No active game in lobby", None
            
            game_state = self.active_games[lobby_code]
            turn_manager = game_state['turn_manager']
            
            # Get answerer username
            answerer_username = self._get_player_username(answerer_sid)
            if not answerer_username:
                return False, "Player not found", None
            
            # Handle answer based on player type
            is_ai = self._is_ai_player(answerer_username)
            
            if is_ai and answerer_username == game_state['outsider']:
                # AI outsider answering
                answer_data = self.answer_manager.handle_ai_answer(
                    answerer_username, "Question text", "Asker", {'location': None}
                )
            elif is_ai:
                # Regular AI answering (not implemented in new structure)
                return False, "Regular AI players not supported", None
            else:
                # Human answering
                answer_data = self.answer_manager.handle_human_answer(
                    answerer_username, answer
                )
            
            if not answer_data:
                return False, "Failed to process answer", None
            
            # Update turn manager
            turn_manager.add_answer_to_current_turn(answer_data.answer)
            
            # Check if should advance to voting
            should_vote = turn_manager.should_advance_to_voting()
            
            result_data = {
                'lobby_code': lobby_code,
                'answer': answer_data.answer,
                'answerer': answerer_username,
                'advance_to_voting': should_vote
            }
            
            if not should_vote:
                # Advance to next turn
                next_player = turn_manager.get_next_player()
                if next_player:
                    turn_manager.advance_turn(next_player)
                    result_data['next_turn'] = {
                        'current_player': next_player,
                        'turn_number': turn_manager.get_turn_number()
                    }
            
            return True, "Answer given", result_data
            
        except Exception as e:
            logger.error(f"Error handling answer: {e}")
            return False, "Failed to handle answer", None
    
    def handle_player_vote(self, voter_sid: str, target_username: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Handle a player casting a vote.
        
        Args:
            voter_sid: Session ID of voter
            target_username: Username being voted for
            
        Returns:
            tuple: (success, message, result_data)
        """
        try:
            from database import get_players_from_lobby
            # Find lobby and validate
            lobby_code = self._find_player_lobby(voter_sid)
            if not lobby_code:
                return False, "Player not in any game", None
            
            if lobby_code not in self.active_games:
                return False, "No active game in lobby", None
            
            game_state = self.active_games[lobby_code]
            
            # Initialize voting session if needed
            if not game_state.get('voting_session'):
                with get_db_session() as session:
                    lobby = session.query(Lobby).filter_by(code=lobby_code).first()
                    if not lobby:
                        return False, "Lobby not found", None
                    
                    eligible_voters = [p.username for p in get_players_from_lobby(lobby.id, is_spectator=False)]
                    eligible_targets = eligible_voters
                    
                    game_state['voting_session'] = self.vote_manager.start_voting_session(
                        eligible_voters, eligible_targets
                    )
            
            voting_session = game_state['voting_session']
            voter_username = self._get_player_username(voter_sid)
            if not voter_username:
                return False, "Player not found", None
            
            # Validate and record vote
            with get_db_session() as session:
                lobby = session.query(Lobby).filter_by(code=lobby_code).first()
                eligible_voters = [p.username for p in get_players_from_lobby(lobby.id, is_spectator=False)]
                eligible_targets = eligible_voters
            
            is_valid, error = self.vote_manager.validate_vote(
                voter_username, target_username, eligible_voters, 
                eligible_targets, voting_session
            )
            
            if not is_valid:
                return False, error, None
            
            success, message = self.vote_manager.record_vote(
                voter_username, target_username, voting_session
            )
            
            if not success:
                return False, message, None
            
            # Check if voting complete
            if self.vote_manager.is_voting_complete(voting_session, len(eligible_voters)):
                # Calculate results
                vote_results = self.vote_manager.finalize_voting(voting_session)
                
                result_data = {
                    'lobby_code': lobby_code,
                    'voter': voter_username,
                    'vote_result': vote_results,
                    'game_result': self._determine_game_result(lobby_code, vote_results)
                }
                
                # Clean up game
                del self.active_games[lobby_code]
            else:
                result_data = {
                    'lobby_code': lobby_code,
                    'voter': voter_username,
                    'vote_result': {'votes_remaining': len(eligible_voters) - len(voting_session.votes)}
                }
            
            return True, "Vote recorded", result_data
            
        except Exception as e:
            logger.error(f"Error handling vote: {e}")
            return False, "Failed to handle vote", None
    
    def get_game_statistics(self) -> Optional[Dict[str, Any]]:
        """Get game statistics from database."""
        try:
            with get_db_session() as session:
                stats = session.query(GameStatistics).filter_by(lobby_code='main').first()
                if stats:
                    return {
                        'human_wins': stats.human_wins,
                        'ai_wins': stats.ai_wins,
                        'total_games': stats.total_games,
                        'human_win_rate': stats.human_win_rate,
                        'avg_game_duration': stats.avg_game_duration
                    }
            return None
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return None
    
    def get_ai_status(self) -> Dict[str, Any]:
        """Get AI system status."""
        try:
            from ai import QuestionGenerator
            return {
                'ai_available': True,
                'ai_system': 'OpenAI',
                'active_games': len(self.active_games)
            }
        except ImportError:
            return {
                'ai_available': False,
                'ai_system': 'None',
                'active_games': len(self.active_games)
            }
    
    def _find_player_lobby(self, session_id: str) -> Optional[str]:
        """Find which lobby a player is in."""
        # This would need to be implemented with proper session tracking
        # For now, return None
        return None
    
    def _get_player_username(self, session_id: str) -> Optional[str]:
        """Get player username from session ID."""
        # This would need to be implemented with proper session tracking
        # For now, return None
        return None
    
    def _is_ai_player(self, username: str) -> bool:
        """Check if a player is AI."""
        # This would need to check the database
        return username.startswith("AI_")
    
    def _select_outsider_player(self, lobby) -> str:
        """Select the AI outsider player for the game."""
        from database import get_players_from_lobby
        # For now, select first AI player
        ai_players = get_players_from_lobby(lobby.id, is_ai=True)
        if ai_players:
            return ai_players[0].username
        # If no AI players, this shouldn't happen
        return "AI_Outsider"
    
    def _determine_game_result(self, lobby_code: str, vote_results) -> Dict[str, Any]:
        """Determine game result based on voting."""
        game_state = self.active_games.get(lobby_code, {})
        outsider = game_state.get('outsider')
        
        if vote_results.winner == outsider:
            return {
                'winner': 'humans',
                'reason': 'Outsider was eliminated',
                'outsider_eliminated': True
            }
        else:
            return {
                'winner': 'ai',
                'reason': 'Outsider survived',
                'outsider_eliminated': False
            }