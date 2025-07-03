"""
Universal Database Setters for The Outsider.

Contains all write operations to the database. All session management
is contained within this module - other modules should never handle sessions directly.
"""

import logging
from typing import Optional
from datetime import datetime, timezone

from .config import get_db_session
from .models import Lobby, Player, GameMessage, Vote, GameSession, GameStatistics

logger = logging.getLogger(__name__)

# ==============================================================================
# UNIVERSAL SETTERS - ALL WRITE OPERATIONS
# ==============================================================================

def create_lobby(code: str, name: str, max_players: int = 8) -> Lobby:
    """Create a new lobby."""
    with get_db_session() as session:
        lobby = Lobby(
            code=code,
            name=name,
            max_players=max_players
        )
        session.add(lobby)
        session.flush()  # Get the ID without committing
        logger.info(f"Created lobby: {code}")
        return lobby

def create_player(lobby_id: int, session_id: str, username: str, 
                 is_ai: bool = False, is_spectator: bool = False,
                 ai_personality: Optional[str] = None) -> Player:
    """Create a new player."""
    with get_db_session() as session:
        player = Player(
            lobby_id=lobby_id,
            session_id=session_id,
            username=username,
            is_ai=is_ai,
            is_spectator=is_spectator,
            ai_personality=ai_personality
        )
        session.add(player)
        session.flush()
        logger.info(f"Created player '{username}' in lobby {lobby_id} (AI: {is_ai})")
        return player

def update_lobby_state(lobby_id: int, new_state: str):
    """Update lobby state."""
    with get_db_session() as session:
        lobby = session.query(Lobby).filter_by(id=lobby_id).first()
        if lobby:
            lobby.state = new_state
            lobby.update_activity()
            logger.info(f"Updated lobby {lobby.code} state to: {new_state}")

def update_player_connection(player_id: int, connected: bool):
    """Update player connection status."""
    with get_db_session() as session:
        player = session.query(Player).filter_by(id=player_id).first()
        if player:
            player.is_connected = connected
            player.update_last_seen()
            logger.info(f"Updated player {player.username} connection: {connected}")

# Outsider functionality removed - AI players are automatically outsiders

def create_game_session(lobby_id: int, location: str) -> GameSession:
    """Create a new game session."""
    with get_db_session() as session:
        lobby = session.query(Lobby).filter_by(id=lobby_id).first()
        if not lobby:
            raise ValueError(f"Lobby {lobby_id} not found")
        
        # Get next session number
        last_session = session.query(GameSession).filter_by(lobby_id=lobby_id)\
            .order_by(GameSession.session_number.desc()).first()
        session_number = (last_session.session_number + 1) if last_session else 1
        
        # Count players
        from .getters import get_players_from_lobby
        human_count = len(get_players_from_lobby(lobby_id, is_ai=False, is_spectator=False))
        ai_count = len(get_players_from_lobby(lobby_id, is_ai=True))
        
        game_session = GameSession(
            lobby_id=lobby_id,
            session_number=session_number,
            location=location,
            total_players=human_count + ai_count,
            human_players=human_count,
            ai_players=ai_count,
            started_at=datetime.now(timezone.utc)
        )
        session.add(game_session)
        session.flush()
        
        # Update lobby
        lobby.state = 'playing'
        lobby.location = location
        lobby.started_at = datetime.now(timezone.utc)
        lobby.current_turn = 0
        lobby.question_count = 0
        lobby.update_activity()
        
        logger.info(f"Created game session {session_number} in lobby '{lobby.code}' with location '{location}'")
        return game_session

def create_game_message(lobby_id: int, content: str, message_type: str = 'chat',
                       sender_id: Optional[int] = None, target_id: Optional[int] = None,
                       is_question: bool = False) -> GameMessage:
    """Create a new game message."""
    with get_db_session() as session:
        message = GameMessage(
            lobby_id=lobby_id,
            content=content,
            message_type=message_type,
            sender_id=sender_id,
            target_id=target_id,
            is_question=is_question
        )
        session.add(message)
        session.flush()
        return message

def create_vote(lobby_id: int, voter_id: int, target_id: int,
               vote_round: int = 1, confidence: Optional[float] = None,
               reasoning: Optional[str] = None) -> Vote:
    """Create a new vote."""
    with get_db_session() as session:
        vote = Vote(
            lobby_id=lobby_id,
            voter_id=voter_id,
            target_id=target_id,
            vote_round=vote_round,
            confidence=confidence,
            reasoning=reasoning
        )
        session.add(vote)
        session.flush()
        logger.info(f"Created vote in lobby {lobby_id}")
        return vote

def update_game_statistics(winner: str):
    """Update global game statistics."""
    with get_db_session() as session:
        stats = session.query(GameStatistics).filter_by(lobby_code='main').first()
        if not stats:
            stats = GameStatistics(lobby_code='main')
            session.add(stats)
        
        stats.total_games += 1
        if winner == 'humans':
            stats.human_wins += 1
        elif winner == 'ai':
            stats.ai_wins += 1
        
        stats.update_stats()
        logger.info(f"Updated statistics: {winner} won (Total: {stats.total_games})")

