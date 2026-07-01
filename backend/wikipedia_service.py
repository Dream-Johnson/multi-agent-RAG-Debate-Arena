"""
Wikipedia retrieval for the RAG pipeline.

Given a debate topic that may not match an exact Wikipedia page title
(e.g. "should AI replace teachers"), this module:
  1. Searches Wikipedia for the best-matching article title
  2. Fetches that article's full plain-text content

This is the "R" in RAG — Retrieval. The raw text returned here gets handed
to chunking.py next, then embedded by embeddings.py.
"""

import httpx

WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"

# Wikipedia's API etiquette policy asks non-browser clients to identify
# themselves with a descriptive User-Agent. Omitting this risks throttling.
HEADERS = {"User-Agent": "MultiAgentDebateRAG/1.0 (educational project)"}

# Wikimedia's edge protection blocks plain HTTP/1.1 connections (httpx's
# default) with a 403 "respect our robot policy" response, even with a
# legitimate User-Agent — but allows HTTP/2, which is what real browsers
# and curl normally negotiate. Discovered by testing: curl (HTTP/2 capable)
# succeeded while a default httpx request (HTTP/1.1) was rejected.
HTTP2 = True


class WikipediaNotFoundError(Exception):
    """Raised when no Wikipedia article could be found for a topic."""


async def search_wikipedia_title(topic: str) -> str:
    """Find the best-matching Wikipedia page title for a free-text topic."""
    params = {
        "action": "query",
        "list": "search",
        "srsearch": topic,
        "format": "json",
        "srlimit": 1,  # we only need the single best match
    }

    async with httpx.AsyncClient(http2=HTTP2) as client:
        response = await client.get(
            WIKIPEDIA_API_URL, params=params, headers=HEADERS, timeout=10.0
        )
        response.raise_for_status()  # raises if Wikipedia returns 4xx/5xx
        data = response.json()

    results = data.get("query", {}).get("search", [])
    if not results:
        raise WikipediaNotFoundError(f"No Wikipedia article found for topic: {topic!r}")

    return results[0]["title"]


async def fetch_wikipedia_article(topic: str) -> str:
    """
    Fetch the full plain-text content of the Wikipedia article most
    relevant to `topic`. Returns raw article text (not yet chunked).
    """
    title = await search_wikipedia_title(topic)

    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": True,  # plain text, not raw wikitext markup
        "titles": title,
        "format": "json",
    }

    async with httpx.AsyncClient(http2=HTTP2) as client:
        response = await client.get(
            WIKIPEDIA_API_URL, params=params, headers=HEADERS, timeout=10.0
        )
        response.raise_for_status()
        data = response.json()

    # The API returns pages as a dict keyed by page ID (not by title), e.g.
    # {"pages": {"12345": {"extract": "..."}}}. We searched for exactly one
    # title, so there's exactly one entry — grab it without knowing the ID.
    pages = data.get("query", {}).get("pages", {})
    page = next(iter(pages.values()))
    extract = page.get("extract", "")

    if not extract:
        raise WikipediaNotFoundError(f"Wikipedia article {title!r} has no text content")

    return extract
