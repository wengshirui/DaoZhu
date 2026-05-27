/**
 * demo6 v2 — 宫廷日记 · 连续动画 + SVG 装饰 + emoji
 * 无幕切换，角色自然进出场，时间轴驱动
 */
(function(){
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
const W = 900, H = 460;
const emojiLayer = document.getElementById('emoji-layer');
const dialogueBox = document.getElementById('dialogue-box');
const dialogueWho = document.getElementById('dialogue-who');
const dialogueText = document.getElementById('dialogue-text');
const narrationEl = document.getElementById('narration');
const sceneLabel = document.getElementById('scene-label');
const sceneTag = document.getElementById('scene-tag');
const directorLine = document.getElementById('director-line');

// SVG 素材缓存
const svgCache = {};
const ASSET = '../assets/';

async function loadSVG(path, color, fill) {
    const key = path+color+fill;
    if (svgCache[key]) return svgCache[key];
    try {
        const r = await fetch(ASSET + path);
        if (!r.ok) return null;
        let s = await r.text();
        if (color) s = s.replace(/stroke="currentColor"/g, `stroke="${color}"`).replace(/stroke="#[0-9a-fA-F]{3,8}"/g, `stroke="${color}"`);
        if (fill) s = s.replace(/fill="none"/g, `fill="${fill}" fill-opacity="0.3"`);
        const img = new Image();
        // 用 data URI 避免 Blob URL 跨域问题
        img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(s)));
        await new Promise((res, rej) => { img.onload = res; img.onerror = rej; });
        svgCache[key] = img;
        return img;
    } catch(e) { console.warn('SVG load failed:', path, e); return null; }
}

// 预加载装饰素材
const decorImgs = {};
async function preloadDecor() {
    const items = [
        ['flower', 'nature/trees/flower.svg', '#ec4899', '#fda4af'],
        ['flower2', 'nature/trees/flower.svg', '#f59e0b', '#fde68a'],
        ['plant', 'nature/trees/plant.svg', '#166534', '#4ade80'],
        ['plant2', 'nature/trees/plant.svg', '#7c3aed', '#c4b5fd'],
        ['lamp', 'props/furniture/lamp.svg', '#d97706', '#fbbf24'],
        ['star', 'nature/sky/star.svg', '#d4a843', '#fde68a'],
        ['cloud', 'nature/sky/cloud.svg', '#94a3b8', '#e2e8f0'],
        ['heart', 'effects/emotions/heart.svg', '#dc2626', '#fca5a5'],
        ['music', 'effects/emotions/music.svg', '#7c3aed', '#c4b5fd'],
        ['sparkle', 'effects/emotions/sparkles.svg', '#d4a843', '#fef3c7'],
        ['sofa', 'props/furniture/sofa.svg', '#92400e', '#d97706'],
        ['armchair', 'props/furniture/armchair.svg', '#78350f', '#a16207'],
        ['book', 'props/items/book.svg', '#1e3a5f', '#60a5fa'],
        ['cup', 'props/items/cup.svg', '#7c3aed', '#c4b5fd'],
        ['moon', 'nature/sky/moon.svg', '#d4a843', '#fef3c7'],
        ['sunrise', 'nature/sky/sunrise.svg', '#f59e0b', '#fde68a'],
    ];
    for (const [id, path, c, f] of items) {
        decorImgs[id] = await loadSVG(path, c, f);
    }
}

// ===== 角色 =====
const CHARS = {
    liuzhu:    { color:'#ec4899', label:'江映柳' },
    shufei:    { color:'#7c3aed', label:'淑妃' },
    princess:  { color:'#f59e0b', label:'三公主', scale:0.7 },
    empress:   { color:'#dc2626', label:'皇后' },
    wenzhaoyi: { color:'#0891b2', label:'温昭仪' },
    chenguifei:{ color:'#991b1b', label:'陈贵妃' },
};

