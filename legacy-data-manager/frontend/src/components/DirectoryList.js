import React, { useState, useEffect } from 'react';
import axios from 'axios';
import config from '../config';
import './DirectoryList.css';

const DirectoryList = ({ onSelectDirectory }) => {
  const [directories, setDirectories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDirectories();
  }, []);

  const fetchDirectories = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${config.apiBaseUrl}/api/v1/drive/directories`);
      setDirectories(response.data.directories || []);
    } catch (err) {
      setError('Failed to fetch directories');
      console.error('Directory fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleExplore = (directory) => {
    onSelectDirectory(directory);
  };

  if (loading) {
    return <div className="directory-loading">Loading directories...</div>;
  }

  if (error) {
    return <div className="directory-error">{error}</div>;
  }

  return (
    <div className="directory-list">
      <div className="directory-header">
        <h3>Google Drive Directories</h3>
        <button 
          className="refresh-button"
          onClick={fetchDirectories}
        >
          Refresh
        </button>
      </div>
      
      <div className="directory-items">
        {directories.map((directory) => (
          <div 
            key={directory.id}
            className="directory-item"
          >
            <div className="directory-item-content">
              <div className="directory-icon">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z" />
                </svg>
              </div>
              <div className="directory-info">
                <div className="directory-name">{directory.name}</div>
                <div className="directory-path">Last modified: {new Date(directory.modifiedTime).toLocaleDateString()}</div>
              </div>
              <button 
                className="explore-button"
                onClick={() => handleExplore(directory)}
              >
                Explore
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default DirectoryList; 