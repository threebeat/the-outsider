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
    create_game, get_game_by_lobby,
    PlayerCache, GameCache
)
from ai.player_initializer import ai_player_initializer
from utils.constants import LOCATIONS

logger = logging.getLogger(__name__)

class GameCreator:
    """
    Handles game creation and AI player population.
    Uses Redis cache only and delegates AI player creation to AI module.
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
            
            # Determine if we need to add AI players
            if existing_ai_count >= min_ai_players:
                logger.info(f"Lobby {lobby_code} already has {existing_ai_count} AI players, no need to add more")
                return True, f"Lobby already has {existing_ai_count} AI players"
            
            # Use AI player initializer to create AI players
            success, message, created_players = ai_player_initializer.initialize_ai_players(
                lobby_code, min_ai_players, max_ai_players
            )
            
            if success:
                logger.info(f"Successfully initialized AI players for lobby {lobby_code}: {message}")
                return True, message
            else:
                logger.error(f"Failed to initialize AI players for lobby {lobby_code}: {message}")
                return False, message
            
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
            
            # Use AI player initializer to validate AI players
            is_valid, message, validation_info = ai_player_initializer.validate_ai_players(lobby_code)
            
            if not is_valid:
                logger.warning(f"AI players validation failed for lobby {lobby_code}: {message}")
                return False
            
            # Check total player count
            all_players = get_players_in_lobby(lobby_code)
            connected_players = [p for p in all_players if p.is_connected and not p.is_spectator]
            
            if len(connected_players) < 2:
                logger.warning(f"Not enough players in lobby {lobby_code} ({len(connected_players)}) - need at least 2")
                return False
            
            ai_count = validation_info.get('ai_count', 0)
            logger.debug(f"Game ready for lobby {lobby_code}: {len(connected_players)} players, {ai_count} AI")
            return True
            
        except Exception as e:
            logger.error(f"Error validating game readiness for lobby {lobby_code}: {e}")
            return False
    
    def add_ai_player(self, lobby_code: str) -> Tuple[bool, str, Optional[PlayerCache]]:
        """
        Add a single AI player to a lobby.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Tuple of (success, message, created_player)
        """
        try:
            # Delegate to AI player initializer
            return ai_player_initializer.add_single_ai_player(lobby_code)
            
        except Exception as e:
            logger.error(f"Error adding AI player to lobby {lobby_code}: {e}")
            return False, f"Error adding AI player: {str(e)}", None
    
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
            
            # Get AI status from AI player initializer
            ai_status = ai_player_initializer.get_ai_status(lobby_code)
            
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
                'ai_status': ai_status,
                'game_exists': game is not None
            }
            
        except Exception as e:
            logger.error(f"Error getting game info for lobby {lobby_code}: {e}")
            return {}