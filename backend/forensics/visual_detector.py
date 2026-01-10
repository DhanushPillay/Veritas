"""
Visual AI Pattern Detector
Detects AI-generated images by analyzing visual artifacts and patterns
common in AI-generated content (Midjourney, Stable Diffusion, etc.)
"""

import io
import numpy as np
from PIL import Image, ImageFilter


class VisualPatternDetector:
    """
    Detects AI-generated images through visual pattern analysis.
    
    AI-generated images often have:
    1. Unusual texture patterns
    2. Symmetric noise patterns
    3. Edge inconsistencies
    4. Color histogram anomalies
    5. Frequency domain artifacts
    """
    
    def __init__(self):
        self.numpy_available = True
        try:
            import numpy as np
        except ImportError:
            self.numpy_available = False
    
    def detect(self, image_path_or_bytes):
        """
        Analyze image for AI generation patterns.
        
        Args:
            image_path_or_bytes: File path string or bytes object
            
        Returns:
            dict: Detection results with detailed analysis
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
                "indicators": []
            }
            
            if not self.numpy_available:
                results["error"] = "NumPy not available for analysis"
                return results
            
            # Run multiple detection methods
            texture_score, texture_indicators = self._analyze_texture_patterns(img)
            edge_score, edge_indicators = self._analyze_edge_consistency(img)
            color_score, color_indicators = self._analyze_color_distribution(img)
            symmetry_score, symmetry_indicators = self._analyze_noise_symmetry(img)
            artifact_score, artifact_indicators = self._detect_ai_artifacts(img)
            
            results["analysis"] = {
                "texture_anomaly": round(texture_score, 3),
                "edge_inconsistency": round(edge_score, 3),
                "color_distribution": round(color_score, 3),
                "noise_symmetry": round(symmetry_score, 3),
                "ai_artifacts": round(artifact_score, 3)
            }
            
            # Collect all indicators
            all_indicators = (texture_indicators + edge_indicators + 
                            color_indicators + symmetry_indicators + artifact_indicators)
            results["indicators"] = all_indicators[:5]  # Top 5 indicators
            
            # Combined score (weighted average)
            combined_score = (
                texture_score * 0.2 +
                edge_score * 0.2 +
                color_score * 0.15 +
                symmetry_score * 0.2 +
                artifact_score * 0.25
            )
            
            results["confidence"] = int(combined_score * 100)
            
            # Lower thresholds for better sensitivity
            if combined_score > 0.40:
                results["detected"] = True
                results["verdict"] = "Likely AI-generated"
            elif combined_score > 0.30:
                results["detected"] = True  # Still flag as detected
                results["verdict"] = "Possibly AI-generated"
            else:
                results["verdict"] = "Likely authentic"
            
            return results
            
        except Exception as e:
            return {
                "detected": False,
                "confidence": 0,
                "error": str(e)
            }
    
    def _analyze_texture_patterns(self, img):
        """
        Analyze texture for AI-typical smoothness or artifacts.
        AI images often have unusual texture uniformity.
        """
        indicators = []
        try:
            arr = np.array(img)
            gray = np.mean(arr, axis=2)
            
            # Calculate local variance (texture roughness)
            # AI images often have regions of unnatural smoothness
            kernel_size = 5
            h, w = gray.shape
            
            scores = []
            for i in range(0, h - kernel_size, kernel_size):
                for j in range(0, w - kernel_size, kernel_size):
                    patch = gray[i:i+kernel_size, j:j+kernel_size]
                    local_var = np.var(patch)
                    scores.append(local_var)
            
            if scores:
                variance_distribution = np.array(scores)
                
                # AI images often have bimodal variance (very smooth + very detailed)
                low_var_ratio = np.mean(variance_distribution < 10)
                high_var_ratio = np.mean(variance_distribution > 100)
                
                # Unusual if both extremes are high
                bimodal_score = low_var_ratio * high_var_ratio * 4
                
                if bimodal_score > 0.1:
                    indicators.append("Unusual texture distribution detected")
                
                return min(1.0, bimodal_score + 0.3), indicators
            
            return 0.3, indicators
            
        except Exception:
            return 0.3, indicators
    
    def _analyze_edge_consistency(self, img):
        """
        Analyze edge sharpness and consistency.
        AI images often have unnaturally sharp or uniform edges.
        """
        indicators = []
        try:
            # Apply edge detection
            edges = img.filter(ImageFilter.FIND_EDGES)
            edge_arr = np.array(edges.convert('L'))
            
            # Calculate edge statistics
            edge_mean = np.mean(edge_arr)
            edge_std = np.std(edge_arr)
            
            # AI images often have more uniform edge strength
            # Natural images have more varied edges
            uniformity_score = 1 - (edge_std / (edge_mean + 1))
            
            if uniformity_score > 0.5:
                indicators.append("Unusually uniform edge patterns")
            
            # Check for unnaturally sharp edges
            sharp_pixels = np.sum(edge_arr > 200) / edge_arr.size
            if sharp_pixels > 0.05:
                indicators.append("Unusually sharp edges detected")
                uniformity_score = min(1.0, uniformity_score + 0.2)
            
            return min(1.0, uniformity_score), indicators
            
        except Exception:
            return 0.3, []
    
    def _analyze_color_distribution(self, img):
        """
        Analyze color distribution patterns.
        AI images often have unusual color saturation patterns.
        """
        indicators = []
        try:
            arr = np.array(img)
            
            # Convert to HSV-like analysis
            # Check for unusual saturation patterns
            r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
            
            # Calculate "vibrancy" - AI images often have heightened colors
            max_rgb = np.maximum(np.maximum(r, g), b).astype(np.float32)
            min_rgb = np.minimum(np.minimum(r, g), b).astype(np.float32)
            # Avoid divide by zero
            saturation = np.divide(max_rgb - min_rgb, max_rgb + 1, where=(max_rgb > 0), out=np.zeros_like(max_rgb))
            
            avg_saturation = np.nanmean(saturation)
            sat_uniformity = 1 - np.nanstd(saturation)
            
            score = 0.3
            
            # AI images often have high, uniform saturation
            if avg_saturation > 0.4 and sat_uniformity > 0.6:
                score = 0.7
                indicators.append("Heightened, uniform color saturation")
            elif avg_saturation > 0.3:
                score = 0.5
            
            return score, indicators
            
        except Exception:
            return 0.3, []
    
    def _analyze_noise_symmetry(self, img):
        """
        Analyze noise patterns for unnatural symmetry.
        AI images may have symmetric or patterned noise.
        """
        indicators = []
        try:
            arr = np.array(img.convert('L'), dtype=np.float64)
            
            # Extract high-frequency noise
            smoothed = np.array(img.convert('L').filter(ImageFilter.GaussianBlur(2)))
            noise = arr - smoothed
            
            # Check for unusual noise patterns
            h, w = noise.shape
            
            # Compare left-right noise
            left = noise[:, :w//2]
            right = np.fliplr(noise[:, w//2:w//2*2])
            
            if left.shape == right.shape:
                lr_correlation = np.corrcoef(left.flatten(), right.flatten())[0, 1]
                
                # Unusual if noise is too symmetric
                if lr_correlation > 0.3:
                    indicators.append("Symmetric noise patterns detected")
                    return min(1.0, lr_correlation + 0.3), indicators
            
            return 0.3, indicators
            
        except Exception:
            return 0.3, []
    
    def _detect_ai_artifacts(self, img):
        """
        Detect specific AI-generation artifacts:
        - Grid patterns from upscaling
        - Repeated texture patterns
        - Unnatural gradients
        """
        indicators = []
        try:
            arr = np.array(img.convert('L'), dtype=np.float64)
            
            # Check for grid patterns (common in AI upscaling)
            fft = np.fft.fft2(arr)
            fft_shift = np.fft.fftshift(fft)
            magnitude = np.log(np.abs(fft_shift) + 1)
            
            h, w = magnitude.shape
            center_h, center_w = h // 2, w // 2
            
            # Check for periodic spikes in frequency domain
            # These indicate repeating patterns
            horizontal_slice = magnitude[center_h, :]
            vertical_slice = magnitude[:, center_w]
            
            # Find peaks
            h_peaks = np.where(horizontal_slice > np.mean(horizontal_slice) * 2)[0]
            v_peaks = np.where(vertical_slice > np.mean(vertical_slice) * 2)[0]
            
            # Regular peaks indicate artifacts
            artifact_score = 0.3
            
            if len(h_peaks) > 5:
                # Check if peaks are regularly spaced
                h_diffs = np.diff(h_peaks)
                if len(h_diffs) > 0 and np.std(h_diffs) < np.mean(h_diffs) * 0.3:
                    artifact_score += 0.3
                    indicators.append("Regular grid pattern detected")
            
            if len(v_peaks) > 5:
                v_diffs = np.diff(v_peaks)
                if len(v_diffs) > 0 and np.std(v_diffs) < np.mean(v_diffs) * 0.3:
                    artifact_score += 0.3
                    indicators.append("Vertical pattern artifacts")
            
            return min(1.0, artifact_score), indicators
            
        except Exception:
            return 0.3, []


# Convenience function
def detect_visual_patterns(image_path_or_bytes):
    """Quick detection function"""
    detector = VisualPatternDetector()
    return detector.detect(image_path_or_bytes)
