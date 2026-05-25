/**
 * panel.js — 右侧面板：历史对话 + 输出日志
 */

const Panel = {
  currentTab: 'history',
  logs: [],

  init() {
    this._bindTabs();
    this._bindToggle();
    this.loadHistory();
    this._addInitLogs();
  },

  // === Tab 切换 ===
  _bindTabs() {
    const tabs = document.querySelectorAll('.infopanel__tabs .tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        this._switchTab(tab.dataset.tab);
      });
    });
  },

  _switchTab(tabName) {
    this.currentTab = tabName;

    document.querySelectorAll('.infopanel__tabs .tab').forEach(t => {
      const isActive = t.dataset.tab === tabName;
      t.classList.toggle('active', isActive);
      t.setAttribute('aria-selected', isActive);
    });

    document.querySelectorAll('.infopanel__content .tab-panel').forEach(p => {
      p.classList.toggle('active', p.id === `panel-${tabName}`);
    });
  },

  // === 折叠/展开 ===
  _bindToggle() {
    const toggle = document.getElementById('infopanel-toggle');
    const panel = document.getElementById('infopanel');

    toggle.addEventListener('click', () => {
      panel.classList.toggle('collapsed');
      toggle.textContent = panel.classList.contains('collapsed') ? '◀' : '▶';
    });
  },

  // === 历史对话 ===
  async loadHistory() {
    const container = document.getElementById('history-list');
    try {
      const conversations = await API.getConversations();
      if (conversations.length === 0) {
        container.innerHTML = `
          <div class="empty-state">
            <div class="empty-state__icon">💬</div>
            <div class="empty-state__title">暂无对话</div>
            <div class="empty-state__desc">开始和管家聊天吧</div>
          </div>
        `;
        return;
      }
      container.innerHTML = conversations.map(c => this._renderHistoryItem(c)).join('');
    } catch (err) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state__icon">⚠️</div>
          <div class="empty-state__title">加载失败</div>
          <div class="empty-state__desc">${err.message}</div>
        </div>
      `;
    }
  },

  _renderHistoryItem(conv) {
    const time = this._formatTime(conv.updated_at);
    return `
      <div class="history-item" data-id="${conv.id}">
        <span class="history-item__icon">💬</span>
        <div class="history-item__body">
          <div class="history-item__title">${conv.title}</div>
          <div class="history-item__time">${time}</div>
        </div>
      </div>
    `;
  },

  _formatTime(isoStr) {
    const date = new Date(isoStr);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return '今天';
    if (diffDays === 1) return '昨天';
    if (diffDays < 7) return `${diffDays} 天前`;
    return date.toLocaleDateString('zh-CN');
  },

  // === 输出日志 ===
  _addInitLogs() {
    this.addLog('info', '岛主平台启动中...');
    this.addLog('success', '平台服务已就绪 (端口 7788)');
    this.addLog('info', '加载工作区列表...');
    this.addLog('success', '3 个工作区已加载');
  },

  addLog(level, message) {
    const container = document.getElementById('log-list');
    const time = new Date().toLocaleTimeString('zh-CN', { hour12: false });
    const prefix = { info: 'INFO', success: ' OK ', warning: 'WARN', error: ' ERR' }[level] || 'INFO';

    const entry = document.createElement('div');
    entry.className = `log-entry log-entry--${level}`;
    entry.textContent = `[${time}] [${prefix}] ${message}`;

    container.appendChild(entry);
    this.logs.push({ level, message, time });

    // 自动滚动到底部
    container.scrollTop = container.scrollHeight;
  }
};
