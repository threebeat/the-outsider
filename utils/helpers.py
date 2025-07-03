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
    
    # Don't allow usernames that are too similar to AI names
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
    existing_lower = [name.lower() for name in existing_names]
    available_names = [name for name in AI_NAMES if name.lower() not in existing_lower]
    
    if available_names:
        return random.choice(available_names)
    return None

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