"""测试中级模式 — Anthropic 实名制新闻"""
import sys, asyncio, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

from pipeline import run_pipeline

TEXT = """突发！AI圈迎来史诗级大地震！那个一直以安全道德自居的Anthropic，终于要对普通用户下手了！用Claude以后不仅要实名，还要刷脸！

就在近日，Anthropic向用户发送了隐私政策更新通知，宣布自2026年7月8日起实施新版服务条款。其中最炸裂的一条：为了保障服务安全，官方将引入实名与人脸身份验证！

具体怎么验？你需要上传政府颁发的实体身份证件，比如护照、驾照，然后对着摄像头拍一张实时自拍照，进行活体比对。

很多人问，好端端的为什么要搞这么严？其实这背后是AI代理能力的狂飙。现在的Claude不仅能陪聊，还能帮你订机票、连Notion、跑自动化任务。当AI的足迹遍布你的各个应用时，平台必须确切知道屏幕背后发号施令的究竟是谁。

说白了，这就是为了建立责任追溯机制，彻底终结AI的匿名时代。

官方强调验证由第三方服务商Persona处理，数据不会存在Anthropic自己的服务器上。但是！新规还悄悄降低了一个门槛：只要Anthropic认为披露数据是合理必要的，就可以主动向执法部门共享你的对话记录！

这波操作对国内用户来说简直是精准打击。因为验证服务商Persona目前根本不支持中国大陆的证件。也就是说就算你愿意交护照、愿意刷脸，系统可能压根不让你过。

面对越来越严格的监管，你手里的Claude账号还能撑多久？你会选择放弃，还是寻找替代方案？"""

async def main():
    def prog(pct, msg):
        print(f"  [{pct:3d}%] {msg}")
    
    r = await run_pipeline(
        text=TEXT,
        title="Anthropic实名制刷脸",
        mode="medium",
        resolution="1920x1080",  # 横屏
        stop_at="video",
        progress_callback=prog,
    )
    print(f"\n结果: state={r['state']}")
    print(f"输出: {r.get('video_path')}")
    if r.get("error"):
        print(f"错误: {r['error']}")
    if r.get("video_path") and Path(r["video_path"]).exists():
        size = Path(r["video_path"]).stat().st_size / 1024 / 1024
        print(f"文件大小: {size:.1f} MB")

asyncio.run(main())
