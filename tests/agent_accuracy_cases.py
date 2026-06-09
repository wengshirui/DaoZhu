"""
岛主 DaoZhu — Agent 准确性测试用例
每个用例有：
  - question: 发给 agent 的问题
  - verify(): 不依赖 AI，直接从数据源获取真实答案
  - match(agent_response, truth): 判断 agent 回答是否与真相一致

用法：
  python tests/agent_accuracy_cases.py          # 只看验真结果
  python tests/agent_accuracy_cases.py --test   # 对接 agent API 做完整测试（后续）
"""

import sqlite3
import os
import re
from datetime import datetime, date
from pathlib import Path

# === 项目根目录 ===
ROOT = Path(__file__).parent.parent
TODO_DB = ROOT / "workspaces" / "todo" / "data.db"
PET_DB = ROOT / "workspaces" / "desktop-pet" / "data.db"
TEST_DIR = ROOT / "tests" / "_test_workspace"


# === 工具函数 ===

def query_db(db_path: Path, sql: str) -> any:
    """执行 SQL 返回结果"""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    result = conn.execute(sql).fetchall()
    conn.close()
    return result


def count_db(db_path: Path, sql: str) -> int:
    """执行 COUNT SQL 返回整数"""
    conn = sqlite3.connect(str(db_path))
    count = conn.execute(sql).fetchone()[0]
    conn.close()
    return count


def extract_number(text: str) -> int | None:
    """从文本中提取第一个数字"""
    match = re.search(r'\b(\d+)\b', text)
    return int(match.group(1)) if match else None


def extract_all_numbers(text: str) -> list[int]:
    """从文本中提取所有数字"""
    return [int(m) for m in re.findall(r'\b(\d+)\b', text)]


# === 测试用例定义 ===

class TestCase:
    def __init__(self, id: str, question: str, verify_fn, match_fn=None):
        self.id = id
        self.question = question
        self.verify_fn = verify_fn
        self.match_fn = match_fn or self._default_match

    def verify(self):
        """获取真实答案"""
        return self.verify_fn()

    def match(self, agent_response: str, truth) -> bool:
        """判断 agent 回答是否正确"""
        return self.match_fn(agent_response, truth)

    def _default_match(self, response: str, truth) -> bool:
        """默认匹配：回复中包含真实数字"""
        if isinstance(truth, int):
            return str(truth) in response
        if isinstance(truth, str):
            return truth.lower() in response.lower()
        return False


# === 10 个测试用例 ===

CASES = [
    # 1. 当前时间
    TestCase(
        id="time_now",
        question="现在是几点？",
        verify_fn=lambda: datetime.now().strftime("%H"),
        match_fn=lambda resp, truth: truth in resp,
    ),

    # 2. 待办总数
    TestCase(
        id="todo_total_count",
        question="我一共有多少个待办任务？",
        verify_fn=lambda: count_db(TODO_DB, "SELECT COUNT(*) FROM tasks"),
        match_fn=lambda resp, truth: str(truth) in resp,
    ),

    # 3. 待办中未完成数量
    TestCase(
        id="todo_active_count",
        question="我有几个未完成的待办？",
        verify_fn=lambda: count_db(TODO_DB, "SELECT COUNT(*) FROM tasks WHERE status != 'done'"),
        match_fn=lambda resp, truth: str(truth) in resp,
    ),

    # 4. 待办中已完成数量
    TestCase(
        id="todo_done_count",
        question="我完成了几个待办？",
        verify_fn=lambda: count_db(TODO_DB, "SELECT COUNT(*) FROM tasks WHERE status = 'done'"),
        match_fn=lambda resp, truth: str(truth) in resp,
    ),

    # 5. 今日到期待办数量
    TestCase(
        id="todo_today_count",
        question="今天有几个到期的待办？",
        verify_fn=lambda: count_db(
            TODO_DB,
            f"SELECT COUNT(*) FROM tasks WHERE due_date = '{date.today().isoformat()}' AND status != 'done'"
        ),
        match_fn=lambda resp, truth: str(truth) in resp or (truth == 0 and ("没有" in resp or "0" in resp)),
    ),

    # 6. 桌面宠物数量
    TestCase(
        id="pet_count",
        question="我现在有几个桌面宠物？",
        verify_fn=lambda: count_db(PET_DB, "SELECT COUNT(*) FROM pets") if PET_DB.exists() else 0,
        match_fn=lambda resp, truth: str(truth) in resp or (truth == 0 and "没有" in resp),
    ),

    # 7. 工作区总数
    TestCase(
        id="workspace_count",
        question="我一共有几个工作区？",
        verify_fn=lambda: len([
            d for d in (ROOT / "workspaces").iterdir()
            if d.is_dir() and (d / "workspace.json").exists()
        ]),
        match_fn=lambda resp, truth: str(truth) in resp,
    ),

    # 8. 某文件行数
    TestCase(
        id="file_line_count",
        question="daozhu/prompts.py 这个文件一共有多少行？",
        verify_fn=lambda: len((ROOT / "daozhu" / "prompts.py").read_text(encoding="utf-8").splitlines()),
        match_fn=lambda resp, truth: str(truth) in resp,
    ),

    # 9. 创建文件（验证文件是否存在）
    TestCase(
        id="create_file",
        question="在 tests/_test_workspace 文件夹下创建一个 hello.txt 文件，内容写'hello daozhu'",
        verify_fn=lambda: (TEST_DIR / "hello.txt").exists() and "hello daozhu" in (TEST_DIR / "hello.txt").read_text(encoding="utf-8"),
        match_fn=lambda resp, truth: truth is True,
    ),

    # 10. 待办分类（项目）数量
    TestCase(
        id="todo_project_count",
        question="待办工作区里一共有几个分类（项目）？",
        verify_fn=lambda: count_db(TODO_DB, "SELECT COUNT(*) FROM projects") if TODO_DB.exists() else 0,
        match_fn=lambda resp, truth: str(truth) in resp,
    ),
]


