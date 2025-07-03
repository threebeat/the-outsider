"""
Helper utilities for The Outsider.

This module contains utility functions used throughout the application
for validation, generation, and data manipulation.
"""

import random
import re
import string
from typing import List, Optional
from .constants import AI_NAMES

def generate_lobby_code(length: int = 6) -> str:
    """Generate a random lobby code."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(characters, k=length))

def get_random_available_name(exclude_names: Optional[List[str]] = None, 
                             lobby_code: Optional[str] = None) -> Optional[str]:
    """
    Get a random available name that's not already taken in the specified lobby.
    
    This function checks both the predefined AI names list and optionally
    checks against players already in a specific lobby.
    
    Args:
        exclude_names: List of names to exclude (already taken)
        lobby_code: Optional lobby code to check for existing players
        
    Returns:
        Random available name or None if all names are taken
    """
    try:
        exclude_names = exclude_names or []
        
        # If lobby_code is provided, get existing players from that lobby
        if lobby_code:
            try:
                from cache import get_players_in_lobby
                existing_players = get_players_in_lobby(lobby_code)
                lobby_names = [player.username for player in existing_players]
                exclude_names = exclude_names + lobby_names
            except ImportError:
                # Cache not available, continue with provided exclude_names only
                pass
            except Exception:
                # Error getting lobby players, continue with provided exclude_names only
                pass
        
        # Convert to lowercase for case-insensitive comparison
        exclude_lower = [name.lower() for name in exclude_names]
        
        # Filter available names from AI_NAMES
        available = [
            name for name in AI_NAMES 
            if name.lower() not in exclude_lower
        ]
        
        if not available:
            return None
        
        return random.choice(available)
        
    except Exception as e:
        # Fallback to a basic random name if anything goes wrong
        fallback_names = ["Alex", "Blake", "Casey", "Drew", "Ellis"]
        exclude_lower = [name.lower() for name in (exclude_names or [])]
        available_fallback = [name for name in fallback_names if name.lower() not in exclude_lower]
        return random.choice(available_fallback) if available_fallback else None

def is_name_available(name: str, exclude_names: Optional[List[str]] = None,
                     lobby_code: Optional[str] = None) -> bool:
    """
    Check if a specific name is available for use.
    
    Args:
        name: Name to check
        exclude_names: List of names to exclude
        lobby_code: Optional lobby code to check for existing players
        
    Returns:
        True if name is available, False otherwise
    """
    try:
        exclude_names = exclude_names or []
        
        # If lobby_code is provided, get existing players from that lobby
        if lobby_code:
            try:
                from cache import get_players_in_lobby
                existing_players = get_players_in_lobby(lobby_code)
                lobby_names = [player.username for player in existing_players]
                exclude_names = exclude_names + lobby_names
            except ImportError:
                # Cache not available, continue with provided exclude_names only
                pass
            except Exception:
                # Error getting lobby players, continue with provided exclude_names only
                pass
        
        # Convert to lowercase for case-insensitive comparison
        exclude_lower = [n.lower() for n in exclude_names]
        
        # Check if name is in exclude list
        if name.lower() in exclude_lower:
            return False
        
        # Name is available if it's not in the exclude list
        return True
        
    except Exception:
        # If anything goes wrong, assume name is not available for safety
        return False

def validate_username(username: str) -> tuple[bool, Optional[str]]:
    """
    Validate a username for the game.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not username:
        return False, "Username cannot be empty"
    
    if len(username) < 2:
        return False, "Username must be at least 2 characters"
    
    if len(username) > 20:
        return False, "Username must be 20 characters or less"
    
    # Allow letters, numbers, spaces, and basic punctuation
    if not re.match(r'^[a-zA-Z0-9\s\-_\.]+$', username):
        return False, "Username contains invalid characters"
    
    # Don't allow usernames that are too similar to AI names (case insensitive)
    username_lower = username.lower()
    for ai_name in AI_NAMES:
        if username_lower == ai_name.lower():
            return False, f"Username too similar to AI name '{ai_name}'"
    
    return True, None

def get_available_ai_name(existing_names: List[str]) -> Optional[str]:
    """
    Get an available AI name that's not already taken.
    
    Args:
        existing_names: List of names already in use
        
    Returns:
        An available AI name or None if all are taken
    """
    return get_random_available_name(exclude_names=existing_names)

def sanitize_message(message: str) -> str:
    """
    Sanitize a chat message to prevent abuse.
    
    Args:
        message: Raw message content
        
    Returns:
        Sanitized message content
    """
    # Remove excessive whitespace
    message = re.sub(r'\s+', ' ', message.strip())
    
    # Limit length
    if len(message) > 500:
        message = message[:500] + "..."
    
    # Remove potential HTML/script content
    message = re.sub(r'<[^>]*>', '', message)
    
    return message

def calculate_vote_winner(votes: dict) -> Optional[str]:
    """
    Calculate the winner of a vote based on vote counts.
    
    Args:
        votes: Dictionary mapping target_username to vote count
        
    Returns:
        Username of the player with the most votes, or None if tied
    """
    if not votes:
        return None
    
    max_votes = max(votes.values())
    winners = [username for username, count in votes.items() if count == max_votes]
    
    # Return None if there's a tie
    if len(winners) > 1:
        return None
        
    return winners[0]

def format_time_duration(seconds: int) -> str:
    """
    Format a duration in seconds to a human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if remaining_seconds == 0:
            return f"{minutes}m"
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        if remaining_minutes == 0:
            return f"{hours}h"
        return f"{hours}h {remaining_minutes}m"

def get_player_display_name(username: str, is_ai: bool) -> str:
    """
    Get the display name for a player, potentially with AI indicator.
    
    Args:
        username: Player's username
        is_ai: Whether the player is AI
        
    Returns:
        Formatted display name
    """
    if is_ai:
        return f"{username} 🤖"
    return username

def shuffle_players(players: List) -> List:
    """
    Shuffle a list of players randomly.
    
    Args:
        players: List of player objects
        
    Returns:
        Shuffled list of players
    """
    shuffled = players.copy()
    random.shuffle(shuffled)
    return shuffled