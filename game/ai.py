import random
import asyncio
import threading
import time
from openai import OpenAI
from config.settings import OPENAI_API_KEY
from utils.constants import AI_NAMES, LOCATIONS
from models.database import Player

client = OpenAI(api_key=OPENAI_API_KEY)

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

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Question: {question}"}
            ],
            max_tokens=50,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating AI response: {e}")
        return "It's pretty nice here."

def generate_ai_question(target_name):
    """Generate an AI question for a target player."""
    try:
        system_prompt = f"""You are playing Spyfall, a social deduction game where players know a specific location except for one outsider (you).
        You are the AI outsider who doesn't know the location. You are asking a question to {target_name} to try to figure out which Spyfall location they know.
        Ask a strategic question that could reveal which specific location they're thinking of.
        Focus on: activities, people, objects, atmosphere, sounds, smells, or unique features of Spyfall locations.
        Keep the question short and natural. Don't reveal that you don't know the location."""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate a question to ask this player:"}
            ],
            max_tokens=50,
            temperature=0.8
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating AI question: {e}")
        return f"What's your favorite thing about this place?"

def ai_vote_random(players, ai_sid):
    """AI votes for a random player (excluding itself) or passes."""
    human_players = [p for p in players if p.sid != ai_sid and not p.is_ai]
    
    # Create options: all human players + pass
    options = human_players + ['pass']
    
    if options:
        choice = random.choice(options)
        if choice == 'pass':
            return 'pass'
        else:
            return choice.sid
    return None

def ai_ask_question_with_delay(socketio, lobby, asker_sid, target_sid, location, delay=6):
    """AI asks a question after a delay."""
    def delayed_question():
        socketio.sleep(delay)
        from models.database import SessionLocal, get_player_by_sid, get_players
        session = SessionLocal()
        try:
            ai_player = get_player_by_sid(session, lobby, asker_sid)
            if not ai_player or not ai_player.is_ai:
                print(f"Error: AI player not found for asker_sid {asker_sid}")
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
            print(f"AI {ai_player.username} asking question: {question}")
            print(f"Emitting question_asked event: {question_data}")
            players = get_players(session, lobby)
            human_players = [p for p in players if not p.is_ai]
            print(f"Found {len(human_players)} human players to send to")
            for player in human_players:
                print(f"  Sending to {player.username} (SID: {player.sid})")
                socketio.emit('question_asked', question_data, room=player.sid)
            print(f"question_asked event emitted to all human SIDs")
            print(f"Event data sent: asker={question_data['asker']}, target={question_data['target']}, question={question_data['question']}")
            print(f"AI {ai_player.username} asked: {question}")
        except Exception as e:
            print(f"Error in AI question: {e}")
        finally:
            session.close()
    socketio.start_background_task(delayed_question)

def ai_answer_with_delay(socketio, lobby, target_sid, question, location, game_manager=None, delay=3):
    """AI answers a question after a delay."""
    def delayed_answer():
        socketio.sleep(delay)
        from models.database import SessionLocal, get_player_by_sid, get_players, get_messages
        session = SessionLocal()
        try:
            ai_player = get_player_by_sid(session, lobby, target_sid)
            if not ai_player or not ai_player.is_ai:
                print(f"Error: AI player not found for target_sid {target_sid}")
                return
            print(f"DEBUG: AI {ai_player.username} starting to answer question: {question}")
            answer = generate_ai_response(question, location, True)  # AI is always outsider
            ai_answer_data = {
                'answer': answer,
                'question': question,
                'target': ai_player.username,
                'target_sid': target_sid
            }
            print(f"AI {ai_player.username} answering: {answer}")
            players = get_players(session, lobby)
            human_players = [p for p in players if not p.is_ai]
            print(f"Found {len(human_players)} human players to send to")
            for player in human_players:
                print(f"  Sending ai_answer to {player.username} (SID: {player.sid})")
                socketio.emit('ai_answer', ai_answer_data, room=player.sid)
            print(f"AI {ai_player.username} answered: {answer}")
            
            # AI is always the outsider, so always try to guess the location
            print(f"DEBUG: AI {ai_player.username} is outsider, attempting location guess...")
            
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
            
            print(f"DEBUG: AI analyzing {len(qa_pairs)} Q&A pairs for location guess")
            for i, qa in enumerate(qa_pairs):
                print(f"DEBUG: Q&A {i+1}: Q='{qa['question']}' A='{qa['answer']}'")
            
            # Generate location guess - include ALL Q&A pairs including current one
            location_guess = generate_location_guess(question, answer, qa_pairs, location, lobby.question_count + 1)
            
            if location_guess:
                print(f"DEBUG: AI {ai_player.username} guessing location: {location_guess}")
                print(f"DEBUG: Actual location: {location}")
                print(f"DEBUG: Location guess type: {type(location_guess)}, length: {len(location_guess)}")
                print(f"DEBUG: Actual location type: {type(location)}, length: {len(location)}")
                print(f"DEBUG: Location guess lower: '{location_guess.lower()}'")
                print(f"DEBUG: Actual location lower: '{location.lower()}'")
                
                # Check if guess is correct
                is_correct = location_guess.lower() == location.lower()
                print(f"DEBUG: Location comparison result: {is_correct}")
                
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
                    print(f"DEBUG: AI {ai_player.username} correctly guessed the location!")
                    print(f"DEBUG: Calling game_manager.end_game with winner='ai'")
                    # AI wins by guessing the location
                    if game_manager:
                        game_manager.end_game(lobby.room, "ai", f"Someone correctly guessed the location: {location}! The AI wins!")
                    else:
                        print(f"ERROR: game_manager is None, cannot end game!")
                else:
                    print(f"DEBUG: AI {ai_player.username} guessed wrong: {location_guess} vs {location}")
                    # Wrong guess - continue game
                    if game_manager:
                        # Handle turn progression manually to avoid immediate voting
                        _handle_ai_answer_turn_progression(game_manager, lobby, answer, target_sid, lobby.room)
            else:
                print(f"DEBUG: AI {ai_player.username} not confident enough to guess")
                # No guess - continue game
                if game_manager:
                    # Handle turn progression manually to avoid immediate voting
                    _handle_ai_answer_turn_progression(game_manager, lobby, answer, target_sid, lobby.room)
            
        except Exception as e:
            print(f"Error in AI answer: {e}")
        finally:
            session.close()
    socketio.start_background_task(delayed_answer)

