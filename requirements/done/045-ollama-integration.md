# 045 — 本地 Ollama 模型集成

> 状态: 🆕 待开发 | Size: M (5 pts) | 优先级: P2

---

## 问题陈述

当前岛主完全依赖 DeepSeek/OpenAI 云端 API：
- 无网络时无法使用 AI 功能
- 所有对话内容经过第三方服务器
- API 费用随使用量增长

支持本地 Ollama 后，用户可实现"数据主权最后一环"——连模型推理都在本地完成。

---

## 方案

在 `chat_service.py` 中抽象 Provider 层，支持多后端切换：

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  DeepSeek   │     │   OpenAI    │     │   Ollama    │
│  (云端)     │     │   (云端)    │     │   (本地)    │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────┴──────┐
                    │  Provider   │
                    │  抽象层     │
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │ chat_service│
                    └─────────────┘
```

Ollama 兼容 OpenAI Chat Completions 格式，改造量可控。

---

## User Stories

### Story 1: 配置本地模型

> As a 岛主用户，I want 在设置页面选择"本地模型（Ollama）"作为 AI 后端，so that 我的对话完全不出本机。

**验收标准：**
1. 设置页面新增"AI 后端"选项：DeepSeek / OpenAI / Ollama / 自定义
2. 选择 Ollama 时自动检测本地服务（http://localhost:11434）
3. 检测到 Ollama 后列出已安装模型供选择
4. 未检测到时显示安装引导链接
5. 配置保存后立即生效，无需重启

### Story 2: 自动降级

> As a 岛主用户，I want 云端 API 不可用时自动切换到本地模型，so that 我的岛不会因为网络问题完全瘫痪。

**验收标准：**
1. 云端 API 连续 2 次超时/错误后自动切换到 Ollama（如已配置）
2. 切换时在对话中提示"已切换到本地模型，部分复杂功能可能受限"
3. 云端恢复后不自动切回（避免频繁切换），需用户手动或下次会话恢复
4. 降级状态在 UI 上有明显标识（如状态栏显示"本地模式"）

### Story 3: 工具调用兼容

> As a 岛主 Agent，I want 本地模型也能调用工具，so that 远程控制等功能在离线时仍可用。

**验收标准：**
1. 7B+ 模型（如 qwen2.5:7b）能正确解析工具调用格式
2. 工具调用失败时 Agent 降级为纯文本回复（不死循环）
3. 对不支持工具调用的小模型，自动禁用工具，仅提供对话能力
4. 记录本地模型的工具调用成功率，供用户参考选择模型

---

## 技术设计要点

### Provider 抽象

```python
# daozhu/services/llm_provider.py

class LLMProvider:
    """LLM 后端抽象基类"""
    
    async def chat_stream(self, messages, tools=None):
        """流式对话，yield delta"""
        raise NotImplementedError
    
    async def health_check(self) -> bool:
        """检测服务是否可用"""
        raise NotImplementedError
    
    def supports_tools(self) -> bool:
        """是否支持工具调用"""
        raise NotImplementedError


class DeepSeekProvider(LLMProvider): ...
class OllamaProvider(LLMProvider): ...
class OpenAIProvider(LLMProvider): ...
```

### Ollama 检测逻辑

```python
async def detect_ollama():
    """检测本地 Ollama 服务"""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return {"available": True, "models": [m["name"] for m in models]}
    except:
        return {"available": False, "models": []}
```

### 配置项

```json
{
  "ai": {
    "provider": "deepseek",
    "deepseek_api_key": "sk-xxx",
    "openai_api_key": "",
    "ollama": {
      "base_url": "http://localhost:11434",
      "model": "qwen2.5:7b",
      "auto_fallback": true
    },
    "custom": {
      "base_url": "",
      "api_key": "",
      "model": ""
    }
  }
}
```

### 推荐模型（文档中引导）

| 模型 | 大小 | 工具调用 | 推荐场景 |
|------|------|----------|----------|
| qwen2.5:7b | ~4.7GB | ✅ 较好 | 日常使用，平衡性能和质量 |
| qwen2.5:14b | ~9GB | ✅ 好 | 复杂任务，需 16GB+ 内存 |
| llama3.1:8b | ~4.7GB | ⚠️ 一般 | 英文场景 |
| deepseek-coder-v2:16b | ~9GB | ✅ 好 | 代码生成场景 |

---

## 模块划分

```
daozhu/
├── services/
│   ├── llm_provider.py      # Provider 抽象 + 工厂
│   ├── ollama_provider.py   # Ollama 实现
│   └── chat_service.py      # 改造：使用 Provider 而非直接调 API
├── routes/
│   └── settings.py          # 新增 Ollama 检测 + 模型列表 API
```

---

## 依赖

- 用户本地安装 Ollama（可选，非必须）
- httpx（已有）
- chat_service.py 重构为 Provider 模式

---

## 风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| 小模型工具调用能力弱 | Agent 功能受限 | 检测能力后动态禁用工具 |
| 用户硬件不足 | 推理极慢 | 检测时提示最低配置要求 |
| Ollama 版本碎片化 | API 兼容问题 | 锁定最低版本要求（0.3+） |
| 降级切换时丢失上下文 | 对话断裂 | 切换时保留最近 N 条消息 |

---

## 与 hermes-agent 的对照

hermes-agent 的做法（可借鉴）：
- **多 Provider 插件体系：** 每个 provider 独立注册，统一接口
- **Fallback 机制：** `fallback_model` 配置，主模型失败自动切换
- **Auxiliary client：** 不同任务可用不同模型（主对话用大模型，标题生成用小模型）

岛主简化版：
- 不需要插件体系，3-4 个 Provider 硬编码即可
- Fallback 只做"云端 → 本地"单向降级
- 暂不做任务级模型路由（后续可扩展）
