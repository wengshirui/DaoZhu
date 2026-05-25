/**
 * 财务助手 API 封装
 */
const API = {
  async _req(path, opts = {}) {
    const res = await fetch(`/api${path}`, {
      headers: { 'Content-Type': 'application/json', ...opts.headers },
      ...opts,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },

  // 公司
  getCompanies() { return this._req('/companies/'); },
  createCompany(data) { return this._req('/companies/', { method: 'POST', body: JSON.stringify(data) }); },

  // 科目
  getAccounts(companyId = 'demo') { return this._req(`/accounts/?company_id=${companyId}`); },
  searchAccounts(q) { return this._req(`/accounts/search?q=${encodeURIComponent(q)}`); },
  createAccount(data) { return this._req('/accounts/', { method: 'POST', body: JSON.stringify(data) }); },
  getBalance(code) { return this._req(`/accounts/${code}/balance`); },

  // 凭证
  getVouchers(companyId = 'demo') { return this._req(`/vouchers/?company_id=${companyId}`); },
  getVoucher(id) { return this._req(`/vouchers/${id}`); },
  createVoucher(data) { return this._req('/vouchers/', { method: 'POST', body: JSON.stringify(data) }); },
  deleteVoucher(id) { return this._req(`/vouchers/${id}`, { method: 'DELETE' }); },
};
