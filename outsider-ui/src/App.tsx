import React, { useState } from 'react';
import AnimatedBackground from './components/background/AnimatedBackground';
import WinBar from './components/layout/WinBar';
import MainLayout from './components/layout/MainLayout';
import LoginScreen from './components/screens/LoginScreen';
import MainMenuSidebar from './components/sidebar/MainMenuSidebar';
import LobbyWaitingSidebar from './components/sidebar/LobbyWaitingSidebar';
import GamePlayingSidebar from './components/sidebar/GamePlayingSidebar';
import GameChat from './components/game/GameChat';

// Mock data types
interface Player {
  id: string;
  username: string;
  isAI: boolean;
  isHost?: boolean;
  isAlive?: boolean;
  hasVoted?: boolean;
}

interface Message {
  id: string;
  type: 'chat' | 'system' | 'question' | 'answer';
  sender?: string;
  content: string;
  timestamp: Date;
  isAI?: boolean;
}

type AppState = 'login' | 'menu' | 'lobby' | 'game';

function App() {
  const [appState, setAppState] = useState<AppState>('login');
  const [username, setUsername] = useState('');
  const [currentLobby, setCurrentLobby] = useState<{
    code: string;
    name: string;
  } | null>(null);
  
  // Mock data for demonstration
  const mockPlayers: Player[] = [
    { id: '1', username: username || 'Player1', isAI: false, isHost: true, isAlive: true },
    { id: '2', username: 'Alex', isAI: true, isAlive: true },
    { id: '3', username: 'Blake', isAI: true, isAlive: true },
    { id: '4', username: 'Casey', isAI: true, isAlive: false },
  ];
  
  const mockMessages: Message[] = [
    {
      id: '1',
      type: 'system',
      content: 'Game started! The location is: Beach',
      timestamp: new Date(),
    },
    {
      id: '2',
      type: 'chat',
      sender: 'Alex',
      content: 'So, what do you all think about the weather here?',
      timestamp: new Date(),
      isAI: true,
    },
    {
      id: '3',
      type: 'question',
      sender: username || 'Player1',
      content: 'Blake, what are you wearing?',
      timestamp: new Date(),
    },
    {
      id: '4',
      type: 'answer',
      sender: 'Blake',
      content: 'Just my usual outfit, nothing special for this place.',
      timestamp: new Date(),
      isAI: true,
    },
  ];

  const handleLogin = (name: string) => {
    setUsername(name);
    setAppState('menu');
  };

  const handleJoinLobby = (code: string) => {
    setCurrentLobby({ code, name: 'Test Lobby' });
    setAppState('lobby');
  };

  const handleCreateLobby = () => {
    setCurrentLobby({ code: 'ABC123', name: 'New Lobby' });
    setAppState('lobby');
  };

  const handleStartGame = () => {
    setAppState('game');
  };

  const handleLogout = () => {
    setUsername('');
    setCurrentLobby(null);
    setAppState('login');
  };

  const handleLeaveLobby = () => {
    setCurrentLobby(null);
    setAppState('menu');
  };

  const handleSendMessage = (message: string) => {
    console.log('Sending message:', message);
  };

  const handleVote = (targetId: string) => {
    console.log('Voting for player:', targetId);
  };

  const handleEndGame = () => {
    setAppState('lobby');
  };

  // Render appropriate sidebar based on state
  const renderSidebar = () => {
    switch (appState) {
      case 'menu':
        return (
          <MainMenuSidebar
            username={username}
            onJoinLobby={handleJoinLobby}
            onCreateLobby={handleCreateLobby}
            onLogout={handleLogout}
          />
        );
      case 'lobby':
        return (
          <LobbyWaitingSidebar
            lobbyCode={currentLobby?.code || ''}
            lobbyName={currentLobby?.name || ''}
            players={mockPlayers.slice(0, 3)}
            currentUserId="1"
            isHost={true}
            onStartGame={handleStartGame}
            onLeaveLobby={handleLeaveLobby}
          />
        );
      case 'game':
        return (
          <GamePlayingSidebar
            location="Beach"
            isOutsider={false}
            currentPlayer={username}
            players={mockPlayers}
            phase="questioning"
            timeRemaining={120}
            onVote={handleVote}
            onEndGame={handleEndGame}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="relative min-h-screen">
      {/* Persistent Background */}
      <AnimatedBackground />
      
      {/* Persistent Win Bar */}
      <WinBar />
      
      {/* Main Content */}
      {appState === 'login' ? (
        <LoginScreen onLogin={handleLogin} />
      ) : (
        <MainLayout sidebar={renderSidebar()}>
          <GameChat
            messages={appState === 'game' ? mockMessages : []}
            currentUser={username}
            isGameActive={appState === 'lobby' || appState === 'game'}
            onSendMessage={handleSendMessage}
          />
        </MainLayout>
      )}
    </div>
  );
}

export default App;
