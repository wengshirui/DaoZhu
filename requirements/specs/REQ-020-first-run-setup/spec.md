# REQ-020 Spec: 首次启动环境初始化

## Story 1: 环境检测任务 + 配置引导

**User Story:** As a 不懂技术的小微企业老板，I want 首次打开 AccoBot 时系统自动检测环境并告诉我缺什么，so that 我不需要手动排查为什么浏览器自动化不能用。

**Story Points:** 3

### Acceptance Criteria

- AC-1: 注册为 ProactiveEngine 的 `once` 任务，首次启动时执行，完成后不再执行
- AC-2: 检测项包括：Node.js/npx 是否可用、浏览器（Chrome/Edge）是否已安装、API Key 是否已配置
- AC-3: 检测结果生成 Notification 推送到前端——缺失项为 warning 级别，全部就绪为 info 级别
- AC-4: 缺失 Node.js 时，notification 的 action_prompt 引导 Agent 协助安装
- AC-5: API Key 未配置时，提示用户打开设置面板

### Design

注册到 ProactiveEngine：
```python
engine.register(ProactiveTask(
    name="first_run_setup",
    trigger="once",
    interval_seconds=0,
    check_fn=check_environment,
))
```

检测逻辑：
```python
def check_environment() -> List[Notification]:
    results = []
    # 1. Check Node.js/npx
    # 2. Check browser
    # 3. Check API Key
    # 4. Check if company exists
    return results
```

### Tasks

**Task 1.1: 实现 check_environment 函数**
- 检测 Node.js（`shutil.which("node")`）
- 检测 npx（`shutil.which("npx")`）
- 检测浏览器（复用 server.py 的 browser_check 逻辑）
- 检测 API Key（`get_api_key()` 是否有值）
- 检测是否有账套
- 预计工时：0.5 天

**Task 1.2: 注册到 ProactiveEngine 并集成**
- 在 `create_default_engine()` 中注册 first_run_setup 任务
- 确保 once 语义正确（完成后持久化，不再执行）
- 预计工时：0.5 天
