"""录制 demo4 并转为 MP4"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).parent.resolve()
RECORDINGS_DIR = BASE_DIR / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

async def main():
    url = (BASE_DIR / "demo4" / "index.html").as_uri()
    print(f"🎬 录制 demo4: {url}")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        video_dir = RECORDINGS_DIR / "demo4_tmp"
        video_dir.mkdir(parents=True, exist_ok=True)

        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(video_dir),
            record_video_size={"width": 1280, "height": 720},
        )
        page = await context.new_page()
        await page.goto(url)
        print("   ✅ 页面已加载，等待动画完成 (45s)...")
        await asyncio.sleep(45)
        print("   ✅ 动画播放完成")
        await context.close()
        await browser.close()

    # 重命名 webm
    webm_files = list(video_dir.glob("*.webm"))
    if webm_files:
        webm_path = RECORDINGS_DIR / "demo4.webm"
        webm_files[0].rename(webm_path)
        video_dir.rmdir()
        print(f"   ✅ WebM 已保存: {webm_path}")

        # 转 MP4
        import subprocess
        mp4_path = RECORDINGS_DIR / "demo4.mp4"
        cmd = [
            "ffmpeg", "-y", "-i", str(webm_path),
            "-c:v", "libx264", "-preset", "fast",
            "-crf", "23", "-pix_fmt", "yuv420p",
            str(mp4_path)
        ]
        subprocess.run(cmd, capture_output=True)
        if mp4_path.exists():
            print(f"   ✅ MP4 已保存: {mp4_path} ({mp4_path.stat().st_size//1024} KB)")
        else:
            print("   ❌ MP4 转换失败")
    else:
        print("   ❌ 未找到视频文件")

if __name__ == "__main__":
    asyncio.run(main())