// 角色运行时状态
const actors = {};
function initActors() {
    for (const [id, c] of Object.entries(CHARS)) {
        actors[id] = { x: -60, y: 300, opacity: 0, arm: 'normal', scale: c.scale||1, targetX: -60, targetY: 300, targetOpacity: 0 };
    }
}

// ===== 火柴人绘制 =====
function drawChar(id) {
    const c = CHARS[id];
    const a = actors[id];
    if (a.opacity < 0.03) return;

    ctx.save();
    ctx.globalAlpha = a.opacity;
    const x = a.x, y = a.y, s = a.scale;

    // 头
    ctx.fillStyle = c.color;
    ctx.beginPath();
    ctx.arc(x, y-36*s, 12*s, 0, Math.PI*2);
    ctx.fill();

    // 身体
    ctx.strokeStyle = c.color;
    ctx.lineWidth = 2.5*s;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(x, y-24*s);
    ctx.lineTo(x, y+16*s);
    ctx.stroke();

    // 手臂
    ctx.beginPath();
    const arm = a.arm;
    if (arm==='up') { ctx.moveTo(x-16*s,y-20*s); ctx.lineTo(x,y-12*s); ctx.lineTo(x+16*s,y-20*s); }
    else if (arm==='hip') { ctx.moveTo(x-14*s,y); ctx.lineTo(x-6*s,y-10*s); ctx.moveTo(x+6*s,y-10*s); ctx.lineTo(x+14*s,y); }
    else if (arm==='point') { ctx.moveTo(x-14*s,y+2*s); ctx.lineTo(x,y-10*s); ctx.lineTo(x+22*s,y-14*s); }
    else if (arm==='hug') { ctx.moveTo(x-18*s,y-4*s); ctx.lineTo(x,y-10*s); ctx.lineTo(x+18*s,y-4*s); }
    else if (arm==='wave') { ctx.moveTo(x-14*s,y+2*s); ctx.lineTo(x,y-10*s); ctx.lineTo(x+18*s,y-24*s); }
    else { ctx.moveTo(x-14*s,y+4*s); ctx.lineTo(x,y-10*s); ctx.lineTo(x+14*s,y+4*s); }
    ctx.stroke();

    // 腿
    ctx.beginPath();
    // 走路时腿动
    if (Math.abs(a.x - a.targetX) > 3) {
        const t = Date.now()*0.006;
        ctx.moveTo(x-10*s+Math.sin(t)*5*s, y+34*s);
        ctx.lineTo(x, y+16*s);
        ctx.lineTo(x+10*s-Math.sin(t)*5*s, y+34*s);
    } else {
        ctx.moveTo(x-10*s, y+34*s); ctx.lineTo(x, y+16*s); ctx.lineTo(x+10*s, y+34*s);
    }
    ctx.stroke();

    // 名牌
    ctx.font = `bold ${9*s}px "ZCOOL KuaiLe", sans-serif`;
    ctx.textAlign = 'center';
    ctx.fillStyle = 'rgba(0,0,0,0.5)';
    ctx.fillText(c.label, x, y-52*s);

    ctx.restore();
}

