import os
import numpy as np
import tempfile
from typing import Tuple
from utils import create_logger
import warnings

# Try to import audio processing libraries, but provide fallbacks if not available
try:
    import librosa
    import soundfile as sf
    from scipy import signal
    AUDIO_LIBS_AVAILABLE = True
except ImportError:
    AUDIO_LIBS_AVAILABLE = False

# Suppress warnings
warnings.filterwarnings("ignore")

class NoiseSuppression:
    def __init__(self):
        self.logger = create_logger("noise_suppression")
        
        if not AUDIO_LIBS_AVAILABLE:
            self.logger.warning("Required audio libraries not available. Noise suppression will be limited.")
        
    def process(self, audio_file: str) -> str:
        """
        Apply noise suppression to audio file
        
        Args:
            audio_file: Path to the audio file
            
        Returns:
            Path to the processed audio file
        """
        self.logger.info(f"Applying noise suppression to {audio_file}")
        
        if not AUDIO_LIBS_AVAILABLE:
            self.logger.warning("Audio libraries not available. Returning original file.")
            return audio_file
        
        try:
            # Load audio file
            audio, sample_rate = librosa.load(audio_file, sr=None)
            
            # Apply spectral subtraction (tailored for courtroom noise as per paper)
            audio_filtered = self._spectral_subtraction(audio, sample_rate)
            
            # Create temporary file for the processed audio
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                cleaned_audio_path = temp_file.name
            
            # Save processed audio
            sf.write(cleaned_audio_path, audio_filtered, sample_rate)
            
            self.logger.info(f"Noise suppression completed, saved to {cleaned_audio_path}")
            return cleaned_audio_path
        
        except Exception as e:
            self.logger.error(f"Error during noise suppression: {str(e)}")
            self.logger.warning("Using original audio file without noise suppression")
            return audio_file
    
    def _spectral_subtraction(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Apply spectral subtraction for noise reduction
        
        This implementation is specifically designed for courtroom environments,
        targeting the 50-150 Hz ceiling fan noise as mentioned in the paper.
        
        Args:
            audio: Audio signal as numpy array
            sample_rate: Sample rate of the audio
            
        Returns:
            Filtered audio signal
        """
        # Parameters
        frame_length = int(0.025 * sample_rate)  # 25ms frame
        hop_length = int(0.010 * sample_rate)    # 10ms hop
        
        # Estimate noise from the first 0.5 seconds (assuming it's noise)
        noise_length = min(int(0.5 * sample_rate), len(audio) // 4)
        noise_sample = audio[:noise_length]
        
        noise_spec = np.abs(librosa.stft(noise_sample, n_fft=frame_length, hop_length=hop_length))
        noise_power = np.mean(noise_spec**2, axis=1)
        
        # Compute STFT of the signal
        spec = librosa.stft(audio, n_fft=frame_length, hop_length=hop_length)
        spec_mag = np.abs(spec)
        spec_phase = np.angle(spec)
        
        # Apply spectral subtraction - specifically targeting the 50-150 Hz frequency range
        # which corresponds to ceiling fan noise in Indian courtrooms as per the paper
        freq_bins = librosa.fft_frequencies(sr=sample_rate, n_fft=frame_length)
        fan_noise_mask = np.logical_and(freq_bins >= 50, freq_bins <= 150)
        
        # Apply stronger suppression to fan noise frequency range
        spec_mag_filtered = spec_mag.copy()
        
        # Standard spectral subtraction for all frequencies
        spec_mag_filtered = np.maximum(spec_mag**2 - noise_power[:, np.newaxis] * 1.0, 0.0) ** 0.5
        
        # Stronger suppression for fan noise frequencies
        fan_indices = np.where(fan_noise_mask)[0]
        spec_mag_filtered[fan_indices] = np.maximum(
            spec_mag[fan_indices]**2 - noise_power[fan_indices, np.newaxis] * 2.0, 
            0.0
        ) ** 0.5
        
        # Reconstruct signal
        spec_filtered = spec_mag_filtered * np.exp(1j * spec_phase)
        audio_filtered = librosa.istft(spec_filtered, hop_length=hop_length, length=len(audio))
        
        return audio_filtered