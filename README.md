# The Outsider - Social Deduction Game

A web-based social deduction game where players must identify "The Outsider" - the one player who doesn't know the secret location. Built with Flask, Socket.IO, and OpenAI.

## Features

- **Real-time multiplayer gameplay** using WebSockets
- **AI player integration** - An AI player automatically joins each game
- **Dynamic question generation** using OpenAI GPT-3.5-turbo
- **Automatic AI responses** that feel natural and human-like
- **Location guessing mechanics** for the AI outsider
- **Responsive web interface**

## How to Play

1. **Join the game** by entering your username
2. **Start the game** when ready (minimum 2 players: 1 human + 1 AI)
3. **Ask questions** to other players to gather clues about the location
4. **Answer questions** when it's your turn
5. **Identify the Outsider** or **guess the location** if you're the Outsider

## Game Rules

- One player is randomly assigned as "The Outsider" and doesn't know the secret location
- All other players know the location and must help identify the Outsider
- Players take turns asking and answering questions
- The Outsider wins by correctly guessing the location
- Other players win by identifying the Outsider

## Technology Stack

- **Backend**: Flask, Flask-SocketIO
- **Frontend**: HTML, CSS, JavaScript
- **AI**: OpenAI GPT-3.5-turbo
- **Deployment**: Render

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key
- `SECRET_KEY`: Flask secret key (auto-generated on Render)

## Local Development

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables in `.env` file
4. Run the app: `python app.py`
5. Visit `http://localhost:5000`

## Deployment

This app is configured for deployment on Render. The `render.yaml` file contains the deployment configuration.

## License

MIT License 