"""
Game Creator Module for The Outsider.

Handles the creation of games within lobbies, including AI player population
and game preparation. Every game starts with 1-3 AI players automatically.
Uses Redis cache only, never touches database.
"""

import logging
import random
from typing import Optional, List, Any, Tuple

# Import cache operations only
from cache import (
    get_lobby_by_code, get_players_in_lobby, get_ai_players_in_lobby,
    add_player_to_lobby, create_game, get_game_by_lobby,
    PlayerCache, GameCache
)
from utils.helpers import get_random_available_name
from utils.constants import LOCATIONS, AI_PERSONALITIES

logger = logging.getLogger(__name__)

class GameCreator:
    """
    Handles game creation and AI player population.
    Uses Redis cache only.
    """
    
    def __init__(self):
        """Initialize the GameCreator."""
        pass
    
    def create_game_with_ai(self, lobby_code: str, 
                           min_ai_players: int = 1, 
                           max_ai_players: int = 3) -> Tuple[bool, str]:
        """
        Create a game in a lobby and populate it with AI players.
        
        Args:
            lobby_code: Code of the lobby to populate with AI players
            min_ai_players: Minimum number of AI players to add
            max_ai_players: Maximum number of AI players to add
            
        Returns:
            Tuple of (success, message)
        """
        try:
            lobby = get_lobby_by_code(lobby_code)
            if not lobby:
                logger.error(f"Lobby {lobby_code} not found")
                return False, f"Lobby {lobby_code} not found"
            
            # Check how many AI players already exist
            existing_ai = get_ai_players_in_lobby(lobby_code)
            existing_ai_count = len(existing_ai)
            
            # Determine how many AI players to add
            if existing_ai_count >= min_ai_players:
                logger.info(f"Lobby {lobby_code} already has {existing_ai_count} AI players, no need to add more")
                return True, f"Lobby already has {existing_ai_count} AI players"
            
            # Calculate number of AI players to add
            ai_players_needed = random.randint(min_ai_players, max_ai_players) - existing_ai_count
            ai_players_needed = max(0, ai_players_needed)  # Ensure non-negative
            
            if ai_players_needed > 0:
                added_players = self._add_ai_players(lobby_code, ai_players_needed)
                logger.info(f"Added {len(added_players)} AI players to lobby {lobby_code}")
                return True, f"Added {len(added_players)} AI players"
            else:
                return True, "No AI players needed"
            
        except Exception as e:
            logger.error(f"Error creating game for lobby {lobby_code}: {e}")
            return False, f"Error creating game: {str(e)}"
    
    def prepare_game_start(self, lobby_code: str, location: Optional[str] = None) -> Tuple[bool, str]:
        """
        Prepare a game to start by ensuring AI players and setting location.
        
        Args:
            lobby_code: Code of the lobby
            location: Optional specific location (random if not provided)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Ensure AI players exist
            ai_success, ai_message = self.create_game_with_ai(lobby_code)
            if not ai_success:
                return False, f"Failed to create AI players: {ai_message}"
            
            # Select location if not provided
            if not location:
                location = random.choice(LOCATIONS)
            
            # Get all players for game creation
            all_players = get_players_in_lobby(lobby_code)
            ai_players = get_ai_players_in_lobby(lobby_code)
            human_players = [p for p in all_players if not p.is_ai and not p.is_spectator]
            
            # Create game session in cache
            game = GameCache(
                lobby_code=lobby_code,
                session_number=1,  # This could be incremented if needed
                location=location,
                total_players=len(all_players),
                human_players=len(human_players),
                ai_players=len(ai_players)
            )
            
            game_success = create_game(game)
            if not game_success:
                logger.error(f"Failed to create game session for lobby {lobby_code}")
                return False, "Failed to create game session"
            
            logger.info(f"Game prepared for lobby {lobby_code} with location '{location}'")
            return True, f"Game prepared with location '{location}'"
            
        except Exception as e:
            logger.error(f"Error preparing game for lobby {lobby_code}: {e}")
            return False, f"Error preparing game: {str(e)}"
    
    def validate_game_ready(self, lobby_code: str) -> bool:
        """
        Validate that a game is ready to start.
        
        Args:
            lobby_code: Code of the lobby to validate
            
        Returns:
            True if game is ready, False otherwise
        """
        try:
            lobby = get_lobby_by_code(lobby_code)
            if not lobby:
                logger.error(f"Lobby {lobby_code} not found")
                return False
            
            # Check for AI players (who are automatically outsiders)
            ai_players = get_ai_players_in_lobby(lobby_code)
            if not ai_players:
                logger.warning(f"No AI players in lobby {lobby_code} - game not ready")
                return False
            
            # Check total player count
            all_players = get_players_in_lobby(lobby_code)
            connected_players = [p for p in all_players if p.is_connected and not p.is_spectator]
            
            if len(connected_players) < 2:
                logger.warning(f"Not enough players in lobby {lobby_code} ({len(connected_players)}) - need at least 2")
                return False
            
            logger.debug(f"Game ready for lobby {lobby_code}: {len(connected_players)} players, {len(ai_players)} AI")
            return True
            
        except Exception as e:
            logger.error(f"Error validating game readiness for lobby {lobby_code}: {e}")
            return False
    
    def _add_ai_players(self, lobby_code: str, count: int) -> List[PlayerCache]:
        """
        Add AI players to a lobby.
        
        Args:
            lobby_code: Code of the lobby
            count: Number of AI players to add
            
        Returns:
            List of created AI players
        """
        created_players = []
        
        try:
            for i in range(count):
                # Generate unique AI name
                name = self._generate_unique_ai_name(lobby_code)
                personality = random.choice(AI_PERSONALITIES)
                
                # Create AI player cache object
                ai_player = PlayerCache(
                    session_id=f"ai_{random.randint(100000, 999999)}",
                    username=name,
                    is_ai=True,
                    ai_personality=personality
                )
                
                # Add to lobby
                success = add_player_to_lobby(lobby_code, ai_player)
                
                if success:
                    created_players.append(ai_player)
                    logger.info(f"Created AI player '{name}' with personality '{personality}'")
                else:
                    logger.error(f"Failed to create AI player for lobby {lobby_code}")
            
        except Exception as e:
            logger.error(f"Error adding AI players to lobby {lobby_code}: {e}")
        
        return created_players
    
    def _generate_unique_ai_name(self, lobby_code: str) -> str:
        """
        Generate a unique AI name for the lobby.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Unique AI name
        """
        existing_players = get_players_in_lobby(lobby_code)
        existing_names = [player.username for player in existing_players if player.is_connected]
        
        # Use name generator to get unique name
        try:
            name = get_random_available_name(existing_names)
            
            if name:
                return name
        except Exception as e:
            logger.warning(f"Error using AI name generator: {e}")
        
        # Fallback: use predefined names
        fallback_names = [
            'Alex', 'Blake', 'Casey', 'Drew', 'Ellis', 'Finley', 'Gray', 'Harper',
            'Indigo', 'Jules', 'Kai', 'Lane', 'Morgan', 'Nova', 'Ocean', 'Parker',
            'Quinn', 'River', 'Sage', 'Taylor', 'Unity', 'Vale', 'Winter', 'Zara'
        ]
        
        available_names = [name for name in fallback_names if name not in existing_names]
        
        if available_names:
            return random.choice(available_names)
        
        # Final fallback: add number suffix
        base_name = "AI"
        counter = 1
        while f"{base_name}_{counter}" in existing_names:
            counter += 1
        
        return f"{base_name}_{counter}"
    
    def get_game_info(self, lobby_code: str) -> dict:
        """
        Get information about the current game state.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Dictionary with game information
        """
        try:
            lobby = get_lobby_by_code(lobby_code)
            if not lobby:
                return {}
            
            all_players = get_players_in_lobby(lobby_code)
            ai_players = get_ai_players_in_lobby(lobby_code)
            human_players = [p for p in all_players if not p.is_ai and not p.is_spectator]
            
            # Get game data if exists
            game = get_game_by_lobby(lobby_code)
            
            return {
                'lobby_code': lobby_code,
                'lobby_name': lobby.name,
                'state': lobby.state,
                'location': lobby.location or (game.location if game else None),
                'total_players': len(all_players),
                'ai_players': len(ai_players),
                'human_players': len(human_players),
                'ready_to_start': self.validate_game_ready(lobby_code),
                'ai_player_names': [p.username for p in ai_players],
                'game_exists': game is not None
            }
            
        except Exception as e:
            logger.error(f"Error getting game info for lobby {lobby_code}: {e}")
            return {}