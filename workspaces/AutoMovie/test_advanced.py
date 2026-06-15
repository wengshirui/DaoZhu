"""快速测试高级模式（GLM-Image + GLM-TTS）"""
import sys, asyncio, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

from pipeline import run_pipeline

TEXT = "黑客攻破了Claude 5的安全防线。三天后系统提示词被泄露到GitHub。Anthropic公开道歉，承认决策错误。"

async def main():
    def prog(pct, msg):
        print(f"  [{pct:3d}%] {msg}")
    
    r = await run_pipeline(
        text=TEXT,
        title="测试高级模式",
        mode="advanced",
        resolution="1920x1080",
        stop_at="video",
        progress_callback=prog,
    )
    print(f"\n结果: state={r['state']}, video={r.get('video_path')}")
    if r.get("error"):
        print(f"错误: {r['error']}")
    if r.get("video_path") and Path(r["video_path"]).exists():
        size = Path(r["video_path"]).stat().st_size / 1024 / 1024
        print(f"文件大小: {size:.1f} MB")

asyncio.run(main())
