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
        # 使用 DuckDuckGo Lite（更稳定，不容易被拦截）
        url = "https://lite.duckduckgo.com/lite/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        # 检测本地代理（Clash 默认 7890）
        import os
        proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
        if not proxy:
            import socket
            try:
                s = socket.socket()
                s.settimeout(0.5)
                s.connect(("127.0.0.1", 7890))
                s.close()
                proxy = "http://127.0.0.1:7890"
            except (OSError, socket.timeout):
                proxy = None

        async with httpx.AsyncClient(timeout=10, follow_redirects=True, proxy=proxy) as client:
            resp = await client.post(url, data={"q": query}, headers=headers)

            if resp.status_code not in (200, 202):
                # 降级：尝试直接用 API
                return await _search_fallback(client, query, max_results, headers)

            html = resp.text
            results = _parse_lite_results(html, max_results)

            if not results:
                # 降级方案
                return await _search_fallback(client, query, max_results, headers)

            return json.dumps({"query": query, "results": results}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": f"搜索出错: {str(e)}"}, ensure_ascii=False)


async def _search_fallback(client: httpx.AsyncClient, query: str, max_results: int, headers: dict) -> str:
    """降级方案：用 DuckDuckGo instant answer API"""
    try:
        resp = await client.get(
            f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1",
            headers=headers,
        )
        if resp.status_code == 200:
            data = resp.json()
            results = []
            # Abstract
            if data.get("Abstract"):
                results.append({
                    "title": data.get("Heading", query),
                    "url": data.get("AbstractURL", ""),
                    "snippet": data["Abstract"][:300],
                })
            # Related topics
            for topic in data.get("RelatedTopics", [])[:max_results]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append({
                        "title": topic.get("Text", "")[:60],
                        "url": topic.get("FirstURL", ""),
                        "snippet": topic.get("Text", "")[:200],
                    })
            if results:
                return json.dumps({"query": query, "results": results}, ensure_ascii=False)
    except Exception:
        pass

    return json.dumps({"error": "搜索服务暂时不可用，请稍后重试", "query": query}, ensure_ascii=False)


def _parse_lite_results(html: str, max_results: int) -> list[dict]:
    """从 DuckDuckGo Lite 结果中提取"""
    results = []

    # Lite 版本的结果格式不同
    # 匹配链接和摘要
    links = re.findall(r'<a rel="nofollow" href="([^"]+)" class=\'result-link\'>(.*?)</a>', html)
    snippets = re.findall(r'<td class="result-snippet">(.*?)</td>', html, re.DOTALL)

    for i, (href, title) in enumerate(links[:max_results]):
        title = re.sub(r'<[^>]+>', '', title).strip()
        snippet = ""
        if i < len(snippets):
            snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()[:200]
        if title:
            results.append({"title": title, "url": href, "snippet": snippet})

    return results


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
