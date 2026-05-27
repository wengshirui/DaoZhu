/**
 * app.js — 主入口：初始化 + 主题切换 + 全局错误处理
 */

const App = {
  init() {
    this._initTheme();
    this._bindThemeToggle();
    this._initModules();
    this._updateStatus();
  },

  // === 模块初始化 ===
  _initModules() {
    try {
      Sidebar.init();
      Chat.init();
      Panel.init();
      Panel.addLog('success', '所有模块初始化完成');
    } catch (err) {
      console.error('初始化失败:', err);
      this.showToast('页面初始化失败，请刷新重试');
      Panel.addLog('error', `初始化失败: ${err.message}`);
    }
  },

  // === 主题 ===
  _initTheme() {
    const saved = localStorage.getItem('daozhu-theme') || 'light';
    document.documentElement.setAttribute('data-theme', saved);
    // 恢复聊天背景
    const chatBg = localStorage.getItem('daozhu-chatbg') || '';
    if (chatBg) {
      document.querySelector('.chat')?.setAttribute('data-bg', chatBg);
    }
  },

  _bindThemeToggle() {
    const btn = document.getElementById('btn-theme');
    btn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('daozhu-theme', next);
      Panel.addLog('info', `主题切换为: ${next === 'dark' ? '暗色' : '亮色'}`);
    });

    // 设置按钮 → 打开设置面板
    const settingsBtn = document.getElementById('btn-settings');
    settingsBtn.addEventListener('click', () => this._showSettings());
  },

  // === 设置面板 ===
  async _showSettings() {
    const container = document.getElementById('chat-messages');
    const form = document.getElementById('chat-form');
    form.style.display = 'none';
    Chat.showingReadme = true;

    // 读取当前配置
    let config = {};
    try {
      const res = await fetch('/api/config');
      config = (await res.json()).config || {};
    } catch (e) {}

    container.innerHTML = `
      <div style="padding:24px;overflow-y:auto;height:100%">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
          <h2 style="font-size:1.2rem">⚙️ 设置</h2>
          <button onclick="ReadmeViewer.hide()" style="padding:6px 14px;background:var(--accent);color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:0.85rem">← 返回</button>
        </div>

        <div style="display:flex;flex-direction:column;gap:16px;max-width:400px">
          <div>
            <label style="font-size:0.85rem;color:var(--text-secondary);display:block;margin-bottom:4px">🏝️ 岛屿名称</label>
            <input type="text" id="settings-island-name" placeholder="我的小岛"
              style="width:100%;padding:10px 12px;border:1.5px solid var(--border-color);border-radius:8px;font:inherit;background:var(--bg-primary)">
          </div>

          <div>
            <label style="font-size:0.85rem;color:var(--text-secondary);display:block;margin-bottom:4px">🧠 AI 模型提供商</label>
            <select id="settings-provider" onchange="App._onProviderChange()"
              style="width:100%;padding:10px 12px;border:1.5px solid var(--border-color);border-radius:8px;font:inherit;background:var(--bg-primary)">
              <option value="deepseek">DeepSeek（推荐）</option>
              <option value="zhipu">智谱 AI (GLM-4)</option>
              <option value="ollama">Ollama（本地离线）</option>
              <option value="openai">OpenAI</option>
            </select>
          </div>

          <div id="key-section-deepseek">
            <label style="font-size:0.85rem;color:var(--text-secondary);display:block;margin-bottom:4px">🔑 DeepSeek API Key <span id="status-apikey" style="font-size:0.75rem"></span></label>
            <input type="password" id="settings-apikey" placeholder="sk-xxxxxxxx"
              style="width:100%;padding:10px 12px;border:1.5px solid var(--border-color);border-radius:8px;font:inherit;background:var(--bg-primary)">
          </div>

          <div id="key-section-zhipu" style="display:none">
            <label style="font-size:0.85rem;color:var(--text-secondary);display:block;margin-bottom:4px">🔑 智谱 API Key <span id="status-zhipu" style="font-size:0.75rem"></span></label>
            <input type="password" id="settings-zhipu-key" placeholder="xxxxxxxx.xxxxxxxx"
              style="width:100%;padding:10px 12px;border:1.5px solid var(--border-color);border-radius:8px;font:inherit;background:var(--bg-primary)">
            <small style="color:var(--text-muted);font-size:0.7rem">从 open.bigmodel.cn 获取</small>
          </div>

          <div id="key-section-ollama" style="display:none">
            <label style="font-size:0.85rem;color:var(--text-secondary);display:block;margin-bottom:4px">🖥️ Ollama 地址</label>
            <input type="text" id="settings-ollama-url" placeholder="http://localhost:11434"
              style="width:100%;padding:10px 12px;border:1.5px solid var(--border-color);border-radius:8px;font:inherit;background:var(--bg-primary)">
            <small style="color:var(--text-muted);font-size:0.7rem">无需 API Key，完全离线运行</small>
          </div>

          <div id="key-section-openai" style="display:none">
            <label style="font-size:0.85rem;color:var(--text-secondary);display:block;margin-bottom:4px">🔑 OpenAI API Key</label>
            <input type="password" id="settings-openai-key" placeholder="sk-xxxxxxxx"
              style="width:100%;padding:10px 12px;border:1.5px solid var(--border-color);border-radius:8px;font:inherit;background:var(--bg-primary)">
          </div>

          <div>
            <label style="font-size:0.85rem;color:var(--text-secondary);display:block;margin-bottom:4px">🔗 Gitee Token（论坛发帖用）<span id="status-gitee" style="font-size:0.75rem"></span></label>
            <input type="password" id="settings-gitee" placeholder="xxxxxxxx" value=""
              style="width:100%;padding:10px 12px;border:1.5px solid var(--border-color);border-radius:8px;font:inherit;background:var(--bg-primary)">
          </div>

          <div>
            <label style="font-size:0.85rem;color:var(--text-secondary);display:block;margin-bottom:4px">🎨 主题</label>
            <select id="settings-theme" style="width:100%;padding:10px 12px;border:1.5px solid var(--border-color);border-radius:8px;font:inherit;background:var(--bg-primary)">
              <option value="light">☀️ 亮色</option>
              <option value="dark">🌙 暗色</option>
            </select>
          </div>

          <div>
            <label style="font-size:0.85rem;color:var(--text-secondary);display:block;margin-bottom:4px">🖼️ 聊天背景</label>
            <select id="settings-chatbg" style="width:100%;padding:10px 12px;border:1.5px solid var(--border-color);border-radius:8px;font:inherit;background:var(--bg-primary)">
              <option value="">无背景</option>
              <option value="vacation">🏝️ 度假海岛</option>
              <option value="work">📚 书架</option>
            </select>
          </div>

          <button onclick="App._saveSettings()" style="padding:10px 20px;background:var(--accent);color:#fff;border:none;border-radius:8px;cursor:pointer;font:inherit;font-weight:500;margin-top:8px">
            保存设置
          </button>
          <div id="settings-status" style="font-size:0.85rem;min-height:20px"></div>
        </div>
      </div>
    `;

    // 填充当前主题
    document.getElementById('settings-theme').value =
      document.documentElement.getAttribute('data-theme') || 'light';

    // 填充当前 provider
    const currentProvider = config?.ai?.provider || 'deepseek';
    document.getElementById('settings-provider').value = currentProvider;
    App._onProviderChange();

    // 填充当前岛名
    fetch('/api/config').then(r => r.json()).then(data => {
      const name = data.config?.island_name;
      if (name) document.getElementById('settings-island-name').value = name;
    }).catch(() => {});

    // 显示配置状态
    fetch('/api/config/secrets-status').then(r => r.json()).then(data => {
      const apiEl = document.getElementById('status-apikey');
      const giteeEl = document.getElementById('status-gitee');
      if (apiEl) apiEl.innerHTML = data.deepseek ? '<span style="color:var(--success)">✓ 已配置</span>' : '<span style="color:var(--error)">✗ 未配置</span>';
      if (giteeEl) giteeEl.innerHTML = data.gitee ? '<span style="color:var(--success)">✓ 已配置</span>' : '<span style="color:var(--error)">✗ 未配置</span>';
    }).catch(() => {});
  },

  _onProviderChange() {
    const provider = document.getElementById('settings-provider')?.value || 'deepseek';
    const sections = ['deepseek', 'zhipu', 'ollama', 'openai'];
    sections.forEach(s => {
      const el = document.getElementById(`key-section-${s}`);
      if (el) el.style.display = s === provider ? 'block' : 'none';
    });
  },

  async _saveSettings() {
    const status = document.getElementById('settings-status');
    const provider = document.getElementById('settings-provider').value;
    const apiKey = document.getElementById('settings-apikey').value.trim();
    const zhipuKey = document.getElementById('settings-zhipu-key')?.value.trim() || '';
    const ollamaUrl = document.getElementById('settings-ollama-url')?.value.trim() || '';
    const openaiKey = document.getElementById('settings-openai-key')?.value.trim() || '';
    const giteeToken = document.getElementById('settings-gitee').value.trim();
    const theme = document.getElementById('settings-theme').value;
    const islandName = document.getElementById('settings-island-name').value.trim();

    try {
      // 保存 provider
      await fetch('/api/config/ai.provider', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value: provider }),
      });

      // 保存岛名
      if (islandName) {
        await fetch('/api/config/island_name', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ value: islandName }),
        });
        document.querySelector('.topbar__title').textContent = islandName;
      }

      // 保存 DeepSeek API Key
      if (apiKey) {
        await fetch('/api/onboarding/save-key', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key: apiKey }),
        });
      }

      // 保存智谱 API Key
      if (zhipuKey) {
        await fetch('/api/onboarding/save-secret', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: 'ZHIPU_API_KEY', value: zhipuKey }),
        });
      }

      // 保存 Ollama URL
      if (ollamaUrl) {
        await fetch('/api/config/ai.base_url', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ value: ollamaUrl + '/v1' }),
        });
      }

      // 保存 OpenAI Key
      if (openaiKey) {
        await fetch('/api/onboarding/save-secret', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: 'OPENAI_API_KEY', value: openaiKey }),
        });
      }

      // 保存 Gitee Token
      if (giteeToken) {
        await fetch('/api/onboarding/save-gitee-token', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: giteeToken }),
        });
      }

      // 保存主题
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('daozhu-theme', theme);

      // 保存聊天背景
      const chatBg = document.getElementById('settings-chatbg').value;
      document.querySelector('.chat').setAttribute('data-bg', chatBg);
      localStorage.setItem('daozhu-chatbg', chatBg);

      status.textContent = '✅ 设置已保存';
      status.style.color = 'var(--success)';
    } catch (e) {
      status.textContent = '❌ 保存失败: ' + e.message;
      status.style.color = 'var(--error)';
    }
  },

  // === 状态栏 ===
  _updateStatus() {
    const info = document.getElementById('status-info');
    API.getWorkspaces().then(workspaces => {
      const running = workspaces.filter(w => w.status === 'running').length;
      info.textContent = `${workspaces.length} 个工作区 | ${running} 个运行中`;
    }).catch(() => {
      info.textContent = '状态获取失败';
    });

    // 加载岛名到顶栏
    fetch('/api/config').then(r => r.json()).then(data => {
      const name = data.config?.island_name;
      if (name) {
        document.querySelector('.topbar__title').textContent = name;
      }
    }).catch(() => {});
  },

  // === 全局错误提示 ===
  showToast(message, duration = 3000) {
    let toast = document.querySelector('.error-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.className = 'error-toast';
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add('visible');

    setTimeout(() => {
      toast.classList.remove('visible');
    }, duration);
  }
};

