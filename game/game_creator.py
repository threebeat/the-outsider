"""
Game Creator for The Outsider.

Handles game creation with automatic AI player population.
Every game is initialized with 1-3 AI players, including the outsider.
"""

import random
import logging
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime

from database import (
    get_db_session, get_lobby_by_id, get_ai_players_in_lobby,
    get_human_players_in_lobby, create_player, set_player_as_outsider,
    create_game_session, update_lobby_state, Player
)
from utils.constants import LOCATIONS, AI_NAMES, AI_PERSONALITIES

logger = logging.getLogger(__name__)

class GameCreator:
    """
    Handles game creation and AI player population.
    
    Automatically adds 1-3 AI players to every game, including
    selecting one as the outsider.
    """
    
    def __init__(self):
        """Initialize game creator."""
        self.min_ai_players = 1
        self.max_ai_players = 3
        logger.debug("Game creator initialized")
    
    def create_game_with_ai(self, session, lobby_id: int, 
                           requested_ai_count: Optional[int] = None) -> Tuple[bool, str]:
        """
        Create a game with AI players.
        
        Args:
            session: Database session
            lobby_id: ID of the lobby to create game in
            requested_ai_count: Optional specific number of AI players (1-3)
            
        Returns:
            tuple: (success, message)
        """
        try:
            # Get lobby
            lobby = get_lobby_by_id(session, lobby_id)
            if not lobby:
                return False, "Lobby not found"
            
            # Determine AI player count
            if requested_ai_count is not None:
                ai_count = max(self.min_ai_players, min(requested_ai_count, self.max_ai_players))
            else:
                # Random between 1-3
                ai_count = random.randint(self.min_ai_players, self.max_ai_players)
            
            # Check if we can add AI players
            current_ai = len(get_ai_players_in_lobby(session, lobby_id))
            current_humans = len(get_human_players_in_lobby(session, lobby_id))
            total_players = current_ai + current_humans
            
            if total_players + ai_count > lobby.max_players:
                # Adjust AI count to fit
                ai_count = max(0, lobby.max_players - total_players)
                if ai_count == 0:
                    return False, "Lobby is full, cannot add AI players"
            
            # Add AI players
            added_players = self._add_ai_players_to_lobby(session, lobby_id, ai_count)
            
            if not added_players:
                return False, "Failed to add AI players"
            
            # Select the outsider (always an AI)
            outsider = self._select_outsider(session, lobby_id, added_players)
            
            if outsider:
                logger.info(f"Created game in lobby {lobby_id} with {len(added_players)} AI players. Outsider: {outsider.username}")
                return True, f"Game created with {len(added_players)} AI players"
            else:
                logger.warning(f"Created game in lobby {lobby_id} but failed to select outsider")
                return True, "Game created but outsider selection failed"
                
        except Exception as e:
            logger.error(f"Error creating game with AI: {e}")
            return False, f"Failed to create game: {str(e)}"
    
    def prepare_game_start(self, session, lobby_id: int) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Prepare a game for starting by ensuring AI players and selecting location.
        
        Args:
            session: Database session
            lobby_id: ID of the lobby
            
        Returns:
            tuple: (success, message, game_data)
        """
        try:
            lobby = get_lobby_by_id(session, lobby_id)
            if not lobby:
                return False, "Lobby not found", None
            
            # Check if we need to add AI players
            ai_players = get_ai_players_in_lobby(session, lobby_id)
            if len(ai_players) < self.min_ai_players:
                # Add AI players to meet minimum
                needed = self.min_ai_players - len(ai_players)
                self._add_ai_players_to_lobby(session, lobby_id, needed)
                ai_players = get_ai_players_in_lobby(session, lobby_id)
            
            # Ensure we have an outsider
            outsider = None
            for player in ai_players:
                if player.is_outsider:
                    outsider = player
                    break
            
            if not outsider and ai_players:
                # Select first AI as outsider
                outsider = ai_players[0]
                set_player_as_outsider(session, outsider)
            
            # Select random location
            location = random.choice(LOCATIONS)
            
            # Create game session
            game_session = create_game_session(session, lobby, location)
            
            game_data = {
                'game_session_id': game_session.id,
                'location': location,
                'outsider': outsider.username if outsider else None,
                'ai_players': [p.username for p in ai_players],
                'total_players': len(lobby.active_players)
            }
            
            logger.info(f"Prepared game start for lobby {lobby_id} with location '{location}'")
            return True, "Game prepared successfully", game_data
            
        except Exception as e:
            logger.error(f"Error preparing game start: {e}")
            return False, f"Failed to prepare game: {str(e)}", None
    
    def _add_ai_players_to_lobby(self, session, lobby_id: int, count: int) -> List[Any]:
        """
        Add AI players to a lobby.
        
        Args:
            session: Database session
            lobby_id: ID of the lobby
            count: Number of AI players to add
            
        Returns:
            List of created AI player objects
        """
        added_players = []
        
        try:
            # Get existing player names to avoid duplicates
            lobby = get_lobby_by_id(session, lobby_id)
            existing_names = [p.username for p in lobby.players if p.is_connected]
            
            # Get available AI names
            available_names = [name for name in AI_NAMES if name not in existing_names]
            if len(available_names) < count:
                logger.warning(f"Not enough unique AI names available. Requested: {count}, Available: {len(available_names)}")
                count = len(available_names)
            
            # Randomly select AI names
            selected_names = random.sample(available_names, count) if available_names else []
            
            # Create AI players
            for ai_name in selected_names:
                # Generate unique session ID for AI
                ai_session_id = f"AI_{ai_name}_{lobby_id}_{datetime.now().timestamp()}"
                
                # Select random personality
                personality = random.choice(AI_PERSONALITIES)
                
                # Create AI player
                ai_player = create_player(
                    session=session,
                    lobby_id=lobby_id,
                    session_id=ai_session_id,
                    username=ai_name,
                    is_ai=True,
                    ai_personality=personality
                )
                
                added_players.append(ai_player)
                logger.debug(f"Added AI player '{ai_name}' with personality '{personality}' to lobby {lobby_id}")
            
            return added_players
            
        except Exception as e:
            logger.error(f"Error adding AI players: {e}")
            return added_players
    
    def _select_outsider(self, session, lobby_id: int, 
                        prefer_from: Optional[List[Any]] = None) -> Optional[Any]:
        """
        Select an AI player to be the outsider.
        
        Args:
            session: Database session
            lobby_id: ID of the lobby
            prefer_from: Optional list of players to prefer selecting from
            
        Returns:
            Selected outsider player or None
        """
        try:
            # Get all AI players if no preference list provided
            if prefer_from:
                ai_players = prefer_from
            else:
                ai_players = get_ai_players_in_lobby(session, lobby_id)
            
            if not ai_players:
                logger.warning(f"No AI players available to be outsider in lobby {lobby_id}")
                return None
            
            # Check if any AI is already the outsider
            for player in ai_players:
                if player.is_outsider:
                    logger.debug(f"AI player '{player.username}' already marked as outsider")
                    return player
            
            # Randomly select one AI to be the outsider
            outsider = random.choice(ai_players)
            set_player_as_outsider(session, outsider)
            
            logger.info(f"Selected AI player '{outsider.username}' as the outsider")
            return outsider
            
        except Exception as e:
            logger.error(f"Error selecting outsider: {e}")
            return None
    
    def update_ai_strategy(self, session, player_id: int, strategy_data: Dict[str, Any]):
        """
        Update AI player's strategy data.
        
        Args:
            session: Database session
            player_id: ID of the AI player
            strategy_data: Strategy information to store
        """
        try:
            import json
            
            player = session.query(Player).filter_by(id=player_id, is_ai=True).first()
            if player:
                player.ai_strategy = json.dumps(strategy_data)
                logger.debug(f"Updated strategy for AI player '{player.username}'")
            else:
                logger.warning(f"AI player {player_id} not found")
                
        except Exception as e:
            logger.error(f"Error updating AI strategy: {e}")
    
    def get_ai_configuration(self, lobby_id: int) -> Dict[str, Any]:
        """
        Get AI configuration for a lobby.
        
        Args:
            lobby_id: ID of the lobby
            
        Returns:
            AI configuration dictionary
        """
        try:
            with get_db_session() as session:
                ai_players = get_ai_players_in_lobby(session, lobby_id)
                
                config = {
                    'ai_count': len(ai_players),
                    'min_ai_players': self.min_ai_players,
                    'max_ai_players': self.max_ai_players,
                    'ai_players': []
                }
                
                for player in ai_players:
                    config['ai_players'].append({
                        'username': player.username,
                        'personality': player.ai_personality,
                        'is_outsider': player.is_outsider
                    })
                
                return config
                
        except Exception as e:
            logger.error(f"Error getting AI configuration: {e}")
            return {
                'ai_count': 0,
                'error': str(e)
            }
    
    def validate_game_ready(self, session, lobby_id: int) -> Tuple[bool, str]:
        """
        Validate if a game is ready to start.
        
        Args:
            session: Database session
            lobby_id: ID of the lobby
            
        Returns:
            tuple: (is_ready, message)
        """
        try:
            lobby = get_lobby_by_id(session, lobby_id)
            if not lobby:
                return False, "Lobby not found"
            
            # Check player counts
            ai_count = len(get_ai_players_in_lobby(session, lobby_id))
            human_count = len(get_human_players_in_lobby(session, lobby_id))
            total_count = ai_count + human_count
            
            if total_count < lobby.min_players:
                return False, f"Need at least {lobby.min_players} players (have {total_count})"
            
            if ai_count < self.min_ai_players:
                return False, f"Need at least {self.min_ai_players} AI players (have {ai_count})"
            
            # Check for outsider
            has_outsider = False
            for player in get_ai_players_in_lobby(session, lobby_id):
                if player.is_outsider:
                    has_outsider = True
                    break
            
            if not has_outsider:
                return False, "No outsider selected"
            
            return True, "Game ready to start"
            
        except Exception as e:
            logger.error(f"Error validating game ready: {e}")
            return False, f"Validation error: {str(e)}"
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the game creator.
        
        Returns:
            Status information dictionary
        """
        return {
            'min_ai_players': self.min_ai_players,
            'max_ai_players': self.max_ai_players,
            'creator_initialized': True
        }