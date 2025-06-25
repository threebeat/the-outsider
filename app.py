# app.py

import os
import random
import argparse
from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room, emit
from dotenv import load_dotenv
import openai

# --- Initialization ---
load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_very_secret_key_that_should_be_changed'
socketio = SocketIO(app)
openai.api_key = os.getenv("OPENAI_API_KEY")

# --- Game State Management ---
# In a real app, you'd use a database. For this prototype, a dictionary is fine.
games = {} 
LOCATIONS = ["Japan", "Brazil", "Egypt", "Italy", "Australia", "Canada", "Thailand", "Mexico"]

# AI player names for variety
AI_NAMES = ["Alex", "Sam", "Jordan", "Casey", "Taylor", "Morgan", "Riley", "Quinn", "Avery", "Blake"]

# --- Helper Functions ---
def get_ai_answer(question, conversation_history):
    """Generates a vague, defensive answer for the AI."""
    system_prompt = (
        "You are 'The Outsider,' an AI in a social deduction game. "
        "You DO NOT know the secret location (a country). You have been asked a question. "
        "Your goal is to give a believable, slightly vague answer that does not reveal your ignorance. "
        "Be casual, human-like, and brief. Analyze the conversation history for clues, but do not assume anything. "
        "Your answer must not commit to any specific facts about a place."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"The conversation so far:\n{conversation_history}\n\nNow, answer this question: '{question}'"}
    ]
    
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=40
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return "Uh, I'm not sure how to answer that. Let me think."

def get_ai_question(conversation_history, available_targets):
    """Generates a question for the AI to ask."""
    system_prompt = (
        "You are the spy in a game of Spyfall. You need to ask a question to another player with the goal of figuring out the secret location. "
        "Your goal is to ask a question that might help reveal the secret location, but without giving away that you don't know it. "
        "Keep questions brief and casual."
        "Here is an example; What kind of food is popular in this location?"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Conversation so far:\n{conversation_history}\n\nAvailable players to ask: {', '.join(available_targets)}\n\nAsk a question to one of these players:"}
    ]
    
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.8,
            max_tokens=60
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling OpenAI for question: {e}")
        return "Is the location considered a tourist destination?"

def create_ai_player():
    """Creates an AI player with a random name."""
    ai_name = random.choice(AI_NAMES)
    ai_sid = f"ai_{random.randint(1000, 9999)}"
    return {
        "username": ai_name,
        "is_ai": True,
        "sid": ai_sid
    }

def get_ai_location_guess(conversation_history):
    """Generates a location guess for the AI based on conversation clues."""
    system_prompt = (
        "You are the spy in a game of Spyfall. Based on the conversation so far, "
        "you need to guess which country the other players are talking about. "
        "Analyze all the clues, hints, and answers given by other players. "
        "Consider cultural references, food, landmarks, weather, customs, etc. "
        "You must respond with ONLY the name of a country from this list: "
        f"{', '.join(LOCATIONS)}. "
        "If you're not confident, make your best guess based on the strongest clues. "
        "Respond with just the country name, nothing else."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Conversation so far:\n{conversation_history}\n\nBased on this conversation, which country do you think it is? Respond with just the country name:"}
    ]
    
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.3,
            max_tokens=20
        )
        guess = response.choices[0].message.content.strip()
        # Clean up the response to just get the country name
        guess = guess.replace('.', '').replace('!', '').replace('?', '').strip()
        return guess
    except Exception as e:
        print(f"Error calling OpenAI for location guess: {e}")
        return random.choice(LOCATIONS)

