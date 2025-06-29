import random
import threading
import time
import logging
from openai import OpenAI
from config.settings import OPENAI_API_KEY
from utils.constants import AI_NAMES, LOCATIONS
from models.database import Player

logger = logging.getLogger(__name__)

# Initialize client lazily to avoid import-time issues
_client = None

def get_openai_client():
    """Get OpenAI client, initializing it if needed."""
    global _client
    if _client is None:
        try:
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY environment variable is not set")
            # Set a longer timeout (20 seconds) to handle slow cold starts on Render
            _client = OpenAI(api_key=OPENAI_API_KEY, timeout=20.0)
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {e}")
            # Return a mock client for development/testing
            class MockClient:
                def __init__(self):
                    self.chat = MockChat()
            class MockChat:
                def __init__(self):
                    self.completions = MockCompletions()
            class MockCompletions:
                def create(self, **kwargs):
                    class MockResponse:
                        def __init__(self):
                            self.choices = [MockChoice()]
                    class MockChoice:
                        def __init__(self):
                            self.message = MockMessage()
                    class MockMessage:
                        def __init__(self):
                            self.content = "Mock response (OpenAI not configured)"
                    return MockResponse()
            _client = MockClient()
    return _client

def get_random_ai_name():
    """Get a random AI name."""
    return random.choice(AI_NAMES)

def generate_ai_response(question, location, is_outsider):
    """Generate an AI response to a question."""
    try:
        # AI is always the outsider but must pretend to know the location
        system_prompt = f"""You are playing Spyfall, a social deduction game where players know a specific location except for one outsider (you).
        You are the AI outsider who doesn't know the location, but you MUST pretend that you do know it.
        When answering questions, act like you know the location and give short, confident answers.
        Be vague but convincing - don't give away that you're guessing.
        Keep your answer short (1 sentence max) and natural."""

        response = get_openai_client().chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Question: {question}"}
            ],
            max_tokens=30,
            temperature=0.7,
            timeout=10  # Add timeout to prevent hanging
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        # Return a quick fallback response instead of hanging
        return "It's pretty nice here."

def generate_ai_question(target_name):
    """Generate an AI question for a target player."""
    try:
        system_prompt = f"""You are playing Spyfall, a social deduction game where players know a specific location except for one outsider (you).
        You are the AI outsider who doesn't know the location. You are asking a question to {target_name} to try to figure out which Spyfall location they know.
        Ask a strategic question that could reveal which specific location they're thinking of.
        Focus on: activities, people, objects, atmosphere, sounds, smells, or unique features of Spyfall locations.
        Keep the question short and natural. Don't reveal that you don't know the location."""

        response = get_openai_client().chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate a question to ask this player:"}
            ],
            max_tokens=30,
            temperature=0.8,
            timeout=10  # Add timeout to prevent hanging
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating AI question: {e}")
        # Return a quick fallback question
        return f"What's your favorite thing about this place?"

def ai_vote_random(players, ai_sid):
    """AI votes for a random player (excluding itself), never passes."""
    # Only vote for human players (never pass)
    human_players = [p for p in players if p.sid != ai_sid and not p.is_ai]
    if human_players:
        choice = random.choice(human_players)
        return choice.sid
    return None