def _handle_ai_answer_turn_progression(game_manager, lobby, answer, target_sid, room):
    """Handle turn progression for AI answers, ensuring location guesses happen before voting."""
    from models.database import SessionLocal, get_player_by_sid, add_message
    session = SessionLocal()
    try:
        # Add the AI answer to the database
        target = get_player_by_sid(session, lobby, target_sid)
        if target:
            message = f"{target.username} answers: {answer}"
            add_message(session, lobby, message)
        
        # Increment question count
        lobby.question_count += 1
        print(f"DEBUG: Question count incremented to {lobby.question_count}")
        session.commit()
        
        # Send question count update to all players
        questions_until_vote = max(0, 5 - lobby.question_count)
        game_manager.socketio.emit('question_count_update', {
            'question_count': lobby.question_count,
            'questions_until_vote': questions_until_vote,
            'can_vote': lobby.question_count >= 5
        }, room=room)
        
        # Move to next turn (no automatic voting)
        lobby.turn += 1
        print(f"DEBUG: Turn incremented to {lobby.turn}")
        session.commit()
        game_manager.start_next_turn(room)
        
    except Exception as e:
        print(f"Error in AI answer turn progression: {e}")
    finally:
        session.close()

def ai_vote_with_delay(socketio, lobby, players, ai_sid, game_manager=None, delay=2):
    """AI votes after a delay."""
    def delayed_vote():
        socketio.sleep(delay)
        voted_for = ai_vote_random(players, ai_sid)
        if voted_for:
            if voted_for == 'pass':
                print(f"DEBUG: AI {ai_sid} chose to pass")
            else:
                # Find the player name for logging
                target_player = next((p for p in players if p.sid == voted_for), None)
                target_name = target_player.username if target_player else voted_for
                print(f"DEBUG: AI {ai_sid} voting for {target_name} (SID: {voted_for})")
            
            if game_manager:
                game_manager.handle_vote(ai_sid, voted_for, lobby.room)
    
    socketio.start_background_task(delayed_vote)

