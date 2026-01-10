"""
C2PA Content Credentials Detector
Detects AI-generated images from DALL-E, Adobe Firefly, Microsoft Copilot
by reading C2PA/IPTC/XMP metadata embedded in images.
"""

import io
import json
import re
from PIL import Image
from PIL.ExifTags import TAGS
import xml.etree.ElementTree as ET


class C2PADetector:
    """
    Detects C2PA (Coalition for Content Provenance and Authenticity) 
    metadata in images to identify AI-generated content.
    """
    
    # Known AI generator signatures in metadata
    AI_SIGNATURES = {
        "dall-e": ["openai", "dall-e", "dalle"],
        "adobe_firefly": ["adobe", "firefly", "adobe firefly"],
        "microsoft_copilot": ["microsoft", "copilot", "designer"],
        "midjourney": ["midjourney"],
        "stable_diffusion": ["stable diffusion", "stability.ai", "stablediffusion"],
        "google_imagen": ["google", "imagen"],
    }
    
    def __init__(self):
        pass
    
    def detect(self, image_path_or_bytes):
        """
        Analyze image for C2PA/metadata AI signatures.
        
        Args:
            image_path_or_bytes: File path string or bytes object
            
        Returns:
            dict: Detection results
        """
        try:
            # Load image
            if isinstance(image_path_or_bytes, bytes):
                img = Image.open(io.BytesIO(image_path_or_bytes))
            else:
                img = Image.open(image_path_or_bytes)
            
            results = {
                "detected": False,
                "source": None,
                "confidence": 0,
                "metadata_found": [],
                "raw_metadata": {}
            }
            
            # Check multiple metadata sources
            xmp_result = self._check_xmp_metadata(img)
            exif_result = self._check_exif_metadata(img)
            iptc_result = self._check_iptc_metadata(img)
            info_result = self._check_image_info(img)
            
            # Combine results
            all_results = [xmp_result, exif_result, iptc_result, info_result]
            
            for result in all_results:
                if result["detected"]:
                    results["detected"] = True
                    if result["source"] and not results["source"]:
                        results["source"] = result["source"]
                    results["metadata_found"].extend(result.get("metadata_found", []))
                    results["raw_metadata"].update(result.get("raw_metadata", {}))
            
            # Calculate confidence
            if results["detected"]:
                results["confidence"] = min(100, len(results["metadata_found"]) * 25 + 50)
            
            return results
            
        except Exception as e:
            return {
                "detected": False,
                "source": None,
                "confidence": 0,
                "error": str(e)
            }
    
    def _check_xmp_metadata(self, img):
        """Check XMP metadata for C2PA assertions"""
        result = {"detected": False, "source": None, "metadata_found": [], "raw_metadata": {}}
        
        try:
            # Get XMP data from image
            xmp_data = None
            
            # Check common XMP locations
            if hasattr(img, 'info'):
                for key in ['XML:com.adobe.xmp', 'xmp', 'XMP']:
                    if key in img.info:
                        xmp_data = img.info[key]
                        break
            
            if xmp_data:
                result["raw_metadata"]["xmp"] = str(xmp_data)[:500]
                
                # Parse XMP for AI signatures
                xmp_lower = str(xmp_data).lower()
                
                for source, signatures in self.AI_SIGNATURES.items():
                    for sig in signatures:
                        if sig in xmp_lower:
                            result["detected"] = True
                            result["source"] = source
                            result["metadata_found"].append(f"XMP contains '{sig}'")
                
                # Check for C2PA specific markers
                if "c2pa" in xmp_lower or "contentcredentials" in xmp_lower:
                    result["detected"] = True
                    result["metadata_found"].append("C2PA content credentials found")
                    
        except Exception as e:
            result["raw_metadata"]["xmp_error"] = str(e)
        
        return result
    
    def _check_exif_metadata(self, img):
        """Check EXIF metadata for AI tool signatures"""
        result = {"detected": False, "source": None, "metadata_found": [], "raw_metadata": {}}
        
        try:
            exif = img._getexif()
            if exif:
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    
                    # Store relevant tags
                    if tag in ['Software', 'Make', 'Model', 'ImageDescription', 'UserComment']:
                        result["raw_metadata"][tag] = str(value)[:200]
                        
                        # Check for AI signatures
                        value_lower = str(value).lower()
                        for source, signatures in self.AI_SIGNATURES.items():
                            for sig in signatures:
                                if sig in value_lower:
                                    result["detected"] = True
                                    result["source"] = source
                                    result["metadata_found"].append(f"EXIF {tag} contains '{sig}'")
                                    
        except Exception as e:
            result["raw_metadata"]["exif_error"] = str(e)
        
        return result
    
    def _check_iptc_metadata(self, img):
        """Check IPTC metadata for AI generation info"""
        result = {"detected": False, "source": None, "metadata_found": [], "raw_metadata": {}}
        
        try:
            # IPTC data is often in the 'app' segments
            if hasattr(img, 'applist'):
                for app in img.applist:
                    if 'iptc' in str(app).lower() or 'photoshop' in str(app).lower():
                        result["raw_metadata"]["iptc"] = str(app)[:200]
                        
                        # Check for AI signatures
                        app_lower = str(app).lower()
                        for source, signatures in self.AI_SIGNATURES.items():
                            for sig in signatures:
                                if sig in app_lower:
                                    result["detected"] = True
                                    result["source"] = source
                                    result["metadata_found"].append(f"IPTC contains '{sig}'")
                                    
        except Exception as e:
            result["raw_metadata"]["iptc_error"] = str(e)
        
        return result
    
    def _check_image_info(self, img):
        """Check PIL image info dict for any AI markers"""
        result = {"detected": False, "source": None, "metadata_found": [], "raw_metadata": {}}
        
        try:
            if hasattr(img, 'info') and img.info:
                for key, value in img.info.items():
                    # Skip binary data
                    if isinstance(value, bytes) and len(value) > 1000:
                        continue
                        
                    value_str = str(value).lower()
                    
                    # Check for AI signatures
                    for source, signatures in self.AI_SIGNATURES.items():
                        for sig in signatures:
                            if sig in value_str:
                                result["detected"] = True
                                result["source"] = source
                                result["metadata_found"].append(f"Image info '{key}' contains '{sig}'")
                                result["raw_metadata"][key] = str(value)[:200]
                                
        except Exception as e:
            result["raw_metadata"]["info_error"] = str(e)
        
        return result


# Convenience function
def detect_c2pa(image_path_or_bytes):
    """Quick detection function"""
    detector = C2PADetector()
    return detector.detect(image_path_or_bytes)
