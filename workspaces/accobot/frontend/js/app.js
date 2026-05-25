/**
 * 财务助手 — 前端主逻辑
 */
const App = {
  currentView: 'overview',

  async init() {
    this.bindNav();
    await this.loadOverview();
  },

  bindNav() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.switchView(btn.dataset.view);
      });
    });
  },

  switchView(view) {
    this.currentView = view;
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(`view-${view}`).classList.add('active');

    if (view === 'overview') this.loadOverview();
    else if (view === 'accounts') this.loadAccounts();
    else if (view === 'vouchers') this.loadVouchers();
    else if (view === 'companies') this.loadCompanies();
  },

  // === 总览 ===
  async loadOverview() {
    try {
      const [accounts, vouchers] = await Promise.all([
        API.getAccounts(), API.getVouchers()
      ]);

      document.getElementById('stats').innerHTML = `
        <div class="stat-card">
          <div class="stat-card__label">科目数量</div>
          <div class="stat-card__value">${accounts.accounts.length}</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__label">凭证数量</div>
          <div class="stat-card__value">${vouchers.vouchers.length}</div>
        </div>
        <div class="stat-card">
          <div class="stat-card__label">草稿凭证</div>
          <div class="stat-card__value">${vouchers.vouchers.filter(v => v.status === 'draft').length}</div>
        </div>
      `;

      const recent = vouchers.vouchers.slice(0, 5);
      document.getElementById('recent-vouchers').innerHTML = recent.length
        ? this.renderVoucherTable(recent)
        : '<p style="color:var(--muted)">暂无凭证</p>';
    } catch (e) {
      document.getElementById('stats').innerHTML = `<p>加载失败: ${e.message}</p>`;
    }
  },

  // === 科目 ===
  async loadAccounts() {
    try {
      const data = await API.getAccounts();
      const container = document.getElementById('account-list');
      if (data.accounts.length === 0) {
        container.innerHTML = '<p style="color:var(--muted)">暂无科目，请先初始化科目表</p>';
        return;
      }
      container.innerHTML = `
        <table class="table">
          <thead><tr><th>编码</th><th>名称</th><th>类别</th><th>方向</th></tr></thead>
          <tbody>${data.accounts.map(a => `
            <tr>
              <td>${a.code}</td>
              <td>${a.name}</td>
              <td>${a.category}</td>
              <td>${a.balance_direction === 'debit' ? '借' : '贷'}</td>
            </tr>
          `).join('')}</tbody>
        </table>`;
    } catch (e) {
      document.getElementById('account-list').innerHTML = `<p>加载失败: ${e.message}</p>`;
    }
  },

  // === 凭证 ===
  async loadVouchers() {
    try {
      const data = await API.getVouchers();
      document.getElementById('voucher-list').innerHTML = data.vouchers.length
        ? this.renderVoucherTable(data.vouchers)
        : '<p style="color:var(--muted)">暂无凭证</p>';
    } catch (e) {
      document.getElementById('voucher-list').innerHTML = `<p>加载失败: ${e.message}</p>`;
    }
  },

  renderVoucherTable(vouchers) {
    return `
      <table class="table">
        <thead><tr><th>日期</th><th>摘要</th><th>状态</th></tr></thead>
        <tbody>${vouchers.map(v => `
          <tr>
            <td>${v.voucher_date}</td>
            <td>${v.summary || '—'}</td>
            <td><span class="tag tag--${v.status}">${v.status}</span></td>
          </tr>
        `).join('')}</tbody>
      </table>`;
  },

  // === 公司 ===
  async loadCompanies() {
    try {
      const data = await API.getCompanies();
      const container = document.getElementById('company-list');
      container.innerHTML = data.companies.map(c => `
        <div class="stat-card">
          <div class="stat-card__label">${c.industry || '未设置行业'}</div>
          <div class="stat-card__value">${c.name}</div>
          <div style="font-size:0.75rem;color:var(--muted);margin-top:4px">
            ${c.taxpayer_type} · ${c.accounting_standard}
          </div>
        </div>
      `).join('');
    } catch (e) {
      document.getElementById('company-list').innerHTML = `<p>加载失败: ${e.message}</p>`;
    }
  },
};

document.addEventListener('DOMContentLoaded', () => App.init());
