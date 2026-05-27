/**
 * 火柴人剧场 — 前端逻辑
 */
const API_BASE = (() => {
    const path = window.location.pathname;
    const dir = path.replace(/\/[^\/]*\.[^\/]*$/, '/');
    return (dir.endsWith('/') ? dir : dir + '/') + 'api/';
})();

const textInput = document.getElementById('text-input');
const titleInput = document.getElementById('title-input');
const charCount = document.getElementById('char-count');
const btnGenerate = document.getElementById('btn-generate');
const statusEl = document.getElementById('status');
const worksList = document.getElementById('works-list');
const fileInput = document.getElementById('file-input');

// 字数统计
textInput.addEventListener('input', () => {
    const len = textInput.value.length;
    charCount.textContent = `${len} / 5000 字`;
    charCount.style.color = len > 5000 ? '#dc2626' : '';
});

// 上传 TXT
fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const text = await file.text();
    textInput.value = text;
    titleInput.value = file.name.replace('.txt', '');
    textInput.dispatchEvent(new Event('input'));
    setStatus('✅ 文件已加载', 'success');
});

// 生成动画
btnGenerate.addEventListener('click', async () => {
    const text = textInput.value.trim();
    if (!text) { setStatus('请输入文本', 'error'); return; }
    if (text.length > 5000) { setStatus('文本过长（最多 5000 字）', 'error'); return; }

    btnGenerate.disabled = true;
    setStatus('🎬 AI 正在生成动画，请稍候（约 10-30 秒）...');

    try {
        const resp = await fetch(API_BASE + 'generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, title: titleInput.value.trim() }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || '生成失败');
        }
        const data = await resp.json();
        setStatus(`✅ 生成成功！动画时长 ${Math.round(data.duration/1000)} 秒`, 'success');
        loadWorks();
    } catch (e) {
        setStatus('❌ ' + e.message, 'error');
    } finally {
        btnGenerate.disabled = false;
    }
});

// 加载作品列表
async function loadWorks() {
    try {
        const resp = await fetch(API_BASE + 'works');
        const data = await resp.json();
        if (data.works.length === 0) {
            worksList.innerHTML = '<div style="color:#8a7a6a;font-size:0.85rem">暂无作品，输入文本生成第一个动画吧！</div>';
            return;
        }
        worksList.innerHTML = data.works.map(w => `
            <div class="work-card">
                <div class="work-card__info">
                    <div class="work-card__title">🎬 ${w.title}</div>
                    <div class="work-card__meta">${formatSize(w.size)} · ${formatTime(w.created)}</div>
                </div>
                <div class="work-card__actions">
                    <a href="${API_BASE.replace('api/','output/')}${w.filename}" target="_blank">▶ 预览</a>
                    <a href="${API_BASE.replace('api/','output/')}${w.filename}" download>⬇ 下载</a>
                    <button class="del" onclick="deleteWork('${w.filename}')">🗑</button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        worksList.innerHTML = '<div style="color:#dc2626;font-size:0.85rem">加载失败</div>';
    }
}

async function deleteWork(filename) {
    if (!confirm('确定删除？')) return;
    await fetch(API_BASE + 'works/' + filename, { method: 'DELETE' });
    loadWorks();
}

function setStatus(text, type) {
    statusEl.textContent = text;
    statusEl.className = 'status' + (type ? ' ' + type : '');
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + 'B';
    return (bytes / 1024).toFixed(1) + 'KB';
}

function formatTime(ts) {
    const d = new Date(ts * 1000);
    return `${d.getMonth()+1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2,'0')}`;
}

// 初始化
loadWorks();
