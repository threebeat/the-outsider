import React from 'react';

interface MainLayoutProps {
  sidebar: React.ReactNode;
  children: React.ReactNode;
}

const MainLayout: React.FC<MainLayoutProps> = ({ sidebar, children }) => {
  return (
    <div className="fixed inset-0 pt-[73px] flex">
      {/* Sidebar */}
      {sidebar}
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {children}
      </div>
    </div>
  );
};

export default MainLayout;