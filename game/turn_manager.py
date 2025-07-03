"""
Turn Manager for The Outsider Game.

Handles turn order, turn progression, and starting player selection.
Contains no lobby logic - purely turn-based game flow management.
"""

import random
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class TurnInfo:
    """Information about the current turn."""
    current_player: str
    next_player: str
    turn_number: int
    question_asker: Optional[str] = None
    question_target: Optional[str] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    turn_start_time: Optional[datetime] = None
    turn_timeout: Optional[datetime] = None

class TurnManager:
    """
    Manages turn order and turn progression in games.
    
    Handles starting player selection, turn rotation, and turn timing.
    Contains no lobby or game state logic - pure turn management.
    """
    
    def __init__(self, turn_timeout_seconds: int = 60):
        """
        Initialize turn manager.
        
        Args:
            turn_timeout_seconds: Maximum time per turn in seconds
        """
        self.turn_timeout_seconds = turn_timeout_seconds
        logger.debug("Turn manager initialized")
    
    def choose_starting_player(self, player_list: List[str]) -> Optional[str]:
        """
        Choose a random starting player from the list of players.
        
        Args:
            player_list: List of player usernames
            
        Returns:
            Username of chosen starting player, or None if no players
        """
        try:
            if not player_list:
                logger.warning("Cannot choose starting player - no players provided")
                return None
            
            starting_player = random.choice(player_list)
            logger.info(f"Chose starting player: {starting_player} from {len(player_list)} players")
            return starting_player
            
        except Exception as e:
            logger.error(f"Error choosing starting player: {e}")
            return None
    
    def create_turn_order(self, player_list: List[str], starting_player: Optional[str] = None) -> List[str]:
        """
        Create turn order starting from a specific player or random player.
        
        Args:
            player_list: List of all players
            starting_player: Player to start with (chosen randomly if None)
            
        Returns:
            Ordered list of players for turn rotation
        """
        try:
            if not player_list:
                logger.warning("Cannot create turn order - no players provided")
                return []
            
            # Choose starting player if not provided
            if starting_player is None:
                starting_player = self.choose_starting_player(player_list)
                if starting_player is None:
                    return []
            
            # Validate starting player is in the list
            if starting_player not in player_list:
                logger.warning(f"Starting player {starting_player} not in player list, choosing random")
                starting_player = self.choose_starting_player(player_list)
                if starting_player is None:
                    return []
            
            # Create turn order starting from the chosen player
            players = player_list.copy()
            start_index = players.index(starting_player)
            
            # Rotate list so starting player is first
            turn_order = players[start_index:] + players[:start_index]
            
            logger.info(f"Created turn order: {turn_order}")
            return turn_order
            
        except Exception as e:
            logger.error(f"Error creating turn order: {e}")
            return []
    
    def get_next_player(self, current_player: str, turn_order: List[str]) -> Optional[str]:
        """
        Get the next player in turn order.
        
        Args:
            current_player: Current player's username
            turn_order: Ordered list of players
            
        Returns:
            Next player's username, or None if error
        """
        try:
            if not turn_order or current_player not in turn_order:
                logger.warning(f"Cannot get next player - invalid turn order or player {current_player}")
                return None
            
            current_index = turn_order.index(current_player)
            next_index = (current_index + 1) % len(turn_order)
            next_player = turn_order[next_index]
            
            logger.debug(f"Next player after {current_player}: {next_player}")
            return next_player
            
        except Exception as e:
            logger.error(f"Error getting next player: {e}")
            return None
    
    def get_previous_player(self, current_player: str, turn_order: List[str]) -> Optional[str]:
        """
        Get the previous player in turn order.
        
        Args:
            current_player: Current player's username
            turn_order: Ordered list of players
            
        Returns:
            Previous player's username, or None if error
        """
        try:
            if not turn_order or current_player not in turn_order:
                logger.warning(f"Cannot get previous player - invalid turn order or player {current_player}")
                return None
            
            current_index = turn_order.index(current_player)
            previous_index = (current_index - 1) % len(turn_order)
            previous_player = turn_order[previous_index]
            
            logger.debug(f"Previous player before {current_player}: {previous_player}")
            return previous_player
            
        except Exception as e:
            logger.error(f"Error getting previous player: {e}")
            return None
    
    def create_turn_info(self, 
                        current_player: str, 
                        turn_order: List[str], 
                        turn_number: int = 1) -> Optional[TurnInfo]:
        """
        Create turn information for the current turn.
        
        Args:
            current_player: Current player's username
            turn_order: Ordered list of players
            turn_number: Current turn number
            
        Returns:
            TurnInfo object or None if error
        """
        try:
            next_player = self.get_next_player(current_player, turn_order)
            if next_player is None:
                return None
            
            turn_start = datetime.now()
            turn_timeout = turn_start + timedelta(seconds=self.turn_timeout_seconds)
            
            turn_info = TurnInfo(
                current_player=current_player,
                next_player=next_player,
                turn_number=turn_number,
                turn_start_time=turn_start,
                turn_timeout=turn_timeout
            )
            
            logger.debug(f"Created turn info for player {current_player}, turn {turn_number}")
            return turn_info
            
        except Exception as e:
            logger.error(f"Error creating turn info: {e}")
            return None
    
    def advance_turn(self, current_turn_info: TurnInfo, turn_order: List[str]) -> Optional[TurnInfo]:
        """
        Advance to the next turn.
        
        Args:
            current_turn_info: Current turn information
            turn_order: Ordered list of players
            
        Returns:
            New TurnInfo for next turn, or None if error
        """
        try:
            next_player = current_turn_info.next_player
            new_turn_number = current_turn_info.turn_number + 1
            
            new_turn_info = self.create_turn_info(
                current_player=next_player,
                turn_order=turn_order,
                turn_number=new_turn_number
            )
            
            if new_turn_info:
                logger.info(f"Advanced to turn {new_turn_number}, player {next_player}")
            
            return new_turn_info
            
        except Exception as e:
            logger.error(f"Error advancing turn: {e}")
            return None
    
    def is_turn_expired(self, turn_info: TurnInfo) -> bool:
        """
        Check if the current turn has expired.
        
        Args:
            turn_info: Current turn information
            
        Returns:
            True if turn has expired, False otherwise
        """
        try:
            if not turn_info.turn_timeout:
                return False
            
            return datetime.now() > turn_info.turn_timeout
            
        except Exception as e:
            logger.error(f"Error checking turn expiration: {e}")
            return False
    
    def get_turn_time_remaining(self, turn_info: TurnInfo) -> Optional[int]:
        """
        Get remaining time in seconds for the current turn.
        
        Args:
            turn_info: Current turn information
            
        Returns:
            Remaining seconds, or None if no timeout set
        """
        try:
            if not turn_info.turn_timeout:
                return None
            
            remaining = turn_info.turn_timeout - datetime.now()
            remaining_seconds = max(0, int(remaining.total_seconds()))
            
            return remaining_seconds
            
        except Exception as e:
            logger.error(f"Error getting turn time remaining: {e}")
            return None
    
    def get_random_target_for_player(self, asker: str, available_players: List[str]) -> Optional[str]:
        """
        Get a random target player for asking questions (excluding the asker).
        
        Args:
            asker: Player who is asking the question
            available_players: List of all available players
            
        Returns:
            Random target player username, or None if no valid targets
        """
        try:
            # Remove the asker from potential targets
            valid_targets = [player for player in available_players if player != asker]
            
            if not valid_targets:
                logger.warning(f"No valid targets for player {asker}")
                return None
            
            target = random.choice(valid_targets)
            logger.debug(f"Chose random target {target} for asker {asker}")
            return target
            
        except Exception as e:
            logger.error(f"Error choosing random target: {e}")
            return None
    
    def update_turn_with_question(self, 
                                 turn_info: TurnInfo, 
                                 asker: str, 
                                 target: str, 
                                 question: str) -> TurnInfo:
        """
        Update turn info with question details.
        
        Args:
            turn_info: Current turn information
            asker: Player asking the question
            target: Player being asked
            question: The question text
            
        Returns:
            Updated TurnInfo
        """
        try:
            turn_info.question_asker = asker
            turn_info.question_target = target
            turn_info.question = question
            
            logger.debug(f"Updated turn with question from {asker} to {target}")
            return turn_info
            
        except Exception as e:
            logger.error(f"Error updating turn with question: {e}")
            return turn_info
    
    def update_turn_with_answer(self, turn_info: TurnInfo, answer: str) -> TurnInfo:
        """
        Update turn info with answer.
        
        Args:
            turn_info: Current turn information
            answer: The answer text
            
        Returns:
            Updated TurnInfo
        """
        try:
            turn_info.answer = answer
            
            logger.debug(f"Updated turn with answer: {answer[:50]}...")
            return turn_info
            
        except Exception as e:
            logger.error(f"Error updating turn with answer: {e}")
            return turn_info
    
    def validate_turn_order(self, turn_order: List[str], expected_players: List[str]) -> bool:
        """
        Validate that turn order contains all expected players.
        
        Args:
            turn_order: Current turn order
            expected_players: List of players that should be in turn order
            
        Returns:
            True if turn order is valid, False otherwise
        """
        try:
            # Check that all expected players are in turn order
            for player in expected_players:
                if player not in turn_order:
                    logger.warning(f"Player {player} missing from turn order")
                    return False
            
            # Check that turn order doesn't have extra players
            for player in turn_order:
                if player not in expected_players:
                    logger.warning(f"Unexpected player {player} in turn order")
                    return False
            
            # Check for duplicates
            if len(set(turn_order)) != len(turn_order):
                logger.warning("Turn order contains duplicate players")
                return False
            
            logger.debug("Turn order validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Error validating turn order: {e}")
            return False
    
    def get_status(self) -> dict:
        """
        Get current status of the turn manager.
        
        Returns:
            Status information dictionary
        """
        return {
            'turn_timeout_seconds': self.turn_timeout_seconds,
            'manager_initialized': True
        }