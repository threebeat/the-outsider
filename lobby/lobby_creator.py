"""
Lobby Creator for The Outsider.

Handles lobby creation, validation, and code generation.
Contains no game logic or player management - purely lobby creation.
Uses Redis cache only, never touches database.
"""

import random
import string
import logging
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from dataclasses import dataclass

# Import cache operations only
from cache import (
    create_lobby, lobby_exists, get_lobby_by_code,
    LobbyCache, PlayerCache
)
from ai.player_initializer import ai_player_initializer
from utils.constants import LOBBY_STATES

logger = logging.getLogger(__name__)

@dataclass
class LobbyConfiguration:
    """Configuration settings for a lobby."""
    max_players: int = 8
    min_players: int = 3
    allow_ai_players: bool = True
    max_ai_players: int = 4
    lobby_timeout_minutes: int = 60
    game_timeout_minutes: int = 30
    questions_per_round: int = 3
    voting_timeout_seconds: int = 120
    turn_timeout_seconds: int = 60

class LobbyCreator:
    """
    Handles lobby creation and code generation.
    
    Manages lobby code generation, validation, and basic lobby setup.
    Contains no player management or game logic.
    Uses Redis cache only.
    """
    
    def __init__(self, code_length: int = 6):
        """
        Initialize lobby creator.
        
        Args:
            code_length: Length of generated lobby codes
        """
        self.code_length = code_length
        self.used_codes = set()  # Track used codes to avoid duplicates
        logger.debug("Lobby creator initialized")
    
    def generate_lobby_code(self, custom_code: Optional[str] = None) -> str:
        """
        Generate a unique lobby code.
        
        Args:
            custom_code: Optional custom code to use
            
        Returns:
            Generated or validated lobby code
        """
        try:
            if custom_code:
                # Validate and use custom code
                validated_code = self._validate_custom_code(custom_code)
                if validated_code:
                    self.used_codes.add(validated_code)
                    logger.info(f"Using custom lobby code: {validated_code}")
                    return validated_code
                else:
                    logger.warning(f"Invalid custom code: {custom_code}, generating random code")
            
            # Generate random code
            attempts = 0
            max_attempts = 100
            
            while attempts < max_attempts:
                code = self._generate_random_code()
                if code not in self.used_codes and not lobby_exists(code):
                    self.used_codes.add(code)
                    logger.debug(f"Generated lobby code: {code}")
                    return code
                attempts += 1
            
            # Fallback if all attempts failed
            timestamp_suffix = str(int(datetime.now().timestamp()))[-4:]
            fallback_code = f"GAME{timestamp_suffix}"
            self.used_codes.add(fallback_code)
            logger.warning(f"Used fallback lobby code: {fallback_code}")
            return fallback_code
            
        except Exception as e:
            logger.error(f"Error generating lobby code: {e}")
            return "ERROR"
    
    def validate_lobby_name(self, name: str) -> Tuple[bool, str]:
        """
        Validate a lobby name.
        
        Args:
            name: Proposed lobby name
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check for empty name
            if not name or not name.strip():
                return False, "Lobby name cannot be empty"
            
            # Check length
            if len(name.strip()) < 2:
                return False, "Lobby name must be at least 2 characters"
            
            if len(name.strip()) > 50:
                return False, "Lobby name must be 50 characters or less"
            
            # Check for inappropriate content (basic filter)
            inappropriate_words = ['fuck', 'shit', 'damn']  # Basic example
            name_lower = name.lower()
            for word in inappropriate_words:
                if word in name_lower:
                    return False, "Lobby name contains inappropriate content"
            
            # Check for special characters that might cause issues
            allowed_chars = set(string.ascii_letters + string.digits + ' -_()[]{}')
            if not all(c in allowed_chars for c in name):
                return False, "Lobby name contains invalid characters"
            
            return True, "Lobby name is valid"
            
        except Exception as e:
            logger.error(f"Error validating lobby name: {e}")
            return False, "Lobby name validation failed"
    
    def create_lobby_config(self, 
                          custom_settings: Optional[Dict[str, Any]] = None) -> LobbyConfiguration:
        """
        Create lobby configuration with optional custom settings.
        
        Args:
            custom_settings: Optional dictionary of custom settings
            
        Returns:
            LobbyConfiguration object
        """
        try:
            config = LobbyConfiguration()
            
            if custom_settings:
                # Apply custom settings with validation
                if 'max_players' in custom_settings:
                    max_players = custom_settings['max_players']
                    if isinstance(max_players, int) and 3 <= max_players <= 12:
                        config.max_players = max_players
                
                if 'min_players' in custom_settings:
                    min_players = custom_settings['min_players']
                    if isinstance(min_players, int) and 2 <= min_players <= config.max_players:
                        config.min_players = min_players
                
                if 'allow_ai_players' in custom_settings:
                    config.allow_ai_players = bool(custom_settings['allow_ai_players'])
                
                if 'max_ai_players' in custom_settings:
                    max_ai = custom_settings['max_ai_players']
                    if isinstance(max_ai, int) and 0 <= max_ai <= config.max_players:
                        config.max_ai_players = max_ai
                
                if 'questions_per_round' in custom_settings:
                    questions = custom_settings['questions_per_round']
                    if isinstance(questions, int) and 1 <= questions <= 10:
                        config.questions_per_round = questions
                
                if 'voting_timeout_seconds' in custom_settings:
                    timeout = custom_settings['voting_timeout_seconds']
                    if isinstance(timeout, int) and 30 <= timeout <= 300:
                        config.voting_timeout_seconds = timeout
                
                if 'turn_timeout_seconds' in custom_settings:
                    timeout = custom_settings['turn_timeout_seconds']
                    if isinstance(timeout, int) and 30 <= timeout <= 180:
                        config.turn_timeout_seconds = timeout
            
            logger.debug(f"Created lobby config: max_players={config.max_players}, allow_ai={config.allow_ai_players}")
            return config
            
        except Exception as e:
            logger.error(f"Error creating lobby config: {e}")
            return LobbyConfiguration()  # Return default config
    
    def validate_lobby_code(self, code: str) -> Tuple[bool, str]:
        """
        Validate a lobby code format.
        
        Args:
            code: Lobby code to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check for empty code
            if not code or not code.strip():
                return False, "Lobby code cannot be empty"
            
            code = code.strip().upper()
            
            # Check length
            if len(code) < 4 or len(code) > 10:
                return False, "Lobby code must be 4-10 characters"
            
            # Check for valid characters (alphanumeric only)
            if not code.isalnum():
                return False, "Lobby code must contain only letters and numbers"
            
            # Check if code is already in use (check cache)
            if code in self.used_codes or lobby_exists(code):
                return False, "Lobby code is already in use"
            
            return True, "Lobby code is valid"
            
        except Exception as e:
            logger.error(f"Error validating lobby code: {e}")
            return False, "Lobby code validation failed"
    
    def release_lobby_code(self, code: str) -> bool:
        """
        Release a lobby code back to the available pool.
        
        Args:
            code: Lobby code to release
            
        Returns:
            True if released successfully, False otherwise
        """
        try:
            if code in self.used_codes:
                self.used_codes.remove(code)
                logger.debug(f"Released lobby code: {code}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error releasing lobby code: {e}")
            return False
    
    def is_code_available(self, code: str) -> bool:
        """
        Check if a lobby code is available for use.
        
        Args:
            code: Lobby code to check
            
        Returns:
            True if available, False if in use
        """
        try:
            return code.upper() not in self.used_codes and not lobby_exists(code.upper())
        except Exception as e:
            logger.error(f"Error checking code availability: {e}")
            return False
    
    def _generate_random_code(self) -> str:
        """Generate a random lobby code."""
        try:
            # Use mix of letters and numbers for better readability
            # Exclude easily confused characters: 0, O, I, 1
            chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
            code = ''.join(random.choices(chars, k=self.code_length))
            return code
            
        except Exception as e:
            logger.error(f"Error generating random code: {e}")
            return "RANDOM"
    
    def _validate_custom_code(self, custom_code: str) -> Optional[str]:
        """
        Validate and normalize a custom lobby code.
        
        Args:
            custom_code: Custom code to validate
            
        Returns:
            Normalized code if valid, None otherwise
        """
        try:
            is_valid, _ = self.validate_lobby_code(custom_code)
            if is_valid:
                return custom_code.strip().upper()
            return None
            
        except Exception as e:
            logger.error(f"Error validating custom code: {e}")
            return None
    
    def create_default_lobby(self) -> Tuple[bool, str, Optional[str]]:
        """
        Create a default lobby for initial setup.
        
        This method is called during initialization to ensure
        there's always at least one lobby available.
        
        Returns:
            tuple: (success, message, lobby_code)
        """
        try:
            # Generate lobby code
            lobby_code = self.generate_lobby_code("MAIN")
            if lobby_code == "ERROR":
                lobby_code = "MAIN01"  # Fallback
            
            # Validate lobby name
            lobby_name = "Main Lobby"
            is_valid, error_msg = self.validate_lobby_name(lobby_name)
            if not is_valid:
                logger.warning(f"Default lobby name validation failed: {error_msg}")
                lobby_name = "Default Game"
            
            # Create the lobby in cache
            success = create_lobby(lobby_code, lobby_name)
            
            if success:
                # Initialize AI players for the new lobby
                ai_success, ai_message, ai_players = ai_player_initializer.initialize_ai_players(lobby_code)
                
                if ai_success:
                    logger.info(f"Created default lobby '{lobby_name}' with code '{lobby_code}' - {ai_message}")
                    return True, f"Default lobby created successfully - {ai_message}", lobby_code
                else:
                    logger.warning(f"Created default lobby but failed to add AI players: {ai_message}")
                    return True, "Default lobby created (without AI players)", lobby_code
            else:
                logger.error(f"Failed to create default lobby in cache")
                return False, "Failed to create default lobby", None
                    
        except Exception as e:
            logger.error(f"Error creating default lobby: {e}")
            return False, f"Failed to create default lobby: {str(e)}", None
    
    def create_lobby(self, name: str, creator_username: str = None, 
                    custom_code: Optional[str] = None,
                    custom_settings: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, Optional[str]]:
        """
        Create a new lobby with automatic AI player population.
        
        This is the main method for creating lobbies. It automatically
        calls AI player initializer to populate 1-3 AI players.
        
        Args:
            name: Lobby name
            creator_username: Username of the creator (optional)
            custom_code: Optional custom lobby code
            custom_settings: Optional custom settings
            
        Returns:
            tuple: (success, message, lobby_code)
        """
        try:
            # Validate lobby name
            is_valid, error_msg = self.validate_lobby_name(name)
            if not is_valid:
                return False, error_msg, None
            
            # Generate or validate lobby code
            lobby_code = self.generate_lobby_code(custom_code)
            if lobby_code == "ERROR":
                return False, "Failed to generate lobby code", None
            
            # Create lobby in cache
            success = create_lobby(lobby_code, name)
            
            if success:
                # Initialize AI players for the new lobby
                ai_success, ai_message, ai_players = ai_player_initializer.initialize_ai_players(lobby_code)
                
                if ai_success:
                    logger.info(f"Created lobby '{name}' with code '{lobby_code}' - {ai_message}")
                    return True, f"Lobby created successfully - {ai_message}", lobby_code
                else:
                    logger.warning(f"Created lobby '{name}' but failed to add AI players: {ai_message}")
                    return True, f"Lobby created (without AI players) - {ai_message}", lobby_code
            else:
                return False, "Failed to create lobby in cache", None
                
        except Exception as e:
            logger.error(f"Error creating lobby: {e}")
            return False, f"Failed to create lobby: {str(e)}", None
    
    def get_lobby_info(self, lobby_code: str) -> dict:
        """
        Get information about a lobby.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Dictionary with lobby information
        """
        try:
            lobby = get_lobby_by_code(lobby_code)
            
            if not lobby:
                return {'exists': False, 'lobby_code': lobby_code}
            
            # Get AI status from AI player initializer
            ai_status = ai_player_initializer.get_ai_status(lobby_code)
            
            return {
                'exists': True,
                'lobby_code': lobby_code,
                'name': lobby.name,
                'state': lobby.state,
                'created_at': lobby.created_at,
                'ai_status': ai_status
            }
            
        except Exception as e:
            logger.error(f"Error getting lobby info for {lobby_code}: {e}")
            return {'exists': False, 'lobby_code': lobby_code, 'error': str(e)}
    
    def prepare_lobby_for_game(self, lobby_code: str) -> Tuple[bool, str]:
        """
        Prepare a lobby for game start by ensuring it has proper AI players.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Tuple of (success, message)
        """
        try:
            lobby = get_lobby_by_code(lobby_code)
            if not lobby:
                return False, f"Lobby {lobby_code} not found"
            
            # Validate AI players are present and ready
            is_valid, message, validation_info = ai_player_initializer.validate_ai_players(lobby_code)
            
            if not is_valid:
                # Try to add AI players if missing
                logger.info(f"AI players not valid for lobby {lobby_code}, attempting to add them")
                ai_success, ai_message, ai_players = ai_player_initializer.initialize_ai_players(lobby_code)
                
                if ai_success:
                    return True, f"Lobby prepared with {len(ai_players)} AI players"
                else:
                    return False, f"Failed to prepare lobby: {ai_message}"
            else:
                ai_count = validation_info.get('ai_count', 0)
                return True, f"Lobby ready with {ai_count} AI players"
            
        except Exception as e:
            logger.error(f"Error preparing lobby {lobby_code} for game: {e}")
            return False, f"Error preparing lobby: {str(e)}"
    
    def get_creator_status(self) -> Dict[str, Any]:
        """
        Get status information about the lobby creator.
        
        Returns:
            Status dictionary
        """
        try:
            # Import cache stats
            from cache import get_cache_stats
            
            cache_stats = get_cache_stats()
            
            return {
                'active': True,
                'codes_in_use': len(self.used_codes),
                'cache_connected': cache_stats.get('connected', False),
                'total_lobbies': cache_stats.get('total_lobbies', 0),
                'code_length': self.code_length
            }
            
        except Exception as e:
            logger.error(f"Error getting creator status: {e}")
            return {
                'active': False,
                'error': str(e)
            }

# Global instance for easy import
lobby_creator = LobbyCreator()