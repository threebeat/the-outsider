# The Outsider - Setup Guide

This project uses a **Flask-SocketIO backend** with a **React frontend** architecture, deployed on Render with PostgreSQL.

## Architecture Overview

```
┌─────────────────┐    HTTP/WebSocket    ┌─────────────────┐
│   React App     │ ◄──────────────────► │ Flask-SocketIO  │
│   (Frontend)    │                      │   (Backend)     │
│   Port 3000     │                      │   Port 5000     │
└─────────────────┘                      └─────────────────┘
                                                    │
                                                    ▼
                                         ┌─────────────────┐
                                         │   PostgreSQL    │
                                         │   (Database)    │
                                         └─────────────────┘
```

## Backend Setup (This Repository)

### 1. Local Development

1. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Up Environment Variables**
   - Copy `.env` file and update values as needed
   - For local development, SQLite is used by default

3. **Initialize Database**
   ```bash
   python database.py
   ```

4. **Run Development Server**
   ```bash
   python app.py
   ```
   
   The backend will be available at `http://localhost:5000`

### 2. API Endpoints

The backend provides both REST API and WebSocket endpoints:

#### REST Endpoints
- `GET /api/health` - Health check
- `GET /api/stats` - Game statistics
- `GET /api/lobbies/active` - List active lobbies
- `GET /api/cleanup` - Clean up inactive lobbies (admin)

#### WebSocket Events
- `create_lobby` - Create a new game lobby
- `join_lobby` - Join an existing lobby
- `start_game` - Start the game
- `ask_question` - Ask a question during the game
- `give_answer` - Give an answer to a question
- `cast_vote` - Cast a vote during voting phase

### 3. Database Models

The backend includes comprehensive models:
- **Lobby** - Game lobbies with state management
- **Player** - Players with AI/human distinction
- **GameMessage** - All game communications
- **Vote** - Voting system with confidence tracking
- **GameSession** - Complete game history
- **GameStatistics** - Win/loss statistics

## Frontend Setup (React App)

### 1. Create React App

```bash
# In a separate directory/repository
npx create-react-app outsider-frontend
cd outsider-frontend

# Install additional dependencies
npm install socket.io-client axios @tailwindcss/forms
npm install -D tailwindcss postcss autoprefixer
```

### 2. Configure Tailwind CSS

```bash
npx tailwindcss init -p
```

Update `tailwind.config.js`:
```javascript
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}
```

### 3. Socket.IO Connection

Create `src/services/socket.js`:
```javascript
import io from 'socket.io-client';

const SOCKET_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:5000';

export const socket = io(SOCKET_URL, {
  autoConnect: false,
  transports: ['websocket', 'polling']
});

export const connectSocket = () => {
  if (!socket.connected) {
    socket.connect();
  }
};

export const disconnectSocket = () => {
  if (socket.connected) {
    socket.disconnect();
  }
};
```

### 4. Environment Variables

Create `.env` in your React app:
```
REACT_APP_BACKEND_URL=http://localhost:5000
REACT_APP_WS_URL=http://localhost:5000
```

## Deployment on Render

### 1. Backend Deployment

1. **Create New Web Service on Render**
   - Connect your repository
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn --worker-class eventlet -w 1 app:app`

2. **Environment Variables on Render**
   ```
   SECRET_KEY=your-production-secret-key-here
   FLASK_ENV=production
   CORS_ORIGINS=https://your-react-app.onrender.com
   DATABASE_URL=(automatically provided by Render PostgreSQL)
   ```

3. **Add PostgreSQL Database**
   - Go to Dashboard → New → PostgreSQL
   - Connect it to your web service
   - DATABASE_URL will be automatically provided

### 2. Frontend Deployment

1. **Create New Static Site on Render**
   - Connect your React app repository
   - Build Command: `npm run build`
   - Publish Directory: `build`

2. **Environment Variables for React**
   ```
   REACT_APP_BACKEND_URL=https://your-backend-app.onrender.com
   REACT_APP_WS_URL=https://your-backend-app.onrender.com
   ```

3. **Update CORS in Backend**
   Update your backend's CORS_ORIGINS environment variable to include your React app's URL.

## Development Workflow

### 1. Local Development
```bash
# Terminal 1: Backend
cd backend-repo
python app.py

# Terminal 2: Frontend
cd frontend-repo
npm start
```

### 2. Testing WebSocket Connection
```javascript
// In your React app
import { socket } from './services/socket';

socket.on('connect', () => {
  console.log('Connected to backend!');
});

socket.emit('create_lobby', {
  name: 'Test Game',
  code: 'TEST123'
});
```

## Key Features Implemented

### Backend Features
- ✅ Real-time multiplayer with Socket.IO
- ✅ PostgreSQL database with SQLAlchemy
- ✅ Comprehensive game state management
- ✅ AI player integration ready
- ✅ Vote tracking and game statistics
- ✅ CORS configured for React frontend
- ✅ Production-ready with proper error handling

### Game Flow
1. **Lobby Creation** - Players create/join lobbies
2. **Game Start** - Automatic AI player addition
3. **Question Phase** - Turn-based questions (5 rounds)
4. **Voting Phase** - Players vote to eliminate the outsider
5. **Results** - Game outcome and statistics
6. **Reset** - Automatic lobby reset for new games

## Next Steps

1. **Create React Frontend** with components for:
   - Lobby creation/joining
   - Game interface with question/answer system
   - Voting interface
   - Results display

2. **Add OpenAI Integration** for smarter AI responses
3. **Implement Advanced Features**:
   - Player statistics dashboard
   - Replay system
   - Multiple game modes

## Troubleshooting

### Common Issues

1. **CORS Errors**: Ensure CORS_ORIGINS includes your frontend URL
2. **Database Connection**: Check DATABASE_URL format for PostgreSQL
3. **Socket Connection**: Verify backend URL in React app
4. **Deployment**: Check Render logs for detailed error messages

### Database Reset
```bash
# Reset database tables (development only)
python -c "from database import Base, engine; Base.metadata.drop_all(engine); Base.metadata.create_all(engine)"
```

This setup provides a solid foundation for a production-ready social deduction game with real-time multiplayer capabilities.