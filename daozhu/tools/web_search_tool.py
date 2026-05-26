"""
岛主工具 — 网络搜索
使用 DuckDuckGo HTML 接口，无需 API Key
"""

import json
import re
from urllib.parse import quote_plus

import httpx

from .registry import registry


async def web_search_tool(query: str, max_results: int = 5) -> str:
    """搜索网络，返回结果摘要"""
    try:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return json.dumps({"error": f"搜索失败: HTTP {resp.status_code}"}, ensure_ascii=False)

            html = resp.text
            results = _parse_results(html, max_results)

            if not results:
                return json.dumps({"results": [], "message": "未找到相关结果"}, ensure_ascii=False)

            return json.dumps({"query": query, "results": results}, ensure_ascii=False)

    except httpx.ConnectError:
        return json.dumps({"error": "无法连接到搜索服务，请检查网络"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"搜索出错: {str(e)}"}, ensure_ascii=False)


def _parse_results(html: str, max_results: int) -> list[dict]:
    """从 DuckDuckGo HTML 结果中提取标题、链接、摘要"""
    results = []

    # 匹配结果块
    blocks = re.findall(
        r'<a rel="nofollow" class="result__a" href="([^"]*)"[^>]*>(.*?)</a>.*?'
        r'<a class="result__snippet"[^>]*>(.*?)</a>',
        html, re.DOTALL
    )

    for href, title, snippet in blocks[:max_results]:
        # 清理 HTML 标签
        title = re.sub(r'<[^>]+>', '', title).strip()
        snippet = re.sub(r'<[^>]+>', '', snippet).strip()
        # DuckDuckGo 的链接是重定向格式，提取真实 URL
        real_url = href
        if "uddg=" in href:
            match = re.search(r'uddg=([^&]+)', href)
            if match:
                from urllib.parse import unquote
                real_url = unquote(match.group(1))

        if title:
            results.append({
                "title": title,
                "url": real_url,
                "snippet": snippet[:200],
            })

    return results


# === 注册工具 ===

registry.register(
    name="web_search",
    description="搜索互联网获取信息。可用于搜索开源项目、查找技术文档、获取最新信息等。无需 API Key。",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词，如 'python weather API github'"},
            "max_results": {"type": "integer", "description": "最大返回结果数，默认 5", "default": 5},
        },
        "required": ["query"],
    },
    handler=web_search_tool,
    category="web",
    emoji="🔍",
)
