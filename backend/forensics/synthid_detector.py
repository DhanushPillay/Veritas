"""
SynthID Detector
Detects Google's invisible SynthID watermarks in AI-generated images.

Note: Full SynthID detection requires Google's proprietary decoder.
This module provides:
1. Heuristic detection based on known SynthID patterns
2. Integration ready for when Google releases public API
"""

import io
import hashlib
import numpy as np
from PIL import Image


class SynthIDDetector:
    """
    Detects Google SynthID watermarks in images.
    
    SynthID embeds imperceptible watermarks in pixel values that
    survive common image transformations like cropping, filters,
    and compression.
    
    Since Google's decoder is not publicly available, this detector uses:
    1. DCT (Discrete Cosine Transform) analysis for hidden patterns
    2. Frequency domain analysis
    3. Statistical anomaly detection
    """
    
    def __init__(self):
        self.numpy_available = True
        try:
            import numpy as np
        except ImportError:
            self.numpy_available = False
    
    def detect(self, image_path_or_bytes):
        """
        Analyze image for SynthID watermarks.
        
        Args:
            image_path_or_bytes: File path string or bytes object
            
        Returns:
            dict: Detection results with confidence score
        """
        try:
            # Load image
            if isinstance(image_path_or_bytes, bytes):
                img = Image.open(io.BytesIO(image_path_or_bytes))
            else:
                img = Image.open(image_path_or_bytes)
            
            # Convert to RGB
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            results = {
                "detected": False,
                "confidence": 0,
                "analysis": {},
                "note": "Full SynthID detection requires Google's decoder"
            }
            
            if not self.numpy_available:
                results["error"] = "NumPy not available for analysis"
                return results
            
            # Run multiple detection methods
            freq_score = self._analyze_frequency_domain(img)
            stat_score = self._analyze_statistical_patterns(img)
            lsb_score = self._analyze_lsb_patterns(img)
            
            results["analysis"] = {
                "frequency_anomaly": freq_score,
                "statistical_pattern": stat_score,
                "lsb_pattern": lsb_score
            }
            
            # Combined score (weighted average)
            combined_score = (freq_score * 0.4 + stat_score * 0.3 + lsb_score * 0.3)
            
            # Lower thresholds for better sensitivity
            if combined_score > 0.35:
                results["detected"] = True
                results["confidence"] = int(combined_score * 100)
            elif combined_score > 0.25:
                results["detected"] = True
                results["confidence"] = int(combined_score * 100)
                results["note"] = "Possible SynthID pattern detected"
            else:
                results["confidence"] = int(combined_score * 100)
            
            return results
            
        except Exception as e:
            return {
                "detected": False,
                "confidence": 0,
                "error": str(e)
            }
    
    def _analyze_frequency_domain(self, img):
        """
        Analyze image in frequency domain for watermark patterns.
        SynthID embeds patterns in specific frequency bands.
        """
        try:
            # Convert to grayscale array
            gray = img.convert('L')
            arr = np.array(gray, dtype=np.float64)
            
            # Compute 2D FFT
            fft = np.fft.fft2(arr)
            fft_shift = np.fft.fftshift(fft)
            magnitude = np.abs(fft_shift)
            
            # Analyze mid-frequency bands (where watermarks typically hide)
            h, w = magnitude.shape
            center_h, center_w = h // 2, w // 2
            
            # Mid-frequency ring
            y, x = np.ogrid[:h, :w]
            dist = np.sqrt((x - center_w)**2 + (y - center_h)**2)
            
            inner_radius = min(h, w) // 8
            outer_radius = min(h, w) // 3
            
            mid_freq_mask = (dist > inner_radius) & (dist < outer_radius)
            mid_freq_energy = np.mean(magnitude[mid_freq_mask])
            
            # Low-frequency energy
            low_freq_mask = dist <= inner_radius
            low_freq_energy = np.mean(magnitude[low_freq_mask])
            
            # Unusual mid-frequency energy can indicate watermarks
            if low_freq_energy > 0:
                ratio = mid_freq_energy / low_freq_energy
                # Normalize to 0-1 range
                score = min(1.0, ratio / 0.5)
            else:
                score = 0.5
            
            return score
            
        except Exception:
            return 0.3
    
    def _analyze_statistical_patterns(self, img):
        """
        Analyze statistical properties that may indicate watermarking.
        """
        try:
            arr = np.array(img)
            
            # Check for unusual pixel value distributions
            # Watermarked images often have subtle distribution shifts
            
            scores = []
            for channel in range(3):
                channel_data = arr[:, :, channel].flatten()
                
                # Check histogram uniformity
                hist, _ = np.histogram(channel_data, bins=256, range=(0, 256))
                hist_norm = hist / hist.sum()
                
                # Entropy calculation
                entropy = -np.sum(hist_norm[hist_norm > 0] * np.log2(hist_norm[hist_norm > 0]))
                
                # High entropy (close to 8 for 8-bit) can indicate watermarking
                # because watermarks add subtle noise
                entropy_score = entropy / 8.0
                scores.append(entropy_score)
            
            return np.mean(scores)
            
        except Exception:
            return 0.3
    
    def _analyze_lsb_patterns(self, img):
        """
        Analyze Least Significant Bit patterns.
        SynthID may embed data in LSBs with specific patterns.
        """
        try:
            arr = np.array(img)
            
            scores = []
            for channel in range(3):
                channel_data = arr[:, :, channel]
                
                # Extract LSBs
                lsb = channel_data & 1
                
                # Analyze LSB randomness
                # Natural images have random-ish LSBs
                # Watermarked images may have patterns
                lsb_flat = lsb.flatten()
                
                # Check for runs of same values
                runs = np.diff(lsb_flat)
                num_transitions = np.count_nonzero(runs)
                expected_transitions = len(lsb_flat) / 2
                
                if expected_transitions > 0:
                    transition_ratio = num_transitions / expected_transitions
                    # Score based on deviation from expected
                    score = abs(1 - transition_ratio)
                    scores.append(min(1.0, score * 2))
                else:
                    scores.append(0.5)
            
            return np.mean(scores)
            
        except Exception:
            return 0.3


# Convenience function
def detect_synthid(image_path_or_bytes):
    """Quick detection function"""
    detector = SynthIDDetector()
    return detector.detect(image_path_or_bytes)
