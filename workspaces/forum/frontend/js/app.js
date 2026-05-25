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
        alert(err.detail || '发送失败');
        return;
      }
      input.value = '';
      await this.showIssue(number);
    } catch (e) {
      alert('发送失败: ' + e.message);
    }
  },

  async createIssue() {
    const title = prompt('帖子标题：');
    if (!title) return;
    const body = prompt('帖子内容（可选）：') || '';

    try {
      const res = await fetch('/api/issues/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, body }),
      });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || '创建失败');
        return;
      }
      await this.loadIssues();
    } catch (e) {
      alert('创建失败: ' + e.message);
    }
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
