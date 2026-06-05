/**
 * chat.js — 聊天核心：消息渲染 + 输入发送 + 流处理
 * 文件上传逻辑在 chat-upload.js
 * ReadmeViewer 在 chat-readme.js
 */

const Chat = {
  messages: [],
  isTyping: false,
  conversationId: null,
  showingReadme: false,
  _debounceTimer: null,
  _pendingMessages: [],
  _debounceMs: 2000,

  init() {
    this._bindForm();
    this._bindTextarea();
    this._bindFileUpload();
    this._showWelcome();
    this._loadGreeting();
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
    const text = textarea.value.trim();

    if (this.isTyping) { this._stopGeneration(); return; }
    if (!text && !this._uploadedFiles.length) return;

    textarea.value = '';
    textarea.style.height = 'auto';
    this._removeWelcome();

    // 构建完整消息（用户文字 + 文件内容）
    let fullMessage = text;
    if (this._uploadedFiles && this._uploadedFiles.length > 0) {
      const fileSection = this._uploadedFiles.map(f =>
        `[文件: ${f.name}]\n${f.content}`
      ).join('\n\n');
      fullMessage = text
        ? `${text}\n\n---\n附件内容：\n${fileSection}`
        : `我上传了以下文件，请帮我处理：\n\n${fileSection}`;
      this._uploadedFiles = [];
      this._renderFileChips();
    }

    this._pendingMessages.push(fullMessage);
    this._addMessage('user', text || '📎 已上传文件');

    if (this._pendingMessages.length > 1) this._showBatchHint();

    if (this._debounceTimer) clearTimeout(this._debounceTimer);
    this._debounceTimer = setTimeout(() => this._flushPendingMessages(), this._debounceMs);
  },

  _flushNow() {
    if (this._debounceTimer) { clearTimeout(this._debounceTimer); this._debounceTimer = null; }
    this._flushPendingMessages();
  },

  // === 合并发送 + 流处理 ===
  async _flushPendingMessages() {
    this._debounceTimer = null;
    this._removeBatchHint();
    if (this._pendingMessages.length === 0) return;

    const combinedText = this._pendingMessages.join('\n');
    this._pendingMessages = [];
    const sendBtn = document.querySelector('.chat__send');

    sendBtn.textContent = '⏹ 停止';
    sendBtn.classList.add('chat__send--stop');
    this.isTyping = true;
    this._abortController = new AbortController();
    this._showTyping();

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: combinedText, conversation_id: this.conversationId || null }),
        signal: this._abortController.signal,
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let msgEl = null, bubble = null, fullText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value);
        for (const line of text.split('\n')) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.tool) { this._handleToolStart(data); continue; }
            if (data.tool_done) { this._handleToolDone(data); continue; }
            if (data.chunk) {
              this._hideTyping();
              this._closeToolPanel();
              if (!msgEl) { msgEl = this._addMessageElement('assistant', ''); bubble = msgEl.querySelector('.message__bubble'); this._streamStartTime = Date.now(); }
              fullText += data.chunk;
              bubble.textContent = this._cleanDSML(fullText);
              this._scrollToBottom();
            }
            if (data.usage) this._lastUsage = data.usage;
            if (data.conversation_id) this.conversationId = data.conversation_id;
          } catch (e) {}
        }
      }

      this.messages.push({ role: 'assistant', content: fullText });
      this._renderUsageStats(msgEl);
      Panel.addLog('info', `管理员回复: ${fullText.substring(0, 30)}...`);

    } catch (err) {
      if (err.name === 'AbortError') { this._addMessage('assistant', '（已停止）'); }
      else { this._addMessage('assistant', `抱歉，出了点问题：${err.message}`); Panel.addLog('error', `发送失败: ${err.message}`); }
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

  _stopGeneration() { if (this._abortController) this._abortController.abort(); },

  // === 工具面板处理 ===
  _handleToolStart(data) {
    this._hideTyping();
    const container = document.getElementById('chat-messages');
    if (!this._toolPanel) {
      const wrapper = document.createElement('div');
      wrapper.className = 'message message--assistant message--tool';
      wrapper.innerHTML = `<div class="message__avatar"><img src="/img/librarian.svg" alt="岛管理员" style="width:28px;height:28px;image-rendering:pixelated" class="librarian-avatar"></div><div class="tool-panel"><div class="tool-panel__header"><span class="tool-panel__indicator"></span><span class="tool-panel__title">⚡ 执行中</span><span class="tool-panel__count">0 步</span></div><div class="tool-panel__body"></div></div>`;
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
  },

  _handleToolDone(data) {
    if (this._lastToolStep) {
      const iconEl = this._lastToolStep.querySelector('.tool-panel__step-icon');
      const statusEl = this._lastToolStep.querySelector('.tool-panel__step-status');
      if (data.status === 'ok') { iconEl.textContent = '✅'; statusEl.textContent = '完成'; this._lastToolStep.className = 'tool-panel__step tool-panel__step--done'; }
      else { iconEl.textContent = '❌'; statusEl.textContent = (data.error || '失败').slice(0, 30); this._lastToolStep.className = 'tool-panel__step tool-panel__step--error'; }
    }
    const icon = data.status === 'ok' ? '✅' : '❌';
    Panel.addLog(data.status === 'ok' ? 'success' : 'error', `${icon} ${data.tool_done} ${data.error || '完成'}`);
  },

  _closeToolPanel() {
    if (this._toolPanel) {
      this._toolPanel.querySelector('.tool-panel__title').textContent = `✅ 完成 (${this._toolStepCount} 步)`;
      this._toolPanel.querySelector('.tool-panel__indicator').classList.add('tool-panel__indicator--done');
      this._toolPanel = null;
      this._toolStepCount = 0;
    }
  },

  // === Token 统计渲染 ===
  _renderUsageStats(msgEl) {
    if (!this._lastUsage || !msgEl) { this._lastUsage = null; return; }
    const u = this._lastUsage;
    const elapsed = (Date.now() - (this._streamStartTime || Date.now())) / 1000;
    const speed = elapsed > 0 && u.completion_tokens ? Math.round(u.completion_tokens / elapsed) : 0;
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
    this._lastUsage = null;
    this._streamStartTime = null;
  },

  // === 消息渲染 ===
  _addMessage(role, content) {
    this._addMessageElement(role, content);
    this.messages.push({ role, content });
    this._scrollToBottom();
  },

  _addMessageElement(role, content) {
    const container = document.getElementById('chat-messages');
    const avatar = role === 'user'
      ? '<div class="avatar-user">我</div>'
      : '<img src="/img/librarian.svg" alt="岛管理员" style="width:28px;height:28px;image-rendering:pixelated" class="librarian-avatar">';
    const undoBtn = role === 'user' ? '<button class="message__undo" onclick="Chat._handleUndo(this)" title="撤回">↩</button>' : '';
    const msgEl = document.createElement('div');
    msgEl.className = `message message--${role}`;
    msgEl.innerHTML = `<div class="message__avatar">${avatar}</div><div class="message__content"><div class="message__bubble">${this._escapeHtml(content)}</div>${undoBtn}</div>`;
    container.appendChild(msgEl);
    this._scrollToBottom();
    return msgEl;
  },

  // === 欢迎 + 问候 ===
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
        <div class="chat__welcome-desc" style="position:relative;z-index:1">告诉我你想建造什么工作区，或者问我任何问题。<br>比如："帮我建一个读书笔记工作区"<br><small style="color:var(--text-muted);margin-top:8px;display:block">💡 单击左侧资源查看说明 · 双击工作区打开</small></div>
      </div>`;
  },

  _removeWelcome() {
    const welcome = document.getElementById('chat-welcome');
    if (welcome) welcome.remove();
    const greeting = document.getElementById('greeting-message');
    if (greeting) greeting.remove();
  },

  async _loadGreeting(conversationId) {
    try {
      const params = conversationId ? `?conversation_id=${conversationId}` : '';
      const res = await fetch(`/api/greeting${params}`);
      if (!res.ok) return;
      const data = await res.json();
      if (!data.greeting) return;
      const container = document.getElementById('chat-messages');
      const existing = document.getElementById('greeting-message');
      if (existing) existing.remove();
      const greetingEl = document.createElement('div');
      greetingEl.id = 'greeting-message';
      greetingEl.className = 'message message--assistant message--greeting';
      greetingEl.innerHTML = `<div class="message__avatar"><img src="/img/librarian.svg" alt="岛管理员" style="width:28px;height:28px;image-rendering:pixelated" class="librarian-avatar"></div><div class="message__content"><div class="message__bubble message__bubble--greeting">${this._escapeHtml(data.greeting)}</div></div>`;
      container.appendChild(greetingEl);
      this._scrollToBottom();
    } catch (e) {}
  },

  // === 打字指示器 ===
  _showTyping() {
    const container = document.getElementById('chat-messages');
    const typing = document.createElement('div');
    typing.id = 'typing-indicator';
    typing.className = 'message message--assistant';
    typing.innerHTML = `<div class="message__avatar"><img src="/img/librarian.svg" alt="岛管理员" style="width:28px;height:28px;image-rendering:pixelated" class="librarian-avatar"></div><div class="typing-indicator"><div class="typing-indicator__dot"></div><div class="typing-indicator__dot"></div><div class="typing-indicator__dot"></div></div>`;
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

  _cleanDSML(text) {
    return text
      .replace(/<[/]?\s*[|｜]\s*[|｜]?\s*DSML\s*[|｜]\s*[|｜]?[^>]*>/gi, '')
      .replace(/[|｜]\s*[|｜]?\s*tool_calls\s*>/gi, '')
      .replace(/[|｜]\s*[|｜]?\s*invoke[^>]*>/gi, '')
      .replace(/[|｜]\s*[|｜]?\s*parameter[^>]*>/gi, '')
      .replace(/\n{3,}/g, '\n\n')
      .trim();
  },

  // === 防抖提示 ===
  _showBatchHint() {
    this._removeBatchHint();
    const container = document.getElementById('chat-messages');
    const hint = document.createElement('div');
    hint.id = 'batch-hint';
    hint.className = 'batch-hint';
    hint.innerHTML = `<span>⏳ 等待更多输入...</span><button class="batch-hint__send" onclick="Chat._flushNow()">立即发送</button>`;
    container.appendChild(hint);
    this._scrollToBottom();
  },

  _removeBatchHint() {
    const hint = document.getElementById('batch-hint');
    if (hint) hint.remove();
  },

  // === 撤回 ===
  async _handleUndo(btnEl) {
    if (!this.conversationId || this.isTyping) return;
    try {
      const res = await fetch(`/api/conversations/${this.conversationId}/undo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ n: 1 }),
      });
      if (!res.ok) return;
      const data = await res.json();
      const msgEl = btnEl.closest('.message');
      const container = document.getElementById('chat-messages');
      let node = msgEl;
      while (node) { const next = node.nextElementSibling; container.removeChild(node); node = next; }
      const lastUserIdx = this.messages.findLastIndex(m => m.role === 'user');
      if (lastUserIdx >= 0) this.messages.splice(lastUserIdx);
      if (data.prefill) {
        const textarea = document.getElementById('chat-input');
        textarea.value = data.prefill;
        textarea.focus();
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
      }
      if (container.children.length === 0) this._showWelcome();
      Panel.addLog('info', `↩ 已撤回 ${data.undone} 条消息`);
    } catch (e) {
      Panel.addLog('error', `撤回失败: ${e.message}`);
    }
  },
};
