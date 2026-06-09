"""
岛主 Agent 准确性测试 — 测试运行器
从 questions.py 随机抽取 N 个问题，对接 agent API 验证准确性。

用法:
  python tests/run_test.py              # 随机 3 题
  python tests/run_test.py -n 5         # 随机 5 题
  python tests/run_test.py --all        # 全部问题
  python tests/run_test.py --verify     # 只跑验真（不调 agent）
  python tests/run_test.py --id todo_total  # 指定单题
"""

import argparse
import json
import random
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from questions import QUESTIONS


def ask_agent(question: str, timeout: float = 90.0) -> str:
    """调 /api/chat 发问题，解析 SSE 流返回完整回复"""
    data = json.dumps({"message": question, "conversation_id": None}).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:7788/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except Exception as e:
        return f"[ERROR: {e}]"

    text = ""
    for line in body.split("\n"):
        if line.startswith("data: "):
            try:
                d = json.loads(line[6:])
                if d.get("chunk"):
                    text += d["chunk"]
            except (json.JSONDecodeError, KeyError):
                pass
    return text.strip()


def run_verify(questions):
    """只验真，不调 agent"""
    print("\n" + "=" * 55)
    print("  验真模式（检查每个问题能否获取真实答案）")
    print("=" * 55 + "\n")

    ok = 0
    for q in questions:
        try:
            truth = q.verify()
            print(f"  ✅ [{q.id}] 真实答案: {truth}")
            print(f"     问题: {q.text}")
            ok += 1
        except Exception as e:
            print(f"  ❌ [{q.id}] 验真失败: {e}")
        print()

    print(f"  验真完成: {ok}/{len(questions)} 成功\n")


def run_test(questions):
    """对接 agent 做完整测试"""
    print("\n" + "=" * 55)
    print(f"  Agent 准确性测试（{len(questions)} 题）")
    print("=" * 55 + "\n")

    passed = 0
    failed = 0

    for q in questions:
        try:
            truth = q.verify()
        except Exception as e:
            print(f"  ⏭️  [{q.id}] 验真失败，跳过: {e}\n")
            continue

        print(f"  🔄 [{q.id}] 问: {q.text}")
        print(f"     真实: {truth}")

        response = ask_agent(q.text)
        preview = response[:120].replace("\n", " ")
        print(f"     回答: {preview}...")

        if q.match(response, truth):
            passed += 1
            print(f"     ✅ 正确\n")
        else:
            failed += 1
            print(f"     ❌ 错误（真实={truth}）\n")

    total = passed + failed
    rate = (passed / total * 100) if total > 0 else 0
    print("=" * 55)
    print(f"  结果: {passed}/{total} 正确 ({rate:.0f}%)")
    print(f"  ✅ 通过: {passed}  ❌ 失败: {failed}")
    print("=" * 55 + "\n")


def main():
    parser = argparse.ArgumentParser(description="岛主 Agent 准确性测试")
    parser.add_argument("-n", type=int, default=3, help="随机抽取问题数（默认3）")
    parser.add_argument("--all", action="store_true", help="测试全部问题")
    parser.add_argument("--verify", action="store_true", help="只验真不测试")
    parser.add_argument("--id", type=str, help="指定单个问题 ID")
    args = parser.parse_args()

    # 选择问题
    if args.id:
        questions = [q for q in QUESTIONS if q.id == args.id]
        if not questions:
            print(f"未找到问题: {args.id}")
            print(f"可用: {', '.join(q.id for q in QUESTIONS)}")
            sys.exit(1)
    elif args.all:
        questions = QUESTIONS[:]
    else:
        questions = random.sample(QUESTIONS, min(args.n, len(QUESTIONS)))

    # 运行
    if args.verify:
        run_verify(questions)
    else:
        run_test(questions)


if __name__ == "__main__":
    main()
