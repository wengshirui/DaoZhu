const API = {
  base: '/api',

  async _req(path, opts = {}) {
    const res = await fetch(`${this.base}${path}`, {
      headers: { 'Content-Type': 'application/json', ...opts.headers },
      ...opts,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  },

  listPrds() { return this._req('/prds'); },
  getPrd(id) { return this._req(`/prds/${id}`); },
  generatePrd(data) { return this._req('/prds/generate', { method: 'POST', body: JSON.stringify(data) }); },
  generateDescription(data) { return this._req('/description/generate', { method: 'POST', body: JSON.stringify(data) }); },
  deletePrd(id) { return this._req(`/prds/${id}`, { method: 'DELETE' }); },
};

const App = {
  prds: [],
  currentPrdId: null,
  currentPrd: null,
  _pendingDeleteId: null,

  resetState() {
    this.prds = [];
    this.currentPrdId = null;
    this.currentPrd = null;
    this._pendingDeleteId = null;
  },

  async init() {
    this.resetState();
    this.showEmptyState();
    this.bindEvents();
    await this.loadPrds();
  },

  bindEvents() {
    window.addEventListener('click', (e) => {
      const modal = e.target.closest('.modal');
      if (modal && e.target === modal) this._closeAllModals();
    });
  },

  showEmptyState() {
    document.getElementById('mainContent').innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📄</div>
        <h2>欢迎使用 PRD 编写助手</h2>
        <p>由 AI 助力，快速生成产品需求文档</p>
        <button class="btn-primary" onclick="showAiGenerateModal()">🤖 开始生成</button>
      </div>
    `;
    this._closeAllModals();
  },

  async loadPrds() {
    try {
      const data = await API.listPrds();
      this.prds = data.data || [];
      this.renderPrdList();
    } catch (e) {
      console.error('加载 PRD 列表失败:', e);
    }
  },

  _formatBejingTime(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr.replace(' ', 'T') + 'Z');
    return date.toLocaleString('zh-CN', { 
      timeZone: 'Asia/Shanghai',
      year: 'numeric', 
      month: '2-digit', 
      day: '2-digit', 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  },

  renderPrdList() {
    const container = document.getElementById('prdList');
    if (this.prds.length === 0) {
      container.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:0.85rem">暂无 PRD 文档<br>点击上方按钮新建</div>';
      return;
    }
    container.innerHTML = this.prds.map(p => {
      const updated = this._formatBejingTime(p.updated_at);
      return `<div class="prd-item" data-id="${p.id}">
        <span class="prd-item__icon">📄</span>
        <div class="prd-item__info" style="cursor:pointer;flex:1" onclick="App.openPrd(${p.id})">
          <div class="prd-item__title">${this._esc(p.title)}</div>
          <div class="prd-item__meta">${updated}</div>
        </div>
        <button class="prd-item__delete" title="删除" onclick="event.stopPropagation();App.deletePrd(${p.id})">🗑️</button>
      </div>`;
    }).join('');
  },

  deletePrd(id) {
    this._pendingDeleteId = id;
    document.getElementById('deleteConfirmModal').classList.add('modal--open');
  },

  cancelDelete() {
    this._pendingDeleteId = null;
    this.closeModal('deleteConfirmModal');
  },

  async confirmDelete() {
    const id = this._pendingDeleteId;
    this._pendingDeleteId = null;
    this.closeModal('deleteConfirmModal');
    try {
      await API.deletePrd(id);
      if (this.currentPrdId === id) {
        this.currentPrdId = null;
        this.currentPrd = null;
        this.closeModal('prdEditorModal');
        this.showEmptyState();
      }
      await this.loadPrds();
    } catch (e) {
      console.error('删除 PRD 失败:', e);
      alert('删除失败');
    }
  },

  exportPrd(id) {
    window.open(`/api/prds/${id}/export`, '_blank');
  },

  async openPrd(id) {
    this.currentPrdId = id;
    try {
      const data = await API.getPrd(id);
      this.currentPrd = data.data;
      this.renderPrdList();
      this.renderDetail();
      document.getElementById('prdEditorModal').classList.add('modal--open');
    } catch (e) {
      console.error('打开 PRD 失败:', e);
      alert('打开 PRD 失败');
    }
  },

  renderDetail() {
    const p = this.currentPrd;
    const sections = p.sections || [];
    const container = document.getElementById('editorBody');

    let prdContent = '';
    if (sections.length > 0 && sections[0].content) {
      prdContent = this._esc(sections[0].content);
    }

    container.innerHTML = `<div class="editor-panel editor-panel--active">
      <div style="margin-bottom:16px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
          <h3 style="margin:0;">${this._esc(p.title)}</h3>
          <div style="display:flex;gap:8px;">
            <button class="btn-secondary" style="padding:6px 12px;font-size:0.8rem" onclick="App.exportPrd(${p.id})">📄 导出 .docx</button>
            <button class="btn-secondary" style="padding:6px 12px;font-size:0.8rem;color:#e74c3c;border-color:#e74c3c" onclick="App.deletePrd(${p.id})">🗑️ 删除</button>
          </div>
        </div>
        <div style="color: var(--text-muted); font-size:0.85rem;">
          作者：${this._esc(p.author || 'AI 助手')}
          &nbsp;|&nbsp;
          版本：${this._esc(p.version || 'v1.0')}
        </div>
      </div>
      <div style="background: var(--bg-sidebar); padding: 16px; border-radius: 8px; white-space: pre-wrap; line-height: 1.6;">
        ${prdContent.replace(/\n/g, '<br>')}
      </div>
    </div>`;
  },

  showAiGenerateModal() {
    document.getElementById('aiGenerateModal').classList.add('modal--open');
  },

  async autoGenerateDescription() {
    const title = document.getElementById('aiTitle').value.trim();
    if (!title) { alert('请先输入产品名称'); return; }

    const textarea = document.getElementById('aiDescription');
    const btn = document.getElementById('autoDescBtn');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '⏳';
    textarea.placeholder = 'AI 正在生成描述...';

    try {
      const result = await API.generateDescription({ title });
      if (result.content) {
        textarea.value = result.content;
      } else {
        alert(result.error || 'AI 返回为空，请重试');
      }
    } catch (e) {
      alert(`生成描述失败: ${e.message}`);
    } finally {
      btn.disabled = false;
      btn.innerHTML = originalText;
      textarea.placeholder = '简单描述一下这个产品要解决什么问题，有什么特点...';
    }
  },

  async generatePrd(event) {
    event.preventDefault();
    const title = document.getElementById('aiTitle').value.trim();
    if (!title) { alert('请输入产品名称'); return; }

    const btn = document.getElementById('aiGenerateBtn');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '⏳ 正在生成...';

    try {
      const description = document.getElementById('aiDescription').value.trim();
      const result = await API.generatePrd({ title, description });
      this.closeModal('aiGenerateModal');
      document.getElementById('aiGenerateForm').reset();
      await this.loadPrds();
      this.openPrd(result.id);
    } catch (e) {
      console.error('AI 生成失败:', e);
      alert('AI 生成失败，请检查 API Key 配置是否正确');
    } finally {
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  },

  closeModal(id) {
    document.getElementById(id).classList.remove('modal--open');
    if (id === 'prdEditorModal') {
      this.currentPrdId = null;
      this.currentPrd = null;
      this.showEmptyState();
    }
  },

  _closeAllModals() {
    document.querySelectorAll('.modal').forEach(m => m.classList.remove('modal--open'));
  },

  _esc(text) {
    if (!text) return '';
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
  },
};

window.showAiGenerateModal = () => App.showAiGenerateModal();
window.closeModal = (id) => App.closeModal(id);
window.generatePrd = (event) => App.generatePrd(event);
window.exportPrd = (id) => App.exportPrd(id);
window.deletePrd = (id) => App.deletePrd(id);
window.openPrd = (id) => App.openPrd(id);
window.autoGenerateDescription = () => App.autoGenerateDescription();
window.confirmDelete = () => App.confirmDelete();
window.cancelDelete = () => App.cancelDelete();
window.showEmptyState = () => App.showEmptyState();

document.addEventListener('DOMContentLoaded', () => {
  // 首先关闭所有可能打开的弹窗
  document.querySelectorAll('.modal').forEach(m => m.classList.remove('modal--open'));
  // 然后初始化应用
  App.init();
});
