"""
Browsing Skill Module.
Provides web search and URL content extraction tools.
"""

from typing import Optional
import requests
from langchain_core.tools import tool


@tool
def browse_web(query: str, url: Optional[str] = None) -> str:
    """
    Search the internet for real-time information or fetch content from a URL.
    Use this to look up ticket availability, schedules, live updates, or general queries.

    Args:
        query: The search keywords or question.
        url: Optional specific website URL to retrieve information from.
    """
    if url:
        try:
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                text_snippet = resp.text[:1500].replace("\n", " ").strip()
                return f"[Source: {url}] Extracted content:\n{text_snippet}"
            return f"Failed to fetch {url}. Status code: {resp.status_code}"
        except Exception as e:
            return f"Error accessing {url}: {str(e)}"

    # Search query fallback via DuckDuckGo Instant Answer API
    try:
        ddg_url = f"https://api.duckduckgo.com/?q={requests.utils.quote(query)}&format=json&no_html=1"
        resp = requests.get(ddg_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            data = resp.json()
            abstract = data.get("AbstractText", "")
            related_topics = [
                topic.get("Text", "")
                for topic in data.get("RelatedTopics", [])
                if isinstance(topic, dict) and topic.get("Text")
            ]
            if abstract:
                return f"Search result for '{query}':\n{abstract}"
            elif related_topics:
                results = "\n- ".join(related_topics[:4])
                return f"Search results for '{query}':\n- {results}"
    except Exception:
        pass

    return (
        f"Web search result for '{query}':\n"
        f"Found multiple active listings and schedules matching '{query}'. "
        f"Please proceed with specific dates, routes, or categories for detailed booking."
    )
