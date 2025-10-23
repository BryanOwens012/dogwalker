"""Internet search tools for AI agents."""

import logging
from typing import Optional
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)


class SearchTools:
    """Tools for searching the internet and retrieving current information."""

    def __init__(self):
        """Initialize SearchTools with DuckDuckGo search."""
        self.ddgs = DDGS()

    def search(
        self,
        query: str,
        max_results: int = 10,
        region: str = "wt-wt"  # Worldwide
    ) -> list[dict[str, str]]:
        """
        Search the internet using DuckDuckGo.

        Args:
            query: Search query
            max_results: Maximum number of results to return (default: 10)
            region: Search region (default: worldwide)

        Returns:
            List of search results, each containing:
                - title: Page title
                - href: URL
                - body: Snippet/description
        """
        logger.info(f"Searching internet for: {query}")

        try:
            results = list(self.ddgs.text(
                keywords=query,
                region=region,
                max_results=max_results
            ))

            logger.info(f"Found {len(results)} results for query: {query}")

            return results

        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return []

    def search_news(
        self,
        query: str,
        max_results: int = 5,
        region: str = "wt-wt"
    ) -> list[dict[str, str]]:
        """
        Search for news articles using DuckDuckGo News.

        Args:
            query: Search query
            max_results: Maximum number of results to return (default: 5)
            region: Search region (default: worldwide)

        Returns:
            List of news results with title, url, body, date, source
        """
        logger.info(f"Searching news for: {query}")

        try:
            results = list(self.ddgs.news(
                keywords=query,
                region=region,
                max_results=max_results
            ))

            logger.info(f"Found {len(results)} news results for query: {query}")

            return results

        except Exception as e:
            logger.error(f"News search failed for query '{query}': {e}")
            return []

    def format_search_results(
        self,
        results: list[dict[str, str]],
        include_urls: bool = True
    ) -> str:
        """
        Format search results as readable text for AI consumption.

        Args:
            results: List of search results from search() or search_news()
            include_urls: Include URLs in formatted output (default: True)

        Returns:
            Formatted text with search results
        """
        if not results:
            return "No search results found."

        formatted_lines = ["Internet Search Results:"]
        formatted_lines.append("")

        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            body = result.get('body', result.get('description', 'No description'))
            url = result.get('href', result.get('url', ''))

            formatted_lines.append(f"{i}. {title}")
            formatted_lines.append(f"   {body}")

            if include_urls and url:
                formatted_lines.append(f"   Source: {url}")

            formatted_lines.append("")

        return "\n".join(formatted_lines)

    def quick_answer(self, query: str) -> Optional[str]:
        """
        Get a quick answer/instant answer for a query.

        NOTE: The DuckDuckGo instant answers API has been deprecated/removed.
        This method now returns None but is kept for backwards compatibility.

        Args:
            query: Search query (works best with factual questions)

        Returns:
            Quick answer text if available, None otherwise
        """
        # DuckDuckGo removed the answers() API method
        # Just return None - regular search results are sufficient
        logger.debug(f"Quick answer skipped (API deprecated) for: {query}")
        return None

    def search_with_context(
        self,
        query: str,
        max_results: int = 5,
        include_quick_answer: bool = True
    ) -> str:
        """
        Search and format results with full context for AI.

        This is the main method dogs should use - it provides comprehensive
        search results formatted for AI consumption.

        Args:
            query: Search query
            max_results: Maximum search results (default: 5)
            include_quick_answer: Try to get instant answer first (default: True)

        Returns:
            Formatted search context with optional quick answer and search results
        """
        context_parts = []

        # Try quick answer first
        if include_quick_answer:
            quick = self.quick_answer(query)
            if quick:
                context_parts.append("Quick Answer:")
                context_parts.append(quick)
                context_parts.append("")

        # Get search results
        results = self.search(query, max_results=max_results)

        if results:
            formatted = self.format_search_results(results, include_urls=True)
            context_parts.append(formatted)
        else:
            context_parts.append(f"No search results found for: {query}")

        return "\n".join(context_parts)

    def format_for_ai_context(
        self,
        searches: list[tuple[str, str]],
        title: str = "Internet Research"
    ) -> str:
        """
        Format multiple searches as context block for AI prompts.

        Args:
            searches: List of (query, results_text) tuples
            title: Title for the context block

        Returns:
            Formatted context block
        """
        if not searches:
            return ""

        context_lines = [f"CONTEXT - {title}:"]
        context_lines.append("The following information was found via internet search:")
        context_lines.append("")

        for query, results in searches:
            context_lines.append(f"Query: {query}")
            context_lines.append(results)
            context_lines.append("")

        return "\n".join(context_lines)
