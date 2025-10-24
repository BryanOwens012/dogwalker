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

    def is_port_available(self, port: int) -> bool:
        """
        Check if a port is available.

        Args:
            port: Port number to check

        Returns:
            True if port is available, False otherwise
        """
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result != 0  # Port is available if connection fails
        except Exception as e:
            logger.warning(f"Error checking port {port}: {e}")
            return False

    def _detect_port_from_output(self, output_lines: list[str]) -> Optional[int]:
        """
        Try to detect the actual port from dev server output.

        Args:
            output_lines: Lines of server output

        Returns:
            Detected port number or None
        """
        import re

        # Common patterns in dev server output
        patterns = [
            r'localhost:(\d+)',
            r'http://.*:(\d+)',
            r'port\s+(\d+)',
            r'PORT\s*=\s*(\d+)',
            r'listening.*?(\d+)',
            r'started.*?(\d+)',
        ]

        for line in reversed(output_lines):  # Check recent output first
            line_lower = line.lower()
            for pattern in patterns:
                match = re.search(pattern, line_lower)
                if match:
                    try:
                        port = int(match.group(1))
                        if 1024 <= port <= 65535:  # Valid port range
                            logger.info(f"Detected port {port} from output: {line.strip()}")
                            return port
                    except (ValueError, IndexError):
                        continue

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

    def find_available_port(self, preferred_port: int) -> Optional[int]:
        """
        Find an available port, starting with the preferred port.

        Args:
            preferred_port: The preferred port to try first

        Returns:
            Available port number, or None if no ports available
        """
        # Try preferred port first
        if self.is_port_available(preferred_port):
            logger.info(f"Preferred port {preferred_port} is available")
            return preferred_port

        logger.warning(f"Preferred port {preferred_port} is not available, trying alternatives...")

        # Try common alternative ports
        alternative_ports = [3001, 3002, 3003, 5173, 5174, 8080, 8081, 4200, 4201]

        # Remove preferred port from alternatives if it's there
        alternative_ports = [p for p in alternative_ports if p != preferred_port]

        for port in alternative_ports:
            if self.is_port_available(port):
                logger.info(f"Found available alternative port: {port}")
                return port

        logger.error("No available ports found")
        return None

    def _clear_build_cache(self) -> None:
        """
        Clear Next.js/Vite build cache to avoid stuck compilation issues.

        This removes .next, .vite, dist, and .cache directories.
        """
        cache_dirs = ['.next', '.vite', 'dist', '.cache', 'out']

        for cache_dir in cache_dirs:
            cache_path = self.repo_path / cache_dir
            if cache_path.exists():
                try:
                    import shutil
                    shutil.rmtree(cache_path)
                    logger.info(f"Cleared build cache: {cache_dir}/")
                except Exception as e:
                    logger.warning(f"Failed to clear {cache_dir}/: {e}")

    def start_dev_server(self, timeout: int = 180, preferred_port: Optional[int] = None, clear_cache: bool = False) -> bool:
        """
        Start the development server and wait for it to be ready.

        Args:
            timeout: Maximum seconds to wait for server to start (default: 180s)
            preferred_port: Preferred port to use (if None, auto-detect)
            clear_cache: Whether to clear build cache before starting (helps with stuck compilations)

        Returns:
            True if server started successfully, False otherwise
        """
        command = self.detect_dev_server_command()
        if not command:
            logger.warning("No dev server command detected, skipping server start")
            return False

        # Clear cache if requested (helps with stuck compilation issues)
        if clear_cache:
            logger.info("Clearing build cache before starting dev server...")
            self._clear_build_cache()

        # Determine preferred port
        if preferred_port is None:
            preferred_port = self.detect_dev_server_port(command)

        # Find an available port
        available_port = self.find_available_port(preferred_port)
        if available_port is None:
            logger.error("No available ports found - cannot start dev server")
            return False

        self.dev_server_port = available_port
        logger.info(f"Using port {self.dev_server_port} for dev server")

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
            # Set PORT environment variable so dev server uses our selected port
            env = os.environ.copy()
            env['PORT'] = str(self.dev_server_port)

            # Start the dev server in the background
            self.dev_server_process = subprocess.Popen(
                command.split(),
                cwd=self.repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout for easier reading
                env=env,  # Pass environment with PORT set
                bufsize=1,  # Line buffered
                universal_newlines=True,  # Text mode
                preexec_fn=None if os.name == 'nt' else lambda: signal.signal(signal.SIGINT, signal.SIG_IGN)
            )

            # Capture server output in background
            server_output_lines = []

            def read_output():
                """Read server output in a non-blocking way."""
                if self.dev_server_process and self.dev_server_process.stdout:
                    try:
                        # On Unix/macOS, use select for non-blocking read
                        if os.name != 'nt':
                            import select
                            ready, _, _ = select.select([self.dev_server_process.stdout], [], [], 0.1)
                            if ready:
                                line = self.dev_server_process.stdout.readline()
                                if line:
                                    server_output_lines.append(line.strip())
                                    logger.debug(f"Dev server: {line.strip()}")
                                    return line
                        else:
                            # On Windows, just try to read (process is in text mode with buffering)
                            # This is less ideal but works
                            import threading
                            line_holder = [None]

                            def read_line():
                                try:
                                    line_holder[0] = self.dev_server_process.stdout.readline()
                                except Exception:
                                    pass

                            thread = threading.Thread(target=read_line)
                            thread.daemon = True
                            thread.start()
                            thread.join(timeout=0.1)

                            if line_holder[0]:
                                server_output_lines.append(line_holder[0].strip())
                                logger.debug(f"Dev server: {line_holder[0].strip()}")
                                return line_holder[0]
                    except Exception as e:
                        logger.debug(f"Error reading output: {e}")
                return None

            # Wait for server to be ready
            start_time = time.time()
            last_check = start_time
            server_ready_seen = False
            compilation_in_progress = False
            last_compilation_check = start_time
            compilation_errors = []
            consecutive_timeouts = 0  # Track repeated HTTP timeouts
            last_output_time = start_time  # Track when we last saw ANY server output

            while time.time() - start_time < timeout:
                # Read any new output
                line = read_output()

                # Track when we last saw output (for silent hang detection)
                if line:
                    last_output_time = time.time()

                # Check server output for readiness indicators and errors
                if line:
                    line_lower = line.lower()

                    # Check for compilation errors (fail fast)
                    # Next.js uses ⨯ symbol for errors, webpack uses "ERROR", others use "error:"
                    if any(err in line_lower for err in ['error:', 'failed to compile', 'module not found', 'cannot find module', 'syntaxerror', 'typeerror']) or '⨯' in line:
                        compilation_errors.append(line.strip())
                        logger.error(f"❌ Compilation error detected: {line.strip()}")

                        # Keep reading more lines after error to capture full error message
                        # (Next.js often prints error across multiple lines)
                        for _ in range(5):  # Read next 5 lines to capture full error
                            next_line = read_output()
                            if next_line:
                                compilation_errors.append(next_line.strip())
                                logger.error(f"  {next_line.strip()}")

                        # If we have error lines, fail immediately (don't wait for 3 errors)
                        if len(compilation_errors) >= 1:
                            logger.error(f"❌ Compilation error detected - failing fast")
                            logger.error(f"Full error context (last 50 lines of output):")
                            for err_line in server_output_lines[-50:]:
                                logger.error(f"  {err_line}")
                            return False

                    # Check for server ready messages
                    if any(msg in line_lower for msg in ['ready in', 'compiled successfully', 'compiled client', 'compiled server']):
                        server_ready_seen = True
                        compilation_in_progress = False
                        compilation_errors = []  # Clear errors on successful compilation
                        logger.info(f"📊 Dev server reports ready: {line.strip()}")
                    # Check for compilation start
                    elif 'compiling' in line_lower and not 'compiled' in line_lower:
                        compilation_in_progress = True
                        last_compilation_check = time.time()
                        logger.info(f"📊 Compilation in progress: {line.strip()}")
                    # Check for compilation completion
                    elif 'compiled' in line_lower:
                        compilation_in_progress = False
                        compilation_errors = []  # Clear errors on successful compilation
                        logger.info(f"📊 Compilation completed: {line.strip()}")

                # If we see compilation in progress, give it time (up to 60s from last compilation message)
                if compilation_in_progress:
                    time_since_compilation = time.time() - last_compilation_check
                    if time_since_compilation < 60:
                        # Still compiling, wait a bit longer before checking HTTP
                        time.sleep(2)
                        continue
                    else:
                        # Compilation stuck - likely has errors that aren't being logged clearly
                        logger.error(f"❌ Compilation stuck for >{int(time_since_compilation)}s without completing")
                        logger.error(f"This usually indicates compilation errors in the code")

                        # Show ALL recent output to help diagnose the issue
                        logger.error(f"Full server output (last 50 lines):")
                        for line in server_output_lines[-50:]:
                            logger.error(f"  {line}")

                        if compilation_errors:
                            logger.error(f"Errors detected during compilation:")
                            for err_line in compilation_errors[:10]:
                                logger.error(f"  {err_line}")
                        else:
                            logger.error(f"No explicit errors detected - compilation may be hanging or very slow")

                        return False

                # Try HTTP request with adaptive timeout
                # Use longer timeout if we saw "Ready" message (server might be compiling pages on-demand)
                http_timeout = 30 if server_ready_seen else 10
                try:
                    import requests
                    response = requests.get(f"http://localhost:{self.dev_server_port}", timeout=http_timeout)
                    if response.status_code < 500:  # Server is responding
                        logger.info(f"✅ Dev server ready on port {self.dev_server_port}")
                        return True
                    consecutive_timeouts = 0  # Reset on successful connection
                except requests.exceptions.Timeout:
                    # Timeout - page might be compiling on-demand or hanging
                    consecutive_timeouts += 1
                    elapsed = int(time.time() - start_time)
                    logger.warning(f"⚠️ HTTP request timed out after {http_timeout}s ({elapsed}s total elapsed, {consecutive_timeouts} consecutive timeouts)")
                    logger.warning(f"   This could mean: (1) page compiling on-demand, (2) page has infinite loop/hang, (3) network issue")

                    # If we've had 4 consecutive timeouts (120s total), give up
                    if consecutive_timeouts >= 4:
                        logger.error(f"❌ Too many consecutive HTTP timeouts ({consecutive_timeouts})")
                        logger.error(f"Server says it's ready but HTTP requests are timing out - likely a code bug")
                        logger.error(f"Recent server output:")
                        for line in server_output_lines[-30:]:
                            logger.error(f"  {line}")
                        return False
                except requests.exceptions.ConnectionError as e:
                    # Connection refused - server not listening yet
                    consecutive_timeouts = 0  # Reset on connection errors (different issue)
                    logger.debug(f"Connection refused (server not listening yet)")
                except Exception as e:
                    consecutive_timeouts = 0  # Reset on other errors
                    logger.warning(f"HTTP check failed: {type(e).__name__}: {e}")
                    pass

                # Check for silent hang (server says "ready" but produces no output while HTTP times out)
                if server_ready_seen:
                    time_since_output = time.time() - last_output_time
                    if time_since_output > 40 and consecutive_timeouts > 0:
                        logger.error(f"❌ Silent hang detected: server has been silent for {int(time_since_output)}s while HTTP requests timeout")
                        logger.error(f"Server said 'Ready' but then produced no output while HTTP requests failed")
                        logger.error(f"This usually indicates:")
                        logger.error(f"  1. Next.js stuck compiling page with no error output")
                        logger.error(f"  2. Code bug causing page to hang silently")
                        logger.error(f"  3. Build cache corruption preventing compilation")
                        logger.error(f"Recent server output:")
                        for line in server_output_lines[-30:]:
                            logger.error(f"  {line}")
                        return False

                # Check if process died
                returncode = self.dev_server_process.poll()
                if returncode is not None:
                    # Process exited - read any remaining output
                    while read_output():
                        pass

                    logger.error(f"❌ Dev server process died with exit code {returncode}")
                    if server_output_lines:
                        logger.error(f"Server output (last 20 lines):")
                        for line in server_output_lines[-20:]:
                            logger.error(f"  {line}")
                    else:
                        logger.error("No server output captured")

                    return False

                # Log progress every 10 seconds
                current_time = time.time()
                if current_time - last_check >= 10:
                    elapsed = int(current_time - start_time)
                    # Provide clearer status based on actual state
                    if compilation_in_progress:
                        status = "server compiling code"
                    elif server_ready_seen:
                        status = "server ready, but HTTP requests timing out (page may be compiling on-demand or hanging)"
                    else:
                        status = "waiting for server process to start"

                    logger.info(f"Dev server status: {status} ({elapsed}s elapsed)")
                    last_check = current_time

                time.sleep(2)

            # Timeout reached - dev server process is running but not responding
            # Read any remaining output
            while read_output():
                pass

            logger.warning(f"❌ Dev server did not become ready within {timeout}s")
            logger.error("Dev server process is running but not responding to HTTP requests on expected port")

            # Try to detect actual port from output
            detected_port = self._detect_port_from_output(server_output_lines)
            if detected_port and detected_port != self.dev_server_port:
                logger.error(f"⚠️ Server may have started on port {detected_port} instead of {self.dev_server_port}")
                logger.error(f"This dev server may not respect the PORT environment variable")
                # Try the detected port (give it a few attempts in case it's still compiling)
                for attempt in range(3):
                    try:
                        import requests
                        response = requests.get(f"http://localhost:{detected_port}", timeout=15)
                        if response.status_code < 500:
                            logger.info(f"✅ Server IS running on port {detected_port}! Using this port instead.")
                            self.dev_server_port = detected_port
                            return True
                    except requests.exceptions.Timeout:
                        if attempt < 2:
                            logger.info(f"Port {detected_port} timed out, retrying (attempt {attempt + 2}/3)...")
                            time.sleep(5)
                    except Exception:
                        break

            logger.error(f"Server output (last 30 lines):")
            for line in server_output_lines[-30:]:
                logger.error(f"  {line}")

            logger.error(f"Possible causes:")
            logger.error(f"  1. Dev server encountered errors during startup (check output above)")
            logger.error(f"  2. Dev server is waiting for user input")
            logger.error(f"  3. Code changes introduced errors that prevent server from starting")
            logger.error(f"  4. Dev server ignoring PORT environment variable (tried port {self.dev_server_port})")

            # Kill the non-responsive process
            if self.dev_server_process and self.dev_server_process.poll() is None:
                logger.warning("Killing non-responsive dev server process...")
                try:
                    self.dev_server_process.kill()
                    self.dev_server_process.wait(timeout=5)
                except Exception as e:
                    logger.error(f"Error killing dev server: {e}")

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

        Some dev servers don't respond to HEAD requests, so we try GET if HEAD fails.

        Args:
            url: URL to validate

        Returns:
            True if URL is valid and accessible, False otherwise
        """
        try:
            import requests

            # Try HEAD first (faster)
            try:
                response = requests.head(url, timeout=5, allow_redirects=True)
                # Accept 200-399 status codes (success and redirects)
                if 200 <= response.status_code < 400:
                    logger.info(f"✅ URL validated: {url} (HTTP {response.status_code})")
                    return True
                elif response.status_code == 405:
                    # Method Not Allowed - try GET instead
                    logger.info(f"HEAD not allowed on {url}, trying GET...")
                else:
                    logger.info(f"❌ URL validation failed for {url}: HTTP {response.status_code}")
                    return False
            except Exception:
                # HEAD failed, try GET
                logger.info(f"HEAD request failed for {url}, trying GET...")

            # Try GET if HEAD failed or returned 405
            response = requests.get(url, timeout=5, allow_redirects=True)
            is_valid = 200 <= response.status_code < 400
            if is_valid:
                logger.info(f"✅ URL validated: {url} (HTTP {response.status_code})")
            else:
                logger.info(f"❌ URL validation failed for {url}: HTTP {response.status_code}")
            return is_valid

        except Exception as e:
            logger.warning(f"❌ URL validation failed for {url}: {e}")
            return False

    def _warm_up_pages(self, urls: list[str]) -> None:
        """
        Pre-fetch URLs to trigger Next.js compilation before screenshotting.

        Next.js compiles pages on-demand, so we need to request them first
        to ensure changes are visible in screenshots.

        Args:
            urls: List of URLs to warm up
        """
        import requests

        logger.info(f"Warming up {len(urls)} pages to trigger compilation...")

        for url in urls:
            full_url = url
            if url.startswith("/"):
                full_url = f"http://localhost:{self.dev_server_port}{url}"

            try:
                # Make request to trigger compilation (don't care about response)
                requests.get(full_url, timeout=15)
                logger.info(f"  ✅ Warmed up: {url}")
            except Exception as e:
                logger.warning(f"  ⚠️  Failed to warm up {url}: {e}")

        # Give server a moment to finish any async compilation
        logger.info("Waiting 5s for compilation to complete...")
        time.sleep(5)

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
        # Warm up pages first to trigger Next.js compilation
        self._warm_up_pages(urls)

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
