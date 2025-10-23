"""Frontend screenshot tools for visual before/after comparison."""

import logging
import os
import subprocess
import time
import signal
from pathlib import Path
from typing import Optional, Any
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


class ScreenshotTools:
    """Tools for capturing before/after screenshots of frontend changes."""

    def __init__(self, repo_path: Path, work_dir: Path, github_client: Optional[Any] = None):
        """
        Initialize ScreenshotTools.

        Args:
            repo_path: Path to repository
            work_dir: Working directory for screenshots
            github_client: GitHubClient instance for uploading screenshots (optional)
        """
        self.repo_path = repo_path
        self.work_dir = work_dir
        self.screenshots_dir = work_dir / ".dogwalker_screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.github_client = github_client

        self.dev_server_process: Optional[subprocess.Popen] = None
        self.dev_server_port: Optional[int] = None

    def detect_dev_server_command(self) -> Optional[str]:
        """
        Detect the development server command from package.json or common patterns.

        Returns:
            Dev server command string or None if not found
        """
        # Check package.json for dev script
        package_json = self.repo_path / "package.json"
        if package_json.exists():
            try:
                import json
                with open(package_json) as f:
                    data = json.load(f)
                    scripts = data.get("scripts", {})

                    # Common dev script names
                    for script_name in ["dev", "start", "develop", "serve"]:
                        if script_name in scripts:
                            logger.info(f"Found dev script: npm run {script_name}")
                            return f"npm run {script_name}"
            except Exception as e:
                logger.error(f"Failed to parse package.json: {e}")

        # Check for common framework files
        if (self.repo_path / "next.config.js").exists() or (self.repo_path / "next.config.mjs").exists():
            return "npm run dev"  # Next.js

        if (self.repo_path / "vite.config.js").exists() or (self.repo_path / "vite.config.ts").exists():
            return "npm run dev"  # Vite

        if (self.repo_path / "angular.json").exists():
            return "npm start"  # Angular

        logger.warning("Could not detect dev server command")
        return None

    def detect_dev_server_port(self, command: str) -> int:
        """
        Detect the port the dev server will run on.

        Args:
            command: Dev server command

        Returns:
            Port number (default: 3000)
        """
        # Framework default ports
        if "next" in command.lower():
            return 3000  # Next.js default
        elif "vite" in command.lower():
            return 5173  # Vite default
        elif "react-scripts" in command.lower():
            return 3000  # Create React App default
        elif "angular" in command.lower():
            return 4200  # Angular default
        elif "vue" in command.lower():
            return 8080  # Vue CLI default

        return 3000  # Default fallback

    def start_dev_server(self, timeout: int = 120) -> bool:
        """
        Start the development server and wait for it to be ready.

        Args:
            timeout: Maximum seconds to wait for server to start

        Returns:
            True if server started successfully, False otherwise
        """
        command = self.detect_dev_server_command()
        if not command:
            logger.warning("No dev server command detected, skipping server start")
            return False

        self.dev_server_port = self.detect_dev_server_port(command)

        # Install dependencies if node_modules doesn't exist
        node_modules = self.repo_path / "node_modules"
        if not node_modules.exists():
            logger.info("📦 Installing npm dependencies (node_modules not found)...")
            try:
                install_result = subprocess.run(
                    ["npm", "install"],
                    cwd=self.repo_path,
                    capture_output=True,
                    timeout=180,  # 3 minutes max for npm install
                )
                if install_result.returncode != 0:
                    logger.error(f"❌ npm install failed: {install_result.stderr.decode('utf-8', errors='ignore')[:500]}")
                    return False
                logger.info("✅ npm install completed successfully")
            except subprocess.TimeoutExpired:
                logger.error("❌ npm install timed out after 3 minutes")
                return False
            except Exception as e:
                logger.error(f"❌ npm install failed: {e}")
                return False

        logger.info(f"Starting dev server: {command}")

        try:
            # Start the dev server in the background
            self.dev_server_process = subprocess.Popen(
                command.split(),
                cwd=self.repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=None if os.name == 'nt' else lambda: signal.signal(signal.SIGINT, signal.SIG_IGN)
            )

            # Wait for server to be ready
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    import requests
                    response = requests.get(f"http://localhost:{self.dev_server_port}", timeout=2)
                    if response.status_code < 500:  # Server is responding
                        logger.info(f"Dev server ready on port {self.dev_server_port}")
                        return True
                except Exception:
                    pass

                # Check if process died
                returncode = self.dev_server_process.poll()
                if returncode is not None:
                    # Process exited - read output to see why
                    stdout, stderr = self.dev_server_process.communicate(timeout=1)
                    stdout_text = stdout.decode('utf-8', errors='ignore')[:500] if stdout else ""
                    stderr_text = stderr.decode('utf-8', errors='ignore')[:500] if stderr else ""

                    logger.error(f"❌ Dev server process died with exit code {returncode}")
                    if stdout_text:
                        logger.error(f"STDOUT: {stdout_text}")
                    if stderr_text:
                        logger.error(f"STDERR: {stderr_text}")

                    return False

                time.sleep(2)

            logger.warning(f"Dev server did not become ready within {timeout}s")
            return False

        except Exception as e:
            logger.error(f"Failed to start dev server: {e}")
            return False

    def stop_dev_server(self) -> None:
        """Stop the development server."""
        if self.dev_server_process:
            logger.info("Stopping dev server")
            try:
                self.dev_server_process.terminate()
                self.dev_server_process.wait(timeout=10)
            except Exception as e:
                logger.error(f"Error stopping dev server: {e}")
                try:
                    self.dev_server_process.kill()
                except Exception:
                    pass

            self.dev_server_process = None
            self.dev_server_port = None

    def capture_screenshot(
        self,
        url: str,
        filename: str,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        full_page: bool = True
    ) -> Optional[str]:
        """
        Capture a screenshot of a URL.

        Args:
            url: URL to screenshot (can be relative like "/about")
            filename: Filename for screenshot
            viewport_width: Browser viewport width
            viewport_height: Browser viewport height
            full_page: Capture full page or just viewport

        Returns:
            Path to screenshot file or None on failure
        """
        # Convert relative URLs to absolute
        if url.startswith("/"):
            if not self.dev_server_port:
                logger.error("Cannot screenshot relative URL - dev server not running")
                return None
            url = f"http://localhost:{self.dev_server_port}{url}"

        logger.info(f"Capturing screenshot: {url} -> {filename}")

        screenshot_path = self.screenshots_dir / filename

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': viewport_width, 'height': viewport_height}
                )
                page = context.new_page()

                # Navigate with timeout
                page.goto(url, wait_until='networkidle', timeout=30000)

                # Wait a bit for any animations/hydration
                page.wait_for_timeout(2000)

                # Capture screenshot
                page.screenshot(path=str(screenshot_path), full_page=full_page)

                browser.close()

                logger.info(f"Screenshot saved: {screenshot_path}")
                return str(screenshot_path)

        except PlaywrightTimeout as e:
            logger.error(f"Timeout capturing screenshot of {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to capture screenshot of {url}: {e}")
            return None

    def validate_url(self, url: str) -> bool:
        """
        Check if a URL exists and returns a valid response (not 404/500).

        Args:
            url: URL to validate

        Returns:
            True if URL is valid and accessible, False otherwise
        """
        try:
            import requests
            response = requests.head(url, timeout=5, allow_redirects=True)
            # Accept 200-399 status codes (success and redirects)
            is_valid = 200 <= response.status_code < 400
            if not is_valid:
                logger.info(f"URL validation failed for {url}: HTTP {response.status_code}")
            return is_valid
        except Exception as e:
            logger.warning(f"URL validation failed for {url}: {e}")
            return False

    def capture_multiple_screenshots(
        self,
        urls: list[str],
        prefix: str = ""
    ) -> list[dict[str, str]]:
        """
        Capture screenshots of multiple URLs and upload to GitHub.
        Only screenshots URLs that return valid HTTP responses (not 404s).

        Args:
            urls: List of URLs to screenshot
            prefix: Filename prefix (e.g., "before_" or "after_")

        Returns:
            List of dicts with url, filename, path (local), and github_url (if uploaded)
        """
        results = []

        for i, url in enumerate(urls, 1):
            # Convert relative URLs to absolute for validation
            full_url = url
            if url.startswith("/"):
                if not self.dev_server_port:
                    logger.warning(f"Cannot validate relative URL {url} - dev server not running")
                    continue
                full_url = f"http://localhost:{self.dev_server_port}{url}"

            # Validate URL before screenshotting
            if not self.validate_url(full_url):
                logger.info(f"Skipping screenshot of {url} - URL not accessible")
                continue

            # Generate filename from URL
            url_slug = url.strip("/").replace("/", "_").replace(":", "").replace("?", "_")[:50]
            if not url_slug:
                url_slug = "home"

            filename = f"{prefix}{url_slug}.png"

            screenshot_path = self.capture_screenshot(url, filename)

            if screenshot_path:
                result = {
                    'url': url,
                    'filename': filename,
                    'path': screenshot_path,
                    'github_url': None  # Will be set if upload succeeds
                }

                # Upload to GitHub if client is available
                if self.github_client:
                    logger.info(f"Uploading screenshot to GitHub: {filename}")
                    github_url = self.github_client.upload_image_to_github(
                        image_path=screenshot_path,
                        screenshot_filename=filename
                    )

                    if github_url:
                        result['github_url'] = github_url
                        logger.info(f"Screenshot uploaded successfully: {github_url}")
                    else:
                        logger.warning(f"Failed to upload screenshot to GitHub: {filename}")
                else:
                    logger.warning("No GitHub client available, screenshot will not be uploaded")

                results.append(result)

        logger.info(f"Captured {len(results)}/{len(urls)} screenshots")
        return results

    def extract_urls_from_plan(self, plan: str) -> list[str]:
        """
        Extract frontend page URLs from implementation plan.

        Args:
            plan: Implementation plan text

        Returns:
            List of URLs to screenshot (defaults to ["/"] if none found)
        """
        import re

        urls = []

        # Look for route patterns: /path, /path/subpath, etc.
        route_patterns = re.findall(r'["\'](/[\w/-]*)["\']', plan)
        urls.extend(route_patterns)

        # Look for page references: "home page", "about page", etc.
        page_refs = re.findall(r'(\w+)\s+page', plan.lower())
        for page in page_refs:
            if page not in ['home', 'main', 'index']:
                urls.append(f"/{page}")

        # Remove duplicates and sort
        urls = sorted(set(urls))

        # Always include home page
        if not urls or "/" not in urls:
            urls.insert(0, "/")

        logger.info(f"Extracted {len(urls)} URLs from plan: {urls}")
        return urls[:5]  # Limit to 5 URLs

    def is_frontend_task(self, plan: str, files: Optional[list[str]] = None) -> bool:
        """
        Determine if this task involves frontend changes.

        Args:
            plan: Implementation plan
            files: List of files to be modified (optional)

        Returns:
            True if frontend changes are expected
        """
        # Check plan for frontend keywords
        frontend_keywords = [
            'page', 'component', 'ui', 'frontend', 'interface', 'react', 'vue', 'angular',
            'tailwind', 'css', 'style', 'button', 'form', 'navbar', 'layout', 'route',
            'next.js', 'view', 'template', 'html', 'jsx', 'tsx'
        ]

        plan_lower = plan.lower()
        if any(keyword in plan_lower for keyword in frontend_keywords):
            logger.info("Frontend task detected from plan keywords")
            return True

        # Check files for frontend extensions
        if files:
            frontend_extensions = ['.tsx', '.jsx', '.vue', '.svelte', '.css', '.scss', '.sass']
            if any(any(file.endswith(ext) for ext in frontend_extensions) for file in files):
                logger.info("Frontend task detected from file extensions")
                return True

        logger.info("Not a frontend task")
        return False

    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_dev_server()
