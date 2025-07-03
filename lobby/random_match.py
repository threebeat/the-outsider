"""
Random Game Matching for The Outsider.

Handles "join random game" functionality using player hashmap and open lobbies.
"""

import logging
from typing import Optional, Tuple
from .player_hashmap import player_hashmap
from database import get_open_lobbies, can_join_lobby
from .manager import LobbyManager

logger = logging.getLogger(__name__)

class RandomMatcher:
    """Handles random game matching for players."""
    
    def __init__(self):
        """Initialize the random matcher."""
        self.lobby_manager = LobbyManager()
        logger.debug("Random matcher initialized")
    
    def join_random_game(self, session_id: str, username: str) -> Tuple[bool, str, Optional[str]]:
        """
        Join a random open game or create a new one if none available.
        
        Args:
            session_id: Player's session ID
            username: Player's username
            
        Returns:
            tuple: (success, message, lobby_code)
        """
        try:
            # Remove player from hashmap since they're trying to join a game
            player_hashmap.remove_player(session_id)
            
            # Try to find an open lobby with space
            open_lobbies = get_open_lobbies()
            available_lobbies = []
            
            for lobby in open_lobbies:
                if can_join_lobby(lobby.id):
                    available_lobbies.append(lobby)
            
            if available_lobbies:
                # Join the first available lobby
                import random
                chosen_lobby = random.choice(available_lobbies)
                
                success, message, player_data = self.lobby_manager.join_lobby(
                    chosen_lobby.code, session_id, username, is_spectator=False
                )
                
                if success:
                    logger.info(f"Player {username} joined random lobby {chosen_lobby.code}")
                    return True, f"Joined lobby {chosen_lobby.code}", chosen_lobby.code
                else:
                    # Join failed, add them back to hashmap
                    player_hashmap.add_player(session_id, username)
                    return False, f"Failed to join lobby: {message}", None
            else:
                # No available lobbies, create a new one
                success, message, lobby_data = self.lobby_manager.create_lobby(
                    f"{username}'s Game", username
                )
                
                if success and lobby_data:
                    # Join the newly created lobby
                    join_success, join_message, player_data = self.lobby_manager.join_lobby(
                        lobby_data.code, session_id, username, is_spectator=False
                    )
                    
                    if join_success:
                        logger.info(f"Created new lobby {lobby_data.code} for player {username}")
                        return True, f"Created and joined new lobby {lobby_data.code}", lobby_data.code
                    else:
                        # Join failed, add them back to hashmap
                        player_hashmap.add_player(session_id, username)
                        return False, f"Created lobby but failed to join: {join_message}", None
                else:
                    # Creation failed, add them back to hashmap
                    player_hashmap.add_player(session_id, username)
                    return False, f"Failed to create lobby: {message}", None
                    
        except Exception as e:
            logger.error(f"Error in random matching: {e}")
            # Make sure they're back in hashmap on error
            player_hashmap.add_player(session_id, username)
            return False, "Random matching failed", None
    
    def player_left_lobby(self, session_id: str, username: str) -> bool:
        """
        Handle a player leaving a lobby (add them back to hashmap).
        
        Args:
            session_id: Player's session ID
            username: Player's username
            
        Returns:
            True if added back to hashmap successfully
        """
        try:
            success = player_hashmap.add_player(session_id, username)
            if success:
                logger.info(f"Player {username} returned to hashmap after leaving lobby")
            return success
            
        except Exception as e:
            logger.error(f"Error returning player to hashmap: {e}")
            return False
    
    def destroy_lobby_and_return_players(self, lobby_code: str) -> int:
        """
        Destroy a lobby after game ends and return all players to hashmap.
        
        Args:
            lobby_code: Code of the lobby to destroy
            
        Returns:
            Number of players returned to hashmap
        """
        try:
            from database import get_lobby_by_code, get_players_from_lobby, delete_lobby
            
            # Get the lobby
            lobby = get_lobby_by_code(lobby_code)
            if not lobby:
                logger.warning(f"Lobby {lobby_code} not found for destruction")
                return 0
            
            # Get all human players (exclude AI)
            human_players = get_players_from_lobby(lobby.id, is_ai=False)
            players_returned = 0
            
            # Add each human player back to hashmap
            for player in human_players:
                if player.is_connected:
                    success = player_hashmap.add_player(player.session_id, player.username)
                    if success:
                        players_returned += 1
            
            # Delete the lobby (this will cascade to all related data)
            delete_lobby(lobby.id)
            
            logger.info(f"Destroyed lobby {lobby_code} and returned {players_returned} players to hashmap")
            return players_returned
            
        except Exception as e:
            logger.error(f"Error destroying lobby {lobby_code}: {e}")
            return 0
    
    def get_matchmaking_stats(self) -> dict:
        """Get current matchmaking statistics."""
        try:
            open_lobbies = get_open_lobbies()
            available_lobbies = sum(1 for lobby in open_lobbies if can_join_lobby(lobby.id))
            
            return {
                'players_waiting': player_hashmap.get_player_count(),
                'open_lobbies': len(open_lobbies),
                'available_lobbies': available_lobbies,
                'matcher_initialized': True
            }
            
        except Exception as e:
            logger.error(f"Error getting matchmaking stats: {e}")
            return {'error': str(e)}

# Global instance for the application
random_matcher = RandomMatcher()