import React, { useState, useEffect } from 'react';
import axios from 'axios';
import config from '../config';
import './GoogleDriveAuth.css';

const GoogleDriveAuth = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const response = await axios.get(`${config.apiBaseUrl}/api/v1/drive/auth/status`);
      setIsAuthenticated(response.data.authenticated);
    } catch (err) {
      setError('Failed to check authentication status');
      console.error('Auth status error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAuth = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${config.apiBaseUrl}/api/v1/drive/auth/url`);
      window.location.href = response.data.auth_url;
    } catch (err) {
      setError('Failed to get authentication URL');
      console.error('Auth URL error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="auth-loading">Checking authentication status...</div>;
  }

  if (error) {
    return <div className="auth-error">{error}</div>;
  }

  return (
    <div className="google-drive-auth">
      {!isAuthenticated ? (
        <button 
          className="auth-button"
          onClick={handleAuth}
          disabled={loading}
        >
          {loading ? 'Connecting...' : 'Connect Google Drive'}
        </button>
      ) : (
        <div className="auth-success">
          <span className="auth-status">Connected to Google Drive</span>
          <button 
            className="auth-refresh"
            onClick={checkAuthStatus}
          >
            Refresh Status
          </button>
        </div>
      )}
    </div>
  );
};

export default GoogleDriveAuth; 