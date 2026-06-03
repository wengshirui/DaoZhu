/**
 * sidebar.js — 左侧面板：Tab 切换 + 列表渲染
 */

const Sidebar = {
  currentTab: 'buildings',

  init() {
    this._bindTabs();
    this._bindToggle();
    this.loadAll();
  },

  // === Tab 切换 ===
  _bindTabs() {
    const tabs = document.querySelectorAll('.sidebar__tabs .tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        this._switchTab(tab.dataset.tab);
      });
    });
  },

  _switchTab(tabName) {
    this.currentTab = tabName;

    // 更新 Tab 状态
    document.querySelectorAll('.sidebar__tabs .tab').forEach(t => {
      const isActive = t.dataset.tab === tabName;
      t.classList.toggle('active', isActive);
      t.setAttribute('aria-selected', isActive);
    });

    // 更新面板显示
    document.querySelectorAll('.sidebar__content .tab-panel').forEach(p => {
      p.classList.toggle('active', p.id === `panel-${tabName}`);
    });
  },

  // === 折叠/展开 ===
  _bindToggle() {
    const toggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');

    toggle.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
      toggle.textContent = sidebar.classList.contains('collapsed') ? '▶' : '◀';
    });
  },

  // === 加载所有数据 ===
  async loadAll() {
    await Promise.all([
      this.loadWorkspaces(),
      this.loadSkills(),
      this.loadTools()
    ]);
    this._bindActionButtons();
  },

  _bindActionButtons() {
    document.querySelectorAll('.card-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const action = btn.dataset.action;
        const id = btn.dataset.id;

        switch (action) {
          case 'preview':
            try { const r = await fetch(`/api/workspaces/${id}/readme`); const d = await r.json(); ReadmeViewer.show(d.content, '', id); } catch(e) { App.showToast('加载失败'); }
            break;
          case 'open':
            const mode = btn.dataset.mode;
            if (mode === 'lightweight') { window.open(`/ws/${id}`, '_blank'); }
            else {
              App.showToast('启动中...');
              try { const r = await fetch(`/api/workspaces/${id}/start`, {method:'POST'}); if(r.ok){const d=await r.json(); window.open(`http://localhost:${d.workspace.port}`,'_blank'); Sidebar.loadWorkspaces();} } catch(e) { App.showToast('失败'); }
            }
            break;
          case 'hide':
            if (confirm('隐藏此工作区？文件不会删除。')) {
              await fetch(`/api/workspaces/${id}/hide`, {method:'POST'});
              Sidebar.loadWorkspaces();
            }
            break;
          case 'preview-skill':
            try { const r = await fetch(`/api/skills/${id}/readme`); const d = await r.json(); ReadmeViewer.show(d.content, ''); } catch(e) { App.showToast('加载失败'); }
            break;
          case 'delete-skill':
            if (confirm(`删除技能 ${id}？`)) {
              await fetch(`/api/skills/${id}`, {method:'DELETE'});
              Sidebar.loadSkills();
              Panel.addLog('info', `技能 ${id} 已删除`);
            }
            break;
          case 'preview-tool':
            const desc = btn.dataset.desc || '暂无说明';
            ReadmeViewer.show(`# 🔧 ${id}\n\n${desc}\n\n此工具由岛管理员自动调用。`, '');
            break;
          case 'disable-tool':
            const isDisabled = btn.textContent.trim() === '✅';
            const endpoint = isDisabled ? 'enable' : 'disable';
            await fetch(`/api/tools/${id}/${endpoint}`, {method:'POST'});
            Sidebar.loadTools();
            break;
        }
      });
    });
  },

  // === 工作区列表 ===
  async loadWorkspaces() {
    const container = document.getElementById('workspace-list');
    try {
      const workspaces = await API.getWorkspaces();
      if (workspaces.length === 0) {
        container.innerHTML = this._renderEmpty('🏗️', '还没有工作区', '告诉管家你想建造什么');
        return;
      }

      // 按 category 分组
      const groups = { user: [], public: [], system: [] };
      for (const w of workspaces) {
        const cat = w.category || 'user';
        if (!groups[cat]) groups[cat] = [];
        groups[cat].push(w);
      }

      // 分组渲染
      const categoryLabels = { user: '🏠 我的工作区', public: '🌐 公开', system: '⚙️ 系统' };
      const categoryOrder = ['user', 'public', 'system'];
      let html = '';

      for (const cat of categoryOrder) {
        const items = groups[cat];
        if (!items || items.length === 0) continue;
        const collapsed = cat === 'system' ? 'collapsed' : '';
        html += `<div class="ws-group ${collapsed}" data-category="${cat}">
          <div class="ws-group__header" onclick="Sidebar._toggleGroup(this)">
            <span class="ws-group__arrow">${collapsed ? '▶' : '▼'}</span>
            <span class="ws-group__label">${categoryLabels[cat]}</span>
            <span class="ws-group__count">${items.length}</span>
          </div>
          <div class="ws-group__body">${items.map(w => this._renderWorkspaceCard(w)).join('')}</div>
        </div>`;
      }

      container.innerHTML = html;

      // 添加"绑定文件夹"按钮
      container.insertAdjacentHTML('beforeend', `
        <div class="card card--add" id="btn-bind-folder">
          <div class="card__icon" style="background:var(--bg-tertiary)">📁</div>
          <div class="card__body">
            <div class="card__name" style="color:var(--text-muted)">+ 绑定本地文件夹</div>
          </div>
        </div>
      `);
      document.getElementById('btn-bind-folder').addEventListener('click', () => this._showBindDialog());
      this._bindWorkspaceClicks(container);
    } catch (err) {
      container.innerHTML = this._renderEmpty('⚠️', '加载失败', err.message);
    }
  },

  _renderWorkspaceCard(workspace) {
    const statusClass = workspace.status === 'running' ? 'badge--running' : 'badge--stopped';
    const statusText = workspace.status === 'running' ? '运行中' : '已停止';

    return `
      <div class="card" data-id="${workspace.id}" data-port="${workspace.port}" data-status="${workspace.status}" data-mode="${workspace.mode || 'standard'}">
        <div class="card__icon" style="background: ${workspace.color}20">
          ${workspace.icon}
        </div>
        <div class="card__body">
          <div class="card__name">${workspace.name}</div>
          <div class="card__desc">${workspace.description}</div>
        </div>
        <div class="card__actions">
          <button class="card-btn" data-action="preview" data-id="${workspace.id}" title="查看说明">📖</button>
          <button class="card-btn card-btn--primary" data-action="open" data-id="${workspace.id}" data-port="${workspace.port}" data-mode="${workspace.mode || 'standard'}" title="打开">▶</button>
          <button class="card-btn card-btn--danger" data-action="hide" data-id="${workspace.id}" title="隐藏">✕</button>
        </div>
      </div>
    `;
  },

  _bindWorkspaceClicks(container) {
    container.querySelectorAll('.card').forEach(card => {
      // 启用拖拽
      card.setAttribute('draggable', 'true');

      card.addEventListener('dragstart', (e) => {
        card.classList.add('card--dragging');
        e.dataTransfer.setData('text/plain', card.dataset.id);
        e.dataTransfer.effectAllowed = 'move';
      });

      card.addEventListener('dragend', () => {
        card.classList.remove('card--dragging');
        container.querySelectorAll('.card--dragover').forEach(c => c.classList.remove('card--dragover'));
      });

      card.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        card.classList.add('card--dragover');
      });

      card.addEventListener('dragleave', () => {
        card.classList.remove('card--dragover');
      });

      card.addEventListener('drop', async (e) => {
        e.preventDefault();
        card.classList.remove('card--dragover');
        const draggedId = e.dataTransfer.getData('text/plain');
        if (draggedId === card.dataset.id) return;

        // 重新排列 DOM
        const draggedEl = container.querySelector(`[data-id="${draggedId}"]`);
        container.insertBefore(draggedEl, card);

        // 收集新顺序并保存
        const order = Array.from(container.querySelectorAll('.card')).map(c => c.dataset.id);
        await fetch('/api/workspaces/reorder', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ order }),
        });
        Panel.addLog('info', '工作区顺序已更新');
      });

      // 单击：直接打开工作区
      card.addEventListener('click', async () => {
        const id = card.dataset.id;
        const mode = card.dataset.mode;
        if (mode === 'bound') {
          // 绑定型工作区：打开文件夹
          try {
            await fetch(`/api/workspaces/${id}/open-folder`, { method: 'POST' });
          } catch(e) { App.showToast('打开失败'); }
        } else if (mode === 'lightweight') {
          window.open(`/ws/${id}`, '_blank');
        } else {
          const status = card.dataset.status;
          const port = card.dataset.port;
          if (status === 'running') {
            window.open(`http://localhost:${port}`, '_blank');
          } else {
            App.showToast('正在启动...');
            try {
              const res = await fetch(`/api/workspaces/${id}/start`, { method: 'POST' });
              if (res.ok) { const d = await res.json(); window.open(`http://localhost:${d.workspace.port}`, '_blank'); Sidebar.loadWorkspaces(); }
            } catch(e) { App.showToast('启动失败'); }
          }
        }
      });

      // 右键：隐藏工作区
      card.addEventListener('contextmenu', async (e) => {
        e.preventDefault();
        const id = card.dataset.id;
        const name = card.querySelector('.card__name').textContent;
        if (confirm(`隐藏「${name}」？\n\n隐藏后可在设置中恢复，文件不会删除。`)) {
          try {
            await fetch(`/api/workspaces/${id}/hide`, { method: 'POST' });
            await Sidebar.loadWorkspaces();
            Panel.addLog('info', `工作区「${name}」已隐藏`);
          } catch (e) {
            App.showToast('隐藏失败');
          }
        }
      });

    });
  },

  // === 技能列表 ===
  async loadSkills() {
    const container = document.getElementById('skill-list');
    try {
      const skills = await API.getSkills();
      if (skills.length === 0) {
        container.innerHTML = this._renderEmpty('📖', '暂无技能', '技能让管家更聪明');
        return;
      }
      container.innerHTML = skills.map(s => this._renderSkillCard(s)).join('');
      this._bindSkillClicks(container);
    } catch (err) {
      container.innerHTML = this._renderEmpty('⚠️', '加载失败', err.message);
    }
  },

  _bindSkillClicks(container) {
    container.querySelectorAll('.card[data-type="skill"]').forEach(card => {
      card.addEventListener('click', async () => {
        const id = card.dataset.id;
        try {
          const res = await fetch(`/api/skills/${id}/readme`);
          const data = await res.json();
          ReadmeViewer.show(data.content, card.querySelector('.card__name').textContent);
        } catch (e) {
          App.showToast('加载技能说明失败');
        }
      });

      // 右键删除技能
      card.addEventListener('contextmenu', async (e) => {
        e.preventDefault();
        const id = card.dataset.id;
        const name = card.querySelector('.card__name').textContent;
        if (confirm(`删除技能「${name}」？\n\n将删除 skills/${id}/ 目录。`)) {
          try {
            await fetch(`/api/skills/${id}`, { method: 'DELETE' });
            await Sidebar.loadSkills();
            Panel.addLog('info', `技能「${name}」已删除`);
          } catch (e) {
            App.showToast('删除失败');
          }
        }
      });
    });
  },

  _renderSkillCard(skill) {
    // 自动赋予图标
    const iconMap = {'create-workspaces':'🏗️','frontend-design':'🎨','create-skill':'⚡','weather':'🌤️','weather-query':'🌤️'};
    const icon = iconMap[skill.id] || '📖';

    return `
      <div class="card" data-id="${skill.id}" data-type="skill">
        <div class="card__icon">${icon}</div>
        <div class="card__body">
          <div class="card__name">${skill.name}</div>
        </div>
        <div class="card__actions">
          <button class="card-btn" data-action="preview-skill" data-id="${skill.id}" title="查看">📖</button>
          <button class="card-btn card-btn--danger" data-action="delete-skill" data-id="${skill.id}" title="删除">✕</button>
        </div>
      </div>
    `;
  },

  // === 工具列表 ===
  async loadTools() {
    const container = document.getElementById('tool-list');
    try {
      const tools = await API.getTools();
      if (tools.length === 0) {
        container.innerHTML = this._renderEmpty('🔧', '暂无工具', '工具连接外部世界');
        return;
      }
      container.innerHTML = tools.map(t => this._renderToolCard(t)).join('');
      this._bindToolClicks(container);
    } catch (err) {
      container.innerHTML = this._renderEmpty('⚠️', '加载失败', err.message);
    }
  },

  _bindToolClicks(container) {
    container.querySelectorAll('.card[data-type="tool"]').forEach(card => {
      card.addEventListener('click', () => {
        const name = card.querySelector('.card__name').textContent;
        const desc = card.dataset.desc || '暂无说明';
        const id = card.dataset.id;
        const content = `# 🔧 ${name}\n\n## 工具 ID\n\n\`${id}\`\n\n## 说明\n\n${desc}\n\n## 使用方式\n\n此工具由岛管理员在对话中自动调用，无需手动操作。`;
        ReadmeViewer.show(content, name, null);
      });
    });
  },

  _renderToolCard(tool) {
    const statusClass = tool.status === 'disabled' ? 'badge--stopped' : 'badge--connected';

    return `
      <div class="card" data-id="${tool.id}" data-type="tool" data-desc="${(tool.description || '').replace(/"/g, '&quot;')}">
        <div class="card__icon">${tool.icon}</div>
        <div class="card__body">
          <div class="card__name">${tool.name}</div>
        </div>
        <div class="card__actions">
          <button class="card-btn" data-action="preview-tool" data-id="${tool.id}" data-desc="${(tool.description || '').replace(/"/g, '&quot;')}" title="查看">📖</button>
          <button class="card-btn" data-action="disable-tool" data-id="${tool.id}" title="${tool.status === 'disabled' ? '启用' : '停用'}">${tool.status === 'disabled' ? '✓' : '⏸'}</button>
        </div>
      </div>
    `;
  },

  // === 工作区分组折叠 ===
  _toggleGroup(headerEl) {
    const group = headerEl.parentElement;
    group.classList.toggle('collapsed');
    const arrow = headerEl.querySelector('.ws-group__arrow');
    arrow.textContent = group.classList.contains('collapsed') ? '▶' : '▼';
  },

  // === 绑定文件夹对话框 ===
  _showBindDialog() {
    const existing = document.getElementById('bind-dialog-overlay');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.id = 'bind-dialog-overlay';
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:1000;display:flex;align-items:center;justify-content:center';
    overlay.innerHTML = `
      <div style="background:var(--bg-secondary);border-radius:16px;padding:24px;width:380px;box-shadow:0 20px 40px rgba(0,0,0,0.3)">
        <h3 style="margin:0 0 16px;color:var(--text-primary)">📁 绑定本地文件夹</h3>
        <label style="font-size:0.85rem;color:var(--text-secondary);display:block;margin-bottom:6px">文件夹路径</label>
        <input type="text" id="bind-path" placeholder="D:\\Projects\\my-app" style="width:100%;padding:10px 12px;border:1.5px solid var(--border-color);border-radius:8px;background:var(--bg-primary);margin-bottom:12px;font-size:0.9rem">
        <label style="font-size:0.85rem;color:var(--text-secondary);display:block;margin-bottom:6px">显示名称（可选）</label>
        <input type="text" id="bind-name" placeholder="留空则用文件夹名" style="width:100%;padding:10px 12px;border:1.5px solid var(--border-color);border-radius:8px;background:var(--bg-primary);margin-bottom:16px;font-size:0.9rem">
        <div style="display:flex;gap:10px;justify-content:flex-end">
          <button id="bind-cancel" style="padding:8px 16px;border:1px solid var(--border-color);border-radius:8px;background:transparent;color:var(--text-secondary);cursor:pointer">取消</button>
          <button id="bind-confirm" style="padding:8px 16px;border:none;border-radius:8px;background:var(--accent);color:#fff;cursor:pointer;font-weight:500">绑定</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    document.getElementById('bind-cancel').onclick = () => overlay.remove();
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

    document.getElementById('bind-confirm').onclick = async () => {
      const path = document.getElementById('bind-path').value.trim();
      const name = document.getElementById('bind-name').value.trim();
      if (!path) { App.showToast('请输入路径'); return; }

      try {
        const res = await fetch('/api/workspaces/bind', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path, name }),
        });
        const data = await res.json();
        if (res.ok) {
          overlay.remove();
          await Sidebar.loadWorkspaces();
          Panel.addLog('info', `📁 已绑定: ${data.workspace.name}`);
          App.showToast('绑定成功 ✓');
        } else {
          App.showToast(data.detail || '绑定失败');
        }
      } catch (e) {
        App.showToast('请求失败: ' + e.message);
      }
    };

    // 回车确认
    document.getElementById('bind-path').focus();
    document.getElementById('bind-name').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') document.getElementById('bind-confirm').click();
    });
    document.getElementById('bind-path').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') document.getElementById('bind-name').focus();
    });
  },

  // === 空状态 ===
  _renderEmpty(icon, title, desc) {
    // 随机选一个装饰 SVG
    const decors = ['flower', 'plant', 'star', 'cloud', 'sparkles', 'tree'];
    const decor = decors[Math.floor(Math.random() * decors.length)];
    return `
      <div class="empty-state">
        <img class="empty-state__decor" src="/img/icons/${decor}.svg" alt="" aria-hidden="true">
        <div class="empty-state__icon">${icon}</div>
        <div class="empty-state__title">${title}</div>
        <div class="empty-state__desc">${desc}</div>
      </div>
    `;
  }
};
