import React, { createContext, useContext, useState, useEffect } from 'react';
import { API_BASE_URL } from '../config';

const AuthContext = createContext();

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Check for token on first load
    checkUserLoggedIn();
  }, []);

  const checkUserLoggedIn = () => {
    const token = localStorage.getItem('token');
    if (token) {
      // Get user info from token (simplified for demo)
      try {
        // In a real app, validate the token with the backend
        const payload = token.split('.')[1];
        const decoded = JSON.parse(atob(payload));
        setUser({
          username: decoded.sub,
          role: decoded.role,
          token: token
        });
      } catch (err) {
        console.error('Invalid token', err);
        localStorage.removeItem('token');
        setUser(null);
      }
    }
    setLoading(false);
  };

  const login = async (username, password) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          username,
          password,
        }),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Login failed');
      }
      
      // Save token to local storage
      localStorage.setItem('token', data.access_token);
      
      // Get user info from token
      const payload = data.access_token.split('.')[1];
      const decoded = JSON.parse(atob(payload));
      
      setUser({
        username: decoded.sub,
        role: decoded.role,
        token: data.access_token
      });
      
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  const value = {
    user,
    loading,
    error,
    login,
    logout
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
