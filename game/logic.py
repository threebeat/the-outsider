import random
import threading
import time
import logging
from models.database import (
    SessionLocal, get_lobby, get_players, get_player_by_sid, 
    add_message, clear_votes, get_vote_count, get_messages,
    get_win_counter, increment_human_wins, increment_ai_wins,
    get_db_session, close_db_session, Message, Player, Lobby
)
from utils.constants import LOCATIONS
from game.ai import ai_ask_question_with_delay, ai_answer_with_delay, ai_vote_with_delay

logger = logging.getLogger(__name__)

class GameManager:
    def __init__(self, socketio):
        self.socketio = socketio
        self.last_activity = time.time()
        self.inactivity_timer = None
        self.warning_timer = None
        self.is_resetting = False  # Add flag to track reset state
        # Don't start inactivity timer on init - only during active games
    
    def start_game(self, room="main"):
        """Start a new game."""
        logger.info("=== GAME MANAGER START_GAME CALLED ===")
        logger.info(f"Starting game for room: {room}")
        session = None
        try:
            logger.info("Creating database session...")
            session = get_db_session()
            logger.info("Getting lobby...")
            lobby = get_lobby(session, room)
            logger.info(f"Got lobby: {lobby.room}, state: {lobby.state}")
            logger.info("Getting players...")
            players = get_players(session, lobby)
            logger.info(f"Found {len(players)} players: {[p.username for p in players]}")
            
            if len(players) < 2:
                logger.warning(f"Not enough players to start game: {len(players)}")
                return False, "Need at least 2 players to start"
            
            logger.info("Setting up game state...")
            # Reset game state
            lobby.state = 'playing'
            lobby.location = random.choice(LOCATIONS)
            lobby.turn = 0
            lobby.question_count = 0
            lobby.current_question_asker = None
            lobby.current_target = None
            
            # Set player order (random)
            player_sids = [p.sid for p in players]
            random.shuffle(player_sids)
            lobby.player_order = ','.join(player_sids)
            logger.info(f"Player order: {player_sids}")
            logger.info(f"First asker will be: {player_sids[0]}")
            
            # Always assign AI as outsider
            ai_players = [p for p in players if p.is_ai]
            if ai_players:
                lobby.outsider_sid = ai_players[0].sid  # Just use the first AI player
                logger.info(f"AI outsider assigned: {ai_players[0].username}")
            
            logger.info("Committing database changes...")
            session.commit()
            logger.info("Database changes committed successfully")
            
            # Send game state to all players
            player_data = [{'sid': p.sid, 'username': p.username, 'is_ai': p.is_ai} for p in players]
            logger.info(f"DEBUG: Sending game_started event with location: {lobby.location}")
            logger.info(f"DEBUG: Emitting to room: {room}")
            logger.info(f"DEBUG: Players in room: {[p.username for p in players]}")
            
            # Get all clients in the room for debugging
            from flask_socketio import rooms
            room_clients = rooms(room)
            logger.info(f"DEBUG: Clients in room {room}: {room_clients}")
            
            # Debug: Check if any clients are in the room at all
            all_rooms = rooms()
            logger.info(f"DEBUG: All rooms: {all_rooms}")
            
            # Try sending to individual clients as fallback
            if not room_clients:
                logger.info(f"DEBUG: Room is empty, sending to individual clients")
                for player in players:
                    if not player.is_ai:
                        logger.info(f"DEBUG: Sending game_started to {player.username} (SID: {player.sid})")
                        self.socketio.emit('game_started', {
                            'location': lobby.location,
                            'players': player_data,
                            'player_order': player_sids
                        }, room=player.sid)
            
            # Also try sending to room (in case the rooms() function is wrong)
            self.socketio.emit('game_started', {
                'location': lobby.location,
                'players': player_data,
                'player_order': player_sids
            }, room=room)
            logger.info(f"DEBUG: game_started event emitted successfully")
            
            # Send game_update to populate target dropdown
            player_names = [p.username for p in players]
            logger.info(f"DEBUG: Sending game_update with players: {player_names}")
            self.socketio.emit('game_update', {
                'players': player_names,
                'log': 'Game started!',
                'can_start_game': False
            }, room=room)
            
            logger.info(f"DEBUG: Starting first turn...")
            # Start first turn
            self.start_next_turn(room)
            
            # Start inactivity timer only when game starts
            self.update_activity()
            logger.info("=== GAME STARTED SUCCESSFULLY ===")
            return True, "Game started successfully"
            
        except Exception as e:
            logger.error(f"Error starting game: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False, "Error starting game"
        finally:
            if session:
                logger.info("Closing database session...")
                close_db_session(session)
    
    def start_next_turn(self, room="main"):
        """Start the next turn in the game."""
        session = None
        try:
            session = get_db_session()
            lobby = get_lobby(session, room)
            players = get_players(session, lobby)
            
            if lobby.state != 'playing':
                return
            
            player_sids = lobby.player_order.split(',') if lobby.player_order else []
            if not player_sids:
                return
            
            # Get next question asker
            current_turn = lobby.turn % len(player_sids)
            logger.info(f"DEBUG: lobby.turn = {lobby.turn}, len(player_sids) = {len(player_sids)}, current_turn = {current_turn}")
            asker_sid = player_sids[current_turn]
            logger.info(f"Turn {lobby.turn}: asker_sid = {asker_sid}")
            
            # Get random target (excluding asker)
            possible_targets = [sid for sid in player_sids if sid != asker_sid]
            if not possible_targets:
                return
            
            target_sid = random.choice(possible_targets)
            logger.info(f"Turn {lobby.turn}: target_sid = {target_sid}")
            
            # Update lobby state
            lobby.current_question_asker = asker_sid
            lobby.current_target = target_sid
            session.commit()
            
            # Get player info
            asker = get_player_by_sid(session, lobby, asker_sid)
            target = get_player_by_sid(session, lobby, target_sid)
            
            if not asker or not target:
                logger.error(f"Error: Could not find asker or target player")
                return
            
            logger.info(f"Turn {lobby.turn}: {asker.username} (SID: {asker_sid}) will ask {target.username} (SID: {target_sid})")
            
            # Send turn update to the asker
            turn_data = {
                'current_asker': asker.username,
                'current_target': None,  # Will be set when question is asked
                'is_my_turn_to_ask': True,
                'is_my_turn_to_answer': False,
                'can_ask': True,
                'can_answer': False,
                'turn': lobby.turn + 1,
                'total_players': len(players)
            }
            
            print(f"DEBUG: Sending turn_update to {asker.username} (SID: {asker_sid})")
            print(f"DEBUG: Turn data: {turn_data}")
            
            self.socketio.emit('turn_update', turn_data, room=asker_sid)
            print(f"DEBUG: Turn update sent to {asker.username}")
            
            # Send spectator turn update to room (spectators will handle this event)
            spectator_turn_data = {
                'current_asker': asker.username,
                'current_target': None,  # Don't show target until question is asked
                'turn': lobby.turn + 1,
                'total_players': len(players)
            }
            logger.info(f"Sending spectator_turn_update to room: {room}")
            self.socketio.emit('spectator_turn_update', spectator_turn_data, room=room)
            
            # If asker is AI, have AI ask question
            if asker.is_ai:
                logger.info(f"AI {asker.username} is the asker, calling ai_ask_question_with_delay")
                ai_ask_question_with_delay(self.socketio, lobby, asker_sid, target_sid, lobby.location, self, delay=4)
            else:
                logger.info(f"Human {asker.username} is the asker, waiting for manual question")
            
            self.update_activity()
            
        except Exception as e:
            logger.error(f"Error starting next turn: {e}")
        finally:
            if session:
                close_db_session(session)
    
    def handle_question(self, asker_sid, target_sid, question, room="main"):
        """Handle a question being asked."""
        session = SessionLocal()
        try:
            lobby = get_lobby(session, room)
            
            if lobby.state != 'playing':
                return
            
            if lobby.current_question_asker != asker_sid or lobby.current_target != target_sid:
                return
            
            # Add question to chat
            asker = get_player_by_sid(session, lobby, asker_sid)
            target = get_player_by_sid(session, lobby, target_sid)
            
            if asker and target:
                message = f"{asker.username} asks {target.username}: {question}"
                add_message(session, lobby, message)
                logger.info(f"DEBUG: Added question message to database: {message}")
                
                # Send question to all players
                self.socketio.emit('question_asked', {
                    'asker': asker.username,
                    'target': target.username,
                    'question': question,
                    'asker_sid': asker_sid,
                    'target_sid': target_sid
                }, room=room)
                
                # Send updated turn info with target now visible
                players = get_players(session, lobby)
                for player in players:
                    if not player.is_ai:
                        # After a question is asked, the asker can no longer ask (they've used their turn)
                        # Only the target can answer
                        is_asking = False  # No one can ask after a question is asked
                        is_answering = (player.sid == target_sid)
                        turn_data = {
                            'current_asker': asker.username,
                            'current_target': target.username,  # Now show the target
                            'is_my_turn_to_ask': is_asking,
                            'is_my_turn_to_answer': is_answering,
                            'can_ask': is_asking,
                            'can_answer': is_answering,
                            'turn': lobby.turn + 1,
                            'total_players': len(players)
                        }
                        self.socketio.emit('turn_update', turn_data, room=player.sid)
                
                # If target is AI, have AI answer
                if target.is_ai:
                    logger.info(f"DEBUG: Target {target.username} is AI, calling ai_answer_with_delay")
                    ai_answer_with_delay(self.socketio, lobby, target_sid, question, lobby.location, self)
                else:
                    logger.info(f"DEBUG: Target {target.username} is human, waiting for manual answer")
            
            self.update_activity()
            
        except Exception as e:
            logger.error(f"Error handling question: {e}")
        finally:
            session.close()
    
    def handle_answer(self, target_sid, answer, room="main"):
        """Handle an answer to a question."""
        session = SessionLocal()
        try:
            lobby = get_lobby(session, room)
            
            if lobby.state != 'playing':
                logger.info(f"DEBUG: handle_answer called but game state is {lobby.state}, not playing")
                return
            
            if lobby.current_target != target_sid:
                logger.info(f"DEBUG: handle_answer called for target_sid {target_sid} but current_target is {lobby.current_target}")
                return
            
            target = get_player_by_sid(session, lobby, target_sid)
            if target:
                logger.info(f"DEBUG: Processing answer from {target.username}: {answer}")
                message = f"{target.username} answers: {answer}"
                add_message(session, lobby, message)
                
                # Only emit answer_given for human players (AI players emit ai_answer)
                if not target.is_ai:
                    self.socketio.emit('answer_given', {
                        'target': target.username,
                        'answer': answer,
                        'target_sid': target_sid
                    }, room=room)
                
                # Increment question count and check for voting
                lobby.question_count += 1
                logger.info(f"DEBUG: Question count incremented to {lobby.question_count}")
                session.commit()
                
                # Send question count update to all players
                questions_until_vote = max(0, 5 - lobby.question_count)
                self.socketio.emit('question_count_update', {
                    'question_count': lobby.question_count,
                    'questions_until_vote': questions_until_vote,
                    'can_vote': lobby.question_count >= 5
                }, room=room)
                
                # Move to next turn (no automatic voting)
                lobby.turn += 1
                logger.info(f"DEBUG: Turn incremented to {lobby.turn}")
                session.commit()
                self.start_next_turn(room)
            else:
                logger.info(f"DEBUG: handle_answer called but target player not found for sid {target_sid}")
            
            self.update_activity()
            
        except Exception as e:
            logger.error(f"Error handling answer: {e}")
        finally:
            session.close()
    
    def start_voting(self, room="main"):
        """Start the voting phase."""
        session = SessionLocal()
        try:
            lobby = get_lobby(session, room)
            players = get_players(session, lobby)
            
            if lobby.state != 'playing':
                return
            
            lobby.state = 'voting'
            session.commit()
            
            logger.info(f"DEBUG: Starting voting with {len(players)} players")
            
            # Clear previous votes
            clear_votes(session, lobby)
            
            # Add voting start message to chat
            add_message(session, lobby, "🗳️ Voting has begun! Each player must vote for someone or choose to pass.")
            
            # Send voting start event to all players
            voting_players = [{'sid': p.sid, 'username': p.username, 'is_ai': p.is_ai} for p in players]
            logger.info(f"DEBUG: Sending voting_started with players: {voting_players}")
            self.socketio.emit('voting_started', {
                'players': voting_players
            }, room=room)
            
            # Send initial vote status
            self.socketio.emit('vote_status_update', {
                'total_votes': 0,
                'total_players': len(players),
                'message': f"0/{len(players)} players have voted"
            }, room=room)
            
            # Have AI players vote automatically
            for player in players:
                if player.is_ai:
                    logger.info(f"DEBUG: AI {player.username} will vote automatically")
                    ai_vote_with_delay(self.socketio, lobby, players, player.sid, self)
            
            self.update_activity()
            
        except Exception as e:
            logger.error(f"Error starting voting: {e}")
        finally:
            session.close()
    
    def handle_vote(self, voter_sid, voted_for_sid, room="main"):
        """Handle a player's vote."""
        session = SessionLocal()
        try:
            lobby = get_lobby(session, room)
            
            if lobby.state != 'voting':
                logger.info(f"DEBUG: Vote rejected - game state is {lobby.state}")
                return
            
            from models.database import Vote
            # Record the vote
            vote = Vote(voter_sid=voter_sid, voted_for_sid=voted_for_sid, lobby_id=lobby.id)
            session.add(vote)
            session.commit()
            
            # Get voter and target names for logging
            voter = get_player_by_sid(session, lobby, voter_sid)
            if voted_for_sid == 'pass':
                target_name = 'pass'
            else:
                target = get_player_by_sid(session, lobby, voted_for_sid)
                target_name = target.username if target else voted_for_sid
            
            voter_name = voter.username if voter else voter_sid
            
            # Add vote message to chat
            if voted_for_sid == 'pass':
                message = f"{voter_name} chose to pass"
            else:
                message = f"{voter_name} voted for {target_name}"
            add_message(session, lobby, message)
            
            # Check if all players have voted
            players = get_players(session, lobby)
            total_votes = session.query(Vote).filter_by(lobby_id=lobby.id).count()
            
            logger.info(f"DEBUG: Vote recorded - {voter_name} voted for {target_name}")
            logger.info(f"DEBUG: Total votes: {total_votes}/{len(players)}")
            
            # Send vote status update
            self.socketio.emit('vote_status_update', {
                'total_votes': total_votes,
                'total_players': len(players),
                'message': f"{total_votes}/{len(players)} players have voted"
            }, room=room)
            
            if total_votes >= len(players):
                logger.info(f"DEBUG: All players have voted, processing results...")
                self.process_voting_results(room)
            
            self.update_activity()
            
        except Exception as e:
            logger.error(f"Error handling vote: {e}")
        finally:
            session.close()
    
    def request_vote(self, requester_sid, room="main"):
        """Handle a player's request to start voting."""
        session = SessionLocal()
        try:
            lobby = get_lobby(session, room)
            
            if lobby.state != 'playing':
                logger.info(f"DEBUG: Vote request rejected - game state is {lobby.state}")
                return False, "Game is not in playing state"
            
            if lobby.question_count < 5:
                logger.info(f"DEBUG: Vote request rejected - only {lobby.question_count} questions asked")
                return False, f"Need at least 5 questions before voting (currently {lobby.question_count})"
            
            # Check if voting is already in progress
            if lobby.state == 'voting':
                return False, "Voting is already in progress"
            
            logger.info(f"DEBUG: Starting voting by player request after {lobby.question_count} questions")
            self.start_voting(room)
            return True, "Voting started"
            
        except Exception as e:
            logger.error(f"Error requesting vote: {e}")
            return False, "Error starting vote"
        finally:
            session.close()
    
    def process_voting_results(self, room="main"):
        """Process voting results and determine winner."""
        session = SessionLocal()
        try:
            lobby = get_lobby(session, room)
            players = get_players(session, lobby)
            
            # Count votes (including passes)
            vote_counts = {}
            pass_count = 0
            
            for player in players:
                count = get_vote_count(session, lobby, player.sid)
                vote_counts[player.sid] = count
            
            # Count pass votes
            pass_count = get_vote_count(session, lobby, 'pass')
            
            logger.info(f"DEBUG: Vote counts: {vote_counts}, Pass count: {pass_count}")
            
            # Find player(s) with most votes (excluding passes)
            if vote_counts:
                max_votes = max(vote_counts.values())
                eliminated = [sid for sid, count in vote_counts.items() if count == max_votes]
            else:
                # All votes were passes
                eliminated = []
                max_votes = 0
            
            # Determine winner
            if not eliminated:
                # All votes were passes or no votes cast
                if pass_count > 0:
                    message = f"Everyone passed! No one was eliminated. The game continues!"
                    add_message(session, lobby, message)
                    
                    # Continue game
                    self.socketio.emit('voting_results', {
                        'message': message,
                        'all_passed': True
                    }, room=room)
                    
                    # Reset for next round
                    lobby.state = 'playing'
                    lobby.question_count = 0
                    session.commit()
                    self.start_next_turn(room)
                else:
                    # No votes cast (shouldn't happen)
                    message = "No votes were cast. The game continues!"
                    add_message(session, lobby, message)
                    
                    # Continue game
                    self.socketio.emit('voting_results', {
                        'message': message
                    }, room=room)
                    
                    # Reset for next round
                    lobby.state = 'playing'
                    lobby.question_count = 0
                    session.commit()
                    self.start_next_turn(room)
            elif len(eliminated) == 1:
                eliminated_sid = eliminated[0]
                eliminated_player = get_player_by_sid(session, lobby, eliminated_sid)
                
                if eliminated_player.is_ai:
                    # Humans win - they voted out the AI
                    message = f"Humans win! {eliminated_player.username} (the AI) was eliminated!"
                    self.end_game(room, "humans", message)
                else:
                    # AI wins - humans voted out a human
                    message = f"AI wins! {eliminated_player.username} was eliminated!"
                    self.end_game(room, "ai", message)
            else:
                # Tie
                if len(players) == 2:
                    # 1v1 tie - humans win
                    message = "Tie in 1v1 game! Humans win by default!"
                    self.end_game(room, "humans", message)
                else:
                    # 3+ player tie - eliminate both
                    eliminated_names = []
                    for sid in eliminated:
                        player = get_player_by_sid(session, lobby, sid)
                        if player:
                            eliminated_names.append(player.username)
                    
                    message = f"Tie! Both {', '.join(eliminated_names)} were eliminated!"
                    add_message(session, lobby, message)
                    
                    # Check if game should continue
                    remaining_players = [p for p in players if p.sid not in eliminated]
                    if len(remaining_players) < 2:
                        # Not enough players left
                        self.end_game(room, "ai", "Not enough players remaining. AI wins!")
                    else:
                        # Continue game
                        self.socketio.emit('voting_results', {
                            'eliminated': eliminated,
                            'message': message
                        }, room=room)
                        
                        # Reset for next round
                        lobby.state = 'playing'
                        lobby.question_count = 0
                        session.commit()
                        self.start_next_turn(room)
            
        except Exception as e:
            logger.error(f"Error processing voting results: {e}")
        finally:
            session.close()
    
    def end_game(self, room="main", winner="", message=""):
        """End the game and announce winner."""
        session = SessionLocal()
        try:
            lobby = get_lobby(session, room)
            
            add_message(session, lobby, message)
            
            logger.info(f"DEBUG: Game ending - Winner: {winner}, Message: {message}")
            
            # Increment win counter
            if winner == "humans":
                counter = increment_human_wins(session, room)
                logger.info(f"DEBUG: Human wins incremented. Total: {counter.human_wins} humans, {counter.ai_wins} AI")
            elif winner == "ai":
                counter = increment_ai_wins(session, room)
                logger.info(f"DEBUG: AI wins incremented. Total: {counter.human_wins} humans, {counter.ai_wins} AI")
            
            # Send win counter update to all players
            win_counter = get_win_counter(session, room)
            logger.info(f"DEBUG: Sending win counter update: {win_counter.human_wins} humans, {win_counter.ai_wins} AI")
            
            self.socketio.emit('game_ended', {
                'winner': winner,
                'message': message
            }, room=room)
            
            # Use unified reset for game completion
            self.unified_reset(room, "Game completed", preserve_win_counter=True)
            
        except Exception as e:
            logger.error(f"Error ending game: {e}")
        finally:
            session.close()
    
    def _perform_database_reset(self, room="main", preserve_win_counter=True):
        """Perform the actual database reset operations."""
        logger.info(f"DEBUG: Performing database reset for room: {room}")
        session = SessionLocal()
        try:
            # Get current win counter before reset
            win_counter = get_win_counter(session, room)
            logger.info(f"DEBUG: Preserving win counter: {{'human_wins': {win_counter.human_wins}, 'ai_wins': {win_counter.ai_wins}}}")
            
            # Clear all game data
            session.query(Message).filter(Message.lobby_id == room).delete()
            session.query(Player).filter(Player.lobby_id == room).delete()
            session.query(Lobby).filter(Lobby.id == room).delete()
            
            # Create fresh lobby
            get_lobby(session, room)
            
            # Restore win counter if preserving
            if preserve_win_counter:
                # The win counter should already exist, but let's make sure it's preserved
                # The WinCounter table is separate and should persist
                logger.info(f"DEBUG: Win counter restored: {{'human_wins': {win_counter.human_wins}, 'ai_wins': {win_counter.ai_wins}}}")
            
            session.commit()
            logger.info(f"DEBUG: Database reset completed successfully!")
            
        except Exception as e:
            logger.error(f"Error in database reset: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def unified_reset(self, room="main", reason="", preserve_win_counter=True):
        """Unified reset function for all reset types."""
        logger.info(f"DEBUG: Unified reset requested for room: {room}, reason: {reason}")
        try:
            # Set reset flag to prevent new joins
            self.is_resetting = True
            
            # Stop all timers
            self.stop_inactivity_timer()
            self.stop_warning_timer()
            
            # Perform database reset
            self._perform_database_reset(room, preserve_win_counter=preserve_win_counter)
            
            # Send reset message to all clients
            reset_message = f"🎮 {reason} - Game reset! Ready for new players to join and start a new game!"
            self.socketio.emit('game_reset', {'message': reset_message}, room=room)
            
            # Send win counter update after database reset completes
            session = SessionLocal()
            try:
                win_counter_after_reset = get_win_counter(session, room)
                logger.info(f"DEBUG: Sending win counter update after reset: {win_counter_after_reset.human_wins} humans, {win_counter_after_reset.ai_wins} AI")
                self.socketio.emit('win_counter_update', {
                    'human_wins': win_counter_after_reset.human_wins,
                    'ai_wins': win_counter_after_reset.ai_wins
                }, room=room)
                logger.info(f"DEBUG: Win counter update event sent after reset")
            except Exception as e:
                logger.error(f"Error sending win counter update after reset: {e}")
            finally:
                session.close()
            
            # Clear reset flag after a short delay to allow clients to process the reset
            def clear_flag():
                time.sleep(1)
                self.is_resetting = False
                logger.info(f"DEBUG: Reset flag cleared after {reason}")
            
            thread = threading.Thread(target=clear_flag)
            thread.daemon = True
            thread.start()
            
            logger.info(f"DEBUG: Unified reset completed for {reason}")
            
        except Exception as e:
            logger.error(f"Error in unified reset: {e}")
            self.is_resetting = False
    
    def update_activity(self):
        """Update the last activity timestamp and reset timer if game is active."""
        session = SessionLocal()
        try:
            lobby = get_lobby(session, room="main")
            # Only update activity and reset timer if game is actively playing
            if lobby.state in ['playing', 'voting']:
                self.last_activity = time.time()
                logger.info(f"Activity updated at {self.last_activity}")
                if self.inactivity_timer:
                    self.inactivity_timer.cancel()
                self.reset_inactivity_timer()
        except Exception as e:
            logger.error(f"Error updating activity: {e}")
        finally:
            session.close()

    def get_question_count(self, room="main"):
        """Get the current question count for a room."""
        session = SessionLocal()
        try:
            lobby = get_lobby(session, room)
            return lobby.question_count
        except Exception as e:
            logger.error(f"Error getting question count: {e}")
            return 0
        finally:
            session.close()
    
    def stop_inactivity_timer(self):
        """Stop the inactivity timer."""
        if self.inactivity_timer:
            self.inactivity_timer.cancel()
            self.inactivity_timer = None
    
    def reset_inactivity_timer(self, room="main"):
        """Reset the inactivity timer with 5-minute timeout and 1-minute warning."""
        # Stop any existing timers
        self.stop_inactivity_timer()
        self.stop_warning_timer()
        
        # Only start timer if game is active
        session = SessionLocal()
        try:
            lobby = get_lobby(session, room)
            if lobby.state in ['playing', 'voting']:
                # Start warning timer (4 minutes = 240 seconds)
                self.warning_timer = threading.Timer(240.0, self.handle_warning, args=[room])
                self.warning_timer.daemon = True
                self.warning_timer.start()
                
                # Start inactivity timer (5 minutes = 300 seconds)
                self.inactivity_timer = threading.Timer(300.0, self.handle_inactivity, args=[room])
                self.inactivity_timer.daemon = True
                self.inactivity_timer.start()
                
                logger.info(f"DEBUG: Inactivity timers started - warning in 4 minutes, reset in 5 minutes")
        except Exception as e:
            logger.error(f"Error resetting inactivity timer: {e}")
        finally:
            session.close()
    
    def handle_warning(self, room="main"):
        """Handle inactivity warning (1 minute before reset)."""
        current_time = time.time()
        if current_time - self.last_activity >= 240:  # 4 minutes
            logger.info(f"Inactivity warning for room {room}")
            self.socketio.emit('game_update', {
                'log': '⚠️ Warning: Game will reset in 1 minute due to inactivity!',
                'error': True
            }, room=room)
    
    def handle_inactivity(self, room="main"):
        """Handle inactivity timeout (5 minutes)."""
        current_time = time.time()
        if current_time - self.last_activity >= 300:  # 5 minutes
            logger.info(f"Inactivity timeout for room {room}")
            self.unified_reset(room, "Inactivity timeout", preserve_win_counter=True)
    
    def stop_warning_timer(self):
        """Stop the warning timer."""
        if self.warning_timer:
            self.warning_timer.cancel()
            self.warning_timer = None
    
    def pause_inactivity_timer(self):
        """Pause the inactivity timer during AI operations."""
        if self.inactivity_timer:
            self.inactivity_timer.cancel()
        if self.warning_timer:
            self.warning_timer.cancel()
        logger.info("Inactivity timers paused during AI operation")

    def resume_inactivity_timer(self):
        """Resume the inactivity timer after AI operations."""
        self.update_activity()
        logger.info("Inactivity timers resumed after AI operation")

    def clear_reset_flag(self):
        """Clear the reset flag to allow new joins and game starts."""
        self.is_resetting = False
        logger.info("DEBUG: Reset flag cleared") 