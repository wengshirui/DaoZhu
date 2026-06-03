"""
岛主工具 — 网络搜索
使用 ddgs 包（DuckDuckGo 搜索引擎的成熟 Python 封装）
支持多后端: auto(自动选择) / html / lite / bing
同 hermes-agent 方案，稳定可靠
"""

import json
import logging

import httpx

from .registry import registry

logger = logging.getLogger(__name__)


def _get_proxy() -> str | None:
    """检测本地代理"""
    import os
    proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    if not proxy:
        import socket
        try:
            s = socket.socket()
            s.settimeout(0.3)
            s.connect(("127.0.0.1", 7890))
            s.close()
            proxy = "http://127.0.0.1:7890"
        except (OSError, socket.timeout):
            proxy = None
    return proxy


async def web_search_tool(query: str, max_results: int = 5) -> str:
    """搜索网络（基于 ddgs 包，多后端自动降级）"""
    try:
        from ddgs import DDGS
    except ImportError:
        return json.dumps(
            {"error": "ddgs 包未安装，请运行: pip install ddgs"},
            ensure_ascii=False,
        )

    proxy = _get_proxy()
    safe_limit = max(1, min(int(max_results), 10))

    try:
        results = []
        with DDGS(proxy=proxy) as client:
            for i, hit in enumerate(client.text(query, max_results=safe_limit)):
                if i >= safe_limit:
                    break
                results.append({
                    "title": str(hit.get("title", "")),
                    "url": str(hit.get("href") or hit.get("url", "")),
                    "snippet": str(hit.get("body", ""))[:200],
                })

        if results:
            return json.dumps(
                {"query": query, "results": results, "source": "ddgs"},
                ensure_ascii=False,
            )
        return json.dumps(
            {"error": "搜索无结果，请换个关键词试试", "query": query},
            ensure_ascii=False,
        )

    except Exception as e:
        logger.warning("ddgs search error: %s", e)
        return json.dumps(
            {"error": f"搜索出错: {e}", "query": query},
            ensure_ascii=False,
        )


async def fetch_url_tool(url: str, method: str = "GET") -> str:
    """访问指定 URL 获取内容（支持公开 API 如 wttr.in）"""
    try:
        proxy = _get_proxy()
        headers = {
            "User-Agent": "curl/7.88.0",
            "Accept": "text/plain, application/json",
        }

        async with httpx.AsyncClient(
            timeout=10, follow_redirects=True, proxy=proxy
        ) as client:
            if method.upper() == "GET":
                resp = await client.get(url, headers=headers)
            else:
                resp = await client.post(url, headers=headers)

            if resp.status_code != 200:
                return json.dumps(
                    {"error": f"HTTP {resp.status_code}", "url": url},
                    ensure_ascii=False,
                )

            content = resp.text[:3000]
            return json.dumps(
                {"url": url, "status": resp.status_code, "content": content},
                ensure_ascii=False,
            )

    except Exception as e:
        return json.dumps({"error": str(e), "url": url}, ensure_ascii=False)


# === 注册工具 ===

registry.register(
    name="web_search",
    description="搜索互联网获取信息（基于 ddgs，自动选择最佳后端）。",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "max_results": {
                "type": "integer",
                "description": "最大结果数，默认5",
                "default": 5,
            },
        },
        "required": ["query"],
    },
    handler=web_search_tool,
    category="web",
    emoji="🔍",
)

registry.register(
    name="fetch_url",
    description="访问指定 URL 获取内容。可用于调用公开 API（如天气、GitHub 等）。",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "要访问的 URL"},
            "method": {
                "type": "string",
                "description": "HTTP 方法，默认 GET",
                "default": "GET",
            },
        },
        "required": ["url"],
    },
    handler=fetch_url_tool,
    category="web",
    emoji="🌐",
)
