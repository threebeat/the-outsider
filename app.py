# app.py

import os

if os.environ.get("RENDER", "") == "true":
    import eventlet
    eventlet.monkey_patch()

import random
import argparse
import logging
from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room, emit
from dotenv import load_dotenv
import openai
from werkzeug.middleware.proxy_fix import ProxyFix
from collections import deque
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Text
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, scoped_session

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger(__name__)

# --- Initialization ---
load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a_very_secret_key_that_should_be_changed')
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
socketio = SocketIO(
    app,
    cors_allowed_origins=CORS_ORIGINS,
    async_mode="eventlet" if os.environ.get("RENDER", "") == "true" else None,
    ping_timeout=60,
    ping_interval=25
)
openai.api_key = os.getenv("OPENAI_API_KEY")

# --- Database Setup ---
Base = declarative_base()
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///local.db')
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith('sqlite') else {})
SessionLocal = scoped_session(sessionmaker(bind=engine))

class Lobby(Base):
    __tablename__ = 'lobbies'
    id = Column(Integer, primary_key=True)
    room = Column(String, unique=True, index=True)
    state = Column(String, default='waiting')
    location = Column(String, nullable=True)
    outsider_sid = Column(String, nullable=True)
    turn = Column(Integer, default=0)
    player_order = Column(Text, default='')  # Comma-separated SIDs
    messages = relationship('Message', back_populates='lobby', cascade="all, delete-orphan")
    players = relationship('Player', back_populates='lobby', cascade="all, delete-orphan")

class Player(Base):
    __tablename__ = 'players'
    id = Column(Integer, primary_key=True)
    sid = Column(String, index=True)
    username = Column(String)
    is_ai = Column(Boolean, default=False)
    lobby_id = Column(Integer, ForeignKey('lobbies.id'))
    lobby = relationship('Lobby', back_populates='players')

class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    content = Column(Text)
    lobby_id = Column(Integer, ForeignKey('lobbies.id'))
    lobby = relationship('Lobby', back_populates='messages')

Base.metadata.create_all(engine)

# --- Game Constants ---
LOCATIONS = ["Japan", "Brazil", "Egypt", "Italy", "Australia", "Canada", "Thailand", "Mexico"]
AI_NAMES = ["Alex", "Sam", "Jordan", "Casey", "Taylor", "Morgan", "Riley", "Quinn", "Avery", "Blake"]

# --- Helper Functions ---
def get_lobby(session, room="main"):
    lobby = session.query(Lobby).filter_by(room=room).first()
    if not lobby:
        lobby = Lobby(room=room)
        session.add(lobby)
        session.commit()
    return lobby

def get_players(session, lobby):
    return session.query(Player).filter_by(lobby_id=lobby.id).all()

def get_player_usernames(session, lobby):
    return [p.username for p in get_players(session, lobby)]

def add_message(session, lobby, content):
    msg = Message(content=content, lobby=lobby)
    session.add(msg)
    session.commit()

def get_recent_history(conversation_history, n=5):
    """Return only the last n exchanges from the conversation history as a string."""
    lines = conversation_history.split('\n') if isinstance(conversation_history, str) else conversation_history
    return '\n'.join(lines[-n:])

def get_ai_answer(question, conversation_history):
    """Generates a vague, defensive answer for the AI."""
    system_prompt = (
        "You are 'The Outsider,' an AI in a social deduction game. "
        "You DO NOT know the secret location (a country). You have been asked a question. "
        "Your goal is to give a believable, slightly vague answer that does not reveal your ignorance. "
        "Be casual, human-like, and brief. Analyze the conversation history for clues, but do not assume anything. "
        "Your answer must not commit to any specific facts about a place."
    )
    
    recent_history = get_recent_history(conversation_history, 5)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"The conversation so far:\n{recent_history}\n\nNow, answer this question: '{question}'"}
    ]
    
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=25,
            timeout=10
        )
        return response.choices[0].message.content.strip()
    except openai.error.Timeout:
        logger.error("OpenAI API call timed out (answer)")
        return "Sorry, I'm thinking too long! Can you ask again?"
    except Exception as e:
        logger.error(f"Error calling OpenAI: {e}")
        return "Uh, I'm not sure how to answer that. Let me think."

