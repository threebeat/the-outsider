import React, { useState, useRef, useEffect } from 'react';

interface Message {
  id: string;
  type: 'chat' | 'system' | 'question' | 'answer';
  sender?: string;
  content: string;
  timestamp: Date;
  isAI?: boolean;
}

interface GameChatProps {
  messages: Message[];
  currentUser: string;
  isGameActive: boolean;
  onSendMessage: (message: string) => void;
}

const GameChat: React.FC<GameChatProps> = ({
  messages,
  currentUser,
  isGameActive,
  onSendMessage
}) => {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const trimmedMessage = inputValue.trim();
    if (!trimmedMessage || !isGameActive) return;
    
    onSendMessage(trimmedMessage);
    setInputValue('');
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const getMessageStyle = (type: string) => {
    switch (type) {
      case 'system':
        return 'text-center text-outsider-gray-500 italic';
      case 'question':
        return 'border-l-2 border-blue-500 pl-4';
      case 'answer':
        return 'border-l-2 border-green-500 pl-4';
      default:
        return '';
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-outsider-black">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-outsider-gray-600 text-sm">
              {isGameActive ? 'Game chat will appear here...' : 'Join a lobby to start playing'}
            </p>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <div
                key={message.id}
                className={`space-y-1 ${getMessageStyle(message.type)}`}
              >
                {message.type === 'system' ? (
                  <p className="text-sm text-outsider-gray-500">
                    {message.content}
                  </p>
                ) : (
                  <>
                    <div className="flex items-baseline space-x-2">
                      <span className={`font-medium ${
                        message.sender === currentUser ? 'text-outsider-white' : 'text-outsider-gray-400'
                      }`}>
                        {message.sender}
                      </span>
                      {message.isAI && (
                        <span className="text-xs text-outsider-gray-600">[AI]</span>
                      )}
                      <span className="text-xs text-outsider-gray-600">
                        {formatTime(message.timestamp)}
                      </span>
                    </div>
                    <p className="text-outsider-gray-200 leading-relaxed">
                      {message.content}
                    </p>
                  </>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>
      
      {/* Input Area */}
      {isGameActive && (
        <form onSubmit={handleSubmit} className="border-t border-outsider-gray-800 p-6">
          <div className="flex space-x-4">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Type your message..."
              className="input-primary flex-1"
              maxLength={200}
            />
            <button
              type="submit"
              disabled={!inputValue.trim()}
              className={`px-6 ${
                inputValue.trim() ? 'btn-primary' : 'btn-secondary opacity-50'
              }`}
            >
              SEND
            </button>
          </div>
          <p className="text-xs text-outsider-gray-600 mt-2">
            {inputValue.length}/200 characters
          </p>
        </form>
      )}
    </div>
  );
};

export default GameChat;