def delete_player(player_id: int):
    """Delete a player from the database."""
    with get_db_session() as session:
        player = session.query(Player).filter_by(id=player_id).first()
        if player:
            username = player.username
            lobby_code = player.lobby.code if player.lobby else "unknown"
            session.delete(player)
            logger.info(f"Deleted player '{username}' from lobby '{lobby_code}'")

def update_lobby_activity(lobby_id: int):
    """Update lobby's last activity timestamp."""
    with get_db_session() as session:
        lobby = session.query(Lobby).filter_by(id=lobby_id).first()
        if lobby:
            lobby.update_activity()

def update_player_last_seen(player_id: int):
    """Update player's last seen timestamp."""
    with get_db_session() as session:
        player = session.query(Player).filter_by(id=player_id).first()
        if player:
            player.update_last_seen()

def increment_player_questions_asked(player_id: int):
    """Increment the number of questions asked by a player."""
    with get_db_session() as session:
        player = session.query(Player).filter_by(id=player_id).first()
        if player:
            player.questions_asked += 1

def increment_player_questions_answered(player_id: int):
    """Increment the number of questions answered by a player."""
    with get_db_session() as session:
        player = session.query(Player).filter_by(id=player_id).first()
        if player:
            player.questions_answered += 1

def increment_player_votes_received(player_id: int):
    """Increment the number of votes received by a player."""
    with get_db_session() as session:
        player = session.query(Player).filter_by(id=player_id).first()
        if player:
            player.votes_received += 1

def update_player_ai_strategy(player_id: int, strategy_data: str):
    """Update AI player's strategy data."""
    with get_db_session() as session:
        player = session.query(Player).filter_by(id=player_id, is_ai=True).first()
        if player:
            player.ai_strategy = strategy_data
            logger.debug(f"Updated strategy for AI player '{player.username}'")

def end_game_session(lobby_id: int, winner: str, winner_reason: str, 
                    eliminated_player_id: Optional[int] = None,
                    ai_final_guess: Optional[str] = None, ai_guessed_correctly: bool = False):
    """End the current game session."""
    with get_db_session() as session:
        # Get current session
        current_session = session.query(GameSession).filter_by(
            lobby_id=lobby_id,
            ended_at=None
        ).first()
        
        if current_session:
            current_session.ended_at = datetime.now(timezone.utc)
            current_session.winner = winner
            current_session.winner_reason = winner_reason
            current_session.ai_final_guess = ai_final_guess
            current_session.ai_guessed_correctly = ai_guessed_correctly
            
            if eliminated_player_id:
                current_session.eliminated_player_id = eliminated_player_id
                eliminated_player = session.query(Player).filter_by(id=eliminated_player_id).first()
                if eliminated_player:
                    current_session.ai_eliminated = eliminated_player.is_ai
            
            # Calculate duration
            if current_session.started_at:
                duration = current_session.ended_at - current_session.started_at
                current_session.duration_seconds = int(duration.total_seconds())
            
            # Update lobby state
            lobby = session.query(Lobby).filter_by(id=lobby_id).first()
            if lobby:
                lobby.state = 'finished'
                lobby.ended_at = current_session.ended_at
                lobby.update_activity()
            
            logger.info(f"Ended game session in lobby {lobby_id}: {winner} won ({winner_reason})")

def reset_lobby_for_new_game(lobby_id: int):
    """Reset a lobby to waiting state for a new game."""
    with get_db_session() as session:
        lobby = session.query(Lobby).filter_by(id=lobby_id).first()
        if lobby:
            lobby.state = 'waiting'
            lobby.location = None
            lobby.current_turn = 0
            lobby.question_count = 0
            lobby.started_at = None
            lobby.ended_at = None
            lobby.update_activity()
            
            # Reset player states
            for player in lobby.players:
                if player.is_connected:
                    player.questions_asked = 0
                    player.questions_answered = 0
                    player.votes_received = 0
            
            # Clear votes
            session.query(Vote).filter_by(lobby_id=lobby_id).delete()
            
            logger.info(f"Reset lobby '{lobby.code}' to waiting state")

def disconnect_all_players_in_lobby(lobby_id: int):
    """Disconnect all players in a lobby."""
    with get_db_session() as session:
        players = session.query(Player).filter_by(lobby_id=lobby_id, is_connected=True).all()
        for player in players:
            player.is_connected = False
            player.update_last_seen()
        logger.info(f"Disconnected all players in lobby {lobby_id}")

def delete_lobby(lobby_id: int):
    """Delete a lobby and all associated data."""
    with get_db_session() as session:
        lobby = session.query(Lobby).filter_by(id=lobby_id).first()
        if lobby:
            lobby_code = lobby.code
            session.delete(lobby)  # Cascades to all related data
            logger.info(f"Deleted lobby '{lobby_code}' and all associated data")

def create_statistics_entry(lobby_code: str = 'main') -> GameStatistics:
    """Create a new statistics entry."""
    with get_db_session() as session:
        stats = GameStatistics(lobby_code=lobby_code)
        session.add(stats)
        session.flush()
        logger.info(f"Created statistics entry for lobby '{lobby_code}'")
        return stats