def check_ai_guess(room, ai_sid):
    """Makes the AI guess the location and checks if it's correct."""
    ai_name = games[room]['players'][ai_sid]['username']
    actual_location = games[room]['location']
    
    # Generate AI's guess
    history = "\n".join(games[room]['conversation'])
    ai_guess = get_ai_location_guess(history)
    
    # Log the guess
    guess_log = f"{ai_name} guesses the location: {ai_guess}"
    games[room]['conversation'].append(guess_log)
    
    # Check if the guess is correct
    if ai_guess.lower() == actual_location.lower():
        # AI wins!
        win_log = f"🎉 {ai_name} correctly guessed the location! The location was {actual_location}. The Outsider wins!"
        games[room]['conversation'].append(win_log)
        games[room]['state'] = 'finished'
        games[room]['winner'] = ai_name
        games[room]['win_reason'] = 'outsider_guess'
        
        emit('game_update', {
            'log': guess_log,
            'game_over': True,
            'winner': ai_name,
            'win_reason': 'outsider_guess',
            'actual_location': actual_location
        }, room=room)
        
        # Send game over to all players
        for sid, player in games[room]['players'].items():
            if not player['is_ai']:
                emit('game_over', {
                    'winner': ai_name,
                    'win_reason': 'outsider_guess',
                    'actual_location': actual_location,
                    'ai_guess': ai_guess
                }, room=sid)
        
        return True
    else:
        # Wrong guess, continue the game
        wrong_log = f"❌ {ai_name} guessed {ai_guess}, but that's not correct. The game continues!"
        games[room]['conversation'].append(wrong_log)
        
        emit('game_update', {
            'log': guess_log + "\n" + wrong_log
        }, room=room)
        
        return False

# --- Flask Routes ---
@app.route('/')
def index():
    # For simplicity, we'll just have one game room: "main"
    # A real app would have dynamic room creation.
    return render_template('game.html')

# --- SocketIO Event Handlers ---
@socketio.on('join')
def on_join(data):
    username = data['username']
    room = "main" # Hardcoded room for simplicity
    join_room(room)

    if room not in games:
        games[room] = {
            "players": {},
            "state": "waiting",
            "conversation": [],
            "ai_player": None
        }
        
        # Create AI player automatically
        ai_player = create_ai_player()
        games[room]["ai_player"] = ai_player
        games[room]["players"][ai_player["sid"]] = {
            "username": ai_player["username"], 
            "is_ai": True
        }
        print(f"AI player {ai_player['username']} created automatically")
    
    games[room]["players"][request.sid] = {"username": username, "is_ai": False}
    
    print(f"{username} has joined the room {room}. Current players: {len(games[room]['players'])}")
    emit('game_update', {'players': [p['username'] for p in games[room]['players'].values()], 'log': "A new player has joined."}, room=room)


@socketio.on('start_game')
def on_start_game():
    room = "main"
    if games[room]['state'] == 'waiting' and len(games[room]['players']) >= 2: # Min 2 players (1 human + 1 AI)
        # --- Assign Roles ---
        player_sids = list(games[room]['players'].keys())
        outsider_sid = random.choice(player_sids)
        location = random.choice(LOCATIONS)
        
        games[room]['state'] = 'playing'
        games[room]['location'] = location
        games[room]['outsider_sid'] = outsider_sid
        games[room]['turn'] = 0 # Index in the player_sids list
        games[room]['player_order'] = player_sids

        # --- Send roles to each player ---
        for sid, player in games[room]['players'].items():
            is_outsider = (sid == outsider_sid)
            
            role_data = {
                'is_outsider': is_outsider,
                'location': "???" if is_outsider else location
            }
            if not player['is_ai']:  # Only send to human players
                emit('game_started', role_data, room=sid)

        # --- Announce game start to everyone ---
        first_player_sid = games[room]['player_order'][games[room]['turn']]
        first_player_name = games[room]['players'][first_player_sid]['username']
        start_log = f"The game has started! The first turn goes to {first_player_name}."
        games[room]['conversation'].append(start_log)
        emit('game_update', {
            'players': [p['username'] for p in games[room]['players'].values()], 
            'log': start_log,
            'current_turn': first_player_name
        }, room=room)
        
        # If AI goes first, make it ask a question
        if games[room]['players'][first_player_sid]['is_ai']:
            socketio.sleep(2)  # Small delay to make it feel natural
            ai_ask_question(room, first_player_sid)


