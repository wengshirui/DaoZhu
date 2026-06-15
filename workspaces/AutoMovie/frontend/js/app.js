/**
 * 火柴人剧场 — 前端逻辑（#083 三级模式升级）
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
const btnGenerateVideo = document.getElementById('btn-generate-video');
const btnPreview = document.getElementById('btn-preview');
const statusEl = document.getElementById('status');
const worksList = document.getElementById('works-list');
const fileInput = document.getElementById('file-input');

// 字数统计
textInput.addEventListener('input', () => {
    const len = textInput.value.length;
    charCount.textContent = `${len} / 10000 字`;
    charCount.style.color = len > 10000 ? '#dc2626' : '';
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

// === 模式检测 & 设置面板 ===
async function detectMode() {
    try {
        const resp = await fetch(API_BASE + 'generate/mode');
        const data = await resp.json();
        const label = document.getElementById('mode-label');
        const icons = { simple: '⚡', medium: '🎬', advanced: '✨' };
        label.textContent = `${icons[data.mode] || ''} ${data.description}`;
        label.className = 'mode-label mode--' + data.mode;
    } catch (e) {
        document.getElementById('mode-label').textContent = '⚡ 简单模式';
    }
}

document.getElementById('btn-settings').addEventListener('click', () => {
    const panel = document.getElementById('settings-panel');
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    if (panel.style.display === 'block') loadSettings();
});

async function loadSettings() {
    // GLM
    try {
        const resp = await fetch(API_BASE + 'glm/config');
        const data = await resp.json();
        document.getElementById('glm-enabled').checked = data.enabled;
        if (data.has_key) document.getElementById('glm-key-input').placeholder = data.key_preview;
        document.getElementById('glm-status').textContent = data.is_ready ? '✅ 就绪' : '';
    } catch (e) {}
    // Pexels
    try {
        const resp = await fetch(API_BASE + 'pexels/config');
        const data = await resp.json();
        document.getElementById('pexels-status').textContent = data.has_keys ? `✅ ${data.key_count} 个 Key` : '';
    } catch (e) {}
}

document.getElementById('btn-save-glm').addEventListener('click', async () => {
    const key = document.getElementById('glm-key-input').value.trim();
    const enabled = document.getElementById('glm-enabled').checked;
    if (!key && enabled) { alert('请输入 API Key'); return; }
    const resp = await fetch(API_BASE + 'glm/config', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ api_key: key, enabled }),
    });
    const data = await resp.json();
    document.getElementById('glm-status').textContent = data.is_ready ? '✅ 已保存' : '⚠️ 已保存但未启用';
    detectMode();
});

document.getElementById('btn-save-pexels').addEventListener('click', async () => {
    const key = document.getElementById('pexels-key-input').value.trim();
    if (!key) return;
    const resp = await fetch(API_BASE + 'pexels/config', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ api_keys: [key] }),
    });
    const data = await resp.json();
    document.getElementById('pexels-status').textContent = `✅ ${data.key_count} 个 Key`;
    detectMode();
});

// === 生成动画（简单模式 — 原有逻辑）===
btnGenerate.addEventListener('click', async () => {
    const text = textInput.value.trim();
    if (!text) { setStatus('请输入文本', 'error'); return; }
    if (text.length > 10000) { setStatus('文本过长（最多 10000 字）', 'error'); return; }

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

// === 预览分镜（stop_at=storyboard，不花 API 额度）===
btnPreview.addEventListener('click', async () => {
    const text = textInput.value.trim();
    if (!text) { setStatus('请输入文本', 'error'); return; }

    btnPreview.disabled = true;
    setStatus('👁 生成分镜预览中...');

    try {
        const resp = await fetch(API_BASE + 'generate/video', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, title: titleInput.value.trim(), stop_at: 'storyboard' }),
        });
        const data = await resp.json();
        if (data.state === 'complete' && data.storyboard) {
            const sb = data.storyboard;
            const frames = sb.frames || [];
            const chars = sb.characters || [];
            setStatus(
                `✅ 分镜预览: ${frames.length} 帧, ${chars.length} 角色\n` +
                frames.slice(0, 5).map((f, i) => `  ${i+1}. [${f.mood_tag}] ${f.narration.slice(0, 30)}`).join('\n'),
                'success'
            );
        } else {
            setStatus('❌ ' + (data.error || '分镜生成失败'), 'error');
        }
    } catch (e) {
        setStatus('❌ ' + e.message, 'error');
    } finally {
        btnPreview.disabled = false;
    }
});

// === 生成视频（完整 Pipeline）===
btnGenerateVideo.addEventListener('click', async () => {
    const text = textInput.value.trim();
    if (!text) { setStatus('请输入文本', 'error'); return; }
    if (text.length > 10000) { setStatus('文本过长', 'error'); return; }

    btnGenerateVideo.disabled = true;
    const resolution = document.getElementById('resolution-select').value;
    setStatus('🎥 正在生成视频（预计 3-5 分钟）...');

    try {
        const resp = await fetch(API_BASE + 'generate/video', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text,
                title: titleInput.value.trim(),
                mode: 'auto',
                resolution,
                stop_at: 'video',
            }),
        });
        const data = await resp.json();
        if (data.state === 'complete' && data.video_path) {
            setStatus(`✅ 视频生成完成！模式: ${data.mode}`, 'success');
            loadWorks();
        } else {
            setStatus('❌ ' + (data.error || '视频生成失败'), 'error');
        }
    } catch (e) {
        setStatus('❌ ' + e.message, 'error');
    } finally {
        btnGenerateVideo.disabled = false;
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
detectMode();