// ===== 场景背景 + SVG 装饰 =====
let currentBg = 'palace';
function drawBg() {
    ctx.clearRect(0, 0, W, H);

    if (currentBg === 'palace') {
        // 宫殿暖色
        const g = ctx.createLinearGradient(0,0,0,H);
        g.addColorStop(0, '#fef3c7');
        g.addColorStop(0.55, '#fde68a');
        g.addColorStop(0.56, '#92400e');
        g.addColorStop(1, '#78350f');
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, W, H);

        // 柱子
        ctx.fillStyle = '#7c2d12';
        ctx.fillRect(50, 30, 14, H-70);
        ctx.fillRect(W-64, 30, 14, H-70);

        // 地砖纹
        ctx.strokeStyle = 'rgba(0,0,0,0.04)';
        ctx.lineWidth = 1;
        for (let x=0;x<W;x+=55) { ctx.beginPath(); ctx.moveTo(x,H*0.56); ctx.lineTo(x,H); ctx.stroke(); }

        // SVG 装饰 — 更大更明显
        const d = (img, x, y, w, h, alpha) => {
            if (!img) return;
            ctx.globalAlpha = alpha || 0.7;
            ctx.drawImage(img, x, y, w, h);
            ctx.globalAlpha = 1;
        };

        // 左侧装饰
        d(decorImgs.flower, 70, 50, 40, 40, 0.7);
        d(decorImgs.plant, 90, 170, 36, 56, 0.6);
        d(decorImgs.lamp, 120, 120, 30, 50, 0.8);

        // 右侧装饰
        d(decorImgs.flower2, W-110, 50, 40, 40, 0.7);
        d(decorImgs.plant2, W-130, 170, 36, 56, 0.6);
        d(decorImgs.lamp, W-150, 120, 30, 50, 0.8);

        // 中央上方装饰
        d(decorImgs.sparkle, W/2-20, 20, 40, 40, 0.5);

        // 家具（下方）
        d(decorImgs.sofa, 160, H*0.56-30, 60, 40, 0.5);
        d(decorImgs.armchair, W-220, H*0.56-28, 50, 38, 0.5);

        // 小物件
        d(decorImgs.book, 180, H*0.56-8, 22, 22, 0.4);
        d(decorImgs.cup, W-180, H*0.56-10, 20, 20, 0.4);

        // 屏风（中央装饰）
        ctx.fillStyle = 'rgba(139,26,26,0.12)';
        ctx.fillRect(W/2-70, 40, 140, 90);
        ctx.strokeStyle = 'rgba(185,28,28,0.3)';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(W/2-70, 40, 140, 90);
        // 屏风上的 SVG 装饰
        d(decorImgs.sunrise, W/2-25, 55, 50, 50, 0.6);
    }
}

// ===== emoji 弹出 =====
function popEmoji(emoji, charId) {
    const a = actors[charId];
    if (!a || a.opacity < 0.1) return;
    const el = document.createElement('div');
    el.className = 'emoji-pop';
    el.textContent = emoji;
    el.style.left = (a.x/W*100) + '%';
    el.style.top = ((a.y-70)/H*100) + '%';
    emojiLayer.appendChild(el);
    setTimeout(() => el.remove(), 2600);
}

// ===== UI =====
function showDialogue(who, text) {
    if (!text) { dialogueBox.classList.remove('show'); return; }
    dialogueWho.textContent = who ? who+'：' : '';
    dialogueText.textContent = text;
    dialogueBox.classList.add('show');
}
function showNarration(text) {
    narrationEl.textContent = text||'';
    narrationEl.classList.toggle('show', !!text);
}

