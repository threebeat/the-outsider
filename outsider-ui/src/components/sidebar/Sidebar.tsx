import React from 'react';

interface SidebarProps {
  children: React.ReactNode;
}

const Sidebar: React.FC<SidebarProps> = ({ children }) => {
  return (
    <div className="w-80 h-full bg-outsider-gray-900 border-r border-outsider-gray-800 flex flex-col">
      {children}
    </div>
  );
};

export default Sidebar;