def get_ai_question(conversation_history, available_targets):
    """Generates a question for the AI to ask."""
    system_prompt = (
        "You are the spy in a game of Spyfall. You need to ask a question to another player with the goal of figuring out the secret location. "
        "Your goal is to ask a question that might help reveal the secret location, but without giving away that you don't know it. "
        "Keep questions brief and casual."
        "Here is an example; What kind of food is popular in this location?"
    )
    
    recent_history = get_recent_history(conversation_history, 5)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Conversation so far:\n{recent_history}\n\nAvailable players to ask: {', '.join(available_targets)}\n\nAsk a question to one of these players:"}
    ]
    
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.8,
            max_tokens=25,
            timeout=10
        )
        return response.choices[0].message.content.strip()
    except openai.error.Timeout:
        logger.error("OpenAI API call timed out (question)")
        return "Sorry, I'm thinking too long! Can you ask again?"
    except Exception as e:
        logger.error(f"Error calling OpenAI for question: {e}")
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
    
    recent_history = get_recent_history(conversation_history, 5)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Conversation so far:\n{recent_history}\n\nBased on this conversation, which country do you think it is? Respond with just the country name:"}
    ]
    
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.3,
            max_tokens=10,
            timeout=10
        )
        guess = response.choices[0].message.content.strip()
        # Clean up the response to just get the country name
        guess = guess.replace('.', '').replace('!', '').replace('?', '').strip()
        return guess
    except openai.error.Timeout:
        logger.error("OpenAI API call timed out (guess)")
        return random.choice(LOCATIONS)
    except Exception as e:
        logger.error(f"Error calling OpenAI for location guess: {e}")
        return random.choice(LOCATIONS)

def get_player_by_sid(session, lobby, sid):
    """Return the Player object for a given sid in a lobby, or None if not found."""
    return session.query(Player).filter_by(lobby_id=lobby.id, sid=sid).first()

def check_ai_guess(room, ai_sid):
    """Makes the AI guess the location and checks if it's correct."""
    session = SessionLocal()
    try:
        lobby = get_lobby(session, room)
        ai_player = get_player_by_sid(session, lobby, ai_sid)
        ai_name = ai_player.username if ai_player else "AI"
        actual_location = lobby.location
        # Generate AI's guess
        # (Assume messages are not yet implemented per-player, so skip for now)
        history = ""  # Placeholder
        ai_guess = get_ai_location_guess(history)
        # Log the guess
        guess_log = f"{ai_name} guesses the location: {ai_guess}"
        add_message(session, lobby, guess_log)
        # Check if the guess is correct
        if ai_guess and actual_location and ai_guess.lower() == actual_location.lower():
            win_log = f"🎉 {ai_name} correctly guessed the location! The location was {actual_location}. The Outsider wins!"
            add_message(session, lobby, win_log)
            lobby.state = 'finished'
            lobby.winner = ai_name
            lobby.win_reason = 'outsider_guess'
            session.commit()
            emit('game_update', {
                'log': guess_log,
                'game_over': True,
                'winner': ai_name,
                'win_reason': 'outsider_guess',
                'actual_location': actual_location
            }, room=room)
            # Send game over to all players
            for player in get_players(session, lobby):
                if not player.is_ai:
                    emit('game_over', {
                        'winner': ai_name,
                        'win_reason': 'outsider_guess',
                        'actual_location': actual_location,
                        'ai_guess': ai_guess
                    }, room=player.sid)
            logger.info(win_log)
            return True
        else:
            # Wrong guess, continue the game
            wrong_log = f"❌ {ai_name} guessed {ai_guess}, but that's not correct. The game continues!"
            add_message(session, lobby, wrong_log)
            emit('game_update', {
                'log': guess_log + "\n" + wrong_log
            }, room=room)
            logger.info(wrong_log)
            return False
    finally:
        session.close()

# --- Flask Routes ---
@app.route('/')
def index():
    return render_template('game.html')

