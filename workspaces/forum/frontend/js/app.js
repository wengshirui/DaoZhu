/**
 * 岛主论坛 — 前端主逻辑
 */
const App = {
  currentState: 'open',

  async init() {
    this.bindTabs();
    document.getElementById('btn-new').addEventListener('click', () => this.createIssue());
    await this.loadIssues();
  },

  bindTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.currentState = btn.dataset.state;
        this.loadIssues();
      });
    });
  },

  async loadIssues() {
    const list = document.getElementById('issue-list');
    const detail = document.getElementById('issue-detail');
    detail.style.display = 'none';
    list.style.display = 'block';

    try {
      const res = await fetch(`/api/issues/?state=${this.currentState}`);
      const data = await res.json();

      if (data.issues.length === 0) {
        list.innerHTML = '<div class="empty">暂无帖子</div>';
        return;
      }

      list.innerHTML = data.issues.map(i => `
        <div class="issue-card" onclick="App.showIssue(${i.number})">
          <div class="issue-card__title">${i.title}</div>
          <div class="issue-card__meta">
            <span>👤 ${i.author}</span>
            <span>💬 ${i.comments_count} 回复</span>
            <span>${this.formatTime(i.updated_at || i.created_at)}</span>
          </div>
        </div>
      `).join('');
    } catch (e) {
      list.innerHTML = `<div class="empty">加载失败: ${e.message}</div>`;
    }
  },

  async showIssue(number) {
    const list = document.getElementById('issue-list');
    const detail = document.getElementById('issue-detail');
    list.style.display = 'none';
    detail.style.display = 'block';

    try {
      const res = await fetch(`/api/issues/${number}`);
      const data = await res.json();

      const comments = (data.comments || []).map(c => `
        <div class="comment">
          <div class="comment__author">👤 ${c.author}</div>
          <div class="comment__body">${c.body}</div>
          <div class="comment__time">${this.formatTime(c.created_at)}</div>
        </div>
      `).join('');

      detail.innerHTML = `
        <a class="issue-detail__back" onclick="App.loadIssues()">← 返回列表</a>
        <div class="issue-detail__title">${data.title}</div>
        <div class="issue-detail__body">${data.body || '（无内容）'}</div>
        <h3 style="font-size:0.9rem;color:var(--muted);margin-bottom:8px">💬 评论 (${data.comments_count || 0})</h3>
        ${comments || '<div class="empty">暂无评论</div>'}
        <div class="comment-form">
          <textarea id="comment-input" placeholder="写下你的回复..."></textarea>
          <button class="btn btn--primary" onclick="App.addComment(${number})">回复</button>
        </div>
      `;
    } catch (e) {
      detail.innerHTML = `<div class="empty">加载失败: ${e.message}</div>`;
    }
  },

  async addComment(number) {
    const input = document.getElementById('comment-input');
    const body = input.value.trim();
    if (!body) return;

    try {
      const res = await fetch(`/api/issues/${number}/comments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body }),
      });
      if (!res.ok) {
        const err = await res.json();
        this.showMsg(err.detail || '发送失败', 'error');
        return;
      }
      input.value = '';
      this.showMsg('✅ 回复成功', 'success');
      await this.showIssue(number);
    } catch (e) {
      this.showMsg('发送失败: ' + e.message, 'error');
    }
  },

  async createIssue() {
    // 用内联表单替代 prompt
    const list = document.getElementById('issue-list');
    list.innerHTML = `
      <div style="background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:20px">
        <h3 style="margin-bottom:12px">📝 发布新帖</h3>
        <input type="text" id="new-issue-title" placeholder="帖子标题" style="width:100%;padding:10px;border:1px solid var(--border);border-radius:var(--radius);font:inherit;margin-bottom:8px">
        <textarea id="new-issue-body" placeholder="帖子内容（可选）" rows="4" style="width:100%;padding:10px;border:1px solid var(--border);border-radius:var(--radius);font:inherit;resize:vertical;margin-bottom:12px"></textarea>
        <div style="display:flex;gap:8px">
          <button class="btn btn--primary" onclick="App.submitNewIssue()">发布</button>
          <button class="btn" onclick="App.loadIssues()">取消</button>
        </div>
      </div>
    `;
  },

  async submitNewIssue() {
    const title = document.getElementById('new-issue-title').value.trim();
    const body = document.getElementById('new-issue-body').value.trim();
    if (!title) { this.showMsg('标题不能为空', 'error'); return; }

    try {
      const res = await fetch('/api/issues/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, body }),
      });
      if (!res.ok) {
        const err = await res.json();
        this.showMsg(err.detail || '创建失败', 'error');
        return;
      }
      this.showMsg('✅ 发布成功', 'success');
      await this.loadIssues();
    } catch (e) {
      this.showMsg('创建失败: ' + e.message, 'error');
    }
  },

  showMsg(text, type) {
    const el = document.createElement('div');
    el.style.cssText = `position:fixed;top:20px;left:50%;transform:translateX(-50%);padding:10px 20px;border-radius:8px;font-size:0.85rem;z-index:9999;color:#fff;background:${type === 'error' ? '#c75450' : '#2d8a4e'}`;
    el.textContent = text;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 3000);
  },

  formatTime(str) {
    if (!str) return '';
    const d = new Date(str);
    const now = new Date();
    const diff = Math.floor((now - d) / 1000 / 60);
    if (diff < 60) return `${diff}分钟前`;
    if (diff < 1440) return `${Math.floor(diff / 60)}小时前`;
    return `${d.getMonth() + 1}/${d.getDate()}`;
  },
};

document.addEventListener('DOMContentLoaded', () => App.init());
