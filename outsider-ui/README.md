# The Outsider - React UI

A modern, minimalist black and white UI for The Outsider game built with React, TypeScript, and Tailwind CSS.

## Features

- **Clean Minimalist Design**: Black and white aesthetic with modern typography
- **Animated Background**: Subtle geometric animations for visual interest
- **Persistent Win Bar**: Real-time display of humans vs AI score
- **Responsive Sidebars**: Context-aware sidebars for different game states
- **Real-time Chat**: Game chat with message types and auto-scrolling

## Component Structure

```
src/
├── components/
│   ├── background/
│   │   └── AnimatedBackground.tsx    # Persistent animated background
│   ├── layout/
│   │   ├── WinBar.tsx                # Persistent score display
│   │   └── MainLayout.tsx            # Main layout wrapper
│   ├── screens/
│   │   └── LoginScreen.tsx           # Initial login screen
│   ├── sidebar/
│   │   ├── Sidebar.tsx               # Base sidebar component
│   │   ├── MainMenuSidebar.tsx       # Main menu state
│   │   ├── LobbyWaitingSidebar.tsx   # Lobby waiting state
│   │   └── GamePlayingSidebar.tsx    # Active game state
│   └── game/
│       └── GameChat.tsx              # Main game chat interface
├── App.tsx                           # Main app component
├── index.tsx                         # Entry point
└── index.css                         # Tailwind CSS imports
```

## Design System

### Colors
- **Primary**: Black (#0a0a0a) and White (#fafafa)
- **Grays**: 9-level gray scale from #f5f5f5 to #171717
- **Accents**: Minimal use of red for warnings, blue/green for message types

### Typography
- **Headers**: Light weight, increased tracking
- **Body**: Regular weight, clean sans-serif
- **Monospace**: Used for codes and timers

### Components
- **Buttons**: Two variants (primary/secondary) with hover states
- **Inputs**: Transparent backgrounds with subtle borders
- **Sidebars**: Fixed width with consistent padding and borders

## Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start development server:
   ```bash
   npm start
   ```

3. Build for production:
   ```bash
   npm run build
   ```

## Environment Variables

Create a `.env` file in the root:

```
REACT_APP_API_URL=http://localhost:5000
REACT_APP_SOCKET_URL=http://localhost:5000
```

## Integration with Backend

The UI is designed to work with the Flask-SocketIO backend. Key integration points:

- **Socket.IO Events**: Real-time game updates
- **REST API**: Stats, lobby management
- **WebSocket**: Chat and game state synchronization

## UI States

1. **Login**: Simple username entry
2. **Main Menu**: Create/join lobby options
3. **Lobby Waiting**: Player list and ready state
4. **Game Active**: Chat, voting, and game actions
5. **Game End**: Results and return to lobby

## Animations

- **Background**: Floating geometric shapes
- **Transitions**: Smooth state changes
- **Hover Effects**: Subtle interactive feedback
- **Loading States**: Minimal progress indicators
