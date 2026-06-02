# 060 — 工具调用权限门控（Permission Gate）

> 来源: DeepSeek-Reasonix 项目 `internal/permission/`
> 状态: 🆕 待开发
> 优先级: P2
> T-shirt Size: S
> 录入日期: 2026-06-02

---

## 问题陈述

岛主当前的工具权限控制仅有两种机制：
1. 工具整体禁用/启用（#035）
2. 删除操作弹确认（#034）

但缺少更细粒度的控制。例如：
- 用户可能想让 `web_search` 免确认但 `terminal` 必须确认
- 某些高危命令模式应该永远拒绝（如 `rm -rf /`）
- 某些常用安全操作应该永远放行（如 `ls`、`cat`）

随着 #054 Python 兜底策略的加入，权限控制变得更重要。

## 用户故事

**As a** 岛主用户
**I want** 精细控制哪些工具操作需要我确认、哪些自动放行、哪些永远禁止
**So that** AI 既能高效执行安全操作，又不会在我不知情的情况下做危险操作

## 范围

### In Scope

- 三级权限：allow（静默放行）/ ask（询问用户）/ deny（永远拒绝）
- 基于工具名 + 参数模式的匹配规则
- 规则配置存储在 config（不在代码中硬编码）
- 默认规则集：常见安全操作 allow，危险模式 deny，其余 ask

### Out of Scope

- 按用户角色区分权限（单用户本地应用）
- 运行时动态修改规则（初期改配置 + 重启）
- UI 配置界面（后续加设置页 tab）

## 验收标准

1. **AC1**: 配置中声明 `allow` 规则后，匹配的工具调用不弹确认直接执行
2. **AC2**: 配置中声明 `deny` 规则后，匹配的工具调用直接拒绝并告知用户
3. **AC3**: 未匹配任何规则的工具调用走默认行为（ask = 弹确认）
4. **AC4**: 规则支持 glob 模式匹配参数，如 `terminal(rm -rf*)` 匹配删库命令
5. **AC5**: 内置默认规则集合理：web_search/list_workspaces 等 allow，
   terminal(rm/del/format) 等 deny

## 业务价值

- 减少重复确认的操作疲劳（预估减少 60% 的无效确认弹窗）
- 防止 AI 执行高危操作（安全兜底）
- 为 #054 Python 兜底策略提供安全保障

## T-Shirt Size

**S** — 配置读取 + 工具调用前增加一个匹配检查函数；不改 UI，不改 schema，
复用现有确认机制

## 依赖

- 现有配置系统（config_db）
- agent.py 工具调用分发逻辑
- #054 Python 兜底策略（此需求是其前置安全保障）

## 技术提示（供开发参考）

参考 Reasonix `internal/permission/` 的设计：

```toml
# reasonix.toml 的权限配置
[permissions]
mode  = "ask"                                # 默认行为
deny  = ["bash(rm -rf*)", "bash(git push*)"] # 永远禁止
allow = ["bash(go test*)"]                   # 永远放行
```

岛主的实现可以放在 config.json 中：
```json
{
  "permissions": {
    "default": "ask",
    "allow": ["web_search(*)", "list_workspaces(*)", "call_workspace_api(GET *)"],
    "deny": ["terminal(rm -rf*)", "terminal(del /s*)", "terminal(format*)"]
  }
}
```

匹配逻辑：
```python
import fnmatch

def check_permission(tool_name: str, args: dict) -> str:
    """返回 'allow' / 'ask' / 'deny'"""
    call_signature = f"{tool_name}({args_to_pattern(args)})"
    for pattern in config.deny_patterns:
        if fnmatch.fnmatch(call_signature, pattern):
            return "deny"
    for pattern in config.allow_patterns:
        if fnmatch.fnmatch(call_signature, pattern):
            return "allow"
    return config.default_mode  # "ask"
```