// ===== 时间轴（连续动画，无幕切换）=====
// 节奏原则：每段对话/旁白后留 4-5 秒阅读时间，角色入场后留 2 秒定格
const TIMELINE = [
    // --- 入宫（0-10s）---
    { t:0, action:'label', text:'📍 怡华宫' },
    { t:0, action:'narr', text:'我叫江映柳，今年十四岁。万万没想到，我被赶鸭子上架进了宫，封了美人，住进怡华宫。' },
    { t:1500, action:'enter', id:'liuzhu', x:450, y:280 },
    { t:3000, action:'enter', id:'shufei', x:250, y:270 },
    { t:4500, action:'emoji', id:'liuzhu', e:'😵‍💫' },
    { t:6000, action:'emoji', id:'shufei', e:'🍳' },
    { t:7000, action:'dialogue', who:'旁白', text:'淑妃爱做饭，我凭衷心赞美获得了她的欢心。' },

    // --- 三公主吃饭（11-22s）---
    { t:12000, action:'narr', text:'四月初一。淑妃在中气十足地大骂三公主——' },
    { t:12000, action:'arm', id:'shufei', arm:'point' },
    { t:14000, action:'enter', id:'princess', x:420, y:310 },
    { t:15000, action:'emoji', id:'shufei', e:'😤' },
    { t:16500, action:'emoji', id:'princess', e:'😭' },
    { t:17500, action:'dialogue', who:'三公主', text:'"美人姐姐救命！我母妃疯了！"' },
    { t:20000, action:'emoji', id:'liuzhu', e:'😅' },
    { t:21500, action:'arm', id:'shufei', arm:'normal' },

    // --- 请安（23-36s）---
    { t:23000, action:'label', text:'📍 未央宫' },
    { t:23000, action:'narr', text:'皇后娘娘真好看啊，跟天上的仙女儿似的。陈贵妃全场找茬十分不和谐。' },
    { t:23000, action:'exit', id:'princess' },
    { t:24500, action:'enter', id:'empress', x:350, y:255 },
    { t:26000, action:'enter', id:'chenguifei', x:130, y:275 },
    { t:27500, action:'emoji', id:'empress', e:'👑' },
    { t:28500, action:'emoji', id:'liuzhu', e:'😍' },
    { t:30000, action:'arm', id:'chenguifei', arm:'point' },
    { t:30500, action:'emoji', id:'chenguifei', e:'😤' },
    { t:31500, action:'dialogue', who:'陈贵妃', text:'"你们进宫一个月了连皇上的面也没见着，丢不丢人！"' },

    // --- 淑妃吐槽（37-48s）---
    { t:37000, action:'label', text:'📍 怡华宫' },
    { t:37000, action:'exit', id:'empress' },
    { t:37000, action:'exit', id:'chenguifei' },
    { t:38000, action:'narr', text:'回到怡华宫，淑妃瘫在躺椅上骂道——' },
    { t:39500, action:'arm', id:'shufei', arm:'hip' },
    { t:40000, action:'emoji', id:'shufei', e:'🤬' },
    { t:41500, action:'dialogue', who:'淑妃', text:'"陈彩容那个蠢货！喜欢皇上是不会有好下场的！千万不能喜欢皇上！"' },
    { t:44000, action:'emoji', id:'liuzhu', e:'🥺' },

    // --- 淑妃教导（48-58s）---
    { t:48000, action:'arm', id:'shufei', arm:'hug' },
    { t:48000, action:'move', id:'shufei', x:350, y:270 },
    { t:49000, action:'narr', text:'淑妃把我当半个女儿半个妹妹看，语重心长地叮嘱。' },
    { t:51000, action:'emoji', id:'shufei', e:'💕' },
    { t:53000, action:'dialogue', who:'淑妃', text:'"小柳儿千万不要喜欢皇上！这不是有病么？"' },
    { t:56000, action:'emoji', id:'liuzhu', e:'😊' },

    // --- 温昭仪 + 大餐（58-72s）---
    { t:59000, action:'label', text:'📍 未央宫 · 午饭' },
    { t:59000, action:'narr', text:'淑妃做了一桌好菜。温昭仪一边吃一边夸，我跟三公主吃得连头都顾不上抬。' },
    { t:59000, action:'arm', id:'shufei', arm:'up' },
    { t:60500, action:'enter', id:'wenzhaoyi', x:600, y:270 },
    { t:61500, action:'enter', id:'empress', x:700, y:260 },
    { t:62500, action:'enter', id:'princess', x:520, y:310 },
    { t:64000, action:'emoji', id:'shufei', e:'🍲' },
    { t:65500, action:'emoji', id:'liuzhu', e:'😋' },
    { t:66500, action:'emoji', id:'princess', e:'😋' },
    { t:67500, action:'emoji', id:'wenzhaoyi', e:'👍' },
    { t:69000, action:'dialogue', who:'温昭仪', text:'"阿柔你别的不行，做菜还是顶好吃的。"' },
    { t:70500, action:'emoji', id:'empress', e:'😊' },

    // --- 温昭仪被召（73-86s）---
    { t:73000, action:'exit', id:'empress' },
    { t:73000, action:'exit', id:'princess' },
    { t:74000, action:'narr', text:'温昭仪的掌事姑姑来报：皇上传了口谕让您晚上侍寝。温昭仪瞬间变脸。' },
    { t:76000, action:'arm', id:'wenzhaoyi', arm:'up' },
    { t:76500, action:'emoji', id:'wenzhaoyi', e:'🤯' },
    { t:78000, action:'dialogue', who:'温昭仪', text:'"皇帝老儿做甚要这么招人讨厌！我的鹤腿还差两条就绣好了！"' },
    { t:81000, action:'emoji', id:'shufei', e:'😂' },
    { t:82500, action:'emoji', id:'liuzhu', e:'😶' },

    // --- 结束（86-92s）---
    { t:86000, action:'narr', text:'我就这样打入高层，成了小圈子中的一员。淑妃说明天给温昭仪做个糖蒸酥酪。真是可喜可贺。' },
    { t:86000, action:'dialogue', who:'', text:'' },
    { t:88000, action:'emoji', id:'liuzhu', e:'🎉' },
    { t:89500, action:'emoji', id:'shufei', e:'🍰' },
    { t:92000, action:'end' },
];

