import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { API_BASE_URL } from '../config';
import '../styles/components/RecordingPage.css';

const RecordingPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [recording, setRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [caseId, setCaseId] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [audioURL, setAudioURL] = useState(null);
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);
  
  useEffect(() => {
    // Clean up when component unmounts
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      
      if (audioURL) {
        URL.revokeObjectURL(audioURL);
      }
    };
  }, [audioURL]);
  
  const startRecording = async () => {
    try {
      audioChunksRef.current = [];
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      mediaRecorderRef.current = new MediaRecorder(stream);
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        const url = URL.createObjectURL(audioBlob);
        
        setAudioBlob(audioBlob);
        setAudioURL(url);
      };
      
      mediaRecorderRef.current.start();
      setRecording(true);
      setRecordingTime(0);
      
      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
      
    } catch (err) {
      setError('Error accessing microphone: ' + err.message);
    }
  };
  
  const stopRecording = () => {
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop();
      
      // Stop all tracks in the stream
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      
      setRecording(false);
      
      // Clear timer
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }
  };
  
  const uploadRecording = async () => {
    if (!audioBlob) {
      setError('No recording available');
      return;
    }
    
    try {
      setUploading(true);
      
      const formData = new FormData();
      formData.append('file', audioBlob, 'recording.wav');
      if (caseId) formData.append('case_id', caseId);
      
      const response = await fetch(`${API_BASE_URL}/api/upload-audio`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${user.token}`
        },
        body: formData
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }
      
      const data = await response.json();
      
      // Navigate to the transcript page
      navigate(`/transcript/${data.transcript_id}`);
      
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };
  
  const discardRecording = () => {
    if (audioURL) {
      URL.revokeObjectURL(audioURL);
    }
    
    setAudioBlob(null);
    setAudioURL(null);
    setRecordingTime(0);
  };
  
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };
  
  return (
    <div className="recording-page">
      <h1>Record Court Session</h1>
      
      {error && <div className="error-message">{error}</div>}
      
      <div className="recording-container">
        <div className="form-group">
          <label htmlFor="case-id">Case ID (optional):</label>
          <input
            type="text"
            id="case-id"
            value={caseId}
            onChange={(e) => setCaseId(e.target.value)}
            placeholder="Enter case ID if applicable"
            disabled={recording || uploading}
          />
        </div>
        
        <div className="recording-controls">
          {!recording && !audioBlob && (
            <button 
              className="start-button"
              onClick={startRecording}
              disabled={uploading}
            >
              Start Recording
            </button>
          )}
          
          {recording && (
            <div className="recording-indicator">
              <div className="recording-light"></div>
              <span className="recording-time">{formatTime(recordingTime)}</span>
              <button 
                className="stop-button"
                onClick={stopRecording}
              >
                Stop Recording
              </button>
            </div>
          )}
          
          {audioBlob && !recording && (
            <div className="recording-playback">
              <audio src={audioURL} controls></audio>
              <div className="recording-info">
                <p>Duration: {formatTime(recordingTime)}</p>
                <p>Size: {(audioBlob.size / (1024 * 1024)).toFixed(2)} MB</p>
              </div>
              <div className="playback-controls">
                <button 
                  className="upload-button"
                  onClick={uploadRecording}
                  disabled={uploading}
                >
                  {uploading ? 'Processing...' : 'Process Recording'}
                </button>
                <button 
                  className="discard-button"
                  onClick={discardRecording}
                  disabled={uploading}
                >
                  Discard & Record Again
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
      
      <div className="recording-notes">
        <h3>Important Notes:</h3>
        <ul>
          <li>Ensure your microphone is properly positioned to capture all speakers</li>
          <li>Reduce background noise as much as possible</li>
          <li>Ask speakers to identify themselves before speaking for better speaker identification</li>
          <li>The maximum recording time is 3 hours</li>
        </ul>
      </div>
    </div>
  );
};

export default RecordingPage;