def ai_ask_question_with_delay(socketio, lobby, asker_sid, target_sid, location, game_manager=None, delay=3):
    """AI asks a question after a delay."""
    def delayed_question():
        socketio.sleep(delay)
        from models.database import SessionLocal, get_player_by_sid, get_players
        session = SessionLocal()
        try:
            # Pause inactivity timer during AI operation
            if game_manager:
                game_manager.pause_inactivity_timer()
            
            ai_player = get_player_by_sid(session, lobby, asker_sid)
            if not ai_player or not ai_player.is_ai:
                logger.error(f"Error: AI player not found for asker_sid {asker_sid}")
                return
            target_player = get_player_by_sid(session, lobby, target_sid)
            target_name = target_player.username if target_player else "Unknown"
            question = generate_ai_question(target_name)
            question_data = {
                'asker': ai_player.username,
                'target': target_name,
                'question': question,
                'asker_sid': ai_player.sid,
                'target_sid': target_sid
            }
            logger.info(f"AI {ai_player.username} asking question: {question}")
            logger.info(f"Emitting question_asked event: {question_data}")
            players = get_players(session, lobby)
            human_players = [p for p in players if not p.is_ai]
            logger.info(f"Found {len(human_players)} human players to send to")
            for player in human_players:
                logger.info(f"  Sending to {player.username} (SID: {player.sid})")
                socketio.emit('question_asked', question_data, room=player.sid)
            logger.info(f"question_asked event emitted to all human SIDs")
            logger.info(f"Event data sent: asker={question_data['asker']}, target={question_data['target']}, question={question_data['question']}")
            logger.info(f"AI {ai_player.username} asked: {question}")
            
            # Send turn_update to the human player to tell them it's their turn to answer
            if target_player and not target_player.is_ai:
                turn_data = {
                    'current_asker': ai_player.username,
                    'current_target': target_player.username,
                    'is_my_turn_to_ask': False,
                    'is_my_turn_to_answer': True,
                    'can_ask': False,
                    'can_answer': True,
                    'turn': lobby.turn + 1,
                    'total_players': len(players)
                }
                logger.info(f"DEBUG: Sending turn_update to {target_player.username} (SID: {target_sid})")
                logger.info(f"DEBUG: Turn data: {turn_data}")
                socketio.emit('turn_update', turn_data, room=target_sid)
                logger.info(f"DEBUG: Turn update sent to {target_player.username}")
            
            # Resume inactivity timer after AI operation
            if game_manager:
                game_manager.resume_inactivity_timer()
                
        except Exception as e:
            logger.error(f"Error in AI question: {e}")
            # Resume inactivity timer even on error
            if game_manager:
                game_manager.resume_inactivity_timer()
        finally:
            session.close()
    socketio.start_background_task(delayed_question)