// ===== 时间轴执行器 =====
let startTime = 0;
let nextEventIdx = 0;
let playing = false;

function processEvents() {
    if (!playing) return;
    const elapsed = Date.now() - startTime;

    while (nextEventIdx < TIMELINE.length && TIMELINE[nextEventIdx].t <= elapsed) {
        const ev = TIMELINE[nextEventIdx];
        switch (ev.action) {
            case 'enter':
                actors[ev.id].targetX = ev.x;
                actors[ev.id].targetY = ev.y;
                actors[ev.id].targetOpacity = 1;
                break;
            case 'exit':
                actors[ev.id].targetX = ev.x ?? (actors[ev.id].x > W/2 ? W+60 : -60);
                actors[ev.id].targetOpacity = 0;
                break;
            case 'move':
                actors[ev.id].targetX = ev.x;
                if (ev.y) actors[ev.id].targetY = ev.y;
                break;
            case 'arm':
                actors[ev.id].arm = ev.arm;
                break;
            case 'emoji':
                popEmoji(ev.e, ev.id);
                break;
            case 'dialogue':
                showDialogue(ev.who, ev.text);
                break;
            case 'narr':
                showNarration(ev.text);
                break;
            case 'label':
                sceneLabel.textContent = ev.text;
                // 场景切换时清除旧对话
                showDialogue('', '');
                break;
            case 'end':
                playing = false;
                directorLine.textContent = '🏁 全剧终 — 可喜可贺，打入高层！';
                break;
        }
        nextEventIdx++;
    }

    // 更新进度
    if (playing) {
        const total = TIMELINE[TIMELINE.length-1].t;
        const pct = Math.min(100, elapsed/total*100);
        sceneTag.textContent = `${Math.floor(pct)}%`;
    }
}

// ===== 物理更新（平滑移动）=====
function updateActors() {
    const speed = 0.05;
    for (const id of Object.keys(actors)) {
        const a = actors[id];
        a.x += (a.targetX - a.x) * speed;
        a.y += (a.targetY - a.y) * speed;
        a.opacity += (a.targetOpacity - a.opacity) * speed;
    }
}

// ===== 渲染循环 =====
function render() {
    processEvents();
    updateActors();
    drawBg();
    for (const id of Object.keys(actors)) {
        drawChar(id);
    }
    requestAnimationFrame(render);
}

// ===== 控制 =====
function start() {
    initActors();
    emojiLayer.innerHTML = '';
    showDialogue('','');
    showNarration('');
    sceneLabel.textContent = '';
    directorLine.textContent = '🎬 播放中...';
    startTime = Date.now();
    nextEventIdx = 0;
    playing = true;
}

function reset() {
    start();
}

// ===== 启动 =====
function init() {
    preloadDecor().then(() => {
        initActors();
        document.getElementById('btn-replay').addEventListener('click', reset);
        render();
        setTimeout(start, 800);
    });
}

init();

})();
