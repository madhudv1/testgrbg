import React, { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import config from '../config';

const AuthCallback = () => {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    console.log('AuthCallback component mounted');
    console.log('Current location:', location);
    
    const handleCallback = async () => {
      console.log('Starting handleCallback...');
      try {
        // Add a small delay to ensure backend has processed the token
        console.log('Waiting for backend processing...');
        await new Promise(resolve => setTimeout(resolve, 2000));

        console.log('Making status check request to:', `${config.apiBaseUrl}/api/v1/auth/google/status`);
        const response = await fetch(`${config.apiBaseUrl}/api/v1/auth/google/status`, {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Accept': 'application/json',
          }
        });

        console.log('Status check response:', response);
        console.log('Response status:', response.status);

        if (!response.ok) {
          throw new Error(`Status check failed: ${response.status}`);
        }

        const data = await response.json();
        console.log('Status check data:', data);

        if (data.isAuthenticated) {
          console.log('Authentication successful, navigating to root');
          // Set authentication in localStorage before navigating
          localStorage.setItem('isAuthenticated', 'true');
          navigate('/', { replace: true });
        } else {
          console.log('Authentication failed, navigating to root');
          localStorage.removeItem('isAuthenticated');
          navigate('/', { replace: true });
        }
      } catch (error) {
        console.error('Error in handleCallback:', error);
        localStorage.removeItem('isAuthenticated');
        navigate('/', { replace: true });
      }
    };

    handleCallback();
  }, [navigate, location]);

  return (
    <div className="auth-container">
      <h1>Processing authentication...</h1>
      <p>Please wait while we complete the authentication process...</p>
    </div>
  );
};

export default AuthCallback; 