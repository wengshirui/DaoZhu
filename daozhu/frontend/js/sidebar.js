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
      container.innerHTML = workspaces.map(w => this._renderWorkspaceCard(w)).join('');
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
        if (mode === 'lightweight') {
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
