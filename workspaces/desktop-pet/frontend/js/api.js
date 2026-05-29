/**
 * 桌面宠物 — API 封装 v3
 */
const PetAPI = {
    // === 商店 ===
    async getManifest(page = 1, kind = '') {
        const params = new URLSearchParams({ page, per_page: 24 });
        if (kind) params.set('kind', kind);
        const res = await fetch(`/api/store/manifest?${params}`);
        if (!res.ok) throw new Error('加载失败');
        return res.json();
    },

    async refreshManifest() {
        const res = await fetch('/api/store/refresh', { method: 'POST' });
        return res.json();
    },

    async downloadPet(slug) {
        const res = await fetch(`/api/store/download?slug=${encodeURIComponent(slug)}`, { method: 'POST' });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || '下载失败');
        }
        return res.json();
    },

    async searchPets(q) {
        const res = await fetch(`/api/store/search?q=${encodeURIComponent(q)}`);
        return res.json();
    },

    async getKinds() {
        const res = await fetch('/api/store/kinds');
        if (!res.ok) return [];
        return res.json();
    },

    // === 我的宠物 ===
    async listPets() {
        const res = await fetch('/api/pets/');
        return res.json();
    },

    async getActivePet() {
        const res = await fetch('/api/pets/active');
        return res.json();
    },

    async activatePet(petId) {
        const res = await fetch(`/api/pets/${petId}/activate`, { method: 'POST' });
        return res.json();
    },

    async deletePet(petId) {
        const res = await fetch(`/api/pets/${petId}`, { method: 'DELETE' });
        return res.json();
    },

    async getSpriteInfo(petId) {
        const res = await fetch(`/api/pets/${petId}/spritesheet`);
        return res.json();
    },

    // === 互动 ===
    async interact(petId, action) {
        const res = await fetch('/api/interact/', {
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
};
