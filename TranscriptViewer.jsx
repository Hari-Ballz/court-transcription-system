import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { API_BASE_URL } from '../config';
import '../styles/components/TranscriptViewer.css';

const TranscriptViewer = () => {
  const { id } = useParams();
  const { user } = useAuth();
  const [transcript, setTranscript] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editingSegment, setEditingSegment] = useState(null);
  const [editText, setEditText] = useState('');
  const [socketConnected, setSocketConnected] = useState(false);
  const socketRef = useRef(null);
  
  useEffect(() => {
    fetchTranscript();
    setupWebSocket();
    
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [id]);
  
  const setupWebSocket = () => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host.replace(/:\d+$/, '')}:8000/ws/${id}`;
    
    const socket = new WebSocket(wsUrl);
    
    socket.onopen = () => {
      console.log('WebSocket connected');
      setSocketConnected(true);
    };
    
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.action === 'segment_updated') {
        // Update the segment in the transcript
        setTranscript(prev => {
          if (!prev) return prev;
          
          const updatedSegments = prev.segments.map(segment => {
            if (segment.id === data.segment_id) {
              return { ...segment, text: data.text };
            }
            return segment;
          });
          
          return { ...prev, segments: updatedSegments };
        });
      }
    };
    
    socket.onclose = () => {
      console.log('WebSocket disconnected');
      setSocketConnected(false);
    };
    
    socketRef.current = socket;
  };
  
  const fetchTranscript = async () => {
    try {
      setLoading(true);
      
      const response = await fetch(`${API_BASE_URL}/api/transcript/${id}`, {
        headers: {
          'Authorization': `Bearer ${user.token}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch transcript');
      }
      
      const data = await response.json();
      setTranscript(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  const handleEditSegment = (segment) => {
    if (user.role !== 'judge' && user.role !== 'admin') {
      return; // Only judges and admins can edit
    }
    
    setEditingSegment(segment.id);
    setEditText(segment.text);
  };
  
  const handleSaveEdit = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/transcript/${id}/segment/${editingSegment}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.token}`
        },
        body: JSON.stringify({ text: editText })
      });
      
      if (!response.ok) {
        throw new Error('Failed to save changes');
      }
      
      // Update locally
      setTranscript(prev => {
        const updatedSegments = prev.segments.map(segment => {
          if (segment.id === editingSegment) {
            return { ...segment, text: editText };
          }
          return segment;
        });
        
        return { ...prev, segments: updatedSegments };
      });
      
      setEditingSegment(null);
    } catch (err) {
      alert(err.message);
    }
  };
  
  const handleCancelEdit = () => {
    setEditingSegment(null);
    setEditText('');
  };
  
  const handleExport = async (format) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/export-transcript/${id}?format=${format}`, {
        headers: {
          'Authorization': `Bearer ${user.token}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`Failed to export as ${format}`);
      }
      
      const data = await response.json();
      
      // In a real app, this would download the file
      alert(`Export successful! File would be downloaded in production: ${data.export_url}`);
    } catch (err) {
      alert(err.message);
    }
  };
  
  if (loading) return <div className="loading">Loading transcript...</div>;
  if (error) return <div className="error">Error: {error}</div>;
  if (!transcript) return <div className="error">Transcript not found</div>;
  
  const formatTime = (seconds) => {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };
  
  return (
    <div className="transcript-viewer">
      <div className="transcript-header">
        <h1>Transcript</h1>
        <div className="connection-status">
          {socketConnected ? 
            <span className="connected">●&nbsp;Connected</span> : 
            <span className="disconnected">●&nbsp;Disconnected</span>
          }
        </div>
        
        {transcript.case_details && (
          <div className="case-details">
            <h2>{transcript.case_details.case_title}</h2>
            <p>Court: {transcript.case_details.court}</p>
            <p>Judge: {transcript.case_details.judge}</p>
            <p>Date: {transcript.case_details.date}</p>
          </div>
        )}
        
        <div className="action-buttons">
          <button onClick={() => handleExport('pdf')}>Export as PDF</button>
          <button onClick={() => handleExport('txt')}>Export as Text</button>
        </div>
      </div>
      
      <div className="transcript-body">
        {transcript.segments.map((segment) => (
          <div 
            key={segment.id} 
            className={`segment ${segment.speaker.toLowerCase().replace(' ', '-')}`}
          >
            <div className="segment-header">
              <span className="speaker">{segment.speaker}</span>
              <span className="timestamp">{formatTime(segment.start_time)} - {formatTime(segment.end_time)}</span>
              
              {(user.role === 'judge' || user.role === 'admin') && (
                <button 
                  className="edit-button"
                  onClick={() => handleEditSegment(segment)}
                >
                  Edit
                </button>
              )}
            </div>
            
            {editingSegment === segment.id ? (
              <div className="edit-container">
                <textarea
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  rows={4}
                />
                <div className="edit-actions">
                  <button onClick={handleSaveEdit}>Save</button>
                  <button onClick={handleCancelEdit}>Cancel</button>
                </div>
              </div>
            ) : (
              <p className="text">{segment.text}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default TranscriptViewer;
