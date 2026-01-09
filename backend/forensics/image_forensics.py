"""
VERITAS - Image Forensics Module
Provides ELA analysis, metadata extraction, and manipulation detection
"""

import io
import os
import base64
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from typing import Dict, List, Optional, Tuple
import json


class ImageForensics:
    """Image forensic analysis toolkit"""
    
    def __init__(self):
        self.ela_quality = 90  # JPEG quality for ELA
    
    def analyze(self, image_data: bytes, filename: str = "") -> Dict:
        """
        Perform full forensic analysis on an image.
        
        Args:
            image_data: Raw image bytes
            filename: Original filename
        
        Returns:
            Dict with all forensic findings
        """
        try:
            image = Image.open(io.BytesIO(image_data))
            
            results = {
                "filename": filename,
                "format": image.format,
                "mode": image.mode,
                "size": {"width": image.width, "height": image.height},
                "metadata": self.extract_metadata(image),
                "ela": self.perform_ela(image),
                "manipulation_indicators": [],
                "risk_score": 0
            }
            
            # Calculate manipulation indicators
            results["manipulation_indicators"] = self._detect_manipulation(results)
            results["risk_score"] = self._calculate_risk(results)
            
            return results
            
        except Exception as e:
            return {"error": str(e)}
    
    def extract_metadata(self, image: Image.Image) -> Dict:
        """Extract EXIF and other metadata from image"""
        metadata = {
            "exif": {},
            "gps": {},
            "camera": {},
            "software": None,
            "has_metadata": False
        }
        
        try:
            exif_data = image._getexif()
            if exif_data:
                metadata["has_metadata"] = True
                
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    
                    # Skip binary data
                    if isinstance(value, bytes):
                        continue
                    
                    # GPS data
                    if tag == "GPSInfo":
                        for gps_tag_id, gps_value in value.items():
                            gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                            metadata["gps"][gps_tag] = str(gps_value)
                    
                    # Camera info
                    elif tag in ["Make", "Model", "LensModel"]:
                        metadata["camera"][tag] = str(value)
                    
                    # Software/editing info
                    elif tag == "Software":
                        metadata["software"] = str(value)
                    
                    # Store other EXIF
                    else:
                        try:
                            metadata["exif"][tag] = str(value)
                        except:
                            pass
                            
        except Exception as e:
            metadata["extraction_error"] = str(e)
        
        return metadata
    
    def perform_ela(self, image: Image.Image) -> Dict:
        """
        Error Level Analysis - detects edits by comparing compression artifacts.
        
        How it works:
        1. Re-save image at known quality
        2. Calculate difference between original and re-saved
        3. Edited areas show higher error levels
        """
        try:
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Save at known quality
            buffer = io.BytesIO()
            image.save(buffer, 'JPEG', quality=self.ela_quality)
            buffer.seek(0)
            
            # Open re-compressed image
            resaved = Image.open(buffer)
            
            # Calculate difference
            diff = self._calculate_ela_diff(image, resaved)
            
            # Analyze ELA results
            analysis = self._analyze_ela(diff)
            
            # Generate ELA visualization as base64
            ela_image = self._enhance_ela(diff)
            ela_buffer = io.BytesIO()
            ela_image.save(ela_buffer, 'PNG')
            ela_base64 = base64.b64encode(ela_buffer.getvalue()).decode('utf-8')
            
            return {
                "performed": True,
                "max_error": analysis["max_error"],
                "avg_error": analysis["avg_error"],
                "suspicious_regions": analysis["suspicious_regions"],
                "ela_image": ela_base64  # Base64 visualization
            }
            
        except Exception as e:
            return {"performed": False, "error": str(e)}
    
    def _calculate_ela_diff(self, original: Image.Image, resaved: Image.Image) -> Image.Image:
        """Calculate pixel-by-pixel difference"""
        from PIL import ImageChops
        
        # Get difference
        diff = ImageChops.difference(original, resaved)
        return diff
    
    def _enhance_ela(self, diff: Image.Image, scale: int = 15) -> Image.Image:
        """Enhance ELA difference for visibility"""
        from PIL import ImageEnhance
        
        # Scale up the difference
        extrema = diff.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        
        if max_diff == 0:
            max_diff = 1
            
        # Scale and enhance
        scale_factor = 255.0 / max_diff * (scale / 10.0)
        
        enhanced = diff.point(lambda x: min(255, int(x * scale_factor)))
        return enhanced
    
    def _analyze_ela(self, diff: Image.Image) -> Dict:
        """Analyze ELA difference image for anomalies"""
        import statistics
        
        # Get pixel data
        pixels = list(diff.getdata())
        
        # Calculate error levels (sum of RGB differences)
        error_levels = [(p[0] + p[1] + p[2]) / 3 for p in pixels]
        
        max_error = max(error_levels)
        avg_error = statistics.mean(error_levels)
        
        # Find suspicious regions (pixels with very high error)
        threshold = avg_error * 3
        suspicious = sum(1 for e in error_levels if e > threshold)
        suspicious_ratio = suspicious / len(error_levels)
        
        return {
            "max_error": round(max_error, 2),
            "avg_error": round(avg_error, 2),
            "suspicious_regions": round(suspicious_ratio * 100, 2)
        }
    
    def _detect_manipulation(self, results: Dict) -> List[Dict]:
        """Detect manipulation indicators from analysis results"""
        indicators = []
        
        metadata = results.get("metadata", {})
        ela = results.get("ela", {})
        
        # Check 1: No EXIF metadata (suspicious for photos)
        if not metadata.get("has_metadata"):
            indicators.append({
                "type": "metadata_missing",
                "severity": "medium",
                "description": "No EXIF metadata found - may have been stripped or image is generated"
            })
        
        # Check 2: Editing software detected
        software = metadata.get("software", "")
        if software:
            editing_tools = ["photoshop", "gimp", "lightroom", "snapseed", "canva"]
            if any(tool in software.lower() for tool in editing_tools):
                indicators.append({
                    "type": "editing_software",
                    "severity": "low",
                    "description": f"Image was edited with: {software}"
                })
        
        # Check 3: High ELA error levels
        if ela.get("performed"):
            if ela.get("max_error", 0) > 50:
                indicators.append({
                    "type": "ela_anomaly",
                    "severity": "high",
                    "description": f"High ELA error detected ({ela['max_error']}%) - possible splicing or editing"
                })
            elif ela.get("suspicious_regions", 0) > 5:
                indicators.append({
                    "type": "ela_regions",
                    "severity": "medium",
                    "description": f"Suspicious regions detected ({ela['suspicious_regions']}% of image)"
                })
        
        # Check 4: No GPS data (not always suspicious, but worth noting)
        if not metadata.get("gps"):
            indicators.append({
                "type": "no_location",
                "severity": "info",
                "description": "No GPS location data - common for screenshots or web images"
            })
        
        return indicators
    
    def _calculate_risk(self, results: Dict) -> int:
        """Calculate overall manipulation risk score (0-100)"""
        risk = 0
        
        indicators = results.get("manipulation_indicators", [])
        
        for indicator in indicators:
            severity = indicator.get("severity", "info")
            if severity == "high":
                risk += 30
            elif severity == "medium":
                risk += 15
            elif severity == "low":
                risk += 5
        
        # ELA contribution
        ela = results.get("ela", {})
        if ela.get("performed"):
            risk += min(20, ela.get("max_error", 0) * 0.4)
        
        return min(100, int(risk))


# Helper function for Flask integration
def analyze_image_bytes(image_bytes: bytes, filename: str = "") -> Dict:
    """Analyze image from bytes - main entry point"""
    forensics = ImageForensics()
    return forensics.analyze(image_bytes, filename)
