"""
Vote Manager for The Outsider Game.

Handles voting phase, vote counting, and result determination.
Contains no game state logic - purely voting mechanics.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import Counter

logger = logging.getLogger(__name__)

@dataclass 
class VoteData:
    """Data about a single vote."""
    voter: str
    target: str
    timestamp: datetime
    confidence: Optional[float] = None  # AI confidence in vote
    reasoning: Optional[str] = None     # AI reasoning for vote

@dataclass
class VotingSession:
    """Complete voting session data."""
    votes: Dict[str, VoteData] = field(default_factory=dict)  # voter -> VoteData
    voting_deadline: Optional[datetime] = None
    voting_started: Optional[datetime] = None
    is_complete: bool = False
    results_calculated: bool = False

@dataclass
class VoteResults:
    """Results of a voting session."""
    vote_counts: Dict[str, int] = field(default_factory=dict)  # target -> count
    winner: Optional[str] = None
    tied_players: List[str] = field(default_factory=list)
    is_tie: bool = False
    total_votes: int = 0
    voting_complete: bool = False

class VoteManager:
    """
    Manages voting sessions and vote counting.
    
    Handles vote validation, collection, counting, and result determination.
    Contains no game logic - pure voting mechanics.
    """
    
    def __init__(self, voting_timeout_seconds: int = 120):
        """
        Initialize vote manager.
        
        Args:
            voting_timeout_seconds: Maximum time for voting phase
        """
        self.voting_timeout_seconds = voting_timeout_seconds
        logger.debug("Vote manager initialized")
    
    def start_voting_session(self, eligible_voters: List[str], eligible_targets: List[str]) -> VotingSession:
        """
        Start a new voting session.
        
        Args:
            eligible_voters: List of players who can vote
            eligible_targets: List of players who can be voted for
            
        Returns:
            New VotingSession object
        """
        try:
            voting_start = datetime.now()
            voting_deadline = voting_start + timedelta(seconds=self.voting_timeout_seconds)
            
            session = VotingSession(
                voting_started=voting_start,
                voting_deadline=voting_deadline
            )
            
            logger.info(f"Started voting session with {len(eligible_voters)} voters, {len(eligible_targets)} targets")
            return session
            
        except Exception as e:
            logger.error(f"Error starting voting session: {e}")
            return VotingSession()
    
    def validate_vote(self, 
                     voter: str, 
                     target: str, 
                     eligible_voters: List[str], 
                     eligible_targets: List[str],
                     existing_session: VotingSession) -> Tuple[bool, str]:
        """
        Validate a vote before recording it.
        
        Args:
            voter: Username of player voting
            target: Username of player being voted for
            eligible_voters: List of players allowed to vote
            eligible_targets: List of players that can be voted for
            existing_session: Current voting session
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check if voting session is still active
            if existing_session.is_complete:
                return False, "Voting session has ended"
            
            if existing_session.voting_deadline and datetime.now() > existing_session.voting_deadline:
                return False, "Voting deadline has passed"
            
            # Check voter eligibility
            if voter not in eligible_voters:
                return False, "You are not eligible to vote"
            
            # Check target eligibility
            if target not in eligible_targets:
                return False, "Invalid vote target"
            
            # Check if voter already voted
            if voter in existing_session.votes:
                return False, "You have already voted"
            
            # Check that voter isn't voting for themselves (if not allowed)
            # Note: In some game variants, self-voting might be allowed
            if voter == target:
                return False, "Cannot vote for yourself"
            
            return True, "Vote is valid"
            
        except Exception as e:
            logger.error(f"Error validating vote: {e}")
            return False, "Vote validation failed"
    
    def record_vote(self, 
                   voter: str, 
                   target: str, 
                   session: VotingSession,
                   confidence: Optional[float] = None,
                   reasoning: Optional[str] = None) -> Tuple[bool, str]:
        """
        Record a vote in the voting session.
        
        Args:
            voter: Username of player voting
            target: Username of player being voted for
            session: Voting session to record vote in
            confidence: AI confidence level (0.0-1.0)
            reasoning: AI reasoning for the vote
            
        Returns:
            Tuple of (success, message)
        """
        try:
            vote_data = VoteData(
                voter=voter,
                target=target,
                timestamp=datetime.now(),
                confidence=confidence,
                reasoning=reasoning
            )
            
            session.votes[voter] = vote_data
            
            logger.info(f"Recorded vote: {voter} -> {target}")
            return True, f"Vote recorded for {target}"
            
        except Exception as e:
            logger.error(f"Error recording vote: {e}")
            return False, "Failed to record vote"
    
    def change_vote(self, 
                   voter: str, 
                   new_target: str, 
                   session: VotingSession,
                   eligible_targets: List[str]) -> Tuple[bool, str]:
        """
        Change an existing vote (if allowed).
        
        Args:
            voter: Username of player changing vote
            new_target: New target for the vote
            session: Voting session
            eligible_targets: List of valid targets
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Check if voter has an existing vote
            if voter not in session.votes:
                return False, "No existing vote to change"
            
            # Check if voting is still open
            if session.is_complete:
                return False, "Voting has ended, cannot change vote"
            
            if session.voting_deadline and datetime.now() > session.voting_deadline:
                return False, "Voting deadline has passed"
            
            # Validate new target
            if new_target not in eligible_targets:
                return False, "Invalid vote target"
            
            # Update the vote
            old_target = session.votes[voter].target
            session.votes[voter].target = new_target
            session.votes[voter].timestamp = datetime.now()
            
            logger.info(f"Changed vote: {voter} from {old_target} to {new_target}")
            return True, f"Vote changed to {new_target}"
            
        except Exception as e:
            logger.error(f"Error changing vote: {e}")
            return False, "Failed to change vote"
    
    def calculate_results(self, session: VotingSession) -> VoteResults:
        """
        Calculate voting results from the session.
        
        Args:
            session: Voting session to calculate results for
            
        Returns:
            VoteResults object with calculated results
        """
        try:
            # Count votes for each target
            vote_counts = Counter()
            for vote_data in session.votes.values():
                vote_counts[vote_data.target] += 1
            
            total_votes = len(session.votes)
            
            # Determine winner
            if not vote_counts:
                # No votes cast
                return VoteResults(
                    total_votes=0,
                    voting_complete=True
                )
            
            max_votes = max(vote_counts.values())
            top_players = [player for player, count in vote_counts.items() if count == max_votes]
            
            # Check for tie
            if len(top_players) > 1:
                results = VoteResults(
                    vote_counts=dict(vote_counts),
                    tied_players=top_players,
                    is_tie=True,
                    total_votes=total_votes,
                    voting_complete=True
                )
            else:
                results = VoteResults(
                    vote_counts=dict(vote_counts),
                    winner=top_players[0],
                    is_tie=False,
                    total_votes=total_votes,
                    voting_complete=True
                )
            
            session.results_calculated = True
            logger.info(f"Calculated results: {len(session.votes)} votes, winner: {results.winner}, tie: {results.is_tie}")
            return results
            
        except Exception as e:
            logger.error(f"Error calculating results: {e}")
            return VoteResults(voting_complete=False)
    
    def is_voting_complete(self, 
                          session: VotingSession, 
                          total_eligible_voters: int,
                          require_all_votes: bool = False) -> bool:
        """
        Check if voting should be considered complete.
        
        Args:
            session: Current voting session
            total_eligible_voters: Total number of players who can vote
            require_all_votes: Whether all eligible voters must vote
            
        Returns:
            True if voting is complete, False otherwise
        """
        try:
            # Check if manually marked complete
            if session.is_complete:
                return True
            
            # Check if deadline passed
            if session.voting_deadline and datetime.now() > session.voting_deadline:
                return True
            
            # Check if all players voted (if required)
            if require_all_votes and len(session.votes) >= total_eligible_voters:
                return True
            
            # Check if majority voted (optional threshold)
            majority_threshold = 0.75  # 75% of players
            if len(session.votes) >= (total_eligible_voters * majority_threshold):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking voting completion: {e}")
            return False
    
    def finalize_voting(self, session: VotingSession) -> VoteResults:
        """
        Finalize voting session and calculate final results.
        
        Args:
            session: Voting session to finalize
            
        Returns:
            Final VoteResults
        """
        try:
            session.is_complete = True
            results = self.calculate_results(session)
            
            logger.info(f"Finalized voting session with {results.total_votes} votes")
            return results
            
        except Exception as e:
            logger.error(f"Error finalizing voting: {e}")
            return VoteResults(voting_complete=False)
    
    def get_voting_status(self, session: VotingSession, total_eligible: int) -> Dict[str, any]:
        """
        Get current status of voting session.
        
        Args:
            session: Current voting session
            total_eligible: Total eligible voters
            
        Returns:
            Status information dictionary
        """
        try:
            time_remaining = None
            if session.voting_deadline:
                remaining = session.voting_deadline - datetime.now()
                time_remaining = max(0, int(remaining.total_seconds()))
            
            return {
                'votes_cast': len(session.votes),
                'total_eligible': total_eligible,
                'voting_complete': session.is_complete,
                'time_remaining_seconds': time_remaining,
                'percentage_voted': (len(session.votes) / total_eligible * 100) if total_eligible > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting voting status: {e}")
            return {}
    
    def get_vote_summary(self, session: VotingSession) -> Dict[str, any]:
        """
        Get summary of votes cast (without revealing individual votes).
        
        Args:
            session: Voting session
            
        Returns:
            Vote summary dictionary
        """
        try:
            # Count votes per target without revealing who voted for whom
            vote_counts = Counter()
            for vote_data in session.votes.values():
                vote_counts[vote_data.target] += 1
            
            return {
                'vote_counts': dict(vote_counts),
                'total_votes': len(session.votes),
                'voters_who_voted': list(session.votes.keys())  # Just the list of who voted
            }
            
        except Exception as e:
            logger.error(f"Error getting vote summary: {e}")
            return {}
    
    def generate_ai_vote(self, 
                        ai_player: str, 
                        eligible_targets: List[str],
                        context: Dict[str, any]) -> Tuple[Optional[str], Optional[float], Optional[str]]:
        """
        Generate an AI vote using the AI system.
        
        Args:
            ai_player: AI player username
            eligible_targets: List of players AI can vote for
            context: Context for AI decision (conversation history, etc.)
            
        Returns:
            Tuple of (target, confidence, reasoning) or (None, None, None) if failed
        """
        try:
            # Import AI system (optional dependency)
            try:
                from ai import LocationGuesser
                
                guesser = LocationGuesser()
                
                # Analyze conversation to determine most likely outsider
                conversation_history = context.get('conversation_history', [])
                guesses = guesser.get_quick_guess(
                    recent_clues=[entry.get('answer', '') for entry in conversation_history],
                    possible_locations=eligible_targets,  # In this case, players
                    max_guesses=1
                )
                
                if guesses:
                    target, confidence = guesses[0]
                    reasoning = f"Based on conversation analysis, {target} seems most likely to be the outsider"
                    
                    logger.info(f"Generated AI vote: {ai_player} -> {target} (confidence: {confidence})")
                    return target, confidence, reasoning
                
            except ImportError:
                logger.warning("AI system not available for vote generation")
            
            # Fallback: random vote
            import random
            target = random.choice(eligible_targets)
            return target, 0.5, "Random vote (AI system unavailable)"
            
        except Exception as e:
            logger.error(f"Error generating AI vote: {e}")
            return None, None, None
    
    def get_manager_status(self) -> Dict[str, any]:
        """
        Get current status of the vote manager.
        
        Returns:
            Status information dictionary
        """
        return {
            'voting_timeout_seconds': self.voting_timeout_seconds,
            'manager_initialized': True
        }