def ai_ask_question(room, ai_sid):
    """Makes the AI ask a question."""
    ai_name = games[room]['players'][ai_sid]['username']
    
    # Get available targets (exclude the AI itself)
    available_targets = [p['username'] for sid, p in games[room]['players'].items() 
                        if sid != ai_sid]
    
    if not available_targets:
        return
    
    # Choose random target
    target_name = random.choice(available_targets)
    
    # Generate question
    history = "\n".join(games[room]['conversation'])
    question = get_ai_question(history, available_targets)
    
    # Emit the question
    log_entry = f"{ai_name} asks {target_name}: {question}"
    games[room]['conversation'].append(log_entry)
    
    # Find target SID
    target_sid = None
    for sid, player in games[room]['players'].items():
        if player['username'] == target_name:
            target_sid = sid
            break
    
    if target_sid:
        # The turn now passes to the person being questioned
        games[room]['turn'] = games[room]['player_order'].index(target_sid)
        
        emit('game_update', {
            'log': log_entry,
            'current_turn': target_name,
            'mode': 'answering'
        }, room=room)
        
        # If the target is also AI, make it answer automatically
        if games[room]['players'][target_sid]['is_ai']:
            history = "\n".join(games[room]['conversation'])
            ai_answer = get_ai_answer(question, history)
            # We add a small delay to make it feel less instant
            socketio.sleep(random.uniform(2, 5))
            on_submit_answer({'answer': ai_answer}, ai_sid=target_sid)


@socketio.on('ask_question')
def on_ask_question(data):
    room = "main"
    question = data['question']
    target_player_name = data['target']
    
    asker_sid = request.sid
    asker_name = games[room]['players'][asker_sid]['username']
    
    # Find target SID
    target_sid = None
    for sid, player in games[room]['players'].items():
        if player['username'] == target_player_name:
            target_sid = sid
            break
            
    if not target_sid: return # Invalid target

    log_entry = f"{asker_name} asks {target_player_name}: {question}"
    games[room]['conversation'].append(log_entry)
    
    # The turn now passes to the person being questioned
    games[room]['turn'] = games[room]['player_order'].index(target_sid)
    
    emit('game_update', {
        'log': log_entry,
        'current_turn': target_player_name,
        'mode': 'answering' # Tell the UI to show the answer box for this player
    }, room=room)
    
    # If the target is the AI, get an answer automatically
    if games[room]['players'][target_sid]['is_ai']:
        history = "\n".join(games[room]['conversation'])
        ai_answer = get_ai_answer(question, history)
        # We add a small delay to make it feel less instant
        socketio.sleep(random.uniform(2, 5))
        on_submit_answer({'answer': ai_answer}, ai_sid=target_sid)


@socketio.on('submit_answer')
def on_submit_answer(data, ai_sid=None):
    room = "main"
    answer = data['answer']
    
    # Use ai_sid if provided, otherwise get from request
    answerer_sid = ai_sid or request.sid
    answerer_name = games[room]['players'][answerer_sid]['username']
    
    log_entry = f"{answerer_name} answers: {answer}"
    games[room]['conversation'].append(log_entry)
    
    # The turn now passes to the person who just answered to ask the next question
    games[room]['turn'] = games[room]['player_order'].index(answerer_sid)
    
    emit('game_update', {
        'log': log_entry,
        'current_turn': answerer_name,
        'mode': 'asking' # Tell UI it's back to asking mode
    }, room=room)
    
    # If the answerer is AI, make it ask the next question
    if games[room]['players'][answerer_sid]['is_ai']:
        # Check if this AI is the outsider and should guess
        if answerer_sid == games[room]['outsider_sid']:
            # AI outsider gets a chance to guess after answering
            socketio.sleep(random.uniform(1, 3))  # Small delay before guessing
            if check_ai_guess(room, answerer_sid):
                return  # Game is over, don't continue
        
        # Continue with normal turn (ask next question)
        socketio.sleep(random.uniform(2, 4))  # Small delay
        ai_ask_question(room, answerer_sid)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run The Outsider game server')
    parser.add_argument('--port', type=int, default=None, help='Port to run the server on')
    args = parser.parse_args()
    
    # Priority: command line arg > environment variable > default
    port = args.port or int(os.getenv('PORT', 5000))
    socketio.run(app, debug=True, port=port)