import React from 'react';

const AnimatedBackground: React.FC = () => {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
      {/* Gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-outsider-black via-outsider-gray-900 to-outsider-black" />
      
      {/* Animated geometric shapes */}
      <div className="absolute inset-0">
        {/* Large circle */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 border border-outsider-gray-800 rounded-full animate-float opacity-20" />
        
        {/* Medium square */}
        <div className="absolute top-1/2 right-1/3 w-64 h-64 border border-outsider-gray-800 rotate-45 animate-float-delayed opacity-20" />
        
        {/* Small triangle */}
        <div className="absolute bottom-1/4 left-1/2 w-0 h-0 
                        border-l-[100px] border-l-transparent
                        border-b-[173px] border-b-outsider-gray-800
                        border-r-[100px] border-r-transparent
                        animate-float-slow opacity-20" />
        
        {/* Lines */}
        <div className="absolute top-0 left-1/4 w-px h-full bg-gradient-to-b from-transparent via-outsider-gray-800 to-transparent opacity-20" />
        <div className="absolute top-0 right-1/4 w-px h-full bg-gradient-to-b from-transparent via-outsider-gray-800 to-transparent opacity-20" />
        
        {/* Dots grid */}
        <div className="absolute inset-0 opacity-10">
          <div className="grid grid-cols-12 gap-8 p-8 h-full">
            {[...Array(144)].map((_, i) => (
              <div
                key={i}
                className="w-1 h-1 bg-outsider-gray-700 rounded-full animate-pulse-slow"
                style={{ animationDelay: `${i * 0.1}s` }}
              />
            ))}
          </div>
        </div>
      </div>
      
      {/* Noise texture overlay */}
      <div className="absolute inset-0 opacity-5">
        <svg width="100%" height="100%">
          <filter id="noise">
            <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="4" />
            <feColorMatrix type="saturate" values="0" />
          </filter>
          <rect width="100%" height="100%" filter="url(#noise)" />
        </svg>
      </div>
    </div>
  );
};

export default AnimatedBackground;