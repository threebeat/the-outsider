"""
Game constants for The Outsider.

This module contains all constant values used throughout the game,
including locations, AI names, game states, and configuration values.
"""

# Game locations for Spyfall-style gameplay
LOCATIONS = [
    "Airport", "Bank", "Beach", "Casino", "Cathedral", "Circus Tent",
    "Corporate Party", "Crusader Army", "Day Spa", "Embassy", "Hospital",
    "Hotel", "Military Base", "Movie Studio", "Museum", "Ocean Liner",
    "Passenger Train", "Pirate Ship", "Polar Station", "Police Station",
    "Restaurant", "School", "Service Station", "Space Station", "Submarine",
    "Supermarket", "Theater", "University", "World War II Squad", "Zoo"
]

# Gender-neutral AI player names
AI_NAMES = [
    "Alex", "Blake", "Casey", "Drew", "Ellis", "Finley", "Gray", "Harper",
    "Indigo", "Jules", "Kai", "Lane", "Morgan", "Nova", "Ocean", "Parker",
    "Quinn", "River", "Sage", "Taylor", "Avery", "Cameron", "Dakota", "Emery"
]

# Game state constants
GAME_STATES = {
    'WAITING': 'waiting',
    'PLAYING': 'playing', 
    'VOTING': 'voting',
    'FINISHED': 'finished'
}

# Message types
MESSAGE_TYPES = {
    'CHAT': 'chat',
    'QUESTION': 'question',
    'ANSWER': 'answer',
    'SYSTEM': 'system',
    'AI_THINKING': 'ai_thinking'
}

# Game configuration
GAME_CONFIG = {
    'MAX_QUESTIONS': 5,
    'MIN_PLAYERS': 1,
    'MAX_PLAYERS': 8,
    'DEFAULT_AI_DIFFICULTY': 'normal',
    'LOBBY_CLEANUP_HOURS': 24,
    'GAME_RESET_DELAY': 10  # seconds
}

# AI difficulty levels
AI_DIFFICULTIES = {
    'EASY': 'easy',
    'NORMAL': 'normal', 
    'HARD': 'hard'
}

# Winner types
WINNER_TYPES = {
    'HUMANS': 'humans',
    'AI': 'ai',
    'DRAW': 'draw'
}

# Vote reasons
VOTE_REASONS = {
    'OUTSIDER_ELIMINATED': 'Outsider eliminated by vote',
    'WRONG_ELIMINATION': 'Humans eliminated wrong player',
    'AI_GUESSED_LOCATION': 'AI correctly guessed the location',
    'TIME_LIMIT': 'Time limit reached'
}