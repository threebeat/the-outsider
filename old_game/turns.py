"""
Turn management for The Outsider.

This module handles turn order, progression, and the question/answer sequence
during the game.
"""

import logging
import random
from typing import Optional, List, Dict, Any
from database import get_db_session, get_lobby_by_code
from utils.constants import GAME_STATES, GAME_CONFIG
from utils.helpers import shuffle_players

logger = logging.getLogger(__name__)

class TurnManager:
    """Manages turn order and progression during the game."""
    
    def __init__(self):
        self.turn_orders: Dict[str, List[str]] = {}  # lobby_code -> [session_ids]
        self.current_states: Dict[str, Dict[str, Any]] = {}  # lobby_code -> state_data
    
    def initialize_turn_order(self, lobby_code: str) -> bool:
        """
        Initialize the turn order for a lobby.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Success status
        """
        try:
            with get_db_session() as session:
                lobby = get_lobby_by_code(session, lobby_code)
                if not lobby:
                    return False
                
                # Get all active players
                active_players = lobby.active_players
                if not active_players:
                    return False
                
                # Shuffle players for random turn order
                shuffled_players = shuffle_players(active_players)
                self.turn_orders[lobby_code] = [p.session_id for p in shuffled_players]
                
                # Initialize turn state
                self.current_states[lobby_code] = {
                    'current_turn': 0,
                    'current_asker': None,
                    'current_target': None,
                    'awaiting_question': False,
                    'awaiting_answer': False,
                    'question_content': None
                }
                
                logger.info(f"Initialized turn order for lobby {lobby_code}: {len(shuffled_players)} players")
                return True
                
        except Exception as e:
            logger.error(f"Error initializing turn order: {e}")
            return False
    
    def get_current_turn_info(self, lobby_code: str) -> Optional[Dict[str, Any]]:
        """
        Get current turn information.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Turn information dictionary or None
        """
        if lobby_code not in self.current_states:
            return None
            
        try:
            with get_db_session() as session:
                lobby = get_lobby_by_code(session, lobby_code)
                if not lobby:
                    return None
                
                state = self.current_states[lobby_code]
                turn_order = self.turn_orders.get(lobby_code, [])
                
                if not turn_order or state['current_turn'] >= len(turn_order):
                    return None
                
                # Get current asker
                current_asker_sid = turn_order[state['current_turn']]
                current_asker = None
                for player in lobby.active_players:
                    if player.session_id == current_asker_sid:
                        current_asker = player
                        break
                
                if not current_asker:
                    return None
                
                return {
                    'turn_number': state['current_turn'] + 1,
                    'total_turns': len(turn_order),
                    'current_asker': {
                        'session_id': current_asker.session_id,
                        'username': current_asker.username,
                        'is_ai': current_asker.is_ai
                    },
                    'current_target': state['current_target'],
                    'awaiting_question': state['awaiting_question'],
                    'awaiting_answer': state['awaiting_answer'],
                    'question_content': state['question_content']
                }
                
        except Exception as e:
            logger.error(f"Error getting turn info: {e}")
            return None
    
    def start_next_turn(self, lobby_code: str) -> Optional[Dict[str, Any]]:
        """
        Start the next turn in the sequence.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Next turn information or None if game should end
        """
        try:
            with get_db_session() as session:
                lobby = get_lobby_by_code(session, lobby_code)
                if not lobby:
                    return None
                
                # Check if we've reached the question limit
                if lobby.question_count >= lobby.max_questions:
                    return None  # Game should move to voting phase
                
                if lobby_code not in self.current_states:
                    self.initialize_turn_order(lobby_code)
                
                state = self.current_states[lobby_code]
                turn_order = self.turn_orders.get(lobby_code, [])
                
                if not turn_order:
                    return None
                
                # Check if we've cycled through all players
                if state['current_turn'] >= len(turn_order):
                    state['current_turn'] = 0  # Reset to beginning
                
                # Get current asker
                current_asker_sid = turn_order[state['current_turn']]
                current_asker = None
                for player in lobby.active_players:
                    if player.session_id == current_asker_sid:
                        current_asker = player
                        break
                
                if not current_asker:
                    # Player no longer active, skip turn
                    state['current_turn'] += 1
                    return self.start_next_turn(lobby_code)
                
                # Select random target (not the asker)
                possible_targets = [p for p in lobby.active_players if p.session_id != current_asker_sid]
                if not possible_targets:
                    return None
                
                target = random.choice(possible_targets)
                
                # Update state
                state['current_asker'] = current_asker.username
                state['current_target'] = target.username
                state['awaiting_question'] = True
                state['awaiting_answer'] = False
                state['question_content'] = None
                
                # Update database
                lobby.current_turn = state['current_turn']
                
                turn_info = {
                    'turn_number': state['current_turn'] + 1,
                    'total_turns': len(turn_order),
                    'current_asker': {
                        'session_id': current_asker.session_id,
                        'username': current_asker.username,
                        'is_ai': current_asker.is_ai
                    },
                    'current_target': {
                        'session_id': target.session_id,
                        'username': target.username,
                        'is_ai': target.is_ai
                    },
                    'awaiting_question': True,
                    'awaiting_answer': False
                }
                
                logger.info(f"Started turn {turn_info['turn_number']} in lobby {lobby_code}: "
                           f"{current_asker.username} -> {target.username}")
                
                return turn_info
                
        except Exception as e:
            logger.error(f"Error starting next turn: {e}")
            return None
    
    def handle_question_asked(self, lobby_code: str, asker_session_id: str, 
                             target_username: str, question: str) -> tuple[bool, str]:
        """
        Handle a question being asked.
        
        Args:
            lobby_code: Code of the lobby
            asker_session_id: Session ID of the player asking
            target_username: Username of the target player
            question: The question content
            
        Returns:
            tuple: (success, error_message)
        """
        try:
            if lobby_code not in self.current_states:
                return False, "Game not in progress"
            
            state = self.current_states[lobby_code]
            
            # Verify it's the asker's turn
            if not state['awaiting_question']:
                return False, "Not awaiting a question"
            
            turn_order = self.turn_orders.get(lobby_code, [])
            if not turn_order or state['current_turn'] >= len(turn_order):
                return False, "Invalid turn state"
            
            expected_asker_sid = turn_order[state['current_turn']]
            if asker_session_id != expected_asker_sid:
                return False, "Not your turn to ask"
            
            # Verify target
            if target_username != state['current_target']:
                return False, f"Must ask {state['current_target']}"
            
            # Update state
            state['awaiting_question'] = False
            state['awaiting_answer'] = True
            state['question_content'] = question
            
            # Update database
            with get_db_session() as session:
                lobby = get_lobby_by_code(session, lobby_code)
                if lobby:
                    # Find and update asker's stats
                    for player in lobby.active_players:
                        if player.session_id == asker_session_id:
                            player.questions_asked += 1
                            break
            
            logger.info(f"Question asked in lobby {lobby_code}: {state['current_asker']} -> {target_username}")
            return True, ""
            
        except Exception as e:
            logger.error(f"Error handling question: {e}")
            return False, "Failed to process question"
    
    def handle_answer_given(self, lobby_code: str, answerer_session_id: str, 
                           answer: str) -> tuple[bool, str]:
        """
        Handle an answer being given.
        
        Args:
            lobby_code: Code of the lobby
            answerer_session_id: Session ID of the player answering
            answer: The answer content
            
        Returns:
            tuple: (success, error_message)
        """
        try:
            if lobby_code not in self.current_states:
                return False, "Game not in progress"
            
            state = self.current_states[lobby_code]
            
            # Verify we're awaiting an answer
            if not state['awaiting_answer']:
                return False, "Not awaiting an answer"
            
            # Verify it's the target's turn to answer
            with get_db_session() as session:
                lobby = get_lobby_by_code(session, lobby_code)
                if not lobby:
                    return False, "Lobby not found"
                
                # Find the target player
                target_player = None
                for player in lobby.active_players:
                    if player.username == state['current_target']:
                        target_player = player
                        break
                
                if not target_player:
                    return False, "Target player not found"
                
                if target_player.session_id != answerer_session_id:
                    return False, "Not your turn to answer"
                
                # Update player stats
                target_player.questions_answered += 1
                
                # Update lobby question count
                lobby.question_count += 1
            
            # Move to next turn
            state['current_turn'] += 1
            state['awaiting_answer'] = False
            state['question_content'] = None
            
            logger.info(f"Answer given in lobby {lobby_code}: {state['current_target']}")
            return True, ""
            
        except Exception as e:
            logger.error(f"Error handling answer: {e}")
            return False, "Failed to process answer"
    
    def should_advance_to_voting(self, lobby_code: str) -> bool:
        """
        Check if the game should advance to voting phase.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Whether to advance to voting
        """
        try:
            with get_db_session() as session:
                lobby = get_lobby_by_code(session, lobby_code)
                if not lobby:
                    return False
                
                return lobby.question_count >= lobby.max_questions
                
        except Exception as e:
            logger.error(f"Error checking voting advancement: {e}")
            return False
    
    def get_turn_summary(self, lobby_code: str) -> Optional[Dict[str, Any]]:
        """
        Get a summary of the current turn state.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Turn summary dictionary or None
        """
        try:
            with get_db_session() as session:
                lobby = get_lobby_by_code(session, lobby_code)
                if not lobby:
                    return None
                
                if lobby_code not in self.current_states:
                    return None
                
                state = self.current_states[lobby_code]
                
                return {
                    'current_turn': state['current_turn'] + 1,
                    'total_questions': lobby.question_count,
                    'max_questions': lobby.max_questions,
                    'current_asker': state['current_asker'],
                    'current_target': state['current_target'],
                    'awaiting_question': state['awaiting_question'],
                    'awaiting_answer': state['awaiting_answer'],
                    'ready_for_voting': self.should_advance_to_voting(lobby_code)
                }
                
        except Exception as e:
            logger.error(f"Error getting turn summary: {e}")
            return None
    
    def reset_turns(self, lobby_code: str):
        """
        Reset turn state for a lobby.
        
        Args:
            lobby_code: Code of the lobby
        """
        if lobby_code in self.turn_orders:
            del self.turn_orders[lobby_code]
        if lobby_code in self.current_states:
            del self.current_states[lobby_code]
        
        logger.info(f"Reset turn state for lobby {lobby_code}")
    
    def is_player_turn(self, lobby_code: str, session_id: str) -> bool:
        """
        Check if it's a specific player's turn.
        
        Args:
            lobby_code: Code of the lobby
            session_id: Player's session ID
            
        Returns:
            Whether it's the player's turn
        """
        if lobby_code not in self.current_states or lobby_code not in self.turn_orders:
            return False
        
        state = self.current_states[lobby_code]
        turn_order = self.turn_orders[lobby_code]
        
        if state['current_turn'] >= len(turn_order):
            return False
        
        expected_session_id = turn_order[state['current_turn']]
        return session_id == expected_session_id