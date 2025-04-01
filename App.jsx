import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './components/LoginPage';
import TranscriptList from './components/TranscriptList';
import TranscriptViewer from './components/TranscriptViewer';
import RecordingPage from './components/RecordingPage';
import UploadPage from './components/UploadPage';
import Navbar from './components/Navbar';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import "./styles/App.css";

// Protected route component
const ProtectedRoute = ({ children }) => {
  const { user } = useAuth();
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="app">
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route 
              path="/" 
              element={
                <ProtectedRoute>
                  <Layout>
                    <TranscriptList />
                  </Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/transcript/:id" 
              element={
                <ProtectedRoute>
                  <Layout>
                    <TranscriptViewer />
                  </Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/record" 
              element={
                <ProtectedRoute>
                  <Layout>
                    <RecordingPage />
                  </Layout>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/upload" 
              element={
                <ProtectedRoute>
                  <Layout>
                    <UploadPage />
                  </Layout>
                </ProtectedRoute>
              } 
            />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

// Layout component with Navbar
const Layout = ({ children }) => {
  return (
    <>
      <Navbar />
      <main className="main-content">
        {children}
      </main>
    </>
  );
};

export default App;