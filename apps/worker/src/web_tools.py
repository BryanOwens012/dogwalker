"""Web browsing and screenshot tools for AI agents."""

import logging
import re
from pathlib import Path
from typing import Optional
from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
import requests

logger = logging.getLogger(__name__)


class WebTools:
    """Tools for fetching websites and capturing screenshots."""

    def __init__(self, work_dir: Path):
        """
        Initialize WebTools.

        Args:
            work_dir: Directory to save screenshots and web content
        """
        self.work_dir = work_dir
        self.screenshots_dir = work_dir / ".dogwalker_web"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def extract_urls(text: str) -> list[str]:
        """
        Extract URLs from text.

        Args:
            text: Text that may contain URLs

        Returns:
            List of URLs found in text
        """
        # Match http/https URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\].,;:!?)]'
        urls = re.findall(url_pattern, text)

        logger.info(f"Extracted {len(urls)} URLs from text")
        return urls

    def fetch_and_screenshot(
        self,
        url: str,
        screenshot_name: Optional[str] = None,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        full_page: bool = True,
    ) -> dict[str, str]:
        """
        Fetch a website and capture a screenshot.

        Args:
            url: URL to fetch
            screenshot_name: Custom name for screenshot (default: derived from URL)
            viewport_width: Browser viewport width in pixels
            viewport_height: Browser viewport height in pixels
            full_page: Capture full page (True) or just viewport (False)

        Returns:
            Dictionary with:
                - url: The fetched URL
                - screenshot_path: Path to saved screenshot
                - page_title: Page title
                - text_content: Extracted text content (headings, key elements)
                - success: Whether fetch was successful
                - error: Error message if failed
        """
        logger.info(f"Fetching website: {url}")

        # Generate screenshot filename
        if not screenshot_name:
            # Extract domain from URL for filename
            domain = re.sub(r'https?://', '', url).split('/')[0].replace('.', '_')
            screenshot_name = f"{domain}.png"

        screenshot_path = self.screenshots_dir / screenshot_name

        try:
            with sync_playwright() as p:
                # Launch browser in headless mode
                browser = p.chromium.launch(headless=True)

                # Create context with viewport size
                context = browser.new_context(
                    viewport={'width': viewport_width, 'height': viewport_height},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )

                page = context.new_page()

                # Navigate to URL with timeout
                logger.info(f"Navigating to {url}...")
                page.goto(url, wait_until='networkidle', timeout=30000)

                # Wait a bit for any dynamic content to load
                page.wait_for_timeout(2000)

                # Get page title
                page_title = page.title()
                logger.info(f"Page title: {page_title}")

                # Capture screenshot
                logger.info(f"Capturing screenshot: {screenshot_path}")
                page.screenshot(path=str(screenshot_path), full_page=full_page)

                # Extract text content
                html_content = page.content()
                text_content = self._extract_text_content(html_content)

                # Clean up
                browser.close()

                logger.info(f"Successfully fetched and captured {url}")

                return {
                    'url': url,
                    'screenshot_path': str(screenshot_path),
                    'page_title': page_title,
                    'text_content': text_content,
                    'success': True,
                    'error': None
                }

        except PlaywrightTimeout as e:
            error_msg = f"Timeout loading {url}: {str(e)}"
            logger.error(error_msg)
            return {
                'url': url,
                'screenshot_path': None,
                'page_title': None,
                'text_content': None,
                'success': False,
                'error': error_msg
            }

        except Exception as e:
            error_msg = f"Failed to fetch {url}: {str(e)}"
            logger.exception(error_msg)
            return {
                'url': url,
                'screenshot_path': None,
                'page_title': None,
                'text_content': None,
                'success': False,
                'error': error_msg
            }

    def _extract_text_content(self, html: str) -> str:
        """
        Extract key text content from HTML.

        Args:
            html: HTML content

        Returns:
            Formatted text with headings and key elements
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer"]):
            script.decompose()

        # Extract headings
        headings = []
        for i in range(1, 7):  # h1 through h6
            for heading in soup.find_all(f'h{i}'):
                text = heading.get_text(strip=True)
                if text:
                    headings.append(f"{'#' * i} {text}")

        # Extract main content (limit to first 1000 characters)
        body = soup.find('body')
        if body:
            text = body.get_text(separator=' ', strip=True)
            # Collapse multiple spaces
            text = re.sub(r'\s+', ' ', text)
            # Limit length
            text = text[:1000] + '...' if len(text) > 1000 else text
        else:
            text = ""

        # Combine headings and content
        result = "\n".join(headings)
        if headings and text:
            result += f"\n\nContent preview:\n{text}"
        elif text:
            result = f"Content preview:\n{text}"

        return result if result else "No text content extracted"

    def fetch_multiple_urls(
        self,
        urls: list[str],
        max_urls: int = 5
    ) -> list[dict[str, str]]:
        """
        Fetch and screenshot multiple URLs.

        Args:
            urls: List of URLs to fetch
            max_urls: Maximum number of URLs to fetch (to prevent abuse)

        Returns:
            List of result dictionaries from fetch_and_screenshot
        """
        # Limit number of URLs
        urls_to_fetch = urls[:max_urls]

        if len(urls) > max_urls:
            logger.warning(f"Limiting to {max_urls} URLs (found {len(urls)})")

        results = []
        for i, url in enumerate(urls_to_fetch, 1):
            logger.info(f"Fetching URL {i}/{len(urls_to_fetch)}: {url}")
            result = self.fetch_and_screenshot(
                url,
                screenshot_name=f"website_{i}.png"
            )
            results.append(result)

        successful = sum(1 for r in results if r['success'])
        logger.info(f"Fetched {successful}/{len(results)} URLs successfully")

        return results

    def format_web_context_for_ai(self, results: list[dict[str, str]]) -> str:
        """
        Format web fetch results as context for AI.

        Args:
            results: List of result dictionaries from fetch_and_screenshot

        Returns:
            Formatted text for inclusion in AI prompts
        """
        if not results:
            return ""

        context_parts = ["CONTEXT - Referenced Websites:"]
        context_parts.append("The following websites were fetched and analyzed:")
        context_parts.append("")

        for i, result in enumerate(results, 1):
            if result['success']:
                context_parts.append(f"{i}. {result['url']}")
                context_parts.append(f"   Title: {result['page_title']}")
                context_parts.append(f"   Screenshot: {Path(result['screenshot_path']).name}")

                # Include text content (truncated)
                text_preview = result['text_content'][:300]
                if len(result['text_content']) > 300:
                    text_preview += "..."
                context_parts.append(f"   Content: {text_preview}")
                context_parts.append("")
            else:
                context_parts.append(f"{i}. {result['url']} - FAILED: {result['error']}")
                context_parts.append("")

        context_parts.append("Screenshots are available in .dogwalker_web/ directory for visual reference.")

        return "\n".join(context_parts)

    def get_screenshot_paths(self, results: list[dict[str, str]]) -> list[str]:
        """
        Get list of screenshot file paths from fetch results.

        Args:
            results: List of result dictionaries from fetch_and_screenshot

        Returns:
            List of screenshot file paths (only successful fetches)
        """
        return [
            result['screenshot_path']
            for result in results
            if result['success'] and result['screenshot_path']
        ]

    def cleanup(self) -> None:
        """Clean up web tools resources (screenshots directory)."""
        # Screenshots will be committed to the branch, so no cleanup needed
        # They'll be removed when the work directory is cleaned up
        pass
