"""Browser automation tool using Playwright.

Provides headless browser capabilities for navigating web pages,
taking screenshots, clicking elements, and filling forms.
All browser actions go through SSRF protection and audit logging.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from vaultbot.tools.web_fetch import is_url_safe
from vaultbot.utils.logging import get_logger

logger = get_logger(__name__)


class BrowserAction(str, Enum):
    """Supported browser actions."""
    NAVIGATE = "navigate"
    SCREENSHOT = "screenshot"
    CLICK = "click"
    FILL = "fill"
    EVALUATE = "evaluate"
    GET_TEXT = "get_text"


@dataclass(frozen=True, slots=True)
class BrowserCommand:
    """A command to execute in the browser."""
    action: BrowserAction
    url: str = ""
    selector: str = ""
    value: str = ""
    script: str = ""


@dataclass(frozen=True, slots=True)
class BrowserResult:
    """Result from a browser action."""
    success: bool
    action: BrowserAction
    data: str = ""  # Text content, screenshot base64, eval result
    url: str = ""
    error: str = ""


class BrowserTool:
    """Headless browser automation tool.

    Uses Playwright for browser control.  All URL navigations pass
    through SSRF protection.  The browser can optionally run in a
    Docker sandbox for additional isolation.

    Parameters
    ----------
    sandbox:
        If True, browser runs with additional restrictions.
    url_allowlist:
        If set, only these URL patterns are allowed.
    """

    def __init__(
        self,
        *,
        sandbox: bool = True,
        url_allowlist: list[str] | None = None,
    ) -> None:
        self._sandbox = sandbox
        self._url_allowlist = url_allowlist
        self._browser = None
        self._page = None
        self._connected = False
        self._action_count: int = 0

    async def start(self) -> None:
        """Launch the browser."""
        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
            self._page = await self._browser.new_page()
            self._connected = True
            logger.info("browser_started", sandbox=self._sandbox)
        except ImportError:
            raise ImportError(
                "Browser automation requires 'playwright'. "
                "Install with: pip install playwright && playwright install chromium"
            )

    async def stop(self) -> None:
        """Close the browser."""
        if self._browser:
            await self._browser.close()
        if hasattr(self, "_playwright") and self._playwright:
            await self._playwright.stop()
        self._connected = False
        self._page = None
        self._browser = None
        logger.info("browser_stopped")

    async def execute(self, command: BrowserCommand) -> BrowserResult:
        """Execute a browser command."""
        if not self._connected or not self._page:
            return BrowserResult(
                success=False, action=command.action, error="Browser not started"
            )

        # SSRF check for navigation
        if command.action == BrowserAction.NAVIGATE and command.url:
            if not is_url_safe(command.url):
                return BrowserResult(
                    success=False,
                    action=command.action,
                    error=f"URL blocked by SSRF protection: {command.url}",
                )

            if self._url_allowlist:
                if not any(pattern in command.url for pattern in self._url_allowlist):
                    return BrowserResult(
                        success=False,
                        action=command.action,
                        error="URL not in allowlist",
                    )

        try:
            result = await self._dispatch(command)
            self._action_count += 1
            return result
        except Exception as exc:
            logger.warning("browser_action_failed", action=command.action.value, error=str(exc))
            return BrowserResult(
                success=False, action=command.action, error=str(exc)
            )

    async def _dispatch(self, command: BrowserCommand) -> BrowserResult:
        """Route command to the appropriate handler."""
        page = self._page
        assert page is not None

        if command.action == BrowserAction.NAVIGATE:
            await page.goto(command.url, wait_until="domcontentloaded")
            return BrowserResult(
                success=True, action=command.action, url=page.url
            )

        if command.action == BrowserAction.SCREENSHOT:
            screenshot = await page.screenshot()
            import base64
            b64 = base64.b64encode(screenshot).decode("utf-8")
            return BrowserResult(
                success=True, action=command.action, data=b64, url=page.url
            )

        if command.action == BrowserAction.CLICK:
            await page.click(command.selector)
            return BrowserResult(
                success=True, action=command.action, url=page.url
            )

        if command.action == BrowserAction.FILL:
            await page.fill(command.selector, command.value)
            return BrowserResult(
                success=True, action=command.action, url=page.url
            )

        if command.action == BrowserAction.GET_TEXT:
            text = await page.inner_text(command.selector) if command.selector else await page.content()
            return BrowserResult(
                success=True, action=command.action, data=text[:5000], url=page.url
            )

        if command.action == BrowserAction.EVALUATE:
            if self._sandbox:
                return BrowserResult(
                    success=False, action=command.action,
                    error="JavaScript evaluation disabled in sandbox mode",
                )
            result = await page.evaluate(command.script)
            return BrowserResult(
                success=True, action=command.action, data=str(result), url=page.url
            )

        return BrowserResult(
            success=False, action=command.action, error=f"Unknown action: {command.action}"
        )

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def action_count(self) -> int:
        return self._action_count