def ai_answer_with_delay(socketio, lobby, target_sid, question, location, game_manager=None, delay=2):
    """AI answers a question after a delay."""
    def delayed_answer():
        socketio.sleep(delay)
        from models.database import SessionLocal, get_player_by_sid, get_players, get_messages
        session = SessionLocal()
        try:
            # Pause inactivity timer during AI operation
            if game_manager:
                game_manager.pause_inactivity_timer()
            
            ai_player = get_player_by_sid(session, lobby, target_sid)
            if not ai_player or not ai_player.is_ai:
                logger.error(f"Error: AI player not found for target_sid {target_sid}")
                return
            logger.info(f"DEBUG: AI {ai_player.username} starting to answer question: {question}")
            answer = generate_ai_response(question, location, True)  # AI is always outsider
            ai_answer_data = {
                'answer': answer,
                'question': question,
                'target': ai_player.username,
                'target_sid': target_sid
            }
            logger.info(f"AI {ai_player.username} answering: {answer}")
            players = get_players(session, lobby)
            human_players = [p for p in players if not p.is_ai]
            logger.info(f"Found {len(human_players)} human players to send to")
            for player in human_players:
                logger.info(f"  Sending ai_answer to {player.username} (SID: {player.sid})")
                socketio.emit('ai_answer', ai_answer_data, room=player.sid)
            logger.info(f"AI {ai_player.username} answered: {answer}")
            
            # AI is always the outsider, so always try to guess the location
            logger.info(f"DEBUG: AI {ai_player.username} is outsider, attempting location guess...")
            
            # Check if game is already in voting state - if so, skip location guess
            if lobby.state == 'voting':
                logger.info(f"DEBUG: Game is in voting state, skipping location guess")
                # Just handle turn progression without location guess
                if game_manager:
                    _handle_ai_answer_turn_progression(game_manager, lobby, answer, target_sid, lobby.room)
                return
            
            # Get previous Q&A pairs from the game
            messages = get_messages(session, lobby)
            qa_pairs = []
            
            # Parse messages to extract Q&A pairs
            for msg in messages:
                if "asks" in msg.content and ":" in msg.content:
                    # This is a question
                    parts = msg.content.split(" asks ")
                    if len(parts) == 2:
                        asker = parts[0]
                        rest = parts[1]
                        if ":" in rest:
                            target_and_q = rest.split(": ")
                            if len(target_and_q) == 2:
                                target = target_and_q[0]
                                q_text = target_and_q[1]
                                qa_pairs.append({
                                    'question': q_text,
                                    'answer': None  # Will be filled by next message
                                })
                elif "answers:" in msg.content and qa_pairs:
                    # This is an answer to the last question
                    parts = msg.content.split(" answers: ")
                    if len(parts) == 2:
                        answer_text = parts[1]
                        if qa_pairs and qa_pairs[-1]['answer'] is None:
                            qa_pairs[-1]['answer'] = answer_text
            
            # Add current Q&A pair
            qa_pairs.append({
                'question': question,
                'answer': answer
            })
            
            logger.info(f"DEBUG: AI analyzing {len(qa_pairs)} Q&A pairs for location guess")
            for i, qa in enumerate(qa_pairs):
                logger.info(f"DEBUG: Q&A {i+1}: Q='{qa['question']}' A='{qa['answer']}'")
            
            # Generate location guess - include ALL Q&A pairs including current one
            location_guess = generate_location_guess(question, answer, qa_pairs, location, lobby.question_count + 1)
            
            if location_guess:
                logger.info(f"DEBUG: AI {ai_player.username} guessing location: {location_guess}")
                logger.info(f"DEBUG: Actual location: {location}")
                logger.info(f"DEBUG: Location guess type: {type(location_guess)}, length: {len(location_guess)}")
                logger.info(f"DEBUG: Actual location type: {type(location)}, length: {len(location)}")
                logger.info(f"DEBUG: Location guess lower: '{location_guess.lower()}'")
                logger.info(f"DEBUG: Actual location lower: '{location.lower()}'")
                
                # Check if guess is correct
                is_correct = location_guess.lower() == location.lower()
                logger.info(f"DEBUG: Location comparison result: {is_correct}")
                
                # Add anonymous location guess to chat with appropriate emoji
                from models.database import add_message
                emoji = "🎯" if is_correct else "❌"
                guess_message = f"Someone guessed the location: {location_guess}"
                add_message(session, lobby, guess_message)
                
                # Send anonymous guess to all players
                socketio.emit('location_guess_made', {
                    'guess': location_guess,
                    'message': guess_message,
                    'is_correct': is_correct
                }, room=lobby.room)
                
                if is_correct:
                    logger.info(f"DEBUG: AI {ai_player.username} correctly guessed the location!")
                    logger.info(f"DEBUG: Calling game_manager.end_game with winner='ai'")
                    # AI wins by guessing the location
                    if game_manager:
                        game_manager.end_game(lobby.room, "ai", f"Someone correctly guessed the location: {location}! The AI wins!")
                    else:
                        logger.error(f"ERROR: game_manager is None, cannot end game!")
                else:
                    logger.info(f"DEBUG: AI {ai_player.username} guessed wrong: {location_guess} vs {location}")
                    # Wrong guess - continue game
                    if game_manager:
                        # Handle turn progression manually to avoid immediate voting
                        _handle_ai_answer_turn_progression(game_manager, lobby, answer, target_sid, lobby.room)
            else:
                logger.info(f"DEBUG: AI {ai_player.username} not confident enough to guess")
                # No guess - continue game
                if game_manager:
                    # Handle turn progression manually to avoid immediate voting
                    _handle_ai_answer_turn_progression(game_manager, lobby, answer, target_sid, lobby.room)
            
            # Resume inactivity timer after AI operation
            if game_manager:
                game_manager.resume_inactivity_timer()
            
        except Exception as e:
            logger.error(f"Error in AI answer: {e}")
            # Resume inactivity timer even on error
            if game_manager:
                game_manager.resume_inactivity_timer()
        finally:
            session.close()
    socketio.start_background_task(delayed_answer)

