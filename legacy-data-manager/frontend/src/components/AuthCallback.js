import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const AuthCallback = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Short delay to ensure the backend has processed the token
    setTimeout(() => {
      // Redirect to the main dashboard
      navigate('/', { replace: true });
      // Reload the page to ensure fresh state
      window.location.reload();
    }, 1000);
  }, [navigate]);

  return (
    <div className="auth-callback">
      <div className="auth-message">
        <h2>Authentication Successful</h2>
        <p>Redirecting you back to the dashboard...</p>
      </div>
    </div>
  );
};

export default AuthCallback; 