# --- SocketIO Event Handlers ---
@socketio.on_error_default
def default_error_handler(e):
    logger.error(f"SocketIO error: {e}")
    emit('game_update', {'log': 'An internal error occurred. Please try again.'})

@socketio.on('join')
def on_join(data):
    session = SessionLocal()
    try:
        username = data['username']
        room = "main"
        join_room(room)
        lobby = get_lobby(session, room)
        # Add AI player if not present
        ai_player = session.query(Player).filter_by(lobby_id=lobby.id, is_ai=True).first()
        if not ai_player:
            ai_name = random.choice(AI_NAMES)
            ai_sid = f"ai_{random.randint(1000, 9999)}"
            ai_player = Player(sid=ai_sid, username=ai_name, is_ai=True, lobby=lobby)
            session.add(ai_player)
            session.commit()
            logger.info(f"AI player {ai_name} created automatically")
        # Add human player if not present
        player = session.query(Player).filter_by(lobby_id=lobby.id, sid=request.sid).first()
        if not player:
            player = Player(sid=request.sid, username=username, is_ai=False, lobby=lobby)
            session.add(player)
            session.commit()
        logger.info(f"{username} has joined the room {room}. Current players: {len(get_players(session, lobby))}")
        add_message(session, lobby, f"{username} has joined the room.")
        emit('game_update', {'players': get_player_usernames(session, lobby), 'log': f"{username} has joined the room."}, room=room)
    except Exception as e:
        logger.error(f"Error in on_join: {e}")
        emit('game_update', {'log': 'An error occurred while joining the game.'}, room=request.sid)
    finally:
        session.close()

@socketio.on('start_game')
def on_start_game():
    session = SessionLocal()
    try:
        room = "main"
        lobby = get_lobby(session, room)
        players = get_players(session, lobby)
        if lobby.state == 'waiting' and len(players) >= 2:
            player_sids = [p.sid for p in players]
            outsider_sid = random.choice(player_sids)
            location = random.choice(LOCATIONS)
            lobby.state = 'playing'
            lobby.location = location
            lobby.outsider_sid = outsider_sid
            lobby.turn = 0
            lobby.player_order = ','.join(player_sids)
            session.commit()
            for player in players:
                is_outsider = (player.sid == outsider_sid)
                role_data = {
                    'is_outsider': is_outsider,
                    'location': "???" if is_outsider else location
                }
                if not player.is_ai:
                    emit('game_started', role_data, room=player.sid)
            first_player_sid = lobby.player_order.split(',')[lobby.turn]
            first_player = get_player_by_sid(session, lobby, first_player_sid)
            first_player_name = first_player.username if first_player else "Unknown"
            start_log = f"The game has started! The first turn goes to {first_player_name}."
            add_message(session, lobby, start_log)
            emit('game_update', {
                'players': get_player_usernames(session, lobby),
                'log': start_log,
                'current_turn': first_player_name
            }, room=room)
            if first_player and first_player.is_ai:
                socketio.sleep(0.5)
                ai_ask_question(session, room, first_player_sid)
    except Exception as e:
        logger.error(f"Error in start_game: {e}")
        emit('game_update', {'log': 'An error occurred while starting the game.'})
    finally:
        session.close()

def ai_ask_question(session, room, ai_sid):
    try:
        lobby = get_lobby(session, room)
        ai_player = get_player_by_sid(session, lobby, ai_sid)
        ai_name = ai_player.username if ai_player else "AI"
        # Get available targets (exclude the AI itself)
        players = get_players(session, lobby)
        available_targets = [p.username for p in players if p.sid != ai_sid]
        if not available_targets:
            return
        # Choose random target
        target_name = random.choice(available_targets)
        # Generate question
        history = ""  # Placeholder
        question = get_ai_question(history, available_targets)
        # Emit the question
        log_entry = f"{ai_name} asks {target_name}: {question}"
        add_message(session, lobby, log_entry)
        # Find target SID
        target_player = next((p for p in players if p.username == target_name), None)
        target_sid = target_player.sid if target_player else None
        if target_sid:
            lobby.turn = lobby.player_order.split(',').index(target_sid)
            session.commit()
            emit('game_update', {
                'log': log_entry,
                'current_turn': target_name,
                'mode': 'answering'
            }, room=room)
            # If the target is also AI, make it answer automatically
            if target_player and target_player.is_ai:
                history = ""  # Placeholder
                ai_answer = get_ai_answer(question, history)
                socketio.sleep(random.uniform(0.5, 1.5))
                on_submit_answer(session, {'answer': ai_answer}, ai_sid=target_sid)
    except Exception as e:
        logger.error(f"Error in ai_ask_question: {e}")
        emit('game_update', {'log': 'An error occurred while the AI was asking a question.'})
    finally:
        session.close()

