import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FiHome, FiFolder, FiMessageSquare, FiSettings, FiMenu, FiX } from 'react-icons/fi';
import '../styles/Layout.css';

const Layout = ({ children }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const location = useLocation();

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  const navItems = [
    { path: '/', icon: <FiHome />, label: 'Home' },
    { path: '/files', icon: <FiFolder />, label: 'Files' },
    { path: '/chat', icon: <FiMessageSquare />, label: 'Chat' },
    { path: '/settings', icon: <FiSettings />, label: 'Settings' },
  ];

  return (
    <div className="layout">
      {/* Sidebar */}
      <aside className={`sidebar ${isSidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <h2>TestLegacy</h2>
          <button className="toggle-btn" onClick={toggleSidebar}>
            {isSidebarOpen ? <FiX /> : <FiMenu />}
          </button>
        </div>
        
        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
            >
              {item.icon}
              {isSidebarOpen && <span>{item.label}</span>}
            </Link>
          ))}
        </nav>
      </aside>

      {/* Main Content */}
      <main className={`main-content ${isSidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
        {/* Header */}
        <header className="header">
          <div className="header-left">
            <button className="menu-btn" onClick={toggleSidebar}>
              <FiMenu />
            </button>
            <h1>{navItems.find(item => item.path === location.pathname)?.label || 'TestLegacy'}</h1>
          </div>
          <div className="header-right">
            {/* Add user profile and settings here */}
          </div>
        </header>

        {/* Page Content */}
        <div className="content">
          {children}
        </div>
      </main>
    </div>
  );
};

export default Layout; 