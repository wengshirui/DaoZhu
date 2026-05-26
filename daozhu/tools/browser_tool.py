"""
岛主工具 — 浏览器搜索（Playwright MCP 兜底）
当 web_search 失败时，通过 Playwright 打开浏览器搜索
"""

import json
import subprocess
import sys
from pathlib import Path

from .registry import registry


async def browser_search_tool(query: str) -> str:
    """通过浏览器搜索（使用百度，国内无障碍）"""
    try:
        # 用 Playwright 的 Python API 直接搜索
        # 不依赖 MCP server，直接用 playwright 库
        result = await _playwright_search(query)
        return json.dumps(result, ensure_ascii=False)
    except ImportError:
        return json.dumps({
            "error": "Playwright 未安装。请运行: pip install playwright && playwright install chromium",
            "hint": "安装后即可使用浏览器搜索功能"
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"浏览器搜索失败: {str(e)}"}, ensure_ascii=False)


async def _playwright_search(query: str) -> dict:
    """用 Playwright 打开百度搜索"""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 用百度搜索（国内无障碍）
        await page.goto(f"https://www.baidu.com/s?wd={query}", timeout=15000)
        await page.wait_for_selector(".result", timeout=10000)

        # 提取搜索结果
        results = await page.evaluate("""() => {
            const items = document.querySelectorAll('.result');
            return Array.from(items).slice(0, 5).map(item => {
                const link = item.querySelector('a');
                const abstract = item.querySelector('.c-abstract') || item.querySelector('.content-right_8Zs40');
                return {
                    title: link ? link.textContent.trim() : '',
                    url: link ? link.href : '',
                    snippet: abstract ? abstract.textContent.trim().slice(0, 200) : ''
                };
            }).filter(r => r.title);
        }""")

        await browser.close()
        return {"query": query, "results": results, "source": "baidu"}


# === 注册工具 ===

registry.register(
    name="browser_search",
    description="通过浏览器搜索（使用百度，国内无障碍）。当 web_search 失败时使用此工具作为兜底。需要安装 Playwright。",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
        },
        "required": ["query"],
    },
    handler=browser_search_tool,
    category="web",
    emoji="🌐",
)