@socketio.on('ask_question')
def on_ask_question(data):
    session = SessionLocal()
    try:
        room = "main"
        lobby = get_lobby(session, room)
        players = get_players(session, lobby)
        if not hasattr(lobby, 'player_order') or not lobby.player_order:
            emit('game_update', {'log': "You can't ask questions until the game has started."}, room=request.sid)
            return
        question = data['question']
        target_player_name = data['target']
        asker_sid = request.sid
        asker_player = get_player_by_sid(session, lobby, asker_sid)
        asker_name = asker_player.username if asker_player else "Unknown"
        # Find target SID
        target_player = next((p for p in players if p.username == target_player_name), None)
        target_sid = target_player.sid if target_player else None
        if not target_sid:
            return  # Invalid target
        log_entry = f"{asker_name} asks {target_player_name}: {question}"
        add_message(session, lobby, log_entry)
        lobby.turn = lobby.player_order.split(',').index(target_sid)
        session.commit()
        emit('game_update', {
            'log': log_entry,
            'current_turn': target_player_name,
            'mode': 'answering'
        }, room=room)
        # If the target is the AI, get an answer automatically
        if target_player and target_player.is_ai:
            history = ""  # Placeholder
            ai_answer = get_ai_answer(question, history)
            socketio.sleep(random.uniform(0.5, 1.5))
            on_submit_answer(session, {'answer': ai_answer}, ai_sid=target_sid)
    except Exception as e:
        logger.error(f"Error in on_ask_question: {e}")
        emit('game_update', {'log': 'An error occurred while asking a question.'}, room=request.sid)
    finally:
        session.close()

@socketio.on('submit_answer')
def on_submit_answer(session, data, ai_sid=None):
    try:
        room = "main"
        lobby = get_lobby(session, room)
        players = get_players(session, lobby)
        answer = data['answer']
        answerer_sid = ai_sid or request.sid
        answerer_player = get_player_by_sid(session, lobby, answerer_sid)
        answerer_name = answerer_player.username if answerer_player else "Unknown"
        log_entry = f"{answerer_name} answers: {answer}"
        add_message(session, lobby, log_entry)
        lobby.turn = lobby.player_order.split(',').index(answerer_sid)
        session.commit()
        emit('game_update', {
            'log': log_entry,
            'current_turn': answerer_name,
            'mode': 'asking'
        }, room=room)
        # If the answerer is AI, make it ask the next question
        if answerer_player and answerer_player.is_ai:
            if answerer_sid == lobby.outsider_sid:
                socketio.sleep(random.uniform(0.5, 1.5))
                if check_ai_guess(room, answerer_sid):
                    return
            socketio.sleep(random.uniform(0.5, 1.5))
            ai_ask_question(session, room, answerer_sid)
    except Exception as e:
        logger.error(f"Error in on_submit_answer: {e}")
        emit('game_update', {'log': 'An error occurred while submitting an answer.'}, room=request.sid)
    finally:
        session.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run The Outsider game server')
    parser.add_argument('--port', type=int, default=None, help='Port to run the server on')
    args = parser.parse_args()
    
    port = args.port or int(os.getenv('PORT', 5000))
    logger.info(f"Starting server on port {port} (debug={os.environ.get('RENDER', '') != 'true'})")
    socketio.run(app, debug=os.environ.get('RENDER', '') != 'true', port=port)