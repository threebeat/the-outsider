"""
Enhanced Turn Manager for The Outsider Game.

Handles turn order, turn progression, and starting player selection with database integration.
Automatically initializes when created, saves game state, and provides dynamic turn advancement.
"""

import random
import logging
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from database import get_db_session, Lobby, Player, GameSession

logger = logging.getLogger(__name__)

@dataclass
class TurnInfo:
    """Enhanced information about the current turn."""
    current_player: str
    next_player: str
    turn_number: int
    round_number: int = 1
    question_asker: Optional[str] = None
    question_target: Optional[str] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    turn_start_time: Optional[datetime] = None
    turn_timeout: Optional[datetime] = None

@dataclass
class GameState:
    """Enhanced game state with database backing."""
    lobby_code: str
    turn_order: List[str]
    current_turn_info: TurnInfo
    game_session_id: Optional[int] = None
    questions_this_round: int = 0
    max_questions_per_round: int = 5
    total_questions: int = 0

class TurnManager:
    """
    Enhanced turn manager with automatic initialization and database integration.
    
    Features:
    - Automatically chooses starting player when initialized
    - Automatically creates turn order right after
    - Saves current player and game details in database
    - Provides advance_turn method that updates database dynamically
    """
    
    def __init__(self, lobby_code: str, turn_timeout_seconds: int = 60, 
                 max_questions_per_round: int = 5):
        """
        Initialize turn manager with automatic setup.
        
        Args:
            lobby_code: Code of the lobby this turn manager handles
            turn_timeout_seconds: Maximum time per turn in seconds
            max_questions_per_round: Maximum questions per round before voting
        """
        self.lobby_code = lobby_code
        self.turn_timeout_seconds = turn_timeout_seconds
        self.max_questions_per_round = max_questions_per_round
        self.game_state: Optional[GameState] = None
        
        # Automatically initialize the game
        self._auto_initialize()
        
        logger.info(f"Turn manager initialized for lobby {lobby_code}")
    
    def _auto_initialize(self):
        """
        Automatically initialize the turn manager by:
        1. Getting player list from lobby
        2. Choosing starting player
        3. Creating turn order
        4. Saving initial state to database
        """
        try:
            with get_db_session() as session:
                lobby = session.query(Lobby).filter_by(code=self.lobby_code).first()
                if not lobby:
                    raise ValueError(f"Lobby {self.lobby_code} not found")
                
                # Get active players
                from database_getters import get_active_players_in_lobby
                active_players = [p.username for p in get_active_players_in_lobby(lobby.id)]
                if len(active_players) < 2:
                    raise ValueError("Need at least 2 players to start game")
                
                # Choose starting player automatically
                starting_player = self._choose_starting_player(active_players)
                logger.info(f"Auto-selected starting player: {starting_player}")
                
                # Create turn order automatically
                turn_order = self._create_turn_order(active_players, starting_player)
                logger.info(f"Auto-created turn order: {turn_order}")
                
                # Create initial turn info
                initial_turn = TurnInfo(
                    current_player=starting_player,
                    next_player=self._get_next_player(starting_player, turn_order),
                    turn_number=1,
                    round_number=1,
                    turn_start_time=datetime.now(),
                    turn_timeout=datetime.now() + timedelta(seconds=self.turn_timeout_seconds)
                )
                
                # Initialize game state
                self.game_state = GameState(
                    lobby_code=self.lobby_code,
                    turn_order=turn_order,
                    current_turn_info=initial_turn,
                    max_questions_per_round=self.max_questions_per_round
                )
                
                # Save initial state to database
                self._save_turn_state_to_db(session, lobby)
                
                logger.info(f"Auto-initialization complete for lobby {self.lobby_code}")
                
        except Exception as e:
            logger.error(f"Failed to auto-initialize turn manager: {e}")
            raise
    
    def _choose_starting_player(self, player_list: List[str]) -> str:
        """
        Choose a random starting player from the list of players.
        
        Args:
            player_list: List of player usernames
            
        Returns:
            Username of chosen starting player
        """
        if not player_list:
            raise ValueError("Cannot choose starting player - no players provided")
        
        starting_player = random.choice(player_list)
        logger.debug(f"Chose starting player: {starting_player} from {len(player_list)} players")
        return starting_player
    
    def _create_turn_order(self, player_list: List[str], starting_player: str) -> List[str]:
        """
        Create turn order starting from a specific player.
        
        Args:
            player_list: List of all players
            starting_player: Player to start with
            
        Returns:
            Ordered list of players for turn rotation
        """
        if starting_player not in player_list:
            raise ValueError(f"Starting player {starting_player} not in player list")
        
        # Create turn order starting from the chosen player
        players = player_list.copy()
        start_index = players.index(starting_player)
        
        # Rotate list so starting player is first
        turn_order = players[start_index:] + players[:start_index]
        
        logger.debug(f"Created turn order: {turn_order}")
        return turn_order
    
    def _get_next_player(self, current_player: str, turn_order: List[str]) -> str:
        """
        Get the next player in turn order.
        
        Args:
            current_player: Current player's username
            turn_order: Ordered list of players
            
        Returns:
            Next player's username
        """
        if current_player not in turn_order:
            raise ValueError(f"Player {current_player} not in turn order")
        
        current_index = turn_order.index(current_player)
        next_index = (current_index + 1) % len(turn_order)
        next_player = turn_order[next_index]
        
        logger.debug(f"Next player after {current_player}: {next_player}")
        return next_player
    
    def advance_turn(self, next_player_name: str) -> bool:
        """
        Advance to the next turn with the given player and update database.
        
        Args:
            next_player_name: Username of the next player to take their turn
            
        Returns:
            True if advance was successful, False otherwise
        """
        try:
            if not self.game_state:
                logger.error("Cannot advance turn - game state not initialized")
                return False
            
            # Validate that the next player is in our turn order
            if next_player_name not in self.game_state.turn_order:
                logger.error(f"Player {next_player_name} not in turn order")
                return False
            
            # Update turn info
            current_turn = self.game_state.current_turn_info
            new_turn_number = current_turn.turn_number + 1
            new_round_number = current_turn.round_number
            
            # Check if we should advance to next round (after voting)
            if self.game_state.questions_this_round >= self.max_questions_per_round:
                new_round_number += 1
                self.game_state.questions_this_round = 0
                logger.info(f"Advancing to round {new_round_number}")
            
            # Create new turn info
            new_turn_info = TurnInfo(
                current_player=next_player_name,
                next_player=self._get_next_player(next_player_name, self.game_state.turn_order),
                turn_number=new_turn_number,
                round_number=new_round_number,
                turn_start_time=datetime.now(),
                turn_timeout=datetime.now() + timedelta(seconds=self.turn_timeout_seconds)
            )
            
            # Update game state
            self.game_state.current_turn_info = new_turn_info
            
            # Save to database
            with get_db_session() as session:
                lobby = session.query(Lobby).filter_by(code=self.lobby_code).first()
                if lobby:
                    self._save_turn_state_to_db(session, lobby)
                    logger.info(f"Advanced to turn {new_turn_number}, player {next_player_name}")
                    return True
                else:
                    logger.error(f"Lobby {self.lobby_code} not found")
                    return False
                    
        except Exception as e:
            logger.error(f"Error advancing turn: {e}")
            return False
    
    def add_question_to_current_turn(self, asker: str, target: str, question: str) -> bool:
        """
        Add a question to the current turn and update database.
        
        Args:
            asker: Player asking the question
            target: Player being asked
            question: The question text
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.game_state:
                logger.error("Cannot add question - game state not initialized")
                return False
            
            # Update current turn with question
            current_turn = self.game_state.current_turn_info
            current_turn.question_asker = asker
            current_turn.question_target = target
            current_turn.question = question
            
            # Increment question counters
            self.game_state.questions_this_round += 1
            self.game_state.total_questions += 1
            
            # Save to database
            with get_db_session() as session:
                lobby = session.query(Lobby).filter_by(code=self.lobby_code).first()
                if lobby:
                    lobby.question_count = self.game_state.total_questions
                    self._save_turn_state_to_db(session, lobby)
                    logger.info(f"Added question from {asker} to {target}")
                    return True
                else:
                    logger.error(f"Lobby {self.lobby_code} not found")
                    return False
                    
        except Exception as e:
            logger.error(f"Error adding question to turn: {e}")
            return False
    
    def add_answer_to_current_turn(self, answer: str) -> bool:
        """
        Add an answer to the current turn and update database.
        
        Args:
            answer: The answer text
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.game_state:
                logger.error("Cannot add answer - game state not initialized")
                return False
            
            # Update current turn with answer
            self.game_state.current_turn_info.answer = answer
            
            # Save to database
            with get_db_session() as session:
                lobby = session.query(Lobby).filter_by(code=self.lobby_code).first()
                if lobby:
                    self._save_turn_state_to_db(session, lobby)
                    logger.info(f"Added answer to current turn")
                    return True
                else:
                    logger.error(f"Lobby {self.lobby_code} not found")
                    return False
                    
        except Exception as e:
            logger.error(f"Error adding answer to turn: {e}")
            return False
    
    def should_advance_to_voting(self) -> bool:
        """
        Check if the game should advance to voting phase.
        
        Returns:
            True if should advance to voting, False if continue questions
        """
        if not self.game_state:
            return False
        
        return self.game_state.questions_this_round >= self.max_questions_per_round
    
    def get_random_target_for_player(self, asker: str) -> Optional[str]:
        """
        Get a random target player for asking questions (excluding the asker).
        
        Args:
            asker: Player who is asking the question
            
        Returns:
            Random target player username, or None if no valid targets
        """
        try:
            if not self.game_state:
                return None
            
            # Remove the asker from potential targets
            valid_targets = [player for player in self.game_state.turn_order if player != asker]
            
            if not valid_targets:
                logger.warning(f"No valid targets for player {asker}")
                return None
            
            target = random.choice(valid_targets)
            logger.debug(f"Chose random target {target} for asker {asker}")
            return target
            
        except Exception as e:
            logger.error(f"Error choosing random target: {e}")
            return None
    
    def _save_turn_state_to_db(self, session, lobby: Lobby):
        """
        Save current turn state and game details to the database.
        
        Args:
            session: Database session
            lobby: Lobby object to update
        """
        try:
            if not self.game_state:
                return
            
            current_turn = self.game_state.current_turn_info
            
            # Update lobby with current turn information
            lobby.current_turn = current_turn.turn_number
            lobby.question_count = self.game_state.total_questions
            lobby.last_activity = datetime.now()
            
            # Update or create game session if needed
            if not self.game_state.game_session_id:
                # Check if there's an active game session
                active_session = session.query(GameSession).filter_by(
                    lobby_id=lobby.id,
                    ended_at=None
                ).first()
                
                if active_session:
                    self.game_state.game_session_id = active_session.id
                    logger.debug(f"Found active game session: {active_session.id}")
            
            logger.debug(f"Saved turn state to database: turn {current_turn.turn_number}, player {current_turn.current_player}")
            
        except Exception as e:
            logger.error(f"Error saving turn state to database: {e}")
    
    def get_current_player(self) -> Optional[str]:
        """Get the current player whose turn it is."""
        if not self.game_state:
            return None
        return self.game_state.current_turn_info.current_player
    
    def get_next_player(self) -> Optional[str]:
        """Get the next player in turn order."""
        if not self.game_state:
            return None
        return self.game_state.current_turn_info.next_player
    
    def get_turn_number(self) -> int:
        """Get the current turn number."""
        if not self.game_state:
            return 0
        return self.game_state.current_turn_info.turn_number
    
    def get_round_number(self) -> int:
        """Get the current round number."""
        if not self.game_state:
            return 0
        return self.game_state.current_turn_info.round_number
    
    def get_questions_this_round(self) -> int:
        """Get the number of questions asked this round."""
        if not self.game_state:
            return 0
        return self.game_state.questions_this_round
    
    def get_total_questions(self) -> int:
        """Get the total number of questions asked in the game."""
        if not self.game_state:
            return 0
        return self.game_state.total_questions
    
    def get_turn_order(self) -> List[str]:
        """Get the current turn order."""
        if not self.game_state:
            return []
        return self.game_state.turn_order.copy()
    
    def is_turn_expired(self) -> bool:
        """Check if the current turn has expired."""
        try:
            if not self.game_state or not self.game_state.current_turn_info.turn_timeout:
                return False
            
            return datetime.now() > self.game_state.current_turn_info.turn_timeout
            
        except Exception as e:
            logger.error(f"Error checking turn expiration: {e}")
            return False
    
    def get_turn_time_remaining(self) -> Optional[int]:
        """Get remaining time in seconds for the current turn."""
        try:
            if not self.game_state or not self.game_state.current_turn_info.turn_timeout:
                return None
            
            remaining = self.game_state.current_turn_info.turn_timeout - datetime.now()
            remaining_seconds = max(0, int(remaining.total_seconds()))
            
            return remaining_seconds
            
        except Exception as e:
            logger.error(f"Error getting turn time remaining: {e}")
            return None
    
    def get_game_state_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current game state.
        
        Returns:
            Dictionary with game state information
        """
        if not self.game_state:
            return {'error': 'Game state not initialized'}
        
        current_turn = self.game_state.current_turn_info
        
        return {
            'lobby_code': self.game_state.lobby_code,
            'current_player': current_turn.current_player,
            'next_player': current_turn.next_player,
            'turn_number': current_turn.turn_number,
            'round_number': current_turn.round_number,
            'questions_this_round': self.game_state.questions_this_round,
            'max_questions_per_round': self.game_state.max_questions_per_round,
            'total_questions': self.game_state.total_questions,
            'turn_order': self.game_state.turn_order,
            'time_remaining': self.get_turn_time_remaining(),
            'should_vote': self.should_advance_to_voting(),
            'current_question': {
                'asker': current_turn.question_asker,
                'target': current_turn.question_target,
                'question': current_turn.question,
                'answer': current_turn.answer
            }
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the turn manager.
        
        Returns:
            Status information dictionary
        """
        base_status = {
            'lobby_code': self.lobby_code,
            'turn_timeout_seconds': self.turn_timeout_seconds,
            'max_questions_per_round': self.max_questions_per_round,
            'manager_initialized': True,
            'auto_initialization': True,
            'database_integration': True
        }
        
        if self.game_state:
            base_status.update(self.get_game_state_summary())
        
        return base_status