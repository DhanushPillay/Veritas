"""
VERITAS - Reverse Image Search Service
Check if images have appeared elsewhere online
"""

import os
import hashlib
import requests
from typing import Dict, List, Optional
import base64


class ReverseImageSearch:
    """Service for finding image origins and duplicates"""
    
    TINEYE_API = "https://api.tineye.com/rest/search/"
    GOOGLE_LENS_URL = "https://lens.google.com/uploadbyurl"
    
    def __init__(self):
        self.tineye_api_key = os.environ.get('TINEYE_API_KEY', '')
    
    def search(self, image_data: bytes) -> Dict:
        """
        Perform reverse image search across multiple services.
        
        Args:
            image_data: Raw image bytes
        
        Returns:
            Dict with search results and match information
        """
        results = {
            "matches_found": 0,
            "sources": [],
            "oldest_match": None,
            "is_stock_photo": False,
            "search_engines_checked": []
        }
        
        # Calculate image hash for caching
        image_hash = hashlib.md5(image_data).hexdigest()
        
        # Try TinEye first (if API key available)
        if self.tineye_api_key:
            tineye_results = self._search_tineye(image_data)
            if tineye_results:
                results["sources"].extend(tineye_results.get("sources", []))
                results["matches_found"] += tineye_results.get("matches", 0)
                results["oldest_match"] = tineye_results.get("oldest")
                results["search_engines_checked"].append("TinEye")
        
        # Generate search URLs for manual checking
        results["manual_search_urls"] = self._generate_search_urls(image_data)
        
        # Analyze results
        results["analysis"] = self._analyze_results(results)
        
        return results
    
    def _search_tineye(self, image_data: bytes) -> Optional[Dict]:
        """Search using TinEye API"""
        if not self.tineye_api_key:
            return None
        
        try:
            # TinEye expects base64 encoded image
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            response = requests.post(
                self.TINEYE_API,
                auth=(self.tineye_api_key, ''),
                data={'image': image_b64},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                matches = data.get('result', {}).get('matches', [])
                
                sources = []
                oldest = None
                
                for match in matches[:10]:  # Limit to 10 results
                    source = {
                        "url": match.get('backlinks', [{}])[0].get('url', ''),
                        "domain": match.get('domain', ''),
                        "crawl_date": match.get('crawl_date', ''),
                        "image_url": match.get('image_url', '')
                    }
                    sources.append(source)
                    
                    # Track oldest
                    if not oldest or (source.get('crawl_date') and source['crawl_date'] < oldest):
                        oldest = source['crawl_date']
                
                return {
                    "matches": len(matches),
                    "sources": sources,
                    "oldest": oldest
                }
                
        except Exception as e:
            print(f"TinEye error: {e}")
        
        return None
    
    def _generate_search_urls(self, image_data: bytes) -> Dict:
        """Generate URLs for manual reverse image search"""
        # Create data URL for some services
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        return {
            "google_lens": "https://lens.google.com/",
            "tineye": "https://tineye.com/",
            "yandex": "https://yandex.com/images/",
            "bing": "https://www.bing.com/images/search?view=detailv2&iss=sbiupload"
        }
    
    def _analyze_results(self, results: Dict) -> Dict:
        """Analyze reverse search results for credibility"""
        analysis = {
            "originality_score": 100,
            "concerns": [],
            "verdict": "unique"
        }
        
        matches = results.get("matches_found", 0)
        sources = results.get("sources", [])
        
        if matches == 0:
            analysis["verdict"] = "unique"
            analysis["originality_score"] = 100
        elif matches < 5:
            analysis["verdict"] = "limited_matches"
            analysis["originality_score"] = 80
            analysis["concerns"].append(f"Found {matches} matches online")
        elif matches < 20:
            analysis["verdict"] = "moderate_reuse"
            analysis["originality_score"] = 50
            analysis["concerns"].append(f"Image appears in {matches} locations")
        else:
            analysis["verdict"] = "widely_circulated"
            analysis["originality_score"] = 20
            analysis["concerns"].append(f"Widely circulated ({matches}+ matches)")
        
        # Check for stock photo domains
        stock_domains = ["shutterstock", "gettyimages", "istockphoto", "adobe.stock", "depositphotos"]
        for source in sources:
            domain = source.get("domain", "").lower()
            if any(stock in domain for stock in stock_domains):
                analysis["is_stock_photo"] = True
                analysis["concerns"].append("This is a stock photo")
                break
        
        # Check oldest match date
        oldest = results.get("oldest_match")
        if oldest:
            analysis["first_seen"] = oldest
            analysis["concerns"].append(f"First seen online: {oldest}")
        
        return analysis


def search_image(image_bytes: bytes) -> Dict:
    """Main entry point for reverse image search"""
    searcher = ReverseImageSearch()
    return searcher.search(image_bytes)
