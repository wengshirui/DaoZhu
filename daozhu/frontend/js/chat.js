/**
 * chat.js — 聊天窗口：消息渲染 + 输入发送 + 自动滚动
 */

const Chat = {
  messages: [],
  isTyping: false,
  conversationId: null,
  showingReadme: false,
  _debounceTimer: null,
  _pendingMessages: [],
  _debounceMs: 2000, // 防抖等待时间（毫秒）

  init() {
    this._bindForm();
    this._bindTextarea();
    this._showWelcome();
  },

  // === 表单提交 ===
  _bindForm() {
    const form = document.getElementById('chat-form');
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      this._handleSend();
    });
  },

  // === 输入框自适应高度 + 快捷键 ===
  _bindTextarea() {
    const textarea = document.getElementById('chat-input');

    textarea.addEventListener('input', () => {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    });

    textarea.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this._handleSend();
      }
    });
  },

  // === 发送消息 ===
  async _handleSend() {
    const textarea = document.getElementById('chat-input');
    const sendBtn = document.querySelector('.chat__send');
    const text = textarea.value.trim();

    // 如果正在输出，点击停止
    if (this.isTyping) {
      this._stopGeneration();
      return;
    }

    if (!text) return;

    textarea.value = '';
    textarea.style.height = 'auto';
    this._removeWelcome();

    // 防抖：收集消息，等待静默后一起发送
    this._pendingMessages.push(text);
    this._addMessage('user', text);

    // 显示等待提示（第二条开始显示）
    if (this._pendingMessages.length > 1) {
      this._showBatchHint();
    }

    // 重置防抖计时器
    if (this._debounceTimer) {
      clearTimeout(this._debounceTimer);
    }
    this._debounceTimer = setTimeout(() => {
      this._flushPendingMessages();
    }, this._debounceMs);
  },

  // === 立即发送（跳过防抖等待） ===
  _flushNow() {
    if (this._debounceTimer) {
      clearTimeout(this._debounceTimer);
      this._debounceTimer = null;
    }
    this._flushPendingMessages();
  },

  // === 合并发送 ===
  async _flushPendingMessages() {
    this._debounceTimer = null;
    this._removeBatchHint();

    if (this._pendingMessages.length === 0) return;

    // 合并所有待发消息为一条（换行分隔）
    const combinedText = this._pendingMessages.join('\n');
    this._pendingMessages = [];

    const sendBtn = document.querySelector('.chat__send');

    // 切换为停止按钮
    sendBtn.textContent = '⏹ 停止';
    sendBtn.classList.add('chat__send--stop');
    this.isTyping = true;
    this._abortController = new AbortController();

    // 显示思考中指示器
    this._showTyping();

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: combinedText,
          conversation_id: this.conversationId || null,
        }),
        signal: this._abortController.signal,
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let msgEl = null;
      let bubble = null;
      let fullText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split('\n');

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.tool) {
              // 收到工具调用，隐藏思考指示器
              this._hideTyping();
              // 工具调用：创建管理员风格的工具面板（带头像）
              const container = document.getElementById('chat-messages');
              if (!this._toolPanel) {
                const wrapper = document.createElement('div');
                wrapper.className = 'message message--assistant message--tool';
                wrapper.innerHTML = `
                  <div class="message__avatar">
                    <img src="/img/librarian.svg" alt="岛管理员" style="width:28px;height:28px;image-rendering:pixelated" class="librarian-avatar">
                  </div>
                  <div class="tool-panel">
                    <div class="tool-panel__header">
                      <span class="tool-panel__indicator"></span>
                      <span class="tool-panel__title">⚡ 执行中</span>
                      <span class="tool-panel__count">0 步</span>
                    </div>
                    <div class="tool-panel__body"></div>
                  </div>
                `;
                container.appendChild(wrapper);
                this._toolPanel = wrapper.querySelector('.tool-panel');
                this._toolStepCount = 0;
              }
              this._toolStepCount++;
              const body = this._toolPanel.querySelector('.tool-panel__body');
              const step = document.createElement('div');
              step.className = 'tool-panel__step tool-panel__step--running';
              step.innerHTML = `<span class="tool-panel__step-icon">⏳</span> <span class="tool-panel__step-name">${data.tool}</span> <span class="tool-panel__step-status">执行中...</span>`;
              body.appendChild(step);
              this._lastToolStep = step;
              this._toolPanel.querySelector('.tool-panel__count').textContent = `${this._toolStepCount} 步`;
              this._scrollToBottom();
              Panel.addLog('info', `🔧 调用工具: ${data.tool}`);
              continue;
            }
            if (data.tool_done) {
              // 更新工具步骤状态
              if (this._lastToolStep) {
                const iconEl = this._lastToolStep.querySelector('.tool-panel__step-icon');
                const statusEl = this._lastToolStep.querySelector('.tool-panel__step-status');
                if (data.status === 'ok') {
                  iconEl.textContent = '✅';
                  statusEl.textContent = '完成';
                  this._lastToolStep.classList.remove('tool-panel__step--running');
                  this._lastToolStep.classList.add('tool-panel__step--done');
                } else {
                  iconEl.textContent = '❌';
                  statusEl.textContent = (data.error || '失败').slice(0, 30);
                  this._lastToolStep.classList.remove('tool-panel__step--running');
                  this._lastToolStep.classList.add('tool-panel__step--error');
                }
              }
              // 更新面板标题
              if (this._toolPanel) {
                const title = this._toolPanel.querySelector('.tool-panel__title');
                title.textContent = '⚡ 执行中';
              }
              const icon = data.status === 'ok' ? '✅' : '❌';
              Panel.addLog(data.status === 'ok' ? 'success' : 'error',
                `${icon} ${data.tool_done} ${data.error || '完成'}`);
              continue;
            }
            if (data.chunk) {
              // 收到文本 chunk 时，隐藏思考指示器，关闭工具面板并创建消息气泡
              this._hideTyping();
              if (this._toolPanel) {
                const title = this._toolPanel.querySelector('.tool-panel__title');
                title.textContent = `✅ 完成 (${this._toolStepCount} 步)`;
                this._toolPanel.querySelector('.tool-panel__indicator').classList.add('tool-panel__indicator--done');
                this._toolPanel = null;
                this._toolStepCount = 0;
              }
              if (!msgEl) {
                msgEl = this._addMessageElement('assistant', '');
                bubble = msgEl.querySelector('.message__bubble');
                this._streamStartTime = Date.now();
              }
              fullText += data.chunk;
              // 实时过滤 DSML 标记
              bubble.textContent = this._cleanDSML(fullText);
              this._scrollToBottom();
            }
            if (data.usage) {
              // Token 使用量统计（#061）
              this._lastUsage = data.usage;
            }
            if (data.conversation_id) {
              this.conversationId = data.conversation_id;
            }
          } catch (e) {}
        }
      }

      this.messages.push({ role: 'assistant', content: fullText });
      // 渲染 token 统计（#061）
      if (this._lastUsage && msgEl) {
        const u = this._lastUsage;
        const elapsed = (Date.now() - (this._streamStartTime || Date.now())) / 1000;
        const speed = elapsed > 0 && u.completion_tokens ? Math.round(u.completion_tokens / elapsed) : 0;
        // DeepSeek 费率: 输入 ¥1/M, 缓存 ¥0.1/M, 输出 ¥2/M
        const inputCost = (u.prompt_tokens - (u.cache_hit_tokens || 0)) * 1 / 1000000;
        const cacheCost = (u.cache_hit_tokens || 0) * 0.1 / 1000000;
        const outputCost = (u.completion_tokens || 0) * 2 / 1000000;
        const totalCost = inputCost + cacheCost + outputCost;

        let statsText = `⚡ ${u.prompt_tokens || 0} 入 / ${u.completion_tokens || 0} 出`;
        if (u.cache_hit_tokens > 0) statsText += ` · 缓存 ${u.cache_hit_tokens}`;
        if (speed > 0) statsText += ` · ${speed} tok/s`;
        if (totalCost > 0) statsText += ` · ≈¥${totalCost.toFixed(4)}`;

        const statsEl = document.createElement('div');
        statsEl.className = 'message__stats';
        statsEl.textContent = statsText;
        msgEl.querySelector('.message__content').appendChild(statsEl);
      }
      this._lastUsage = null;
      this._streamStartTime = null;
      Panel.addLog('info', `管理员回复: ${fullText.substring(0, 30)}...`);

    } catch (err) {
      if (err.name === 'AbortError') {
        this._addMessage('assistant', '（已停止）');
        Panel.addLog('info', '用户打断了输出');
      } else {
        this._addMessage('assistant', `抱歉，出了点问题：${err.message}`);
        Panel.addLog('error', `发送失败: ${err.message}`);
      }
    } finally {
      this._hideTyping();
      this.isTyping = false;
      sendBtn.textContent = '发送';
      sendBtn.classList.remove('chat__send--stop');
      this._abortController = null;
      this._toolPanel = null;
      this._toolStepCount = 0;
    }
  },

  _stopGeneration() {
    if (this._abortController) {
      this._abortController.abort();
    }
  },

  // === 添加消息到列表 ===
  _addMessage(role, content) {
    const msgEl = this._addMessageElement(role, content);
    this.messages.push({ role, content });
    this._scrollToBottom();
  },

  _addMessageElement(role, content) {
    const container = document.getElementById('chat-messages');
    const avatar = role === 'user'
      ? '<div class="avatar-user">我</div>'
      : '<img src="/img/librarian.svg" alt="岛管理员" style="width:28px;height:28px;image-rendering:pixelated" class="librarian-avatar">';

    const msgEl = document.createElement('div');
    msgEl.className = `message message--${role}`;

    // 用户消息显示撤回按钮
    const undoBtn = role === 'user'
      ? '<button class="message__undo" onclick="Chat._handleUndo(this)" title="撤回">↩</button>'
      : '';

    msgEl.innerHTML = `
      <div class="message__avatar">${avatar}</div>
      <div class="message__content">
        <div class="message__bubble">${this._escapeHtml(content)}</div>
        ${undoBtn}
      </div>
    `;

    container.appendChild(msgEl);
    this._scrollToBottom();
    return msgEl;
  },

  // === 欢迎消息 ===
  _showWelcome() {
    const container = document.getElementById('chat-messages');
    container.innerHTML = `
      <div class="chat__welcome" id="chat-welcome">
        <div class="chat__welcome-scene">
          <img src="/img/decor/cloud.svg" class="chat__welcome-cloud chat__welcome-cloud--1" alt="">
          <img src="/img/decor/cloud.svg" class="chat__welcome-cloud chat__welcome-cloud--2" alt="">
          <img src="/img/decor/cloud.svg" class="chat__welcome-cloud chat__welcome-cloud--3" alt="">
          <img src="/img/decor/birds.svg" class="chat__welcome-birds" alt="">
          <img src="/img/decor/island.svg" class="chat__welcome-island" alt="">
          <img src="/img/decor/wave.svg" class="chat__welcome-wave" alt="">
        </div>
        <img src="/img/librarian.svg" alt="岛管理员" style="width:80px;height:80px;image-rendering:pixelated;margin-bottom:16px;position:relative;z-index:1" class="librarian-avatar librarian-avatar--float">
        <div class="chat__welcome-title" style="position:relative;z-index:1">你好，我是岛管理员</div>
        <div class="chat__welcome-desc" style="position:relative;z-index:1">
          告诉我你想建造什么工作区，或者问我任何问题。<br>
          比如："帮我建一个读书笔记工作区"<br>
          <small style="color:var(--text-muted);margin-top:8px;display:block">
            💡 单击左侧资源查看说明 · 双击工作区打开
          </small>
        </div>
      </div>
    `;
  },

  _removeWelcome() {
    const welcome = document.getElementById('chat-welcome');
    if (welcome) welcome.remove();
  },

  // === 打字指示器 ===
  _showTyping() {
    const container = document.getElementById('chat-messages');
    const typing = document.createElement('div');
    typing.id = 'typing-indicator';
    typing.className = 'message message--assistant';
    typing.innerHTML = `
      <div class="message__avatar">
        <img src="/img/librarian.svg" alt="岛管理员" style="width:28px;height:28px;image-rendering:pixelated" class="librarian-avatar">
      </div>
      <div class="typing-indicator">
        <div class="typing-indicator__dot"></div>
        <div class="typing-indicator__dot"></div>
        <div class="typing-indicator__dot"></div>
      </div>
    `;
    container.appendChild(typing);
    this._scrollToBottom();
  },

  _hideTyping() {
    const typing = document.getElementById('typing-indicator');
    if (typing) typing.remove();
  },

  // === 工具方法 ===
  _scrollToBottom() {
    const container = document.getElementById('chat-messages');
    container.scrollTop = container.scrollHeight;
  },

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },

  // === 防抖提示 ===
  _showBatchHint() {
    this._removeBatchHint();
    const container = document.getElementById('chat-messages');
    const hint = document.createElement('div');
    hint.id = 'batch-hint';
    hint.className = 'batch-hint';
    hint.innerHTML = `
      <span>⏳ 等待更多输入...</span>
      <button class="batch-hint__send" onclick="Chat._flushNow()">立即发送</button>
    `;
    container.appendChild(hint);
    this._scrollToBottom();
  },

  _removeBatchHint() {
    const hint = document.getElementById('batch-hint');
    if (hint) hint.remove();
  },

  // === 撤回消息 ===
  async _handleUndo(btnEl) {
    if (!this.conversationId) return;
    if (this.isTyping) return; // 正在生成时不允许撤回

    try {
      const res = await fetch(`/api/conversations/${this.conversationId}/undo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ n: 1 }),
      });
      if (!res.ok) return;

      const data = await res.json();

      // 从 DOM 中移除最后一轮消息（从按钮所在的 user 消息开始，往后全部移除）
      const msgEl = btnEl.closest('.message');
      const container = document.getElementById('chat-messages');
      let node = msgEl;
      while (node) {
        const next = node.nextElementSibling;
        container.removeChild(node);
        node = next;
      }

      // 从内存消息数组中也移除（找到最后一个 user 并删到末尾）
      const lastUserIdx = this.messages.findLastIndex(m => m.role === 'user');
      if (lastUserIdx >= 0) {
        this.messages.splice(lastUserIdx);
      }

      // 回填到输入框
      if (data.prefill) {
        const textarea = document.getElementById('chat-input');
        textarea.value = data.prefill;
        textarea.focus();
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
      }

      // 如果没有消息了，显示欢迎
      if (container.children.length === 0) {
        this._showWelcome();
      }

      Panel.addLog('info', `↩ 已撤回 ${data.undone} 条消息`);
    } catch (e) {
      Panel.addLog('error', `撤回失败: ${e.message}`);
    }
  },

  _cleanDSML(text) {
    // 过滤 DeepSeek DSML 工具调用标记泄露
    return text
      .replace(/<[/]?\s*[|｜]\s*[|｜]?\s*DSML\s*[|｜]\s*[|｜]?[^>]*>/gi, '')
      .replace(/[|｜]\s*[|｜]?\s*tool_calls\s*>/gi, '')
      .replace(/[|｜]\s*[|｜]?\s*invoke[^>]*>/gi, '')
      .replace(/[|｜]\s*[|｜]?\s*parameter[^>]*>/gi, '')
      .replace(/\n{3,}/g, '\n\n')
      .trim();
  }
};


// === README 展示 ===
const ReadmeViewer = {
  show(content, title, workspaceId) {
    Chat.showingReadme = true;
    const container = document.getElementById('chat-messages');
    const form = document.getElementById('chat-form');
    form.style.display = 'none';

    const openBtn = workspaceId
      ? `<button onclick="ReadmeViewer.openWorkspace('${workspaceId}')" style="padding:6px 14px;background:var(--success);color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:0.85rem">▶ 打开工作区</button>`
      : '';

    const deleteBtn = workspaceId
      ? `<button onclick="ReadmeViewer.hideWorkspace('${workspaceId}')" style="padding:6px 14px;background:transparent;color:var(--error);border:1px solid var(--error);border-radius:8px;cursor:pointer;font-size:0.8rem">🗑 隐藏工作区</button>`
      : '';

    const html = this._renderMarkdown(content);
    container.innerHTML = `
      <div style="padding:20px;overflow-y:auto;height:100%;display:flex;flex-direction:column">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <button onclick="ReadmeViewer.hide()" style="padding:6px 14px;background:var(--accent);color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:0.85rem">← 返回聊天</button>
          ${openBtn}
        </div>
        <div class="readme-content" style="line-height:1.8;color:var(--text-secondary);flex:1">${html}</div>
        ${workspaceId ? `<div style="padding-top:16px;border-top:1px solid var(--border-color);margin-top:16px;text-align:right">${deleteBtn}</div>` : ''}
      </div>
    `;
  },

  async openWorkspace(id) {
    App.showToast('正在启动...');
    try {
      // 检查是否是 lightweight 模式
      const wsRes = await fetch(`/api/workspaces`);
      const wsData = await wsRes.json();
      const ws = wsData.workspaces.find(w => w.id === id);
      if (ws && ws.mode === 'lightweight') {
        window.open(`/ws/${id}`, '_blank');
        return;
      }

      const res = await fetch(`/api/workspaces/${id}/start`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        window.open(`http://localhost:${data.workspace.port}`, '_blank');
      } else {
        App.showToast('启动失败');
      }
    } catch (e) {
      App.showToast('启动失败: ' + e.message);
    }
  },

  async hideWorkspace(id) {
    if (!confirm('隐藏此工作区？\n\n隐藏后可在设置中恢复，文件不会删除。')) return;
    try {
      await fetch(`/api/workspaces/${id}/hide`, { method: 'POST' });
      ReadmeViewer.hide();
      Sidebar.loadWorkspaces();
      Panel.addLog('info', '工作区已隐藏');
    } catch (e) {
      App.showToast('操作失败');
    }
  },

  hide() {
    Chat.showingReadme = false;
    const form = document.getElementById('chat-form');
    form.style.display = 'flex';
    Chat._showWelcome();
  },

  _renderMarkdown(md) {
    return md
      .replace(/^### (.+)$/gm, '<h4 style="margin:16px 0 8px;color:var(--text-primary)">$1</h4>')
      .replace(/^## (.+)$/gm, '<h3 style="margin:20px 0 10px;color:var(--text-primary)">$1</h3>')
      .replace(/^# (.+)$/gm, '<h2 style="margin:24px 0 12px;color:var(--text-primary)">$1</h2>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code style="background:var(--bg-tertiary);padding:2px 6px;border-radius:4px;font-size:0.85em">$1</code>')
      .replace(/^- \[x\] (.+)$/gm, '<div style="padding:3px 0">✅ $1</div>')
      .replace(/^- \[ \] (.+)$/gm, '<div style="padding:3px 0">⬜ $1</div>')
      .replace(/^- (.+)$/gm, '<div style="padding:3px 0;padding-left:12px">• $1</div>')
      .replace(/^> (.+)$/gm, '<blockquote style="border-left:3px solid var(--accent);padding-left:12px;color:var(--text-muted);margin:8px 0">$1</blockquote>')
      .replace(/\n\n/g, '<br><br>')
      .replace(/\n/g, '<br>');
  },
};
