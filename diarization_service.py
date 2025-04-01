import os
import torch
import numpy as np
from typing import List, Dict
import warnings
from utils import create_logger
import json
import tempfile
import time

# Try to import pyannote, but provide fallback if not available
try:
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False

# Suppress warnings
warnings.filterwarnings("ignore")

class DiarizationService:
    def __init__(self):
        self.logger = create_logger("diarization_service")
        
        # Get Hugging Face token from environment
        self.hf_token = os.environ.get("HF_TOKEN")
        
        # Flag to indicate if diarization is available
        self.diarization_available = False
        
        # Initialize diarization pipeline if token is available and pyannote is installed
        self.pipeline = None
        if PYANNOTE_AVAILABLE and self.hf_token:
            try:
                self.logger.info("Initializing speaker diarization pipeline")
                self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                self.pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.0",
                    use_auth_token=self.hf_token
                ).to(self.device)
                self.diarization_available = True
                self.logger.info("Speaker diarization pipeline initialized successfully")
            except Exception as e:
                self.logger.error(f"Error initializing diarization pipeline: {str(e)}")
                self.logger.warning("Speaker diarization will not be available")
        else:
            if not PYANNOTE_AVAILABLE:
                self.logger.warning("Pyannote.audio not installed, speaker diarization will not be available")
            if not self.hf_token:
                self.logger.warning("No Hugging Face token provided, speaker diarization will not be available")
    
    def diarize(self, audio_file: str) -> List[Dict]:
        """
        Perform speaker diarization on an audio file
        
        Args:
            audio_file: Path to the audio file
            
        Returns:
            List of segments with speaker labels
        """
        segments = []
        
        if not self.diarization_available:
            self.logger.warning("Speaker diarization is not available, returning empty segments")
            # Return mock segments for demonstration when diarization is not available
            return self._generate_mock_segments(audio_file)
        
        try:
            self.logger.info(f"Running speaker diarization on {audio_file}")
            diarization_result = self.pipeline(audio_file)
            
            # Convert diarization result to a list of segments with speaker labels
            for turn, _, speaker in diarization_result.itertracks(yield_label=True):
                segments.append({
                    "start": turn.start,
                    "end": turn.end,
                    "speaker": self._map_speaker_to_role(speaker)
                })
            
            self.logger.info(f"Found {len(set([s['speaker'] for s in segments]))} unique speakers")
            return segments
        except Exception as e:
            self.logger.error(f"Error during diarization: {str(e)}")
            self.logger.info("Falling back to mock segments")
            return self._generate_mock_segments(audio_file)
    
    def _map_speaker_to_role(self, speaker: str) -> str:
        """
        Map speaker ID to a courtroom role
        
        In a real implementation, this would use a trained classifier model
        to identify judges, advocates, witnesses based on acoustic features
        
        Args:
            speaker: Speaker ID from diarization
            
        Returns:
            Speaker role/label
        """
        # This is a mock implementation
        # In a real system, we'd use positional info and voice characteristics
        speaker_id = speaker.split("_")[-1]
        
        # Map to courtroom roles (simplified)
        if speaker_id == "0":
            return "Judge"
        elif speaker_id == "1":
            return "Advocate (Plaintiff)"
        elif speaker_id == "2":
            return "Advocate (Defense)"
        else:
            return f"Speaker {speaker_id}"
    
    def _generate_mock_segments(self, audio_file: str) -> List[Dict]:
        """
        Generate mock diarization segments when actual diarization is not available
        
        Args:
            audio_file: Path to the audio file
            
        Returns:
            List of mock segments with speaker labels
        """
        import librosa
        
        try:
            # Get audio duration
            y, sr = librosa.load(audio_file, sr=None)
            duration = librosa.get_duration(y=y, sr=sr)
            
            # Create segments - simplistic approach dividing the audio into chunks
            segment_length = 10.0  # 10 seconds per segment
            num_segments = int(duration / segment_length)
            
            segments = []
            speaker_roles = ["Judge", "Advocate (Plaintiff)", "Advocate (Defense)", "Witness"]
            
            for i in range(num_segments):
                start_time = i * segment_length
                end_time = min((i + 1) * segment_length, duration)
                
                # Alternate speakers
                speaker_idx = i % len(speaker_roles)
                
                segments.append({
                    "start": start_time,
                    "end": end_time,
                    "speaker": speaker_roles[speaker_idx]
                })
            
            self.logger.info(f"Generated {len(segments)} mock segments with {len(speaker_roles)} speakers")
            return segments
            
        except Exception as e:
            self.logger.error(f"Error generating mock segments: {str(e)}")
            # Return minimal segments if all else fails
            return [
                {"start": 0, "end": 30, "speaker": "Judge"},
                {"start": 30, "end": 60, "speaker": "Advocate (Plaintiff)"},
                {"start": 60, "end": 90, "speaker": "Advocate (Defense)"}
            ]