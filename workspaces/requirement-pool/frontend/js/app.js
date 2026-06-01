/**
 * 需求池管理 — 前端主逻辑
 */
const App = {
  // ===== 状态 =====
  state: {
    currentSystemId: 'all',
    systems: [],
    requirements: [],
    stats: {},
    filters: {
      status: '',
      source: '',
      priority: '',
      port: '',
      keyword: ''
    },
    pagination: {
      page: 1,
      pageSize: 10,
      total: 0,
      totalPages: 1
    },
    sort: {
      by: 'created_at',
      order: 'desc'
    }
  },

  // ===== 初始化 =====
  async init() {
    await this.loadSystems();
    await this.loadStats();
    await this.loadRequirements();
  },

  // ===== API: 系统管理 =====
  async loadSystems() {
    try {
      const res = await fetch('/api/systems/');
      const data = await res.json();
      this.state.systems = data.systems || [];
      this.renderSystemList();
    } catch (e) {
      console.error('加载系统列表失败:', e);
    }
  },

  async createSystem(name, description) {
    const res = await fetch('/api/systems/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description })
    });
    if (!res.ok) throw new Error('创建系统失败');
    return res.json();
  },

  async updateSystem(id, data) {
    const res = await fetch(`/api/systems/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error('更新系统失败');
    return res.json();
  },

  async deleteSystem(id) {
    if (!confirm('删除系统会同时删除其下所有需求，确定要删除吗？')) return;
    const res = await fetch(`/api/systems/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('删除系统失败');
    await this.loadSystems();
    await this.loadStats();
    await this.loadRequirements();
  },

  // ===== API: 需求管理 =====
  async loadRequirements() {
    try {
      const params = new URLSearchParams({
        page: this.state.pagination.page,
        page_size: this.state.pagination.pageSize,
        sort_by: this.state.sort.by,
        sort_order: this.state.sort.order
      });

      if (this.state.currentSystemId !== 'all') {
        params.append('system_id', this.state.currentSystemId);
      }
      if (this.state.filters.status) params.append('status', this.state.filters.status);
      if (this.state.filters.source) params.append('source', this.state.filters.source);
      if (this.state.filters.priority) params.append('priority', this.state.filters.priority);
      if (this.state.filters.port) params.append('port', this.state.filters.port);
      if (this.state.filters.keyword) params.append('keyword', this.state.filters.keyword);

      const res = await fetch(`/api/requirements/?${params}`);
      const data = await res.json();
      
      this.state.requirements = data.items || [];
      this.state.pagination.total = data.total;
      this.state.pagination.totalPages = data.total_pages;
      if (data.sort_by) this.state.sort.by = data.sort_by;
      if (data.sort_order) this.state.sort.order = data.sort_order;

      this.renderRequirementTable();
      this.renderPagination();
      this.updateTotalCount();
    } catch (e) {
      console.error('加载需求列表失败:', e);
    }
  },

  async createRequirement(formData) {
    const res = await fetch('/api/requirements/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || '创建需求失败');
    }
    return res.json();
  },

  async updateRequirement(id, formData) {
    const res = await fetch(`/api/requirements/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || '更新需求失败');
    }
    return res.json();
  },

  async deleteRequirement(id) {
    if (!confirm('确定要删除这条需求吗？')) return;
    const res = await fetch(`/api/requirements/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('删除需求失败');
    await this.loadRequirements();
    await this.loadStats();
    await this.loadSystems();
  },

  // ===== API: 统计 =====
  async loadStats() {
    try {
      const res = await fetch('/api/requirements/stats');
      const data = await res.json();
      this.state.stats = data;
      this.renderStats();
    } catch (e) {
      console.error('加载统计数据失败:', e);
    }
  },

  // ===== 渲染: 系统列表 =====
  renderSystemList() {
    const container = document.getElementById('systemList');
    const totalReqs = this.state.stats.total_requirements || 0;
    
    document.getElementById('totalCount').textContent = totalReqs;

    if (this.state.systems.length === 0) {
      container.innerHTML = '<div style="padding: 12px; color: var(--text-light); font-size: 13px; text-align: center;">暂无系统</div>';
      return;
    }

    container.innerHTML = this.state.systems.map(sys => `
      <div class="system-item ${this.state.currentSystemId == sys.id ? 'active' : ''}" 
           data-id="${sys.id}" 
           onclick="App.selectSystem(${sys.id})">
        <span class="sys-name">${this._esc(sys.name)}</span>
        <span class="sys-count">${sys.requirement_count || 0}</span>
        <div class="sys-actions">
          <button onclick="event.stopPropagation(); App.showEditSystemModal(${sys.id}, '${this._esc(sys.name)}', '${this._esc(sys.description || '')}')" title="编辑">✏️</button>
          <button class="btn-del" onclick="event.stopPropagation(); App.deleteSystem(${sys.id})" title="删除">🗑️</button>
        </div>
      </div>
    `).join('');
  },

  // ===== 渲染: 统计卡片 =====
  renderStats() {
    const stats = this.state.stats;
    const total = stats.total_requirements || 0;
    const systems = stats.total_systems || 0;
    const statusDist = stats.status_distribution || {};
    
    const pending = (statusDist['进入需求池'] || 0) + 
                   (statusDist['待论证'] || 0) + 
                   (statusDist['待设计'] || 0);
    const online = statusDist['已上线'] || 0;

    document.getElementById('statTotal').textContent = total;
    document.getElementById('statSystems').textContent = systems;
    document.getElementById('statPending').textContent = pending;
    document.getElementById('statOnline').textContent = online;
    document.getElementById('totalReqs').textContent = total;
    document.getElementById('totalCount').textContent = total;
  },

  // ===== 判断需求是否快到期或已过期 =====
  _getDeadlineClass(item) {
    if (!item.plan_date) return '';
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const planDate = new Date(item.plan_date);
    
    const diffTime = planDate - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays < 0) return 'expired';      // 已过期
    if (diffDays <= 7) return 'near-deadline'; // 快到期（7天内）
    return '';
  },

  // ===== 渲染: 需求表格 =====
  renderRequirementTable() {
    const container = document.getElementById('requirementTable');
    const items = this.state.requirements;

    if (items.length === 0) {
      container.innerHTML = `
        <tr>
          <td colspan="15">
            <div class="empty-state">
              <div class="icon">📋</div>
              <p>暂无需求数据</p>
            </div>
          </td>
        </tr>
      `;
      return;
    }

    const startIndex = (this.state.pagination.page - 1) * this.state.pagination.pageSize;

    container.innerHTML = items.map((item, index) => {
        const priorityLabels = { 1: 'P0', 2: 'P1', 3: 'P2' };
        const priorityLabel = priorityLabels[item.priority] || `P${item.priority}`;
        const deadlineClass = this._getDeadlineClass(item);
        return `
      <tr class="${deadlineClass}">
        <td>${startIndex + index + 1}</td>
        <td>
          <span class="priority-badge priority-${item.priority}">${priorityLabel}</span>
        </td>
        <td class="text-ellipsis" title="${this._esc(item.system_name || '')}">${this._esc(item.system_name || '-')}</td>
        <td class="text-ellipsis" title="${this._esc(item.module || '')}">${this._esc(item.module || '-')}</td>
        <td class="text-ellipsis" title="${this._esc(item.name)}">${this._esc(item.name)}</td>
        <td><span class="port-badge">${this._esc(item.port || 'web')}</span></td>
        <td>${this._esc(item.source || '-')}</td>
        <td>${this._getStatusBadge(item.status)}</td>
        <td class="text-ellipsis" title="${this._esc(item.proposer || '')}">${this._esc(item.proposer || '-')}</td>
        <td>${this._esc(item.propose_date || '-')}</td>
        <td class="plan-date">${this._esc(item.plan_date || '-')}</td>
        <td>${this._esc(item.plan_version || '-')}</td>
        <td>${this._esc(item.actual_version || '-')}</td>
        <td>${this._esc(item.online_date || '-')}</td>
        <td>
          <button class="action-btn edit" onclick="App.showEditRequirementModal(${item.id})">编辑</button>
          <button class="action-btn del" onclick="App.deleteRequirement(${item.id})">删除</button>
        </td>
      </tr>
    `;
    }).join('');
  },

  // ===== 渲染: 分页 =====
  renderPagination() {
    const container = document.getElementById('pagination');
    const { page, pageSize, total, totalPages } = this.state.pagination;

    if (totalPages <= 1) {
      container.innerHTML = total > 0 ? `<span>共 ${total} 条</span>` : '';
      return;
    }

    let pages = [];
    if (totalPages <= 7) {
      pages = Array.from({ length: totalPages }, (_, i) => i + 1);
    } else {
      if (page <= 4) {
        pages = [1, 2, 3, 4, 5, '...', totalPages];
      } else if (page >= totalPages - 3) {
        pages = [1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
      } else {
        pages = [1, '...', page - 1, page, page + 1, '...', totalPages];
      }
    }

    container.innerHTML = `
      <span>共 ${total} 条，第 ${page}/${totalPages} 页</span>
      <div class="page-controls">
        <button ${page === 1 ? 'disabled' : ''} onclick="App.goToPage(${page - 1})">上一页</button>
        ${pages.map(p => p === '...' 
          ? '<span style="padding: 0 8px;">...</span>' 
          : `<button class="${p === page ? 'active' : ''}" onclick="App.goToPage(${p})">${p}</button>`
        ).join('')}
        <button ${page === totalPages ? 'disabled' : ''} onclick="App.goToPage(${page + 1})">下一页</button>
        <select class="page-size-select" onchange="App.changePageSize(this.value)">
          <option value="10" ${pageSize == 10 ? 'selected' : ''}>10条/页</option>
          <option value="20" ${pageSize == 20 ? 'selected' : ''}>20条/页</option>
          <option value="50" ${pageSize == 50 ? 'selected' : ''}>50条/页</option>
        </select>
      </div>
    `;
  },

  // ===== 辅助函数 =====
  _esc(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  },

  _getStatusBadge(status) {
    const statusMap = {
      '进入需求池': 'pool',
      '待论证': 'demo',
      '待设计': 'design',
      '设计中': 'designing',
      '交付UI': 'ui',
      '开发中': 'dev',
      '已上线': 'online',
      '已关闭': 'closed'
    };
    const cls = statusMap[status] || 'pool';
    return `<span class="status-badge status-${cls}">${this._esc(status)}</span>`;
  },

  updateTotalCount() {
    document.getElementById('totalReqs').textContent = this.state.pagination.total;
  },

  // ===== 交互: 选择系统 =====
  selectSystem(systemId) {
    this.state.currentSystemId = systemId;
    this.state.pagination.page = 1;

    document.querySelectorAll('.system-item, .system-all').forEach(el => {
      el.classList.remove('active');
    });
    const activeEl = systemId === 'all' 
      ? document.querySelector('.system-all')
      : document.querySelector(`.system-item[data-id="${systemId}"]`);
    if (activeEl) activeEl.classList.add('active');

    const system = this.state.systems.find(s => s.id === systemId);
    document.getElementById('pageTitle').textContent = systemId === 'all' 
      ? '全部需求' 
      : system?.name || '需求详情';
    
    const descEl = document.getElementById('systemDescription');
    if (systemId === 'all' || !system?.description) {
      descEl.style.display = 'none';
    } else {
      descEl.textContent = system.description;
      descEl.style.display = 'block';
    }
    
    this.loadRequirements();
  },

  // ===== 交互: 筛选和搜索 =====
  search() {
    this.state.filters = {
      status: document.getElementById('filterStatus').value,
      source: document.getElementById('filterSource').value,
      priority: document.getElementById('filterPriority').value,
      port: document.getElementById('filterPort').value,
      keyword: document.getElementById('filterKeyword').value.trim()
    };
    this.state.pagination.page = 1;
    this.loadRequirements();
  },

  resetFilters() {
    document.getElementById('filterStatus').value = '';
    document.getElementById('filterSource').value = '';
    document.getElementById('filterPriority').value = '';
    document.getElementById('filterPort').value = '';
    document.getElementById('filterKeyword').value = '';
    this.state.filters = { status: '', source: '', priority: '', port: '', keyword: '' };
    this.state.pagination.page = 1;
    this.loadRequirements();
  },

  // ===== 交互: 分页 =====
  goToPage(page) {
    this.state.pagination.page = page;
    this.loadRequirements();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  },

  changePageSize(size) {
    this.state.pagination.pageSize = parseInt(size);
    this.state.pagination.page = 1;
    this.loadRequirements();
  },

  // ===== 交互: 系统弹窗 =====
  showAddSystemModal() {
    document.getElementById('sysModalTitle').textContent = '添加系统';
    document.getElementById('sysId').value = '';
    document.getElementById('sysName').value = '';
    document.getElementById('sysDescription').value = '';
    const modal = document.getElementById('systemModal');
    modal.style.display = 'flex';
    setTimeout(() => modal.classList.add('show'), 10);
  },

  showEditSystemModal(id, name, description) {
    document.getElementById('sysModalTitle').textContent = '编辑系统';
    document.getElementById('sysId').value = id;
    document.getElementById('sysName').value = name;
    document.getElementById('sysDescription').value = description;
    const modal = document.getElementById('systemModal');
    modal.style.display = 'flex';
    setTimeout(() => modal.classList.add('show'), 10);
  },

  closeSystemModal() {
    const modal = document.getElementById('systemModal');
    modal.classList.remove('show');
    setTimeout(() => modal.style.display = 'none', 200);
  },

  async saveSystem() {
    const id = document.getElementById('sysId').value;
    const name = document.getElementById('sysName').value.trim();
    const description = document.getElementById('sysDescription').value.trim();

    if (!name) {
      alert('请输入系统名称');
      return;
    }

    try {
      if (id) {
        await this.updateSystem(parseInt(id), { name, description });
      } else {
        await this.createSystem(name, description);
      }
      this.closeSystemModal();
      await this.loadSystems();
      await this.loadStats();
    } catch (e) {
      alert(e.message);
    }
  },

  // ===== 交互: 需求弹窗 =====
  async showAddRequirementModal() {
    await this.loadSystemOptions();
    document.getElementById('reqModalTitle').textContent = '添加需求';
    document.getElementById('reqId').value = '';
    document.getElementById('requirementForm').reset();
    
    if (this.state.currentSystemId !== 'all') {
      document.getElementById('reqSystemId').value = this.state.currentSystemId;
    }
    
    const modal = document.getElementById('requirementModal');
    modal.style.display = 'flex';
    setTimeout(() => modal.classList.add('show'), 10);
  },

  async showEditRequirementModal(id) {
    await this.loadSystemOptions();
    
    try {
      const res = await fetch(`/api/requirements/${id}`);
      const data = await res.json();
      const req = data;

      document.getElementById('reqModalTitle').textContent = '编辑需求';
      document.getElementById('reqId').value = id;
      document.getElementById('reqSystemId').value = req.system_id;
      document.getElementById('reqName').value = req.name;
      document.getElementById('reqModule').value = req.module || '';
      document.getElementById('reqPort').value = req.port || 'web';
      document.getElementById('reqSource').value = req.source || '产品';
      document.getElementById('reqPriority').value = req.priority || 2;
      document.getElementById('reqProposer').value = req.proposer || '';
      document.getElementById('reqProposeDate').value = req.propose_date || '';
      document.getElementById('reqPlanDate').value = req.plan_date || '';
      document.getElementById('reqPlanVersion').value = req.plan_version || '';
      document.getElementById('reqActualVersion').value = req.actual_version || '';
      document.getElementById('reqOnlineDate').value = req.online_date || '';
      document.getElementById('reqStatus').value = req.status || '进入需求池';
      document.getElementById('reqDescription').value = req.description || '';
      document.getElementById('reqRemark').value = req.remark || '';

      const modal = document.getElementById('requirementModal');
      modal.style.display = 'flex';
      setTimeout(() => modal.classList.add('show'), 10);
    } catch (e) {
      alert('加载需求详情失败');
      console.error(e);
    }
  },

  closeRequirementModal() {
    const modal = document.getElementById('requirementModal');
    modal.classList.remove('show');
    setTimeout(() => modal.style.display = 'none', 200);
  },

  async loadSystemOptions() {
    const select = document.getElementById('reqSystemId');
    const currentValue = select.value;
    
    select.innerHTML = '<option value="">请选择系统</option>' + 
      this.state.systems.map(sys => 
        `<option value="${sys.id}">${this._esc(sys.name)}</option>`
      ).join('');
    
    if (currentValue) {
      select.value = currentValue;
    }
  },

  async saveRequirement() {
    const id = document.getElementById('reqId').value;
    const formData = {
      system_id: parseInt(document.getElementById('reqSystemId').value),
      name: document.getElementById('reqName').value.trim(),
      module: document.getElementById('reqModule').value.trim(),
      port: document.getElementById('reqPort').value,
      source: document.getElementById('reqSource').value,
      priority: parseInt(document.getElementById('reqPriority').value),
      proposer: document.getElementById('reqProposer').value.trim(),
      propose_date: document.getElementById('reqProposeDate').value,
      plan_date: document.getElementById('reqPlanDate').value,
      status: document.getElementById('reqStatus').value,
      plan_version: document.getElementById('reqPlanVersion').value.trim(),
      actual_version: document.getElementById('reqActualVersion').value.trim(),
      online_date: document.getElementById('reqOnlineDate').value,
      description: document.getElementById('reqDescription').value.trim(),
      remark: document.getElementById('reqRemark').value.trim()
    };

    if (!formData.system_id) {
      alert('请选择所属系统');
      return;
    }
    if (!formData.name) {
      alert('请输入需求名称');
      return;
    }

    try {
      if (id) {
        await this.updateRequirement(parseInt(id), formData);
      } else {
        await this.createRequirement(formData);
      }
      this.closeRequirementModal();
      await this.loadRequirements();
      await this.loadStats();
      await this.loadSystems();
    } catch (e) {
      alert(e.message);
    }
  },

  // ===== 排序功能 =====
  sortByPlanDate() {
    if (this.state.sort.by === 'plan_date') {
      this.state.sort.order = this.state.sort.order === 'desc' ? 'asc' : 'desc';
    } else {
      this.state.sort.by = 'plan_date';
      this.state.sort.order = 'desc';
    }
    this.state.pagination.page = 1;
    this.updateSortIcon();
    this.loadRequirements();
  },

  sortByPriority() {
    if (this.state.sort.by === 'priority') {
      this.state.sort.order = this.state.sort.order === 'desc' ? 'asc' : 'desc';
    } else {
      this.state.sort.by = 'priority';
      this.state.sort.order = 'desc';
    }
    this.state.pagination.page = 1;
    this.updateSortIcon();
    this.loadRequirements();
  },

  updateSortIcon() {
    const planDateIcon = document.getElementById('planDateSortIcon');
    const priorityIcon = document.getElementById('prioritySortIcon');
    
    if (planDateIcon) {
      planDateIcon.textContent = this.state.sort.by === 'plan_date' 
        ? (this.state.sort.order === 'desc' ? '↓' : '↑') 
        : '↕';
    }
    if (priorityIcon) {
      priorityIcon.textContent = this.state.sort.by === 'priority' 
        ? (this.state.sort.order === 'desc' ? '↓' : '↑') 
        : '↕';
    }
  }
};

// ===== 启动 =====
document.addEventListener('DOMContentLoaded', () => {
  App.init();
});