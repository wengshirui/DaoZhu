"""快速测试 3 个问题"""
import urllib.request, json

def ask(question):
    data = json.dumps({"message": question, "conversation_id": None}).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:7788/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        body = resp.read().decode("utf-8")
    text = ""
    for line in body.split("\n"):
        if line.startswith("data: "):
            try:
                d = json.loads(line[6:])
                if d.get("chunk"):
                    text += d["chunk"]
            except:
                pass
    return text.strip()

print("=" * 50)
print("  快速准确性测试（3 个问题）")
print("=" * 50)

# 测试 1
print("\n[1] 问: 我一共有多少个待办任务？ (真实=71)")
r = ask("我一共有多少个待办任务？帮我查一下")
print(f"    答: {r[:200]}")
print(f"    {'✅ 正确' if '71' in r else '❌ 错误'}")

# 测试 2
print("\n[2] 问: 我有几个未完成的待办？ (真实=22)")
r = ask("查一下我有几个未完成的待办")
print(f"    答: {r[:200]}")
print(f"    {'✅ 正确' if '22' in r else '❌ 错误'}")

# 测试 3
print("\n[3] 问: 我有几个工作区？ (真实=10)")
r = ask("帮我看看我有几个工作区")
print(f"    答: {r[:200]}")
print(f"    {'✅ 正确' if '10' in r else '❌ 错误'}")

print("\n" + "=" * 50)
