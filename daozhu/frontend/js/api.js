/**
 * api.js — API 调用封装 + Mock 数据
 * 当后端未就绪时使用 Mock 数据，后端就绪后切换为真实请求
 */

const API = {
  baseUrl: '',
  useMock: false, // 后端已就绪，使用真实 API

  // === Mock 数据 ===
  _mockData: {
    workspaces: [
      {
        id: 'todo',
        name: '个人待办',
        icon: '📋',
        color: '#10B981',
        description: '任务管理，待办清单',
        port: 7801,
        status: 'running',
        tags: ['效率', '待办']
      },
      {
        id: 'forum',
        name: '岛主论坛',
        icon: '🏝️',
        color: '#6366F1',
        description: '岛民交流，分享经验',
        port: 7802,
        status: 'stopped',
        tags: ['社区', '交流']
      },
      {
        id: 'finance',
        name: '个人记账',
        icon: '💰',
        color: '#2563EB',
        description: 'AI 驱动的记账报表',
        port: 7803,
        status: 'running',
        tags: ['财务', '记账']
      }
    ],
    skills: [
      { id: 'workspace-builder', name: '工作区建造', icon: '🏗️', status: 'active' },
      { id: 'code-gen', name: '代码生成', icon: '💻', status: 'active' },
      { id: 'data-analysis', name: '数据分析', icon: '📊', status: 'inactive' }
    ],
    tools: [
      { id: 'browser', name: '浏览器', icon: '🌐', status: 'connected' },
      { id: 'filesystem', name: '文件系统', icon: '📁', status: 'connected' },
      { id: 'terminal', name: '终端', icon: '⌨️', status: 'disconnected' }
    ],
    conversations: [
      { id: 'conv-001', title: '建造记账工作区', updated_at: '2025-05-25T10:00:00Z' },
      { id: 'conv-002', title: '安装番茄钟', updated_at: '2025-05-24T15:30:00Z' },
      { id: 'conv-003', title: '配置 AI 模型', updated_at: '2025-05-23T09:00:00Z' }
    ]
  },

  // === 请求方法 ===
  async _fetch(endpoint) {
    if (this.useMock) {
      await new Promise(r => setTimeout(r, 200)); // 模拟延迟
      const key = endpoint.replace('/api/', '');
      const data = this._mockData[key];
      if (!data) throw new Error(`Mock 数据不存在: ${endpoint}`);
      return data;
    }

    const res = await fetch(`${this.baseUrl}${endpoint}`);
    if (!res.ok) throw new Error(`请求失败: HTTP ${res.status}`);
    const json = await res.json();
    return json[Object.keys(json)[0]] || json;
  },

  async getWorkspaces() {
    return this._fetch('/api/workspaces');
  },

  async getSkills() {
    return this._fetch('/api/skills');
  },

  async getTools() {
    return this._fetch('/api/tools');
  },

  async getConversations() {
    return this._fetch('/api/conversations');
  },

  async sendMessage(message) {
    if (this.useMock) {
      await new Promise(r => setTimeout(r, 800));
      return {
        role: 'assistant',
        content: `收到你的消息："${message}"。我是管家，目前处于演示模式。后端接入后我就能真正帮你建造工作区了！`
      };
    }

    const res = await fetch(`${this.baseUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    if (!res.ok) throw new Error(`发送失败: HTTP ${res.status}`);
    return res.json();
  }
};
