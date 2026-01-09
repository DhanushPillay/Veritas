"""
VERITAS - Fact Check Service
Integrates with Google Fact Check Tools API and other verification sources
"""

import os
import requests
from typing import List, Dict, Optional


class FactCheckService:
    """Service for cross-referencing claims with fact-check databases"""
    
    GOOGLE_FACTCHECK_API = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('GOOGLE_API_KEY', '')
    
    def search_claims(self, query: str, language: str = "en") -> List[Dict]:
        """
        Search for fact-checks related to a claim using Google Fact Check API.
        
        Args:
            query: The claim or text to search for
            language: Language code (default: en)
        
        Returns:
            List of fact-check results with ratings
        """
        if not self.api_key:
            return []
        
        try:
            params = {
                "query": query[:200],  # Limit query length
                "languageCode": language,
                "key": self.api_key
            }
            
            response = requests.get(self.GOOGLE_FACTCHECK_API, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_factcheck_results(data)
            else:
                print(f"Fact Check API error: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Fact Check error: {e}")
            return []
    
    def _parse_factcheck_results(self, data: Dict) -> List[Dict]:
        """Parse Google Fact Check API response into structured results"""
        results = []
        
        for claim in data.get("claims", []):
            claim_text = claim.get("text", "")
            claimant = claim.get("claimant", "Unknown")
            
            for review in claim.get("claimReview", []):
                results.append({
                    "claim": claim_text,
                    "claimant": claimant,
                    "publisher": review.get("publisher", {}).get("name", "Unknown"),
                    "url": review.get("url", ""),
                    "title": review.get("title", ""),
                    "rating": review.get("textualRating", "Unknown"),
                    "language": review.get("languageCode", "en")
                })
        
        return results[:5]  # Limit to top 5 results
    
    def get_credibility_boost(self, results: List[Dict]) -> Dict:
        """
        Analyze fact-check results to determine credibility impact.
        
        Returns:
            dict with credibility_modifier (-30 to +30) and summary
        """
        if not results:
            return {"modifier": 0, "summary": "No matching fact-checks found"}
        
        # Count positive vs negative ratings
        positive_terms = ["true", "correct", "accurate", "verified", "real"]
        negative_terms = ["false", "fake", "misleading", "incorrect", "pants on fire", "lie"]
        
        positive = 0
        negative = 0
        
        for r in results:
            rating = r.get("rating", "").lower()
            if any(term in rating for term in positive_terms):
                positive += 1
            elif any(term in rating for term in negative_terms):
                negative += 1
        
        if negative > positive:
            modifier = -20 - (negative * 5)
            summary = f"Found {len(results)} fact-checks. {negative} rated FALSE/MISLEADING."
        elif positive > negative:
            modifier = 15 + (positive * 3)
            summary = f"Found {len(results)} fact-checks. {positive} rated TRUE/VERIFIED."
        else:
            modifier = 0
            summary = f"Found {len(results)} fact-checks with mixed ratings."
        
        return {
            "modifier": max(-30, min(30, modifier)),  # Clamp to -30 to +30
            "summary": summary,
            "sources": [{"publisher": r["publisher"], "rating": r["rating"], "url": r["url"]} for r in results]
        }


def search_news_for_claim(claim: str) -> List[Dict]:
    """
    Search news articles related to a claim using free NewsAPI.
    Requires NEWS_API_KEY environment variable.
    """
    api_key = os.environ.get('NEWS_API_KEY', '')
    if not api_key:
        return []
    
    try:
        # Extract key terms (first ~100 chars)
        query = claim[:100].replace('"', '').strip()
        
        response = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "sortBy": "relevancy",
                "pageSize": 5,
                "apiKey": api_key
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return [{
                "title": a.get("title"),
                "source": a.get("source", {}).get("name"),
                "url": a.get("url"),
                "published": a.get("publishedAt")
            } for a in data.get("articles", [])[:5]]
        
        return []
        
    except Exception as e:
        print(f"News API error: {e}")
        return []