# === 执行验真 ===

def run_verification():
    """运行所有用例的验真（不需要 agent）"""
    print("\n" + "=" * 60)
    print("  岛主 Agent 准确性测试 — 验真结果")
    print("=" * 60 + "\n")

    results = []
    for case in CASES:
        try:
            truth = case.verify()
            results.append((case.id, case.question, truth, None))
            print(f"  ✅ [{case.id}]")
            print(f"     问题: {case.question}")
            print(f"     真实答案: {truth}")
            print()
        except Exception as e:
            results.append((case.id, case.question, None, str(e)))
            print(f"  ❌ [{case.id}] 验真失败: {e}")
            print(f"     问题: {case.question}")
            print()

    print("=" * 60)
    ok = sum(1 for r in results if r[3] is None)
    print(f"  验真完成: {ok}/{len(results)} 成功")
    print("=" * 60 + "\n")
    return results


if __name__ == "__main__":
    # 确保测试目录存在
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    run_verification()


# === 对接 Agent API 做完整测试 ===

import httpx
import asyncio
import json
import sys


async def ask_agent(question: str, timeout: float = 60.0) -> str:
    """调 /api/chat 发问题，收集流式回复（用 urllib 避免代理问题）"""
    import urllib.request

    data = json.dumps({"message": question, "conversation_id": None}).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:7788/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return f"[HTTP ERROR {resp.status}]"
            body = resp.read().decode("utf-8")
    except Exception as e:
        return f"[ERROR: {e}]"

    # 解析 SSE 流
    full_text = ""
    for line in body.split("\n"):
        if not line.startswith("data: "):
            continue
        try:
            chunk_data = json.loads(line[6:])
            if chunk_data.get("chunk"):
                full_text += chunk_data["chunk"]
        except (json.JSONDecodeError, KeyError):
            pass
    return full_text.strip()


def run_agent_test():
    """对接 agent 做完整准确性测试"""
    print("\n" + "=" * 60)
    print("  岛主 Agent 准确性测试 — Agent 对接测试")
    print("=" * 60 + "\n")

    passed = 0
    failed = 0
    skipped = 0

    for case in CASES:
        # 跳过"创建文件"用例（需要特殊处理）
        if case.id == "create_file":
            skipped += 1
            print(f"  ⏭️  [{case.id}] 跳过（需要文件操作验证）\n")
            continue

        # 获取真实答案
        try:
            truth = case.verify()
        except Exception as e:
            skipped += 1
            print(f"  ⏭️  [{case.id}] 验真失败: {e}\n")
            continue

        # 问 agent
        print(f"  🔄 [{case.id}] 问: {case.question}")
        print(f"     真实答案: {truth}")

        try:
            response = asyncio.run(ask_agent(case.question))
        except Exception as e:
            failed += 1
            print(f"     ❌ Agent 调用失败: {e}\n")
            continue

        # 截取回复前 100 字符显示
        resp_preview = response[:100].replace("\n", " ")
        print(f"     Agent 回答: {resp_preview}...")

        # 比对
        is_correct = case.match(response, truth)
        if is_correct:
            passed += 1
            print(f"     ✅ 正确\n")
        else:
            failed += 1
            print(f"     ❌ 幻觉！真实={truth}, 回复中未找到\n")

    print("=" * 60)
    total = passed + failed
    rate = (passed / total * 100) if total > 0 else 0
    print(f"  结果: {passed}/{total} 正确 ({rate:.0f}%)")
    print(f"  通过: {passed}  幻觉: {failed}  跳过: {skipped}")
    print("=" * 60 + "\n")

    return {"passed": passed, "failed": failed, "skipped": skipped}


if __name__ == "__main__":
    TEST_DIR.mkdir(parents=True, exist_ok=True)

    if "--test" in sys.argv:
        run_agent_test()
    else:
        run_verification()
