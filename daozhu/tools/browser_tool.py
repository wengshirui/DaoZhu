"""
岛主工具 — 浏览器操作（参考 AccoBot）
使用 Playwright 操作浏览器，支持打开网页、搜索、点击、截图
headless=False 让用户能看到操作过程
"""

import json
import logging

from .registry import registry

logger = logging.getLogger(__name__)

# 全局浏览器实例（懒加载）
_browser = None
_page = None


def _get_page():
    """获取或创建浏览器页面"""
    global _browser, _page
    if _page and not _page.is_closed():
        return _page

    try:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        _browser = pw.chromium.launch(headless=False)
        _page = _browser.new_page()
        return _page
    except Exception as e:
        logger.error("启动浏览器失败: %s", e)
        return None


async def browser_open_tool(url: str) -> str:
    """打开网页"""
    page = _get_page()
    if not page:
        return json.dumps({"error": "无法启动浏览器。请确认已安装: pip install playwright && playwright install chromium"})

    try:
        page.goto(url, timeout=15000)
        title = page.title()
        return json.dumps({
            "success": True,
            "title": title,
            "url": page.url,
            "message": f"已打开：{title}",
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"打开失败: {e}"}, ensure_ascii=False)


async def browser_search_tool(query: str) -> str:
    """通过浏览器搜索（百度，国内无障碍）"""
    page = _get_page()
    if not page:
        return json.dumps({"error": "无法启动浏览器"})

    try:
        page.goto(f"https://www.baidu.com/s?wd={query}", timeout=15000)
        page.wait_for_selector(".result", timeout=8000)

        results = page.evaluate("""() => {
            const items = document.querySelectorAll('.result');
            return Array.from(items).slice(0, 5).map(item => {
                const link = item.querySelector('a');
                const abs = item.querySelector('.c-abstract') || item.querySelector('.content-right_8Zs40');
                return {
                    title: link ? link.textContent.trim() : '',
                    url: link ? link.href : '',
                    snippet: abs ? abs.textContent.trim().slice(0, 200) : ''
                };
            }).filter(r => r.title);
        }""")

        return json.dumps({"query": query, "results": results, "source": "baidu"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"浏览器搜索失败: {e}"}, ensure_ascii=False)


async def browser_snapshot_tool() -> str:
    """获取当前页面信息"""
    global _page
    if not _page or _page.is_closed():
        return json.dumps({"error": "浏览器未打开"})

    try:
        title = _page.title()
        url = _page.url
        text = _page.inner_text("body")[:1500]
        return json.dumps({
            "title": title, "url": url,
            "content": text,
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


async def browser_close_tool() -> str:
    """关闭浏览器"""
    global _browser, _page
    try:
        if _page and not _page.is_closed():
            _page.close()
        if _browser:
            _browser.close()
        _page = None
        _browser = None
        return json.dumps({"success": True, "message": "浏览器已关闭"})
    except Exception as e:
        _page = None
        _browser = None
        return json.dumps({"success": True, "message": f"已关闭({e})"})


# === 注册工具 ===

registry.register(
    name="browser_open",
    description="打开指定网页（可见浏览器窗口）。用于访问网站、税务系统等。",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "要打开的网址"},
        },
        "required": ["url"],
    },
    handler=browser_open_tool,
    category="browser",
    emoji="🌐",
)

registry.register(
    name="browser_search",
    description="通过浏览器搜索（百度，国内无障碍）。当 web_search 失败时使用。",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
        },
        "required": ["query"],
    },
    handler=browser_search_tool,
    category="browser",
    emoji="🔍",
)

registry.register(
    name="browser_snapshot",
    description="获取当前浏览器页面的标题、URL 和内容预览。",
    parameters={"type": "object", "properties": {}, "required": []},
    handler=browser_snapshot_tool,
    category="browser",
    emoji="📸",
)

registry.register(
    name="browser_close",
    description="关闭浏览器。操作完成后使用。",
    parameters={"type": "object", "properties": {}, "required": []},
    handler=browser_close_tool,
    category="browser",
    emoji="❌",
)
