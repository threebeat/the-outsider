"""
Player Hashmap Manager for The Outsider.

Manages a hashmap of players who are not currently in games.
Used for "join random game" functionality.
"""

import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class PlayerInfo:
    """Information about a player in the hashmap."""
    session_id: str
    username: str
    joined_at: datetime
    
class PlayerHashmap:
    """
    Manages players who are not currently in games.
    
    When players leave/finish games, they're added here.
    When they join new games, they're removed.
    Used for random game matching.
    """
    
    def __init__(self):
        """Initialize the player hashmap."""
        self.players: Dict[str, PlayerInfo] = {}  # session_id -> PlayerInfo
        self.usernames: Set[str] = set()  # Track usernames to prevent duplicates
        logger.debug("Player hashmap initialized")
    
    def add_player(self, session_id: str, username: str) -> bool:
        """
        Add a player to the hashmap (they're available for random matching).
        
        Args:
            session_id: Player's session ID
            username: Player's username
            
        Returns:
            True if added successfully, False if already exists
        """
        try:
            if session_id in self.players:
                logger.debug(f"Player {username} already in hashmap")
                return False
            
            # Check for username conflicts
            if username in self.usernames:
                logger.warning(f"Username {username} already exists in hashmap")
                return False
            
            player_info = PlayerInfo(
                session_id=session_id,
                username=username,
                joined_at=datetime.now()
            )
            
            self.players[session_id] = player_info
            self.usernames.add(username)
            
            logger.info(f"Added player {username} to hashmap")
            return True
            
        except Exception as e:
            logger.error(f"Error adding player to hashmap: {e}")
            return False
    
    def remove_player(self, session_id: str) -> bool:
        """
        Remove a player from the hashmap (they joined a game).
        
        Args:
            session_id: Player's session ID
            
        Returns:
            True if removed successfully, False if not found
        """
        try:
            if session_id not in self.players:
                logger.debug(f"Player {session_id} not in hashmap")
                return False
            
            player_info = self.players[session_id]
            del self.players[session_id]
            self.usernames.discard(player_info.username)
            
            logger.info(f"Removed player {player_info.username} from hashmap")
            return True
            
        except Exception as e:
            logger.error(f"Error removing player from hashmap: {e}")
            return False
    
    def get_random_player(self) -> Optional[PlayerInfo]:
        """
        Get a random player for matching.
        
        Returns:
            PlayerInfo if available, None if no players
        """
        try:
            if not self.players:
                return None
            
            import random
            session_id = random.choice(list(self.players.keys()))
            return self.players[session_id]
            
        except Exception as e:
            logger.error(f"Error getting random player: {e}")
            return None
    
    def get_player_count(self) -> int:
        """Get the number of players available for matching."""
        return len(self.players)
    
    def get_all_players(self) -> List[PlayerInfo]:
        """Get all players in the hashmap."""
        return list(self.players.values())
    
    def is_player_available(self, session_id: str) -> bool:
        """Check if a player is in the hashmap (available for matching)."""
        return session_id in self.players
    
    def cleanup_old_players(self, hours_old: int = 2) -> int:
        """
        Remove players who have been in the hashmap too long.
        
        Args:
            hours_old: Hours after which to remove players
            
        Returns:
            Number of players removed
        """
        try:
            from datetime import timedelta
            
            cutoff_time = datetime.now() - timedelta(hours=hours_old)
            to_remove = []
            
            for session_id, player_info in self.players.items():
                if player_info.joined_at < cutoff_time:
                    to_remove.append(session_id)
            
            removed_count = 0
            for session_id in to_remove:
                if self.remove_player(session_id):
                    removed_count += 1
            
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old players from hashmap")
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Error cleaning up hashmap: {e}")
            return 0
    
    def get_status(self) -> dict:
        """Get current status of the player hashmap."""
        return {
            'total_players': len(self.players),
            'usernames_tracked': len(self.usernames),
            'hashmap_initialized': True
        }

# Global instance for the application
player_hashmap = PlayerHashmap()