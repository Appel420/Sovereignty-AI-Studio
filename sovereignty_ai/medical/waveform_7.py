"""7.887 Hz waveform peak detection - resonance frequency analysis."""

import numpy as np
from typing import List, Tuple, Optional
from scipy import signal
from dataclasses import dataclass


@dataclass
class Peak:
    """Represents a detected peak in waveform."""
    frequency: float
    amplitude: float
    index: int
    prominence: float


class WaveformAnalyzer:
    """
    Waveform analyzer focusing on 7.887 Hz resonance frequency.
    Detects peaks and analyzes frequency components.
    """
    
    def __init__(
        self,
        target_frequency: float = 7.887,
        sample_rate: int = 256,
        bandwidth: float = 0.5
    ):
        """
        Initialize waveform analyzer.
        
        Args:
            target_frequency: Target resonance frequency (Hz)
            sample_rate: Sampling rate (Hz)
            bandwidth: Frequency bandwidth for peak detection (Hz)
        """
        self.target_frequency = target_frequency
        self.sample_rate = sample_rate
        self.bandwidth = bandwidth
        self.waveform: Optional[np.ndarray] = None
        self.frequencies: Optional[np.ndarray] = None
        self.spectrum: Optional[np.ndarray] = None
    
    def load_waveform(self, data: np.ndarray):
        """
        Load waveform data for analysis.
        
        Args:
            data: Time-series waveform data
        """
        self.waveform = data
    
    def compute_fft(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute Fast Fourier Transform of waveform.
        
        Returns:
            Tuple of (frequencies, spectrum magnitude)
        """
        if self.waveform is None:
            raise ValueError("No waveform loaded")
        
        n = len(self.waveform)
        
        # Compute FFT
        fft_values = np.fft.fft(self.waveform)
        fft_magnitude = np.abs(fft_values)
        
        # Get frequency bins
        frequencies = np.fft.fftfreq(n, 1 / self.sample_rate)
        
        # Only keep positive frequencies
        positive_freq_idx = frequencies >= 0
        self.frequencies = frequencies[positive_freq_idx]
        self.spectrum = fft_magnitude[positive_freq_idx]
        
        return self.frequencies, self.spectrum
    
    def detect_peaks(
        self,
        prominence_threshold: float = 0.1,
        min_distance: int = 10
    ) -> List[Peak]:
        """
        Detect peaks in frequency spectrum.
        
        Args:
            prominence_threshold: Minimum prominence for peak detection
            min_distance: Minimum distance between peaks (in samples)
            
        Returns:
            List of detected peaks
        """
        if self.spectrum is None:
            self.compute_fft()
        
        # Find peaks using scipy
        peak_indices, properties = signal.find_peaks(
            self.spectrum,
            prominence=prominence_threshold * np.max(self.spectrum),
            distance=min_distance
        )
        
        peaks = []
        for idx in peak_indices:
            peak = Peak(
                frequency=self.frequencies[idx],
                amplitude=self.spectrum[idx],
                index=idx,
                prominence=properties['prominences'][list(peak_indices).index(idx)]
            )
            peaks.append(peak)
        
        # Sort by amplitude
        peaks.sort(key=lambda p: p.amplitude, reverse=True)
        
        return peaks
    
    def detect_target_frequency(self) -> Optional[Peak]:
        """
        Detect peak at target frequency (7.887 Hz).
        
        Returns:
            Peak object if found within bandwidth, None otherwise
        """
        peaks = self.detect_peaks()
        
        # Find peak closest to target frequency
        target_peaks = [
            p for p in peaks
            if abs(p.frequency - self.target_frequency) < self.bandwidth
        ]
        
        if target_peaks:
            # Return the one with highest amplitude
            return max(target_peaks, key=lambda p: p.amplitude)
        
        return None
    
    def compute_power_in_band(
        self,
        low_freq: Optional[float] = None,
        high_freq: Optional[float] = None
    ) -> float:
        """
        Compute total power in frequency band.
        
        Args:
            low_freq: Lower frequency bound (defaults to target - bandwidth)
            high_freq: Upper frequency bound (defaults to target + bandwidth)
            
        Returns:
            Total power in band
        """
        if self.spectrum is None:
            self.compute_fft()
        
        if low_freq is None:
            low_freq = self.target_frequency - self.bandwidth
        if high_freq is None:
            high_freq = self.target_frequency + self.bandwidth
        
        # Find indices in frequency band
        band_mask = (self.frequencies >= low_freq) & (self.frequencies <= high_freq)
        band_power = np.sum(self.spectrum[band_mask] ** 2)
        
        return band_power
    
    def apply_bandpass_filter(
        self,
        low_freq: Optional[float] = None,
        high_freq: Optional[float] = None,
        order: int = 4
    ) -> np.ndarray:
        """
        Apply bandpass filter centered on target frequency.
        
        Args:
            low_freq: Lower cutoff frequency
            high_freq: Upper cutoff frequency
            order: Filter order
            
        Returns:
            Filtered waveform
        """
        if self.waveform is None:
            raise ValueError("No waveform loaded")
        
        if low_freq is None:
            low_freq = self.target_frequency - self.bandwidth
        if high_freq is None:
            high_freq = self.target_frequency + self.bandwidth
        
        # Design Butterworth bandpass filter
        nyquist = self.sample_rate / 2
        low_norm = low_freq / nyquist
        high_norm = high_freq / nyquist
        
        b, a = signal.butter(order, [low_norm, high_norm], btype='band')
        
        # Apply filter
        filtered = signal.filtfilt(b, a, self.waveform)
        
        return filtered
    
    def analyze_resonance(self) -> dict:
        """
        Comprehensive resonance analysis at target frequency.
        
        Returns:
            Dictionary with analysis results
        """
        if self.waveform is None:
            raise ValueError("No waveform loaded")
        
        # Compute spectrum
        self.compute_fft()
        
        # Detect target peak
        target_peak = self.detect_target_frequency()
        
        # Compute band power
        band_power = self.compute_power_in_band()
        total_power = np.sum(self.spectrum ** 2)
        relative_power = band_power / total_power if total_power > 0 else 0
        
        # Filter waveform
        filtered = self.apply_bandpass_filter()
        
        results = {
            'target_frequency': self.target_frequency,
            'peak_detected': target_peak is not None,
            'peak_frequency': target_peak.frequency if target_peak else None,
            'peak_amplitude': target_peak.amplitude if target_peak else None,
            'band_power': band_power,
            'relative_power': relative_power,
            'filtered_waveform': filtered,
            'resonance_strength': relative_power * 100  # As percentage
        }
        
        return results
    
    def generate_synthetic_waveform(
        self,
        duration: float = 10.0,
        noise_level: float = 0.1
    ) -> np.ndarray:
        """
        Generate synthetic waveform with target frequency component.
        
        Args:
            duration: Duration in seconds
            noise_level: Noise amplitude relative to signal
            
        Returns:
            Synthetic waveform
        """
        n_samples = int(duration * self.sample_rate)
        t = np.linspace(0, duration, n_samples)
        
        # Primary signal at target frequency
        signal_wave = np.sin(2 * np.pi * self.target_frequency * t)
        
        # Add harmonics
        signal_wave += 0.3 * np.sin(2 * np.pi * 2 * self.target_frequency * t)
        signal_wave += 0.15 * np.sin(2 * np.pi * 3 * self.target_frequency * t)
        
        # Add noise
        noise = noise_level * np.random.randn(n_samples)
        
        waveform = signal_wave + noise
        
        return waveform
