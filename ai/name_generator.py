"""
AI Name Generator for The Outsider.

Generates random names for AI players from a predefined list.
Does NOT use OpenAI API - just random selection from constants.
"""

import random
import logging
from typing import List, Optional
from utils.constants import AI_NAMES

logger = logging.getLogger(__name__)

class NameGenerator:
    """
    Generates random names for AI players.
    
    Handles name selection and availability checking without using OpenAI API.
    Pure utility class with no game logic.
    """
    
    def __init__(self):
        """Initialize the name generator."""
        self.available_names = AI_NAMES.copy()
        logger.debug(f"Name generator initialized with {len(self.available_names)} names")
    
    def get_random_name(self, exclude_names: Optional[List[str]] = None) -> Optional[str]:
        """
        Get a random AI name that's not in the exclusion list.
        
        Args:
            exclude_names: List of names to exclude (already taken)
            
        Returns:
            Random available name or None if all names are taken
        """
        try:
            exclude_names = exclude_names or []
            
            # Convert to lowercase for case-insensitive comparison
            exclude_lower = [name.lower() for name in exclude_names]
            
            # Filter available names
            available = [
                name for name in self.available_names 
                if name.lower() not in exclude_lower
            ]
            
            if not available:
                logger.warning("No AI names available - all names are taken")
                return None
            
            selected_name = random.choice(available)
            logger.debug(f"Selected AI name: {selected_name}")
            return selected_name
            
        except Exception as e:
            logger.error(f"Error generating AI name: {e}")
            return None
    
    def get_available_names(self, exclude_names: Optional[List[str]] = None) -> List[str]:
        """
        Get list of all available names.
        
        Args:
            exclude_names: List of names to exclude
            
        Returns:
            List of available names
        """
        try:
            exclude_names = exclude_names or []
            exclude_lower = [name.lower() for name in exclude_names]
            
            available = [
                name for name in self.available_names 
                if name.lower() not in exclude_lower
            ]
            
            return available
            
        except Exception as e:
            logger.error(f"Error getting available names: {e}")
            return []
    
    def is_name_available(self, name: str, exclude_names: Optional[List[str]] = None) -> bool:
        """
        Check if a specific name is available.
        
        Args:
            name: Name to check
            exclude_names: List of names to exclude
            
        Returns:
            True if name is available, False otherwise
        """
        try:
            exclude_names = exclude_names or []
            exclude_lower = [n.lower() for n in exclude_names]
            
            return (
                name.lower() not in exclude_lower and 
                any(ai_name.lower() == name.lower() for ai_name in self.available_names)
            )
            
        except Exception as e:
            logger.error(f"Error checking name availability: {e}")
            return False
    
    def get_names_count(self) -> int:
        """
        Get total number of available AI names.
        
        Returns:
            Total count of AI names
        """
        return len(self.available_names)
    
    def validate_name(self, name: str) -> bool:
        """
        Validate if a name is in the AI names list.
        
        Args:
            name: Name to validate
            
        Returns:
            True if name is valid AI name, False otherwise
        """
        try:
            return any(ai_name.lower() == name.lower() for ai_name in self.available_names)
        except Exception as e:
            logger.error(f"Error validating name: {e}")
            return False
    
    def get_random_names(self, count: int, exclude_names: Optional[List[str]] = None) -> List[str]:
        """
        Get multiple random names.
        
        Args:
            count: Number of names to get
            exclude_names: List of names to exclude
            
        Returns:
            List of random names (may be fewer than requested if not enough available)
        """
        try:
            if count <= 0:
                return []
            
            available = self.get_available_names(exclude_names)
            
            if count >= len(available):
                # Return all available names if requesting more than available
                return available.copy()
            
            # Return random sample of requested size
            return random.sample(available, count)
            
        except Exception as e:
            logger.error(f"Error getting random names: {e}")
            return []
    
    def reset(self):
        """Reset the name generator to initial state."""
        try:
            self.available_names = AI_NAMES.copy()
            logger.debug("Name generator reset")
        except Exception as e:
            logger.error(f"Error resetting name generator: {e}")
    
    def get_status(self) -> dict:
        """
        Get current status of the name generator.
        
        Returns:
            Status information dictionary
        """
        return {
            'total_names': len(AI_NAMES),
            'available_names': len(self.available_names),
            'names_loaded': bool(self.available_names)
        }