"""
Data models for game management.

These represent game-specific data structures that operate within lobbies.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class GameState(Enum):
    """Game state enumeration."""
    WAITING = "waiting"
    PLAYING = "playing" 
    VOTING = "voting"
    FINISHED = "finished"

@dataclass
class TurnData:
    """Represents a turn in the game."""
    turn_number: int
    asker_session_id: str
    asker_username: str
    target_session_id: str
    target_username: str
    question: Optional[str] = None
    answer: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'turn_number': self.turn_number,
            'asker_session_id': self.asker_session_id,
            'asker_username': self.asker_username,
            'target_session_id': self.target_session_id,
            'target_username': self.target_username,
            'question': self.question,
            'answer': self.answer,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

@dataclass
class VoteData:
    """Represents a vote during voting phase."""
    voter_session_id: str
    voter_username: str
    target_session_id: str
    target_username: str
    cast_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'voter_session_id': self.voter_session_id,
            'voter_username': self.voter_username,
            'target_session_id': self.target_session_id,
            'target_username': self.target_username,
            'cast_at': self.cast_at.isoformat()
        }

@dataclass
class GameData:
    """Represents a game session within a lobby."""
    lobby_code: str
    session_id: str
    state: GameState
    location: Optional[str] = None
    outsider_session_id: Optional[str] = None
    outsider_username: Optional[str] = None
    current_turn: int = 0
    max_questions: int = 5
    question_count: int = 0
    turns: List[TurnData] = field(default_factory=list)
    votes: List[VoteData] = field(default_factory=list)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    winner: Optional[str] = None  # 'humans', 'ai', 'draw'
    end_reason: Optional[str] = None
    
    @property
    def is_active(self) -> bool:
        """Check if game is currently active."""
        return self.state in [GameState.PLAYING, GameState.VOTING]
    
    @property
    def is_voting_phase(self) -> bool:
        """Check if game is in voting phase."""
        return self.state == GameState.VOTING
    
    @property
    def is_finished(self) -> bool:
        """Check if game is finished."""
        return self.state == GameState.FINISHED
    
    def get_current_turn(self) -> Optional[TurnData]:
        """Get the current turn data."""
        if self.turns and self.current_turn < len(self.turns):
            return self.turns[self.current_turn]
        return None
    
    def get_vote_counts(self) -> Dict[str, int]:
        """Get vote counts by target username."""
        vote_counts = {}
        for vote in self.votes:
            target = vote.target_username
            vote_counts[target] = vote_counts.get(target, 0) + 1
        return vote_counts
    
    def get_most_voted_player(self) -> Optional[str]:
        """Get the username of the most voted player."""
        vote_counts = self.get_vote_counts()
        if not vote_counts:
            return None
        
        max_votes = max(vote_counts.values())
        most_voted = [username for username, count in vote_counts.items() if count == max_votes]
        
        # Return None if there's a tie
        if len(most_voted) > 1:
            return None
        
        return most_voted[0]
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        
        Args:
            include_sensitive: Whether to include sensitive info like outsider identity
        """
        data = {
            'lobby_code': self.lobby_code,
            'session_id': self.session_id,
            'state': self.state.value,
            'location': self.location,
            'current_turn': self.current_turn,
            'max_questions': self.max_questions,
            'question_count': self.question_count,
            'is_active': self.is_active,
            'is_voting_phase': self.is_voting_phase,
            'is_finished': self.is_finished,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'winner': self.winner,
            'end_reason': self.end_reason,
            'turns': [turn.to_dict() for turn in self.turns],
            'votes': [vote.to_dict() for vote in self.votes],
            'vote_counts': self.get_vote_counts()
        }
        
        # Only include sensitive info if requested (e.g., for spectators or post-game)
        if include_sensitive:
            data.update({
                'outsider_session_id': self.outsider_session_id,
                'outsider_username': self.outsider_username
            })
        
        return data

@dataclass
class PlayerGameStatus:
    """Represents a player's status within a game."""
    session_id: str
    username: str
    is_outsider: bool = False
    questions_asked: int = 0
    questions_answered: int = 0
    has_voted: bool = False
    can_ask_question: bool = False
    can_answer_question: bool = False
    can_vote: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'session_id': self.session_id,
            'username': self.username,
            'is_outsider': self.is_outsider,
            'questions_asked': self.questions_asked,
            'questions_answered': self.questions_answered,
            'has_voted': self.has_voted,
            'can_ask_question': self.can_ask_question,
            'can_answer_question': self.can_answer_question,
            'can_vote': self.can_vote
        }

@dataclass
class GameResult:
    """Represents the final result of a game."""
    winner: str  # 'humans', 'ai', 'draw'
    reason: str
    eliminated_player: Optional[str] = None
    outsider_player: Optional[str] = None
    vote_results: Dict[str, int] = field(default_factory=dict)
    game_duration: Optional[int] = None  # seconds
    total_questions: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'winner': self.winner,
            'reason': self.reason,
            'eliminated_player': self.eliminated_player,
            'outsider_player': self.outsider_player,
            'vote_results': self.vote_results,
            'game_duration': self.game_duration,
            'total_questions': self.total_questions
        }