"""
Lobby Creator for The Outsider.

Handles lobby creation, validation, and code generation.
Contains no game logic or player management - purely lobby creation.
"""

import random
import string
import logging
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from dataclasses import dataclass

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
                if code not in self.used_codes:
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
            
            # Check if code is already in use
            if code in self.used_codes:
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
            return code.upper() not in self.used_codes
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
    
    def create_lobby_data(self, 
                         name: str, 
                         creator_username: str,
                         lobby_code: str,
                         config: LobbyConfiguration) -> Dict[str, Any]:
        """
        Create initial lobby data structure.
        
        Args:
            name: Lobby name
            creator_username: Username of lobby creator
            lobby_code: Generated lobby code
            config: Lobby configuration
            
        Returns:
            Initial lobby data dictionary
        """
        try:
            lobby_data = {
                'code': lobby_code,
                'name': name.strip(),
                'creator': creator_username,
                'created_at': datetime.now().isoformat(),
                'status': 'waiting',  # waiting, in_game, finished
                'players': [],
                'max_players': config.max_players,
                'min_players': config.min_players,
                'allow_ai_players': config.allow_ai_players,
                'max_ai_players': config.max_ai_players,
                'current_player_count': 0,
                'current_ai_count': 0,
                'game_settings': {
                    'questions_per_round': config.questions_per_round,
                    'voting_timeout_seconds': config.voting_timeout_seconds,
                    'turn_timeout_seconds': config.turn_timeout_seconds,
                    'lobby_timeout_minutes': config.lobby_timeout_minutes,
                    'game_timeout_minutes': config.game_timeout_minutes
                },
                'last_activity': datetime.now().isoformat()
            }
            
            logger.info(f"Created lobby data: {lobby_code} - {name}")
            return lobby_data
            
        except Exception as e:
            logger.error(f"Error creating lobby data: {e}")
            return {}
    
    def generate_ai_player_names(self, count: int, exclude_names: Optional[list] = None) -> list:
        """
        Generate AI player names for the lobby.
        
        Args:
            count: Number of AI names to generate
            exclude_names: Names to exclude (already taken)
            
        Returns:
            List of AI player names
        """
        try:
            # Import AI name generator
            try:
                from ai import NameGenerator
                
                name_gen = NameGenerator()
                ai_names = name_gen.get_random_names(count, exclude_names or [])
                
                logger.debug(f"Generated {len(ai_names)} AI names")
                return ai_names
                
            except ImportError:
                logger.warning("AI name generator not available, using fallback")
                return self._get_fallback_ai_names(count, exclude_names or [])
                
        except Exception as e:
            logger.error(f"Error generating AI names: {e}")
            return []
    
    def _get_fallback_ai_names(self, count: int, exclude_names: list) -> list:
        """Get fallback AI names when AI system unavailable."""
        fallback_names = [
            'Alex', 'Blake', 'Casey', 'Drew', 'Ellis', 'Finley', 'Gray', 'Harper',
            'Indigo', 'Jules', 'Kai', 'Lane', 'Morgan', 'Nova', 'Ocean', 'Parker',
            'Quinn', 'River', 'Sage', 'Taylor', 'Unity', 'Vale', 'Winter', 'Zara'
        ]
        
        exclude_lower = [name.lower() for name in exclude_names]
        available = [name for name in fallback_names if name.lower() not in exclude_lower]
        
        return available[:count]
    
    def get_creator_status(self) -> Dict[str, Any]:
        """
        Get current status of the lobby creator.
        
        Returns:
            Status information dictionary
        """
        return {
            'code_length': self.code_length,
            'codes_in_use': len(self.used_codes),
            'creator_initialized': True
        }