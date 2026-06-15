"""
火柴人剧场 — Pexels 视频素材服务（#083 中级模式）
按场景关键词搜索免费高清视频片段作为动态背景。

参考: MoneyPrinterTurbo app/services/material.py
特点: URL hash 缓存 + API Key 轮换 + 分辨率筛选

失败时降级到 SVG 背景（AC9），不阻塞。
"""

import hashlib
import logging
import threading
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "output" / "videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PEXELS_API_URL = "https://api.pexels.com/videos/search"

# Key 轮换（线程安全，参考 MoneyPrinterTurbo AC7）
_key_counter = 0
_key_lock = threading.Lock()


def _get_api_key(keys: list[str]) -> str:
    """线程安全的 Key 轮换。"""
    global _key_counter
    if not keys:
        return ""
    with _key_lock:
        _key_counter += 1
        return keys[_key_counter % len(keys)]


async def search_and_download(
    keyword: str,
    scene_index: int,
    api_keys: list[str],
    orientation: str = "landscape",
    min_duration: int = 5,
    target_width: int = 1920,
    target_height: int = 1080,
) -> Optional[str]:
    """
    搜索并下载 Pexels 视频片段。

    Args:
        keyword: 搜索关键词（英文，由导演 LLM 生成）
        scene_index: 场景序号
        api_keys: Pexels API Key 列表
        orientation: landscape / portrait / square
        min_duration: 最短时长（秒）
        target_width/height: 目标分辨率

    Returns:
        本地视频文件路径，失败返回 None
    """
    if not api_keys:
        logger.warning("[Pexels] 无 API Key 配置")
        return None

    api_key = _get_api_key(api_keys)

    try:
        # 搜索视频
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                PEXELS_API_URL,
                params={
                    "query": keyword,
                    "per_page": 10,
                    "orientation": orientation,
                },
                headers={
                    "Authorization": api_key,
                    "User-Agent": "DaoZhu-AutoMovie/1.0",
                },
            )

            if resp.status_code != 200:
                logger.warning(f"[Pexels] 搜索失败 HTTP {resp.status_code}")
                return None

            data = resp.json()
            videos = data.get("videos", [])
            if not videos:
                logger.info(f"[Pexels] 关键词 '{keyword}' 无结果")
                return None

            # 筛选合适的视频文件
            video_url = _find_best_video(
                videos, min_duration, target_width, target_height
            )
            if not video_url:
                logger.info(f"[Pexels] 无匹配分辨率的视频: {keyword}")
                return None

            # 下载（URL hash 缓存，AC8）
            return await _download_video(client, video_url, scene_index)

    except httpx.TimeoutException:
        logger.warning(f"[Pexels] 场景 {scene_index} 搜索超时")
        return None
    except Exception as e:
        logger.warning(f"[Pexels] 场景 {scene_index} 失败: {e}")
        return None


def _find_best_video(
    videos: list[dict],
    min_duration: int,
    target_width: int,
    target_height: int,
) -> Optional[str]:
    """从搜索结果中找到最匹配分辨率的视频 URL。"""
    for v in videos:
        duration = v.get("duration", 0)
        if duration < min_duration:
            continue

        video_files = v.get("video_files", [])
        for vf in video_files:
            w = int(vf.get("width", 0))
            h = int(vf.get("height", 0))
            # 精确匹配或接近目标分辨率
            if w >= target_width * 0.8 and h >= target_height * 0.8:
                return vf.get("link")

    # 退而求其次：取第一个可用视频的最大分辨率
    for v in videos:
        if v.get("duration", 0) >= min_duration:
            files = v.get("video_files", [])
            if files:
                # 按宽度降序取最大的
                best = max(files, key=lambda f: int(f.get("width", 0)))
                return best.get("link")

    return None


async def _download_video(
    client: httpx.AsyncClient,
    url: str,
    scene_index: int,
) -> Optional[str]:
    """下载视频到本地（URL hash 缓存）。"""
    # 下载（URL hash 缓存，AC8）
    url_clean = url.split("?")[0]
    url_hash = hashlib.md5(url_clean.encode()).hexdigest()[:12]
    # 缓存按 hash 命名（不含 scene_index），确保同一视频只下载一次
    filename = f"pexels_{url_hash}.mp4"
    filepath = OUTPUT_DIR / filename

    # 已缓存则跳过
    if filepath.exists() and filepath.stat().st_size > 10000:
        logger.info(f"[Pexels] 缓存命中: {filename}")
        return str(filepath)

    # 下载
    try:
        resp = await client.get(url, timeout=60, follow_redirects=True)
        if resp.status_code == 200 and len(resp.content) > 10000:
            filepath.write_bytes(resp.content)
            logger.info(
                f"[Pexels] 下载完成: {filename} "
                f"({len(resp.content) // 1024}KB)"
            )
            return str(filepath)
        else:
            logger.warning(f"[Pexels] 下载异常: HTTP {resp.status_code}")
            return None
    except Exception as e:
        logger.warning(f"[Pexels] 下载失败: {e}")
        return None
