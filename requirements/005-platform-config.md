# REQ-005: 平台全局配置

> Intake ID: 2025-05-25-platform-config

---

## 原始需求

平台需要统一的配置管理，包括 AI API Key、工作区目录、端口范围、主题偏好等。参考 Hermes-Agent 的 config.yaml + .env 分离模式。

---

## 提取意图

config.py 模块负责：
- 读取/写入 config.json（非敏感配置）
- 读取 .env（API Key 等敏感信息）
- 提供默认值 + 用户覆盖的合并机制
- 前端设置页面可修改配置

---

## 配置结构（草案）

```json
{
  "platform": {
    "port": 7788,
    "workspace_dir": "./workspaces",
    "port_range": [7801, 7899]
  },
  "ai": {
    "provider": "deepseek",
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com/v1"
  },
  "display": {
    "theme": "light",
    "language": "zh-CN"
  }
}
```

`.env` 文件：
```
DEEPSEEK_API_KEY=sk-xxx
OPENAI_API_KEY=sk-xxx
```

---

## 开放问题

| # | 模块 | 问题 | AI 猜测 | 答案 |
|---|------|------|---------|------|
| 1 | 用户与现状 | 用户如何首次配置 AI API Key？是否需要引导向导？ | 首次启动弹出设置引导，填写 API Key | |
| 2 | 范围与影响 | 配置变更是否需要重启平台才能生效？ | 大部分热加载，端口变更需重启 | |
| 3 | 业务规则 | 是否支持多 AI 提供商切换？切换时历史对话如何处理？ | 支持切换，历史对话保留不受影响 | |

---

## T-Shirt Size

**S (3 pts)** — 配置读写逻辑简单，无外部依赖，主要是文件 I/O + 合并逻辑。

---

## 状态

- [x] 需求录入
- [ ] 开放问题确认
- [ ] 需求提炼
- [ ] 移交开发