def _handle_ai_answer_turn_progression(game_manager, lobby, answer, target_sid, room):
    """Handle turn progression for AI answers, ensuring location guesses happen before voting."""
    from models.database import SessionLocal, get_player_by_sid, add_message, get_lobby
    session = SessionLocal()
    try:
        # Get a fresh lobby object in this session
        fresh_lobby = get_lobby(session, room)
        if not fresh_lobby:
            logger.error(f"ERROR: Could not find lobby for room {room}")
            return
        
        # Add the AI answer to the database
        target = get_player_by_sid(session, fresh_lobby, target_sid)
        if target:
            message = f"{target.username} answers: {answer}"
            add_message(session, fresh_lobby, message)
        
        # Increment question count
        fresh_lobby.question_count += 1
        logger.info(f"DEBUG: Question count incremented to {fresh_lobby.question_count}")
        session.commit()
        
        # Send question count update to all players
        questions_until_vote = max(0, 5 - fresh_lobby.question_count)
        game_manager.socketio.emit('question_count_update', {
            'question_count': fresh_lobby.question_count,
            'questions_until_vote': questions_until_vote,
            'can_vote': fresh_lobby.question_count >= 5
        }, room=room)
        
        # Move to next turn (no automatic voting)
        fresh_lobby.turn += 1
        logger.info(f"DEBUG: Turn incremented to {fresh_lobby.turn}")
        session.commit()
        game_manager.start_next_turn(room)
        
    except Exception as e:
        logger.error(f"Error in AI answer turn progression: {e}")
    finally:
        session.close()

def ai_vote_with_delay(socketio, lobby, players, ai_sid, game_manager=None, delay=1):
    """AI votes after a delay."""
    # Get the room name before the lobby object becomes detached
    room = lobby.room if hasattr(lobby, 'room') else 'main'
    logger.info(f"DEBUG: AI voting setup for room: {room}")
    
    def delayed_vote():
        socketio.sleep(delay)
        voted_for = ai_vote_random(players, ai_sid)
        if voted_for:
            if voted_for == 'pass':
                logger.info(f"DEBUG: AI {ai_sid} chose to pass")
            else:
                # Find the player name for logging
                target_player = next((p for p in players if p.sid == voted_for), None)
                target_name = target_player.username if target_player else voted_for
                logger.info(f"DEBUG: AI {ai_sid} voting for {target_name} (SID: {voted_for})")
            
            if game_manager:
                logger.info(f"DEBUG: AI calling handle_vote for room: {room}")
                game_manager.handle_vote(ai_sid, voted_for, room)
    
    socketio.start_background_task(delayed_vote)

