# The Outsider - Social Deduction Game

A Flask-SocketIO based social deduction game where players try to identify the AI "outsider" who doesn't know the location. The AI plays as the outsider and tries to guess the location based on the conversation.

## Features

- **Real-time multiplayer gameplay** using Flask-SocketIO
- **AI integration** with OpenAI GPT-4 for intelligent outsider gameplay
- **Turn-based question system** with random player selection
- **Voting mechanism** after 5 questions to eliminate suspected outsiders
- **Spectator mode** for players joining mid-game
- **Automatic game reset** after completion or inactivity
- **Win counter tracking** for humans vs AI
- **Classic Spyfall locations** for authentic gameplay

## Game Rules

1. **Setup**: Players join the game and an AI player is automatically added
2. **Location Assignment**: All human players know the same location, except the AI (the outsider)
3. **Question Phase**: Players take turns asking questions to other players
4. **AI Behavior**: The AI pretends to know the location while trying to guess it
5. **Voting**: After 5 questions, players vote to eliminate someone
6. **Winning Conditions**:
   - **Humans win**: If they vote out the AI outsider
   - **AI wins**: If it correctly guesses the location or humans vote out a human player

## Technical Architecture

### Backend Structure
```
the-outsider/
├── app.py                 # Main Flask application entry point
├── config/
│   └── settings.py        # Configuration and environment variables
├── game/
│   ├── logic.py          # Core game logic and state management
│   └── ai.py             # AI player behavior and OpenAI integration
├── models/
│   └── database.py       # SQLAlchemy models and database operations
├── socket_handlers/
│   └── handlers.py       # WebSocket event handlers
├── utils/
│   └── constants.py      # Game constants (locations, AI names)
├── static/
│   └── game.js          # Frontend JavaScript
└── templates/
    └── game.html        # Main game interface
```

### Key Components

- **GameManager**: Manages game state, turn progression, and voting
- **AI Module**: Handles AI question generation, answers, and location guessing
- **Database Models**: Lobby, Player, Message, Vote, and WinCounter
- **Socket Handlers**: Real-time communication between clients and server

## Setup and Installation

### Prerequisites
- Python 3.8+
- OpenAI API key
- PostgreSQL (for production) or SQLite (for development)

### Environment Variables
```bash
SECRET_KEY=your_secret_key
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=postgresql://user:pass@localhost/dbname  # or sqlite:///local.db
CORS_ORIGINS=*  # or specific origins for production
```

### Installation
```bash
pip install -r requirements.txt
python app.py
```

## Deployment

The application is configured for deployment on Render with:
- `render.yaml` for service configuration
- `Procfile` for process management
- Automatic database reset on startup
- Environment-based configuration

## Code Quality

### Recent Cleanup Improvements
- **Proper logging**: Replaced all `print()` statements with structured logging
- **Error handling**: Added comprehensive try-catch blocks and validation
- **Code organization**: Modular structure with clear separation of concerns
- **Documentation**: Added docstrings and inline comments
- **Unused imports**: Removed unused dependencies (asyncio, etc.)

### Logging Levels
- `INFO`: Game events, player actions, AI behavior
- `ERROR`: Exceptions, failed operations, validation errors
- `DEBUG`: Detailed debugging information (when needed)

## Game Flow

1. **Join Phase**: Players join with unique usernames
2. **Start Game**: Minimum 2 players required (1 human + 1 AI)
3. **Question Rounds**: Random turn order, players ask questions to targets
4. **AI Responses**: AI generates contextual answers while trying to guess location
5. **Voting Phase**: After 5 questions, players vote to eliminate someone
6. **Game End**: Winner determined and game resets automatically

## Contributing

When contributing to this project:
1. Use proper logging instead of print statements
2. Add error handling for all external operations
3. Follow the existing modular structure
4. Add docstrings for new functions
5. Test thoroughly before submitting changes 