// === 启动 ===
document.addEventListener('DOMContentLoaded', () => {
  App.init();
});

// === 全局错误捕获 ===
window.addEventListener('unhandledrejection', (e) => {
  console.error('Unhandled rejection:', e.reason);
  App.showToast('操作失败: ' + (e.reason?.message || '未知错误'));
});


// === 游戏化：发现的快乐 ===
const Fun = {
  titleClickCount: 0,
  idleTimer: null,
  IDLE_TIMEOUT: 30000, // 30秒

  init() {
    this._setTimeAmbience();
    this._bindTitleEasterEgg();
    this._startIdleDetection();
    // 每小时更新时间氛围
    setInterval(() => this._setTimeAmbience(), 3600000);
  },

  // 时间氛围：根据当前时间微调背景
  _setTimeAmbience() {
    const hour = new Date().getHours();
    let time = 'afternoon';
    if (hour >= 5 && hour < 10) time = 'morning';
    else if (hour >= 10 && hour < 17) time = 'afternoon';
    else if (hour >= 17 && hour < 21) time = 'evening';
    else time = 'night';
    document.documentElement.setAttribute('data-time', time);
  },

  // 彩蛋：连续点击标题5次 → 管理员跳舞
  _bindTitleEasterEgg() {
    const title = document.querySelector('.topbar__title');
    if (!title) return;
    let lastClick = 0;
    title.addEventListener('click', () => {
      const now = Date.now();
      if (now - lastClick > 1000) this.titleClickCount = 0;
      lastClick = now;
      this.titleClickCount++;
      if (this.titleClickCount >= 5) {
        this.titleClickCount = 0;
        this._triggerDance();
      }
    });
  },

  _triggerDance() {
    // 所有管理员跳舞
    document.querySelectorAll('.librarian').forEach(el => {
      el.className = el.className.replace(/librarian--\w+/g, '').trim() + ' librarian--dance';
    });
    // 3秒后恢复
    setTimeout(() => {
      document.querySelectorAll('.librarian--dance').forEach(el => {
        el.className = el.className.replace('librarian--dance', 'librarian--idle').trim();
      });
    }, 3000);
    Panel.addLog('success', '🎉 管理员开心地跳了一支舞！');
  },

  // 空闲检测：30秒无操作 → 管理员看书
  _startIdleDetection() {
    const resetIdle = () => {
      // 恢复为 idle
      document.querySelectorAll('.librarian--reading').forEach(el => {
        el.className = el.className.replace('librarian--reading', 'librarian--idle');
      });
      clearTimeout(this.idleTimer);
      this.idleTimer = setTimeout(() => this._goReading(), this.IDLE_TIMEOUT);
    };

    ['mousemove', 'keydown', 'click', 'scroll'].forEach(evt => {
      document.addEventListener(evt, resetIdle, { passive: true });
    });

    // 初始启动
    this.idleTimer = setTimeout(() => this._goReading(), this.IDLE_TIMEOUT);
  },

  _goReading() {
    document.querySelectorAll('.librarian--idle').forEach(el => {
      el.className = el.className.replace('librarian--idle', 'librarian--reading');
    });
  },

  // 撒花庆祝（创建工作区时调用）
  celebrate() {
    const container = document.createElement('div');
    container.className = 'confetti-container';
    document.body.appendChild(container);

    const colors = ['#ff6b6b', '#ffd93d', '#6bcb77', '#4d96ff', '#ff8fab', '#a855f7'];
    for (let i = 0; i < 40; i++) {
      const confetti = document.createElement('div');
      confetti.className = 'confetti';
      confetti.style.left = Math.random() * 100 + '%';
      confetti.style.background = colors[Math.floor(Math.random() * colors.length)];
      confetti.style.animationDelay = Math.random() * 0.8 + 's';
      confetti.style.borderRadius = Math.random() > 0.5 ? '50%' : '2px';
      container.appendChild(confetti);
    }

    // 管理员庆祝
    document.querySelectorAll('.librarian').forEach(el => {
      el.className = el.className.replace(/librarian--\w+/g, '').trim() + ' librarian--celebrate';
    });

    setTimeout(() => {
      container.remove();
      document.querySelectorAll('.librarian--celebrate').forEach(el => {
        el.className = el.className.replace('librarian--celebrate', 'librarian--idle');
      });
    }, 3000);
  },
};

// 初始化游戏化
document.addEventListener('DOMContentLoaded', () => Fun.init());
