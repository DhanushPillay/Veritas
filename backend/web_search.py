"""
Web Search Module for Veritas Chatbot
Uses DuckDuckGo for free web searches
"""

import requests
import logging
from urllib.parse import quote_plus

# Configure logger
logger = logging.getLogger(__name__)


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web using DuckDuckGo's instant answer API.
    Returns a list of search results with title, url, and snippet.
    """
    try:
        # Use DuckDuckGo HTML search (more reliable for general queries)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Try DuckDuckGo instant answer API first
        api_url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1"
        response = requests.get(api_url, headers=headers, timeout=10)
        data = response.json()
        
        results = []
        
        # Get abstract (main answer)
        if data.get('Abstract'):
            results.append({
                'title': data.get('Heading', 'Result'),
                'url': data.get('AbstractURL', ''),
                'snippet': data.get('Abstract', '')
            })
        
        # Get related topics
        for topic in data.get('RelatedTopics', [])[:max_results]:
            if isinstance(topic, dict) and 'Text' in topic:
                results.append({
                    'title': topic.get('Text', '')[:100],
                    'url': topic.get('FirstURL', ''),
                    'snippet': topic.get('Text', '')
                })
        
        # If no results from instant answer, try a different approach
        if not results:
            # Use DuckDuckGo lite for scraping (backup)
            results = _search_ddg_lite(query, max_results)
        
        return results[:max_results]
        
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return []


def _search_ddg_lite(query: str, max_results: int = 5) -> list[dict]:
    """Backup search using DuckDuckGo lite version"""
    try:
        from html.parser import HTMLParser
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        url = f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}"
        response = requests.get(url, headers=headers, timeout=10)
        
        # Simple parsing - extract links and text
        results = []
        lines = response.text.split('\n')
        
        for i, line in enumerate(lines):
            if 'class="result-link"' in line or 'href="http' in line:
                # Extract URL
                import re
                url_match = re.search(r'href="([^"]+)"', line)
                if url_match:
                    result_url = url_match.group(1)
                    if result_url.startswith('http') and 'duckduckgo' not in result_url:
                        # Try to get title from same or next line
                        title_match = re.search(r'>([^<]+)</a>', line)
                        title = title_match.group(1) if title_match else result_url[:50]
                        
                        results.append({
                            'title': title,
                            'url': result_url,
                            'snippet': ''
                        })
                        
                        if len(results) >= max_results:
                            break
        
        return results
        
    except Exception as e:
        logger.error(f"DDG Lite search error: {e}", exc_info=True)
        return []


def format_search_results(results: list[dict]) -> str:
    """Format search results for inclusion in AI context"""
    if not results:
        return "No search results found."
    
    formatted = "**Web Search Results:**\n\n"
    for i, result in enumerate(results, 1):
        formatted += f"{i}. **{result['title']}**\n"
        if result['url']:
            formatted += f"   Link: {result['url']}\n"
        if result['snippet']:
            formatted += f"   {result['snippet']}\n"
        formatted += "\n"
    
    return formatted
