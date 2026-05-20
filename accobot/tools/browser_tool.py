"""Browser automation tools — Playwright-based web interaction.

Toolset: "browser"
Automates repetitive tasks on B/S financial systems (tax filing, banking, etc.)
Security: NEVER stores credentials. User logs in manually, bot operates after.

Inspired by Hermes Agent's browser tools, simplified for accounting workflows.
"""

import json
import logging
from accobot.tools.registry import registry, tool_result, tool_error

logger = logging.getLogger(__name__)

# Lazy-loaded playwright instance
_browser = None
_page = None


def _check_playwright() -> bool:
    """Check if playwright is available."""
    try:
        import playwright
        return True
    except ImportError:
        return False


def _get_page():
    """Get or create a browser page (lazy init)."""
    global _browser, _page
    if _page and not _page.is_closed():
        return _page

    try:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        _browser = pw.chromium.launch(headless=False)  # Visible so user can log in
        _page = _browser.new_page()
        return _page
    except Exception as e:
        logger.error("Failed to launch browser: %s", e)
        return None


def browser_open(args: dict, **kwargs) -> str:
    """Open a URL in the browser for user to log in."""
    url = args.get("url", "").strip()
    if not url:
        return tool_error("请提供要打开的网址")

    page = _get_page()
    if not page:
        return tool_error("无法启动浏览器。请确认已安装 playwright：pip install playwright && playwright install chromium")

    try:
        page.goto(url, timeout=30000)
        title = page.title()
        return tool_result(
            success=True,
            title=title,
            url=page.url,
            message=f"已打开：{title}\n请在浏览器中完成登录，登录后告诉我继续操作。",
        )
    except Exception as e:
        return tool_error(f"打开网页失败：{e}")


def browser_snapshot(args: dict, **kwargs) -> str:
    """Get current page info (title, url, visible text summary)."""
    global _page
    if not _page or _page.is_closed():
        return tool_error("浏览器未打开，请先使用 browser_open 打开网页")

    try:
        title = _page.title()
        url = _page.url

        # Get visible text (simplified)
        text = _page.inner_text("body")
        # Truncate to reasonable length
        if len(text) > 2000:
            text = text[:2000] + "...(截断)"

        return tool_result(
            success=True,
            title=title,
            url=url,
            text_preview=text[:500],
            message=f"当前页面：{title}\nURL：{url}\n内容预览：{text[:300]}...",
        )
    except Exception as e:
        return tool_error(f"获取页面信息失败：{e}")


def browser_click(args: dict, **kwargs) -> str:
    """Click an element on the page."""
    global _page
    if not _page or _page.is_closed():
        return tool_error("浏览器未打开")

    selector = args.get("selector", "")
    text = args.get("text", "")

    try:
        if text:
            # Click by visible text
            _page.get_by_text(text, exact=False).first.click(timeout=10000)
        elif selector:
            _page.click(selector, timeout=10000)
        else:
            return tool_error("请指定要点击的元素（selector 或 text）")

        _page.wait_for_load_state("networkidle", timeout=10000)
        return tool_result(success=True, message=f"已点击：{text or selector}")
    except Exception as e:
        return tool_error(f"点击失败：{e}")


def browser_fill(args: dict, **kwargs) -> str:
    """Fill a form field on the page."""
    global _page
    if not _page or _page.is_closed():
        return tool_error("浏览器未打开")

    selector = args.get("selector", "")
    label = args.get("label", "")
    value = args.get("value", "")

    if not value:
        return tool_error("请指定要填入的值")

    try:
        if label:
            _page.get_by_label(label).fill(value)
        elif selector:
            _page.fill(selector, value)
        else:
            return tool_error("请指定表单字段（selector 或 label）")

        return tool_result(success=True, message=f"已填入：{label or selector} = {value}")
    except Exception as e:
        return tool_error(f"填写失败：{e}")


def browser_screenshot(args: dict, **kwargs) -> str:
    """Take a screenshot of the current page."""
    global _page
    if not _page or _page.is_closed():
        return tool_error("浏览器未打开")

    try:
        import time
        from accobot.config import get_data_dir
        screenshot_dir = get_data_dir() / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        filename = f"screenshot_{int(time.time())}.png"
        path = screenshot_dir / filename
        _page.screenshot(path=str(path))
        return tool_result(success=True, path=str(path), message=f"截图已保存：{path}")
    except Exception as e:
        return tool_error(f"截图失败：{e}")


def browser_close(args: dict, **kwargs) -> str:
    """Close the browser."""
    global _browser, _page
    try:
        if _page and not _page.is_closed():
            _page.close()
        if _browser:
            _browser.close()
        _page = None
        _browser = None
        return tool_result(success=True, message="浏览器已关闭")
    except Exception as e:
        return tool_result(success=True, message=f"浏览器已关闭（{e}）")


# =========================================================================
# Registration
# =========================================================================

registry.register(
    name="browser_open",
    toolset="browser",
    schema={
        "name": "browser_open",
        "description": "打开网页（用于税务系统、网银等）。打开后用户需要自行登录，登录完成后告诉AI继续操作。",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "要打开的网址"},
            },
            "required": ["url"],
        },
    },
    handler=browser_open,
    check_fn=_check_playwright,
    emoji="🌐",
)

registry.register(
    name="browser_snapshot",
    toolset="browser",
    schema={
        "name": "browser_snapshot",
        "description": "获取当前网页的信息（标题、内容预览）。用于了解页面状态。",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=browser_snapshot,
    check_fn=_check_playwright,
    emoji="📸",
)

registry.register(
    name="browser_click",
    toolset="browser",
    schema={
        "name": "browser_click",
        "description": "点击网页上的按钮或链接。",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS选择器"},
                "text": {"type": "string", "description": "按钮/链接的文字内容（优先用这个）"},
            },
        },
    },
    handler=browser_click,
    check_fn=_check_playwright,
    emoji="👆",
)

registry.register(
    name="browser_fill",
    toolset="browser",
    schema={
        "name": "browser_fill",
        "description": "在网页表单中填入数据。用于自动填写申报表等。",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS选择器"},
                "label": {"type": "string", "description": "表单字段的标签文字（优先用这个）"},
                "value": {"type": "string", "description": "要填入的值"},
            },
            "required": ["value"],
        },
    },
    handler=browser_fill,
    check_fn=_check_playwright,
    emoji="✍️",
)

registry.register(
    name="browser_screenshot",
    toolset="browser",
    schema={
        "name": "browser_screenshot",
        "description": "对当前网页截图保存。用于记录操作结果。",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=browser_screenshot,
    check_fn=_check_playwright,
    emoji="📷",
)

registry.register(
    name="browser_close",
    toolset="browser",
    schema={
        "name": "browser_close",
        "description": "关闭浏览器。操作完成后使用。",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=browser_close,
    check_fn=_check_playwright,
    emoji="❌",
)