def generate_location_guess(question, answer, previous_qa_pairs, location, question_count):
    """Generate an AI location guess based on the conversation."""
    try:
        # Build context from previous Q&A pairs
        context = ""
        for qa in previous_qa_pairs:
            context += f"Q: {qa['question']}\nA: {qa['answer']}\n"
        
        print(f"DEBUG: Location guess - Question count: {question_count}")
        print(f"DEBUG: Location guess - Context length: {len(context)}")
        print(f"DEBUG: Location guess - Context: {context}")
        
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

            print(f"DEBUG: Sending forced guess prompt to GPT-4o")
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Which Spyfall location do you think this is? Return only the location name."}
                ],
                max_tokens=20,
                temperature=0.2
            )
            
            guess = response.choices[0].message.content.strip()
            print(f"DEBUG: GPT-4o forced guess response: '{guess}'")
            
            # Clean up and extract location
            guess = guess.replace('"', '').replace("'", '').strip()
            
            # Extract location name from response - look for exact matches first
            for loc in LOCATIONS:
                if loc.lower() in guess.lower():
                    print(f"DEBUG: Found location match: {loc}")
                    return loc
            
            # If no exact match, try to extract any capitalized words that might be locations
            words = guess.split()
            for word in words:
                word_clean = word.replace('"', '').replace("'", '').replace(',', '').replace('.', '').strip()
                if word_clean[0].isupper() and len(word_clean) > 2 and word_clean.lower() not in ['the', 'and', 'but', 'for', 'with', 'from', 'this', 'that', 'what', 'when', 'where', 'why', 'how', 'no', 'guess', 'not', 'sure', 'confident', 'i', 'don\'t', 'know', 'have', 'enough', 'information', 'could', 'would', 'should', 'might', 'may', 'based', 'clues', 'provided', 'location', 'think', 'other', 'players', 'know']:
                    # Check if this word matches any location
                    for loc in LOCATIONS:
                        if loc.lower() == word_clean.lower():
                            print(f"DEBUG: Found location match from word extraction: {loc}")
                            return loc
            
            return "Unknown"
            
        else:
            # Before question 3, be very aggressive about guessing
            confidence_prompt = "You should be willing to guess if you see ANY location-related clues."
            if question_count >= 2:
                confidence_prompt = "You should be very willing to guess now. If you see ANY clues about location, make your best guess."
            
            system_prompt = f"""You are playing Spyfall, a social deduction game where players know a specific location except for one outsider (you).
            
            You are the AI outsider who doesn't know the location. Based on the questions asked and answers given, 
            you need to determine if you can guess which Spyfall location the other players know.
            
            Available Spyfall locations: {', '.join(LOCATIONS)}
            
            Current question count: {question_count}
            {confidence_prompt}
            
            Rules:
            1. If you see ANY location-related clues, return just the location name from the available options
            2. Only return "NO_GUESS" if you have absolutely NO clues at all
            3. Look for clues about: activities, people, objects, atmosphere, sounds, smells, or unique features
            4. Be very aggressive about guessing - you're trying to win by figuring out the location
            5. Even vague clues should prompt a guess
            6. Choose from: {', '.join(LOCATIONS)}
            7. IMPORTANT: Return ONLY the location name, nothing else
            
            Previous conversation:
            {context}
            
            Latest Q&A:
            Q: {question}
            A: {answer}
            
            Based on all this information, can you guess which Spyfall location the other players know? If you see ANY clues, what is your best guess from the available options? If absolutely no clues, say "NO_GUESS"."""

            print(f"DEBUG: Sending regular guess prompt to GPT-4o")
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Which Spyfall location do you think this is? Return only the location name."}
                ],
                max_tokens=30,
                temperature=0.3
            )
            
            guess = response.choices[0].message.content.strip()
            print(f"DEBUG: GPT-4o regular guess response: '{guess}'")
            
            # Clean up the response
            if "NO_GUESS" in guess.upper() or "NOT CONFIDENT" in guess.upper() or "NOT SURE" in guess.upper():
                print(f"DEBUG: AI returned NO_GUESS - not confident enough")
                return None
            
            # Extract location name (remove quotes, extra text, etc.)
            guess = guess.replace('"', '').replace("'", '').strip()
            if guess.lower() in ['no guess', 'not sure', 'i don\'t know', 'i don\'t have enough information']:
                print(f"DEBUG: AI returned no guess after cleanup")
                return None
            
            # Extract location name from response - look for exact matches first
            for loc in LOCATIONS:
                if loc.lower() in guess.lower():
                    print(f"DEBUG: Found location match: {loc}")
                    return loc
            
            # If no exact match, try to extract any capitalized words that might be locations
            words = guess.split()
            for word in words:
                word_clean = word.replace('"', '').replace("'", '').replace(',', '').replace('.', '').strip()
                if word_clean[0].isupper() and len(word_clean) > 2 and word_clean.lower() not in ['the', 'and', 'but', 'for', 'with', 'from', 'this', 'that', 'what', 'when', 'where', 'why', 'how', 'no', 'guess', 'not', 'sure', 'confident', 'i', 'don\'t', 'know', 'have', 'enough', 'information', 'could', 'would', 'should', 'might', 'may', 'based', 'clues', 'provided', 'location', 'think', 'other', 'players', 'know']:
                    # Check if this word matches any location
                    for loc in LOCATIONS:
                        if loc.lower() == word_clean.lower():
                            print(f"DEBUG: Found location match from word extraction: {loc}")
                            return loc
                
            print(f"DEBUG: AI returning guess: {guess}")
            return guess
        
    except Exception as e:
        print(f"Error generating location guess: {e}")
        if question_count >= 3:
            return "Unknown"  # Force a guess after Q3 even on error
        return None 