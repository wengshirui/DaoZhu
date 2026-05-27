"""录制 demo6 为 mp4 视频"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent / "recordings"
OUTPUT_DIR.mkdir(exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={"width": 960, "height": 580},
            record_video_dir=str(OUTPUT_DIR),
            record_video_size={"width": 960, "height": 580},
        )
        page = await context.new_page()
        
        print("🎬 开始录制 demo6...")
        await page.goto("http://localhost:8899/demo6/index.html")
        
        # 等待动画播放完毕（92秒 + 3秒缓冲）
        print("⏳ 等待动画播放（约95秒）...")
        await page.wait_for_timeout(95000)
        
        print("✅ 录制完成，保存视频...")
        await page.close()
        await context.close()
        await browser.close()
        
        # 找到生成的 webm 文件
        webm_files = list(OUTPUT_DIR.glob("*.webm"))
        if webm_files:
            latest = max(webm_files, key=lambda f: f.stat().st_mtime)
            print(f"📁 视频文件: {latest}")
            print(f"💡 转换为 mp4: ffmpeg -i \"{latest}\" -c:v libx264 -preset fast \"{OUTPUT_DIR / 'demo6.mp4'}\"")
        else:
            print("⚠️ 未找到视频文件")

if __name__ == "__main__":
    asyncio.run(main())
