/**
 * 桌面宠物 — API 封装
 */
const PetAPI = {
    // === 商店（下载） ===
    async downloadPet(name) {
        const res = await fetch(`/api/store/download?name=${encodeURIComponent(name)}`, { method: 'POST' });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || '下载失败');
        }
        return res.json();
    },

    async listLocalPets() {
        const res = await fetch('/api/store/local');
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
