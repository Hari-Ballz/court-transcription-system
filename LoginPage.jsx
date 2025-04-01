import React, { useState } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import '../styles/components/LoginPage.css';

const LoginPage = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loggingIn, setLoggingIn] = useState(false);
  const { user, login, error } = useAuth();
  const navigate = useNavigate();
  
  // If already logged in, redirect to home
  if (user) {
    return <Navigate to="/" replace />;
  }
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoggingIn(true);
    
    const success = await login(username, password);
    
    setLoggingIn(false);
    
    if (success) {
      navigate('/');
    }
  };
  
  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <h1>Court Transcription System</h1>
          <p>AI-Powered Speech Processing for Judicial Proceedings</p>
        </div>
        
        <form onSubmit={handleSubmit} className="login-form">
          <h2>Login</h2>
          
          {error && <div className="error-message">{error}</div>}
          
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              disabled={loggingIn}
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loggingIn}
            />
          </div>
          
          <button 
            type="submit" 
            className="login-button" 
            disabled={loggingIn}
          >
            {loggingIn ? 'Logging in...' : 'Login'}
          </button>
        </form>
        
        <div className="login-demo-info">
          <h3>Demo Credentials:</h3>
          <div className="demo-users">
            <div className="demo-user">
              <p><strong>Role: Judge</strong></p>
              <p>Username: judge1</p>
              <p>Password: judge1_password</p>
            </div>
            <div className="demo-user">
              <p><strong>Role: Advocate</strong></p>
              <p>Username: advocate1</p>
              <p>Password: advocate1_password</p>
            </div>
            <div className="demo-user">
              <p><strong>Role: Clerk</strong></p>
              <p>Username: clerk1</p>
              <p>Password: clerk1_password</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
