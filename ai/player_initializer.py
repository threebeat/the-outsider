"""
AI Player Initializer for The Outsider.

Handles the initialization and creation of AI players for lobbies.
Uses the shared helper function for consistent name generation.
"""

import logging
import random
from typing import List, Tuple, Optional

from cache import PlayerCache, add_player_to_lobby, get_players_in_lobby
from utils.helpers import get_random_available_name
from utils.constants import AI_PERSONALITIES

logger = logging.getLogger(__name__)

class AIPlayerInitializer:
    """
    Handles initialization of AI players for game lobbies.
    
    Uses the shared helper function for name generation to ensure
    consistency with the login page random name functionality.
    """
    
    def __init__(self):
        """Initialize the AI player initializer."""
        pass
    
    def initialize_ai_players(self, lobby_code: str, 
                            min_ai_players: int = 1, 
                            max_ai_players: int = 3) -> Tuple[bool, str, List[PlayerCache]]:
        """
        Initialize AI players for a lobby.
        
        Args:
            lobby_code: Code of the lobby to add AI players to
            min_ai_players: Minimum number of AI players to create
            max_ai_players: Maximum number of AI players to create
            
        Returns:
            Tuple of (success, message, list_of_created_players)
        """
        try:
            # Determine how many AI players to create (1-3)
            ai_count = random.randint(min_ai_players, max_ai_players)
            
            logger.info(f"Initializing {ai_count} AI players for lobby {lobby_code}")
            
            # Create the AI players
            created_players = []
            for i in range(ai_count):
                ai_player = self._create_single_ai_player(lobby_code)
                if ai_player:
                    created_players.append(ai_player)
                else:
                    logger.warning(f"Failed to create AI player {i+1} for lobby {lobby_code}")
            
            if created_players:
                success_count = len(created_players)
                logger.info(f"Successfully created {success_count} AI players for lobby {lobby_code}")
                return True, f"Created {success_count} AI players", created_players
            else:
                logger.error(f"Failed to create any AI players for lobby {lobby_code}")
                return False, "Failed to create AI players", []
                
        except Exception as e:
            logger.error(f"Error initializing AI players for lobby {lobby_code}: {e}")
            return False, f"Error initializing AI players: {str(e)}", []
    
    def add_single_ai_player(self, lobby_code: str) -> Tuple[bool, str, Optional[PlayerCache]]:
        """
        Add a single AI player to a lobby.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Tuple of (success, message, created_player)
        """
        try:
            ai_player = self._create_single_ai_player(lobby_code)
            
            if ai_player:
                logger.info(f"Added single AI player '{ai_player.username}' to lobby {lobby_code}")
                return True, f"Added AI player '{ai_player.username}'", ai_player
            else:
                return False, "Failed to create AI player", None
                
        except Exception as e:
            logger.error(f"Error adding single AI player to lobby {lobby_code}: {e}")
            return False, f"Error adding AI player: {str(e)}", None
    
    def _create_single_ai_player(self, lobby_code: str) -> Optional[PlayerCache]:
        """
        Create a single AI player for the lobby.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Created AI player or None if failed
        """
        try:
            # Get a random available name using the shared helper function
            ai_name = get_random_available_name(lobby_code=lobby_code)
            
            if not ai_name:
                logger.warning(f"No available names for AI player in lobby {lobby_code}")
                # Try to generate a fallback name with number suffix
                ai_name = self._generate_fallback_name(lobby_code)
            
            if not ai_name:
                logger.error(f"Could not generate any name for AI player in lobby {lobby_code}")
                return None
            
            # Select random AI personality
            personality = random.choice(AI_PERSONALITIES)
            
            # Generate unique session ID for AI
            session_id = f"ai_{random.randint(100000, 999999)}_{lobby_code}"
            
            # Create AI player cache object
            ai_player = PlayerCache(
                session_id=session_id,
                username=ai_name,
                is_ai=True,
                is_spectator=False,
                is_connected=True,
                ai_personality=personality
            )
            
            # Add AI player to lobby cache
            success = add_player_to_lobby(lobby_code, ai_player)
            
            if success:
                logger.info(f"Created AI player '{ai_name}' with personality '{personality}' for lobby {lobby_code}")
                return ai_player
            else:
                logger.error(f"Failed to add AI player '{ai_name}' to lobby {lobby_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating single AI player for lobby {lobby_code}: {e}")
            return None
    
    def _generate_fallback_name(self, lobby_code: str) -> Optional[str]:
        """
        Generate a fallback name when all predefined names are taken.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Fallback name or None if all attempts fail
        """
        try:
            # Get existing players to avoid conflicts
            existing_players = get_players_in_lobby(lobby_code)
            existing_names = [player.username.lower() for player in existing_players]
            
            # Try AI with number suffix
            base_name = "AI"
            counter = 1
            max_attempts = 100
            
            while counter <= max_attempts:
                candidate_name = f"{base_name}_{counter}"
                if candidate_name.lower() not in existing_names:
                    return candidate_name
                counter += 1
            
            # If all numbered AI names are taken, try Bot with number suffix
            base_name = "Bot"
            counter = 1
            
            while counter <= max_attempts:
                candidate_name = f"{base_name}_{counter}"
                if candidate_name.lower() not in existing_names:
                    return candidate_name
                counter += 1
            
            logger.error(f"Could not generate fallback name for lobby {lobby_code} after {max_attempts * 2} attempts")
            return None
            
        except Exception as e:
            logger.error(f"Error generating fallback name for lobby {lobby_code}: {e}")
            return None
    
    def validate_ai_players(self, lobby_code: str) -> Tuple[bool, str, dict]:
        """
        Validate the AI players in a lobby.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Tuple of (is_valid, message, validation_info)
        """
        try:
            from cache import get_ai_players_in_lobby
            
            ai_players = get_ai_players_in_lobby(lobby_code)
            
            validation_info = {
                'ai_count': len(ai_players),
                'ai_names': [player.username for player in ai_players],
                'ai_personalities': [player.ai_personality for player in ai_players],
                'has_minimum': len(ai_players) >= 1,
                'within_maximum': len(ai_players) <= 3
            }
            
            if len(ai_players) == 0:
                return False, "No AI players found in lobby", validation_info
            elif len(ai_players) > 3:
                return False, f"Too many AI players ({len(ai_players)}) - maximum is 3", validation_info
            else:
                return True, f"AI players valid ({len(ai_players)} players)", validation_info
                
        except Exception as e:
            logger.error(f"Error validating AI players for lobby {lobby_code}: {e}")
            return False, f"Error validating AI players: {str(e)}", {}
    
    def get_ai_status(self, lobby_code: str) -> dict:
        """
        Get status information about AI players in a lobby.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Status information dictionary
        """
        try:
            is_valid, message, validation_info = self.validate_ai_players(lobby_code)
            
            return {
                'lobby_code': lobby_code,
                'is_valid': is_valid,
                'message': message,
                'ai_count': validation_info.get('ai_count', 0),
                'ai_names': validation_info.get('ai_names', []),
                'ai_personalities': validation_info.get('ai_personalities', []),
                'initialized': validation_info.get('ai_count', 0) > 0
            }
            
        except Exception as e:
            logger.error(f"Error getting AI status for lobby {lobby_code}: {e}")
            return {
                'lobby_code': lobby_code,
                'is_valid': False,
                'message': f"Error getting AI status: {str(e)}",
                'ai_count': 0,
                'ai_names': [],
                'ai_personalities': [],
                'initialized': False
            }

# Global instance for easy import
ai_player_initializer = AIPlayerInitializer()