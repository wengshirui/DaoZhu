"""测试中级模式（Pexels 视频背景 + Edge-TTS）"""
import sys, asyncio, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

from pipeline import run_pipeline

TEXT = """刚刚，地表最强Claude 5被攻破了！

知名黑客普林尼公开宣布，Fable 5的安全分类器已被自己率领的团队彻底攻破。属于绝对禁区的漏洞利用代码，以及各种违禁化学品的制作步骤，全部被Claude吐了出来。

要知道，6月9日Claude 5发布时，Anthropic特意强调，模型经历了超过1000小时的外部测试，没有发现任何通用越狱方法。然而这个神话只维持了三天，72小时后就被黑客毫不留情地破解了。

黑客的关键杀招有三个。第一招是字符级迷魂阵，把英文字母替换成西里尔字母，让分类器认不出关键词。第二招是把意图稀释进漫长的对话中，让分类器的注意力被稀释。第三招是穿上学术马甲，将敏感请求包装成科幻小说或学术评审。

更令Anthropic尴尬的是，黑客顺手将内部12万字符的系统提示词全部打包上传到了GitHub。这无异于将模型的行为宪法赤裸裸地暴露在阳光之下。

面对全网的舆论海啸，Anthropic很快撑不住了。就在昨天公开致歉，承认决策错误，宣布紧急撤回隐形降智政策。

用Claude的人会不断怀疑——我拿到的答案是真的吗？这就是Anthropic永远失去的东西。"""

async def main():
    def prog(pct, msg):
        print(f"  [{pct:3d}%] {msg}")
    
    r = await run_pipeline(
        text=TEXT,
        title="Claude5被黑客攻破",
        mode="medium",
        resolution="1920x1080",
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
