"""
使用 Playwright 录制 demo1/demo2/demo3 的动画视频
输出到 workspaces/AutoMovie/recordings/ 文件夹
"""
import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

# 项目根目录
BASE_DIR = Path(__file__).parent.resolve()
RECORDINGS_DIR = BASE_DIR / "recordings"

# 三个 demo 的配置
DEMOS = [
    {
        "name": "demo1",
        "url": (BASE_DIR / "demo.html").as_uri(),
        "wait_seconds": 10,  # 动画 ~6.5s + 缓冲
    },
    {
        "name": "demo2",
        "url": (BASE_DIR / "demo2" / "index.html").as_uri(),
        "wait_seconds": 14,  # 动画 ~10.3s + 缓冲
    },
    {
        "name": "demo3",
        "url": (BASE_DIR / "demo3" / "index.html").as_uri(),
        "wait_seconds": 16,  # 动画 ~12.3s + 缓冲
    },
]


async def record_demo(playwright, demo_config):
    """录制单个 demo"""
    name = demo_config["name"]
    url = demo_config["url"]
    wait_seconds = demo_config["wait_seconds"]

    print(f"\n{'='*50}")
    print(f"🎬 开始录制: {name}")
    print(f"   URL: {url}")
    print(f"   等待时长: {wait_seconds}s")

    # 创建输出目录
    video_dir = RECORDINGS_DIR / name
    video_dir.mkdir(parents=True, exist_ok=True)

    # 启动浏览器，开启视频录制
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        record_video_dir=str(video_dir),
        record_video_size={"width": 1280, "height": 720},
    )

    page = await context.new_page()

    # 导航到 demo 页面
    await page.goto(url)
    print(f"   ✅ 页面已加载")

    # 等待动画播放完成
    await asyncio.sleep(wait_seconds)
    print(f"   ✅ 动画播放完成")

    # 关闭上下文以保存视频
    await context.close()
    await browser.close()

    # 找到生成的视频文件并重命名
    video_files = list(video_dir.glob("*.webm"))
    if video_files:
        final_path = RECORDINGS_DIR / f"{name}.webm"
        video_files[0].rename(final_path)
        # 清理临时目录
        video_dir.rmdir()
        print(f"   ✅ 视频已保存: {final_path}")
        return final_path
    else:
        print(f"   ❌ 未找到视频文件")
        return None


async def main():
    print("🎭 AutoMovie Demo 录屏工具")
    print(f"   输出目录: {RECORDINGS_DIR}")

    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        results = []
        for demo in DEMOS:
            result = await record_demo(playwright, demo)
            results.append((demo["name"], result))

    print(f"\n{'='*50}")
    print("📁 录制结果:")
    for name, path in results:
        status = f"✅ {path}" if path else "❌ 失败"
        print(f"   {name}: {status}")
    print("🎬 全部完成!")


if __name__ == "__main__":
    asyncio.run(main())
