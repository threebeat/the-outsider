"""
Voting management for The Outsider.

This module handles the voting phase, vote counting, and determining
game outcomes based on elimination results.
"""

import logging
from typing import Optional, Dict, List, Any
from database import get_db_session, get_lobby_by_code
from utils.constants import GAME_STATES, WINNER_TYPES, VOTE_REASONS
from utils.helpers import calculate_vote_winner

logger = logging.getLogger(__name__)

class VotingManager:
    """Manages voting phase and outcome determination."""
    
    def __init__(self):
        self.voting_sessions: Dict[str, Dict[str, Any]] = {}  # lobby_code -> voting_data
    
    def start_voting_phase(self, lobby_code: str) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Start the voting phase for a lobby.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            tuple: (success, message, voting_data)
        """
        try:
            with get_db_session() as session:
                lobby = get_lobby_by_code(session, lobby_code)
                if not lobby:
                    return False, "Lobby not found", None
                
                if lobby.state != GAME_STATES['PLAYING']:
                    return False, "Game not in playing state", None
                
                # Update lobby state to voting
                lobby.state = GAME_STATES['VOTING']
                
                # Get all active players for voting
                active_players = lobby.active_players
                eligible_voters = [p for p in active_players if not p.is_spectator]
                voteable_players = [p for p in active_players if not p.is_spectator]
                
                if not eligible_voters:
                    return False, "No eligible voters", None
                
                # Initialize voting session
                self.voting_sessions[lobby_code] = {
                    'voters': [
                        {
                            'session_id': p.session_id,
                            'username': p.username,
                            'is_ai': p.is_ai,
                            'has_voted': False
                        } 
                        for p in eligible_voters
                    ],
                    'candidates': [
                        {
                            'session_id': p.session_id,
                            'username': p.username,
                            'is_ai': p.is_ai,
                            'vote_count': 0
                        }
                        for p in voteable_players
                    ],
                    'votes': {},  # session_id -> target_username
                    'voting_complete': False,
                    'vote_round': 1
                }
                
                voting_data = {
                    'eligible_voters': len(eligible_voters),
                    'candidates': [
                        {
                            'username': c['username'],
                            'is_ai': c['is_ai']
                        }
                        for c in self.voting_sessions[lobby_code]['candidates']
                    ]
                }
                
                logger.info(f"Started voting phase in lobby {lobby_code}: {len(eligible_voters)} voters")
                return True, "Voting phase started", voting_data
                
        except Exception as e:
            logger.error(f"Error starting voting phase: {e}")
            return False, "Failed to start voting", None
    
    def cast_vote(self, lobby_code: str, voter_session_id: str, 
                 target_username: str) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Cast a vote for elimination.
        
        Args:
            lobby_code: Code of the lobby
            voter_session_id: Session ID of the voter
            target_username: Username of the player being voted for
            
        Returns:
            tuple: (success, message, vote_result)
        """
        try:
            if lobby_code not in self.voting_sessions:
                return False, "Voting not in progress", None
            
            voting_session = self.voting_sessions[lobby_code]
            
            if voting_session['voting_complete']:
                return False, "Voting already complete", None
            
            # Find voter
            voter = None
            for v in voting_session['voters']:
                if v['session_id'] == voter_session_id:
                    voter = v
                    break
            
            if not voter:
                return False, "You are not eligible to vote", None
            
            if voter['has_voted']:
                return False, "You have already voted", None
            
            # Verify target exists and is voteable
            target_candidate = None
            for c in voting_session['candidates']:
                if c['username'] == target_username:
                    target_candidate = c
                    break
            
            if not target_candidate:
                return False, "Invalid vote target", None
            
            # Cast vote
            voting_session['votes'][voter_session_id] = target_username
            voter['has_voted'] = True
            target_candidate['vote_count'] += 1
            
            # Store vote in database
            with get_db_session() as session:
                lobby = get_lobby_by_code(session, lobby_code)
                if lobby:
                    from database import Vote
                    
                    # Find voter and target players
                    voter_player = None
                    target_player = None
                    for player in lobby.active_players:
                        if player.session_id == voter_session_id:
                            voter_player = player
                        elif player.username == target_username:
                            target_player = player
                    
                    if voter_player and target_player:
                        vote = Vote(
                            lobby_id=lobby.id,
                            voter_id=voter_player.id,
                            target_id=target_player.id,
                            vote_round=voting_session['vote_round']
                        )
                        session.add(vote)
            
            # Check if voting is complete
            votes_cast = sum(1 for v in voting_session['voters'] if v['has_voted'])
            total_voters = len(voting_session['voters'])
            
            vote_result = {
                'voter_username': voter['username'],
                'target_username': target_username,
                'votes_cast': votes_cast,
                'total_voters': total_voters,
                'voting_complete': votes_cast >= total_voters
            }
            
            if votes_cast >= total_voters:
                voting_session['voting_complete'] = True
                self._finalize_voting(lobby_code)
            
            logger.info(f"Vote cast in lobby {lobby_code}: {voter['username']} -> {target_username}")
            return True, "Vote cast successfully", vote_result
            
        except Exception as e:
            logger.error(f"Error casting vote: {e}")
            return False, "Failed to cast vote", None
    
    def get_voting_status(self, lobby_code: str) -> Optional[Dict[str, Any]]:
        """
        Get current voting status.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Voting status dictionary or None
        """
        if lobby_code not in self.voting_sessions:
            return None
        
        voting_session = self.voting_sessions[lobby_code]
        
        # Calculate vote counts
        vote_counts = {}
        for candidate in voting_session['candidates']:
            vote_counts[candidate['username']] = candidate['vote_count']
        
        # Get voter status
        voter_status = []
        for voter in voting_session['voters']:
            voter_status.append({
                'username': voter['username'],
                'is_ai': voter['is_ai'],
                'has_voted': voter['has_voted']
            })
        
        return {
            'voting_complete': voting_session['voting_complete'],
            'vote_counts': vote_counts,
            'voter_status': voter_status,
            'votes_cast': sum(1 for v in voting_session['voters'] if v['has_voted']),
            'total_voters': len(voting_session['voters'])
        }
    
    def _finalize_voting(self, lobby_code: str) -> Optional[Dict[str, Any]]:
        """
        Finalize voting and determine game outcome.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Game result dictionary or None
        """
        try:
            voting_session = self.voting_sessions[lobby_code]
            
            # Calculate vote results
            vote_counts = {}
            for candidate in voting_session['candidates']:
                vote_counts[candidate['username']] = candidate['vote_count']
            
            # Find most voted player
            eliminated_username = calculate_vote_winner(vote_counts)
            
            if not eliminated_username:
                # Handle tie - could implement tiebreaker logic
                logger.warning(f"Vote tie in lobby {lobby_code}")
                return None
            
            # Determine game outcome
            with get_db_session() as session:
                lobby = get_lobby_by_code(session, lobby_code)
                if not lobby:
                    return None
                
                # Find eliminated player and outsider
                eliminated_player = None
                outsider_player = None
                
                for player in lobby.active_players:
                    if player.username == eliminated_username:
                        eliminated_player = player
                    if player.is_outsider:
                        outsider_player = player
                
                if not eliminated_player or not outsider_player:
                    logger.error(f"Could not find eliminated or outsider player in lobby {lobby_code}")
                    return None
                
                # Determine winner
                if eliminated_player.is_outsider:
                    winner = WINNER_TYPES['HUMANS']
                    reason = VOTE_REASONS['OUTSIDER_ELIMINATED']
                else:
                    winner = WINNER_TYPES['AI']
                    reason = VOTE_REASONS['WRONG_ELIMINATION']
                
                # Update lobby state
                lobby.state = GAME_STATES['FINISHED']
                
                result = {
                    'winner': winner,
                    'reason': reason,
                    'eliminated_player': eliminated_username,
                    'eliminated_was_outsider': eliminated_player.is_outsider,
                    'actual_outsider': outsider_player.username,
                    'vote_results': vote_counts,
                    'game_ended': True
                }
                
                logger.info(f"Voting finalized in lobby {lobby_code}: {winner} won, eliminated {eliminated_username}")
                return result
                
        except Exception as e:
            logger.error(f"Error finalizing voting: {e}")
            return None
    
    def handle_ai_votes(self, lobby_code: str) -> bool:
        """
        Handle AI players casting their votes automatically.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Success status
        """
        try:
            if lobby_code not in self.voting_sessions:
                return False
            
            voting_session = self.voting_sessions[lobby_code]
            
            with get_db_session() as session:
                lobby = get_lobby_by_code(session, lobby_code)
                if not lobby:
                    return False
                
                # Get AI voters who haven't voted yet
                ai_voters = [v for v in voting_session['voters'] 
                           if v['is_ai'] and not v['has_voted']]
                
                for ai_voter in ai_voters:
                    # Simple AI voting logic - vote for a random human player
                    human_candidates = [c for c in voting_session['candidates'] 
                                      if not c['is_ai']]
                    
                    if human_candidates:
                        import random
                        target = random.choice(human_candidates)
                        
                        # Cast AI vote
                        success, message, result = self.cast_vote(
                            lobby_code, ai_voter['session_id'], target['username']
                        )
                        
                        if success:
                            logger.info(f"AI player {ai_voter['username']} voted for {target['username']}")
                
                return True
                
        except Exception as e:
            logger.error(f"Error handling AI votes: {e}")
            return False
    
    def get_game_result(self, lobby_code: str) -> Optional[Dict[str, Any]]:
        """
        Get the final game result after voting.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Game result dictionary or None
        """
        if lobby_code not in self.voting_sessions:
            return None
        
        voting_session = self.voting_sessions[lobby_code]
        
        if not voting_session['voting_complete']:
            return None
        
        return self._finalize_voting(lobby_code)
    
    def reset_voting(self, lobby_code: str):
        """
        Reset voting state for a lobby.
        
        Args:
            lobby_code: Code of the lobby
        """
        if lobby_code in self.voting_sessions:
            del self.voting_sessions[lobby_code]
        
        logger.info(f"Reset voting state for lobby {lobby_code}")
    
    def force_complete_voting(self, lobby_code: str) -> Optional[Dict[str, Any]]:
        """
        Force complete voting (for timeout scenarios).
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Game result or None
        """
        try:
            if lobby_code not in self.voting_sessions:
                return None
            
            voting_session = self.voting_sessions[lobby_code]
            voting_session['voting_complete'] = True
            
            return self._finalize_voting(lobby_code)
            
        except Exception as e:
            logger.error(f"Error force completing voting: {e}")
            return None
    
    def get_vote_summary(self, lobby_code: str) -> Optional[Dict[str, Any]]:
        """
        Get a summary of the voting process.
        
        Args:
            lobby_code: Code of the lobby
            
        Returns:
            Vote summary dictionary or None
        """
        try:
            if lobby_code not in self.voting_sessions:
                return None
            
            voting_session = self.voting_sessions[lobby_code]
            
            # Count votes by candidate
            vote_breakdown = {}
            for vote_target in voting_session['votes'].values():
                vote_breakdown[vote_target] = vote_breakdown.get(vote_target, 0) + 1
            
            # Get non-voters
            non_voters = [v['username'] for v in voting_session['voters'] if not v['has_voted']]
            
            return {
                'total_voters': len(voting_session['voters']),
                'votes_cast': len(voting_session['votes']),
                'vote_breakdown': vote_breakdown,
                'non_voters': non_voters,
                'voting_complete': voting_session['voting_complete']
            }
            
        except Exception as e:
            logger.error(f"Error getting vote summary: {e}")
            return None