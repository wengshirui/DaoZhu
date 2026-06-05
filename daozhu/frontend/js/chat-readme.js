/**
 * chat-readme.js — README/文档展示模块
 */

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
