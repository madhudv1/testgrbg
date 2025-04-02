import React from 'react';
import ChatInterface from './components/ChatInterface';
import './App.css';

function App() {
  return (
    <div className="min-h-screen bg-gray-900">
      <header className="bg-gray-800/50 backdrop-blur-xl shadow-lg border-b border-gray-700/50">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 via-blue-400 to-blue-300 text-transparent bg-clip-text">
            Legacy Data Manager
          </h1>
        </div>
      </header>
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <ChatInterface />
        </div>
      </main>
    </div>
  );
}

export default App; 