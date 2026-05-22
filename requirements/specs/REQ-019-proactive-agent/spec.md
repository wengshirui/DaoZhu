# REQ-019 Spec: Agent 主动任务机制

## Story 1: 主动任务注册与调度框架

**User Story:** As a 系统，I want 一个通用的主动任务注册和调度框架，so that 各种检查逻辑（税务提醒、凭证积压、环境检测）可以统一注册和执行。

**Story Points:** 3

### Acceptance Criteria

- AC-1: 支持注册任务，每个任务包含 name、trigger_type（periodic/once/condition）、interval、check_fn、on_result
- AC-2: 周期性任务按 interval 定时执行
- AC-3: 一次性任务执行成功后标记完成，后续不再执行
- AC-4: 单个任务异常不影响其他任务
- AC-5: 改造现有 Heartbeat 为基于此框架的实现

### Design

```python
# accobot/proactive.py

@dataclass
class ProactiveTask:
    name: str
    trigger: str          # "periodic" | "once" | "on_start"
    interval_seconds: int # for periodic tasks
    check_fn: Callable    # () -> List[Notification]
    completed: bool = False

@dataclass  
class Notification:
    type: str             # "tax_reminder" | "voucher_reminder" | "system"
    level: str            # "info" | "warning" | "action"
    title: str
    message: str
    action_prompt: str    # prompt to send to Agent if user confirms
    
class ProactiveEngine:
    def register(self, task: ProactiveTask) -> None
    def start(self) -> None
    def stop(self) -> None
    def mark_completed(self, task_name: str) -> None
    def get_pending_notifications(self) -> List[Notification]
```

### Tasks

**Task 1.1: 实现 ProactiveEngine 核心**
- 创建 `accobot/proactive.py`
- 实现任务注册、调度循环、错误隔离
- 一次性任务完成标记持久化到 `~/.accobot/.proactive_state.json`
- 预计工时：1 天

**Task 1.2: 迁移现有 Heartbeat 逻辑**
- 将 `heartbeat.py` 中的税务提醒、凭证检查改为注册到 ProactiveEngine 的任务
- Heartbeat 模块变为 ProactiveEngine 的薄封装（保持 API 兼容）
- 预计工时：0.5 天

---

## Story 2: 通知推送与用户确认流

**User Story:** As a 小微企业老板，I want 主动任务的结果推送到界面上，点击确认后 Agent 帮我执行，so that 我不会错过重要事项且操作安全可控。

**Story Points:** 2

### Acceptance Criteria

- AC-1: 通知通过 WebSocket 推送到前端
- AC-2: 前端待办区域显示通知，区分 info/warning/action 级别
- AC-3: action 级别通知带"执行"按钮，点击后将 action_prompt 发送到对话
- AC-4: 已处理的通知可以标记为已读/已处理

### Design

**WebSocket 消息格式：**
```json
{"type": "notification", "data": {"type": "tax_reminder", "level": "warning", "title": "...", "message": "...", "action_prompt": "..."}}
```

**前端交互：**
- 待办 dropdown 中显示通知列表
- action 级别显示"让 Agent 处理"按钮
- 点击按钮 → 将 action_prompt 填入聊天输入框并发送

### Tasks

**Task 2.1: WebSocket 通知推送**
- 在 server.py 的 WebSocket 连接中注册 ProactiveEngine 的回调
- 通知产生时推送到所有连接的客户端
- 预计工时：0.5 天

**Task 2.2: 前端通知展示与交互**
- 改造待办 dropdown 支持接收 WebSocket 通知
- action 级别通知显示执行按钮
- 预计工时：0.5 天

---

## 实施顺序

Story 1 → Story 2（Story 2 依赖 Story 1 的引擎）
