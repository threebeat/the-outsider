"""
Game Creator Module for The Outsider.

Handles the creation of games within lobbies, including AI player population
and game preparation. Every game starts with 1-3 AI players automatically.
"""

import logging
import random
from typing import Optional, List, Any

from database_getters import (
    get_lobby_by_id, get_players, get_ai_players_in_lobby, get_human_players_in_lobby
)
from database_setters import create_player, create_game_session
from ai.name_generator import NameGenerator
from utils.constants import LOCATIONS, AI_PERSONALITIES

logger = logging.getLogger(__name__)

class GameCreator:
    """Handles game creation and AI player population."""
    
    def __init__(self):
        """Initialize the GameCreator."""
        pass
    
    def create_game_with_ai(self, lobby_id: int, 
                           min_ai_players: int = 1, 
                           max_ai_players: int = 3) -> bool:
        """
        Create a game in a lobby and populate it with AI players.
        
        Args:
            lobby_id: ID of the lobby to populate with AI players
            min_ai_players: Minimum number of AI players to add
            max_ai_players: Maximum number of AI players to add
            
        Returns:
            True if game was created successfully, False otherwise
        """
        try:
            lobby = get_lobby_by_id(lobby_id)
            if not lobby:
                logger.error(f"Lobby {lobby_id} not found")
                return False
            
            # Check how many AI players already exist
            existing_ai = get_ai_players_in_lobby(lobby_id)
            existing_ai_count = len(existing_ai)
            
            # Determine how many AI players to add
            if existing_ai_count >= min_ai_players:
                logger.info(f"Lobby {lobby_id} already has {existing_ai_count} AI players, no need to add more")
                return True
            
            # Calculate number of AI players to add
            ai_players_needed = random.randint(min_ai_players, max_ai_players) - existing_ai_count
            ai_players_needed = max(0, ai_players_needed)  # Ensure non-negative
            
            if ai_players_needed > 0:
                added_players = self._add_ai_players(lobby_id, ai_players_needed)
                logger.info(f"Added {len(added_players)} AI players to lobby {lobby_id}")
            
            logger.info(f"Game creation completed for lobby {lobby_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating game for lobby {lobby_id}: {e}")
            return False
    
    def prepare_game_start(self, lobby_id: int, location: Optional[str] = None) -> bool:
        """
        Prepare a game to start by ensuring AI players and setting location.
        
        Args:
            lobby_id: ID of the lobby
            location: Optional specific location (random if not provided)
            
        Returns:
            True if preparation successful, False otherwise
        """
        try:
            # Ensure AI players exist
            if not self.create_game_with_ai(lobby_id):
                return False
            
            # Select location if not provided
            if not location:
                location = random.choice(LOCATIONS)
            
            # Create game session
            game_session = create_game_session(lobby_id, location)
            if not game_session:
                logger.error(f"Failed to create game session for lobby {lobby_id}")
                return False
            
            logger.info(f"Game prepared for lobby {lobby_id} with location '{location}'")
            return True
            
        except Exception as e:
            logger.error(f"Error preparing game for lobby {lobby_id}: {e}")
            return False
    
    def validate_game_ready(self, lobby_id: int) -> bool:
        """
        Validate that a game is ready to start.
        
        Args:
            lobby_id: ID of the lobby to validate
            
        Returns:
            True if game is ready, False otherwise
        """
        try:
            lobby = get_lobby_by_id(lobby_id)
            if not lobby:
                logger.error(f"Lobby {lobby_id} not found")
                return False
            
            # Check for AI players (who are automatically outsiders)
            ai_players = get_ai_players_in_lobby(lobby_id)
            if not ai_players:
                logger.warning(f"No AI players in lobby {lobby_id} - game not ready")
                return False
            
            # Check total player count
            all_players = get_players(lobby_id=lobby_id, is_connected=True, is_spectator=False)
            if len(all_players) < 2:
                logger.warning(f"Not enough players in lobby {lobby_id} ({len(all_players)}) - need at least 2")
                return False
            
            logger.debug(f"Game ready for lobby {lobby_id}: {len(all_players)} players, {len(ai_players)} AI")
            return True
            
        except Exception as e:
            logger.error(f"Error validating game readiness for lobby {lobby_id}: {e}")
            return False
    
    def _add_ai_players(self, lobby_id: int, count: int) -> List[Any]:
        """
        Add AI players to a lobby.
        
        Args:
            lobby_id: ID of the lobby
            count: Number of AI players to add
            
        Returns:
            List of created AI players
        """
        created_players = []
        
        try:
            for i in range(count):
                # Generate unique AI name
                name = self._generate_unique_ai_name(lobby_id)
                personality = random.choice(AI_PERSONALITIES)
                
                # Create AI player (they are automatically outsiders due to is_ai=True)
                ai_player = create_player(
                    lobby_id=lobby_id,
                    session_id=f"ai_{random.randint(100000, 999999)}",
                    username=name,
                    is_ai=True,
                    ai_personality=personality
                )
                
                if ai_player:
                    created_players.append(ai_player)
                    logger.info(f"Created AI player '{name}' with personality '{personality}'")
                else:
                    logger.error(f"Failed to create AI player for lobby {lobby_id}")
            
        except Exception as e:
            logger.error(f"Error adding AI players to lobby {lobby_id}: {e}")
        
        return created_players
    
    def _generate_unique_ai_name(self, lobby_id: int) -> str:
        """
        Generate a unique AI name for the lobby.
        
        Args:
            lobby_id: ID of the lobby
            
        Returns:
            Unique AI name
        """
        existing_players = get_players(lobby_id=lobby_id, is_connected=True)
        existing_names = [player.username for player in existing_players]
        
        # Use name generator to get unique name
        name_generator = NameGenerator()
        name = name_generator.get_random_name(exclude_names=existing_names)
        
        if name:
            return name
        
        # Fallback: add number suffix to a random name
        available_names = name_generator.get_available_names()
        if available_names:
            base_name = available_names[0]
        else:
            base_name = "AI"
        
        counter = 1
        while f"{base_name}_{counter}" in existing_names:
            counter += 1
        
        return f"{base_name}_{counter}"
    
    def get_game_info(self, lobby_id: int) -> dict:
        """
        Get information about the current game state.
        
        Args:
            lobby_id: ID of the lobby
            
        Returns:
            Dictionary with game information
        """
        try:
            lobby = get_lobby_by_id(lobby_id)
            if not lobby:
                return {}
            
            all_players = get_players(lobby_id=lobby_id, is_connected=True, is_spectator=False)
            ai_players = get_ai_players_in_lobby(lobby_id)
            human_players = get_human_players_in_lobby(lobby_id)
            
            return {
                'lobby_id': lobby_id,
                'lobby_code': lobby.code,
                'state': lobby.state,
                'location': lobby.location,
                'total_players': len(all_players),
                'ai_players': len(ai_players),
                'human_players': len(human_players),
                'ready_to_start': self.validate_game_ready(lobby_id),
                'ai_player_names': [p.username for p in ai_players]
            }
            
        except Exception as e:
            logger.error(f"Error getting game info for lobby {lobby_id}: {e}")
            return {}