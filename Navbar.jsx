import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import '../styles/components/Navbar.css';

const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  
  const handleLogout = () => {
    logout();
    navigate('/login');
  };
  
  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/">Court Transcription System</Link>
      </div>
      
      <ul className="navbar-nav">
        <li className="nav-item">
          <Link to="/" className="nav-link">Transcripts</Link>
        </li>
        <li className="nav-item">
          <Link to="/upload" className="nav-link">Upload</Link>
        </li>
        <li className="nav-item">
          <Link to="/record" className="nav-link">Record</Link>
        </li>
      </ul>
      
      <div className="navbar-user">
        {user && (
          <>
            <span className="user-info">
              <span className="username">{user.username}</span>
              <span className="role">{user.role}</span>
            </span>
            <button className="logout-button" onClick={handleLogout}>
              Logout
            </button>
          </>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
