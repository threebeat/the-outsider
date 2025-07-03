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

# Lobby state constants
LOBBY_STATES = {
    'OPEN': 'open',      # Players can join
    'ACTIVE': 'active'   # Game in progress, no joining allowed
}

# Message types
MESSAGE_TYPES = {
    'CHAT': 'chat',
    'QUESTION': 'question',
    'ANSWER': 'answer',
    'SYSTEM': 'system',
    'AI_THINKING': 'ai_thinking'
}

# Lobby constants
MAX_PLAYERS_PER_LOBBY = 12  # Total players including 1-3 AI players

# Game configuration
GAME_CONFIG = {
    'MAX_QUESTIONS': 5,
    'MIN_PLAYERS': 1,
    'MAX_PLAYERS': MAX_PLAYERS_PER_LOBBY,
    'LOBBY_CLEANUP_HOURS': 24,
    'GAME_RESET_DELAY': 10  # seconds
}

# AI difficulty removed - not a feature we want

# AI personality types
AI_PERSONALITIES = [
    'cautious',      # Asks safe questions, gives vague answers
    'aggressive',    # Asks direct questions, challenges others
    'analytical',    # Asks logical questions, methodical approach
    'friendly',      # Asks personal questions, builds rapport
    'deceptive',     # Misdirects, creates confusion
    'observant'      # Notices patterns, asks follow-up questions
]

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