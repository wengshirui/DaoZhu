/**
 * 桌面宠物 — API 封装
 */
const PetAPI = {
    base: '',

    // === 商店 ===
    async getCatalog(page = 1) {
        const res = await fetch(`${this.base}/api/store/catalog?page=${page}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },

    async refreshCatalog() {
        const res = await fetch(`${this.base}/api/store/refresh`, { method: 'POST' });
        return res.json();
    },

    async downloadPet(name) {
        const res = await fetch(`${this.base}/api/store/download/${name}`, { method: 'POST' });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || '下载失败');
        }
        return res.json();
    },

    async searchCatalog(q) {
        const res = await fetch(`${this.base}/api/store/search?q=${encodeURIComponent(q)}`);
        return res.json();
    },

    // === 我的宠物 ===
    async listPets() {
        const res = await fetch(`${this.base}/api/pets/`);
        return res.json();
    },

    async getActivePet() {
        const res = await fetch(`${this.base}/api/pets/active`);
        return res.json();
    },

    async activatePet(petId) {
        const res = await fetch(`${this.base}/api/pets/${petId}/activate`, { method: 'POST' });
        return res.json();
    },

    async deletePet(petId) {
        const res = await fetch(`${this.base}/api/pets/${petId}`, { method: 'DELETE' });
        return res.json();
    },

    async getSpriteInfo(petId) {
        const res = await fetch(`${this.base}/api/pets/${petId}/spritesheet`);
        return res.json();
    },

    // === 互动 ===
    async interact(petId, action) {
        const res = await fetch(`${this.base}/api/interact/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pet_id: petId, action }),
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || '操作失败');
        }
        return res.json();
    },

    async getHistory(petId, limit = 20) {
        const res = await fetch(`${this.base}/api/interact/history/${petId}?limit=${limit}`);
        return res.json();
    },
};
