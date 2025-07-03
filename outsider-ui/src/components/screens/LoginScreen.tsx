import React, { useState } from 'react';

interface LoginScreenProps {
  onLogin: (username: string) => void;
}

const LoginScreen: React.FC<LoginScreenProps> = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isGeneratingName, setIsGeneratingName] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate username
    const trimmedUsername = username.trim();
    if (!trimmedUsername) {
      setError('Please enter a name');
      return;
    }
    
    if (trimmedUsername.length < 2) {
      setError('Name must be at least 2 characters');
      return;
    }
    
    if (trimmedUsername.length > 20) {
      setError('Name must be 20 characters or less');
      return;
    }
    
    // Check for valid characters
    if (!/^[a-zA-Z0-9_-]+$/.test(trimmedUsername)) {
      setError('Name can only contain letters, numbers, - and _');
      return;
    }
    
    setError('');
    setIsLoading(true);
    
    // Simulate async login
    setTimeout(() => {
      onLogin(trimmedUsername);
    }, 500);
  };

  const handleRandomName = async () => {
    setIsGeneratingName(true);
    setError('');
    
    try {
      const response = await fetch('/api/random-name', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.name) {
          setUsername(data.name);
        } else {
          setError('No available names found');
        }
      } else {
        // Fallback to client-side random names if API fails
        const fallbackNames = ['Alex', 'Blake', 'Casey', 'Drew', 'Ellis', 'Finley', 'Gray', 'Harper'];
        const randomName = fallbackNames[Math.floor(Math.random() * fallbackNames.length)];
        setUsername(randomName);
      }
    } catch (error) {
      // Fallback to client-side random names if fetch fails
      const fallbackNames = ['Alex', 'Blake', 'Casey', 'Drew', 'Ellis', 'Finley', 'Gray', 'Harper'];
      const randomName = fallbackNames[Math.floor(Math.random() * fallbackNames.length)];
      setUsername(randomName);
    } finally {
      setIsGeneratingName(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div className="max-w-md w-full space-y-8">
        {/* Logo/Title */}
        <div className="text-center space-y-2">
          <h1 className="text-6xl font-light tracking-wider">THE OUTSIDER</h1>
          <p className="text-outsider-gray-500 text-sm tracking-wide">
            A GAME OF DEDUCTION AND DECEPTION
          </p>
        </div>
        
        {/* Login Form */}
        <form onSubmit={handleSubmit} className="mt-12 space-y-6">
          <div className="space-y-4">
            <div className="relative">
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="ENTER YOUR NAME"
                className="input-primary text-center tracking-wider pr-12"
                maxLength={20}
                disabled={isLoading}
                autoFocus
              />
              <button
                type="button"
                onClick={handleRandomName}
                disabled={isLoading || isGeneratingName}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 w-6 h-6 flex items-center justify-center text-outsider-gray-500 hover:text-white transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Generate random name"
              >
                {isGeneratingName ? (
                  <div className="w-4 h-4 border border-outsider-gray-500 border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <span className="text-lg font-light">?</span>
                )}
              </button>
            </div>
            
            {error && (
              <p className="text-red-500 text-sm text-center">{error}</p>
            )}
          </div>
          
          <button
            type="submit"
            disabled={isLoading}
            className="btn-primary w-full tracking-wider"
          >
            {isLoading ? 'JOINING...' : 'JOIN GAME'}
          </button>
        </form>
        
        {/* Instructions */}
        <div className="mt-12 space-y-2 text-center text-outsider-gray-600 text-xs">
          <p>FIND THE AI OUTSIDER WHO DOESN'T KNOW THE LOCATION</p>
          <p>OR BLEND IN AS THE OUTSIDER AND GUESS THE SECRET</p>
          <p className="text-outsider-gray-700 text-xs mt-3">
            Click ? to generate a random name
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginScreen;