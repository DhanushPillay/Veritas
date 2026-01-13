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


def search_web_context(query: str) -> List[Dict]:
    """
    Search web using DuckDuckGo (Free, no key required).
    """
    try:
        from duckduckgo_search import DDGS
        
        results = []
        # Use DDGS context manager for stability
        with DDGS() as ddgs:
            # Search for the query
            ddg_results = list(ddgs.text(query[:200], max_results=5))
            
            for r in ddg_results:
                results.append({
                    "title": r.get('title'),
                    "url": r.get('href'),
                    "snippet": r.get('body'),
                    "source": "Web Search (DuckDuckGo)"
                })
                
        return results
    except Exception as e:
        print(f"DuckDuckGo error: {e}")
        return []


def scrape_url_content(url: str) -> str:
    """
    Fetch and extract text content from a URL.
    """
    try:
        from bs4 import BeautifulSoup
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return ""
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
            
        # Get text
        text = soup.get_text()
        
        # Break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text[:5000]  # Limit content
        
    except Exception as e:
        print(f"Scraping error: {e}")
        return ""


def scrape_article_details(url: str) -> Dict:
    """
    Extract detailed article information from a URL.
    Returns title, source, date, and content for fact-checking.
    """
    try:
        from bs4 import BeautifulSoup
        from urllib.parse import urlparse
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return {"error": f"Failed to fetch URL (status {response.status_code})"}
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title = ""
        if soup.title:
            title = soup.title.string or ""
        og_title = soup.find("meta", property="og:title")
        if og_title:
            title = og_title.get("content", title)
            
        # Extract source/publisher
        domain = urlparse(url).netloc.replace("www.", "")
        publisher = domain
        og_site = soup.find("meta", property="og:site_name")
        if og_site:
            publisher = og_site.get("content", publisher)
            
        # Extract publish date
        publish_date = ""
        date_meta = soup.find("meta", property="article:published_time")
        if date_meta:
            publish_date = date_meta.get("content", "")
        if not publish_date:
            time_tag = soup.find("time")
            if time_tag:
                publish_date = time_tag.get("datetime", time_tag.get_text())
                
        # Extract main content
        article_content = ""
        
        # Try common article containers
        article = soup.find("article")
        if article:
            for tag in article(["script", "style", "nav", "aside"]):
                tag.decompose()
            article_content = article.get_text(separator="\n", strip=True)
        else:
            # Fallback: get all paragraphs
            paragraphs = soup.find_all("p")
            article_content = "\n".join([p.get_text(strip=True) for p in paragraphs])
        
        # Clean up content
        lines = [line.strip() for line in article_content.split("\n") if len(line.strip()) > 30]
        article_content = "\n".join(lines[:50])  # Limit to first 50 meaningful lines
        
        return {
            "url": url,
            "title": title.strip()[:200] if title else "Unknown Title",
            "publisher": publisher,
            "publish_date": publish_date[:30] if publish_date else "Unknown Date",
            "content": article_content[:4000],  # Limit content length
            "domain": domain,
            "success": True
        }
        
    except Exception as e:
        print(f"Article scraping error: {e}")
        return {
            "url": url,
            "error": str(e),
            "success": False
        }

