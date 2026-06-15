"""
测试脚本：用同一段文本生成三种模式的视频，用于对比。
运行: python workspaces/AutoMovie/test_3modes.py
"""
import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # 项目根目录（daozhu 包）

from pipeline import run_pipeline

TEXT = """刚刚，地表最强Claude 5被攻破！

知名黑客普林尼公开宣布：Fable 5的安全分类器，已被自己率领的团队彻底攻破。

6月9日Claude Fable 5发布时，Anthropic特意强调：模型在发布前经历了超过1000小时的外部漏洞赏金测试，没有发现任何通用越狱方法。

然而，这个神话只维持了三天。72小时后，就被黑客毫不留情地破解了。

黑客的关键杀招是什么？

第一招，字符级迷魂阵——把英文字母替换成几乎一模一样的西里尔字母，让安全分类器认不出关键词。

第二招，把意图稀释进一场漫长的对话里，让分类器的注意力权重被稀释。

第三招，穿上学术马甲——将敏感请求包装成科幻小说创作或学术评审。

更令Anthropic尴尬的是，黑客顺手将Fable 5内部那条长达12万字符的系统提示词全部打包，上传到了GitHub。

面对席卷全网的舆论海啸，Anthropic很快撑不住了。就在昨天，Anthropic公开致歉，承认决策错误。

用Claude的人，会不断怀疑：我拿到的答案是真的吗？这，就是Anthropic永远失去的东西。"""


async def main():
    print("=" * 60)
    print("  火柴人剧场 — 三模式对比测试")
    print("=" * 60)

    results = {}

    # 1. 简单模式
    print("\n[1/3] 简单模式（SVG 无声 HTML）...")
    r1 = await run_pipeline(
        text=TEXT,
        title="Claude5被攻破",
        mode="simple",
        stop_at="video",
    )
    results["simple"] = r1
    print(f"  状态: {r1['state']}")
    print(f"  输出: {r1.get('video_path', 'N/A')}")

    # 2. 中级模式
    print("\n[2/3] 中级模式（Pexels视频 + Edge-TTS）...")
    r2 = await run_pipeline(
        text=TEXT,
        title="Claude5被攻破",
        mode="medium",
        resolution="1920x1080",
        stop_at="video",
    )
    results["medium"] = r2
    print(f"  状态: {r2['state']}")
    print(f"  输出: {r2.get('video_path', 'N/A')}")

    # 3. 高级模式
    print("\n[3/3] 高级模式（GLM-Image + GLM-TTS）...")
    r3 = await run_pipeline(
        text=TEXT,
        title="Claude5被攻破",
        mode="advanced",
        resolution="1920x1080",
        stop_at="video",
    )
    results["advanced"] = r3
    print(f"  状态: {r3['state']}")
    print(f"  输出: {r3.get('video_path', 'N/A')}")

    # 汇总
    print("\n" + "=" * 60)
    print("  汇总")
    print("=" * 60)
    for mode, r in results.items():
        path = r.get("video_path", "")
        size = ""
        if path and Path(path).exists():
            size = f"{Path(path).stat().st_size / 1024 / 1024:.1f} MB"
        print(f"  {mode:10} | 状态: {r['state']:8} | 文件: {size or 'N/A'}")
        if r.get("error"):
            print(f"            | 错误: {r['error'][:80]}")

    print("\n输出目录: workspaces/AutoMovie/output/")
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