def generate_location_guess(question, answer, previous_qa_pairs, location, question_count):
    """Generate an AI location guess based on the conversation."""
    try:
        # Build context from previous Q&A pairs
        context = ""
        for qa in previous_qa_pairs:
            context += f"Q: {qa['question']}\nA: {qa['answer']}\n"
        
        logger.info(f"DEBUG: Location guess - Question count: {question_count}")
        logger.info(f"DEBUG: Location guess - Context length: {len(context)}")
        
        if question_count >= 3:
            # After question 3, force a guess with a very aggressive prompt
            system_prompt = f"""You are playing Spyfall, a social deduction game where players know a specific location except for one outsider (you).
            
            You are the AI outsider who doesn't know the location. You have reached question 3 and MUST make your best educated guess.
            
            Available Spyfall locations: {', '.join(LOCATIONS)}
            
            Previous conversation:
            {context}
            
            Latest Q&A:
            Q: {question}
            A: {answer}
            
            Based on ALL the clues from the questions and answers, which Spyfall location do you think the other players know? 
            You MUST choose from the available locations: {', '.join(LOCATIONS)}
            Look for clues about: activities, people, objects, atmosphere, sounds, smells, or unique features.
            Do not say "I don't know" or "not sure" - make your best educated guess based on the conversation.
            If you see ANY location-related clues, use them to make your guess.
            
            IMPORTANT: Return ONLY the location name from the list, nothing else."""

            logger.info(f"DEBUG: Sending forced guess prompt to GPT-4o")
            response = get_openai_client().chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Which Spyfall location do you think this is? Return only the location name."}
                ],
                max_tokens=20,
                temperature=0.2,
                timeout=15  # Add timeout
            )
            
            guess = response.choices[0].message.content.strip()
            logger.info(f"DEBUG: GPT-4o forced guess response: '{guess}'")
            
            # Clean up and extract location
            guess = guess.replace('"', '').replace("'", '').strip()
            
            # Extract location name from response - look for exact matches first
            for loc in LOCATIONS:
                if loc.lower() in guess.lower():
                    logger.info(f"DEBUG: Found location match: {loc}")
                    return loc
            
            # If no exact match, try to extract any capitalized words that might be locations
            words = guess.split()
            for word in words:
                word_clean = word.replace('"', '').replace("'", '').replace(',', '').replace('.', '').strip()
                if word_clean[0].isupper() and len(word_clean) > 2 and word_clean.lower() not in ['the', 'and', 'but', 'for', 'with', 'from', 'this', 'that', 'what', 'when', 'where', 'why', 'how', 'no', 'guess', 'not', 'sure', 'confident', 'i', 'don\'t', 'know', 'have', 'enough', 'information', 'could', 'would', 'should', 'might', 'may', 'based', 'clues', 'provided', 'location', 'think', 'other', 'players', 'know']:
                    # Check if this word matches any location
                    for loc in LOCATIONS:
                        if loc.lower() == word_clean.lower():
                            logger.info(f"DEBUG: Found location match from word extraction: {loc}")
                            return loc
            
            return "Unknown"
        else:
            # For early questions, only guess if we have strong clues
            if len(context) < 50:  # Not enough context yet
                logger.info(f"DEBUG: Not enough context for location guess (length: {len(context)})")
                return None
            
            system_prompt = f"""You are playing Spyfall, a social deduction game where players know a specific location except for one outsider (you).
            
            You are the AI outsider who doesn't know the location. Based on the conversation so far, can you guess which Spyfall location the other players know?
            
            Available Spyfall locations: {', '.join(LOCATIONS)}
            
            Previous conversation:
            {context}
            
            Latest Q&A:
            Q: {question}
            A: {answer}
            
            Based on all this information, can you guess which Spyfall location the other players know? If you see ANY clues, what is your best guess from the available options? If absolutely no clues, say "NO_GUESS"."""

            logger.info(f"DEBUG: Sending regular guess prompt to GPT-4o")
            response = get_openai_client().chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Which Spyfall location do you think this is? Return only the location name."}
                ],
                max_tokens=30,
                temperature=0.3,
                timeout=15  # Add timeout
            )
            
            guess = response.choices[0].message.content.strip()
            logger.info(f"DEBUG: GPT-4o regular guess response: '{guess}'")
            
            # Clean up the response
            if "NO_GUESS" in guess.upper() or "NOT CONFIDENT" in guess.upper() or "NOT SURE" in guess.upper():
                logger.info(f"DEBUG: AI returned NO_GUESS - not confident enough")
                return None
            
            # Extract location name (remove quotes, extra text, etc.)
            guess = guess.replace('"', '').replace("'", '').strip()
            if guess.lower() in ['no guess', 'not sure', 'i don\'t know', 'i don\'t have enough information']:
                logger.info(f"DEBUG: AI returned no guess after cleanup")
                return None
            
            # Extract location name from response - look for exact matches first
            for loc in LOCATIONS:
                if loc.lower() in guess.lower():
                    logger.info(f"DEBUG: Found location match: {loc}")
                    return loc
            
            # If no exact match, try to extract any capitalized words that might be locations
            words = guess.split()
            for word in words:
                word_clean = word.replace('"', '').replace("'", '').replace(',', '').replace('.', '').strip()
                if word_clean[0].isupper() and len(word_clean) > 2 and word_clean.lower() not in ['the', 'and', 'but', 'for', 'with', 'from', 'this', 'that', 'what', 'when', 'where', 'why', 'how', 'no', 'guess', 'not', 'sure', 'confident', 'i', 'don\'t', 'know', 'have', 'enough', 'information', 'could', 'would', 'should', 'might', 'may', 'based', 'clues', 'provided', 'location', 'think', 'other', 'players', 'know']:
                    # Check if this word matches any location
                    for loc in LOCATIONS:
                        if loc.lower() == word_clean.lower():
                            logger.info(f"DEBUG: Found location match from word extraction: {loc}")
                            return loc
                
            logger.info(f"DEBUG: AI returning guess: {guess}")
            return guess
        
    except Exception as e:
        logger.error(f"Error generating location guess: {e}")
        if question_count >= 3:
            return "Unknown"  # Force a guess after Q3 even on error
        return None 