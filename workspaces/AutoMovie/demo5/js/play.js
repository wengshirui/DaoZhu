/**
 * demo5 — 极简火柴人 + emoji 表情 + 动作为王
 * 原则：Less is More. 用位移、抖动、缩放表达情感。
 */
(function(){
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
const W = 880, H = 440;
const emotionEl = document.getElementById('emotion');
const narrationEl = document.getElementById('narration');
const sceneTag = document.getElementById('scene-tag');
const directorLine = document.getElementById('director-line');

// ===== 角色（火柴人）=====
const father = { x: 350, y: 260, color: '#1a1a2e', label: '父亲', shake: 0, scale: 1, opacity: 1, armAngle: 0 };
const son = { x: 560, y: 260, color: '#1e40af', label: '我', shake: 0, scale: 1, opacity: 1, armAngle: 0 };

// ===== 绘制火柴人 =====
function drawStickman(p, state) {
    if (p.opacity <= 0.05) return;
    ctx.save();
    ctx.globalAlpha = p.opacity;
    const x = p.x + (p.shake ? (Math.random()-0.5)*p.shake : 0);
    const y = p.y;
    const s = p.scale;

    // 头（圆）
    ctx.fillStyle = p.color;
    ctx.beginPath();
    ctx.arc(x, y - 40*s, 14*s, 0, Math.PI*2);
    ctx.fill();

    // 身体（线）
    ctx.strokeStyle = p.color;
    ctx.lineWidth = 3*s;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(x, y - 26*s);
    ctx.lineTo(x, y + 20*s);
    ctx.stroke();

    // 手臂
    ctx.beginPath();
    if (state === 'climbing') {
        // 双手举起
        ctx.moveTo(x - 20*s, y - 30*s);
        ctx.lineTo(x, y - 14*s);
        ctx.lineTo(x + 20*s, y - 28*s);
    } else if (state === 'carrying') {
        // 抱东西
        ctx.moveTo(x - 18*s, y);
        ctx.lineTo(x, y - 8*s);
        ctx.lineTo(x + 18*s, y);
    } else if (state === 'helping') {
        // 伸手搀扶
        ctx.moveTo(x - 24*s, y - 6*s);
        ctx.lineTo(x, y - 14*s);
        ctx.lineTo(x + 16*s, y - 10*s);
    } else if (state === 'waving') {
        // 挥手告别
        ctx.moveTo(x - 16*s, y - 4*s);
        ctx.lineTo(x, y - 14*s);
        ctx.moveTo(x, y - 14*s);
        ctx.lineTo(x + 20*s, y - 26*s);
    } else {
        // 自然
        ctx.moveTo(x - 16*s, y + 4*s);
        ctx.lineTo(x, y - 14*s);
        ctx.lineTo(x + 16*s, y + 4*s);
    }
    ctx.stroke();

    // 腿
    ctx.beginPath();
    if (state === 'walking') {
        const t = Date.now() * 0.005;
        ctx.moveTo(x - 12*s + Math.sin(t)*6*s, y + 40*s);
        ctx.lineTo(x, y + 20*s);
        ctx.lineTo(x + 12*s - Math.sin(t)*6*s, y + 40*s);
    } else if (state === 'climbing') {
        ctx.moveTo(x - 8*s, y + 30*s);
        ctx.lineTo(x, y + 20*s);
        ctx.lineTo(x + 8*s, y + 26*s);
    } else {
        ctx.moveTo(x - 12*s, y + 40*s);
        ctx.lineTo(x, y + 20*s);
        ctx.lineTo(x + 12*s, y + 40*s);
    }
    ctx.stroke();

    // 名牌
    ctx.font = `bold ${10*s}px "Noto Serif SC", serif`;
    ctx.fillStyle = 'rgba(0,0,0,0.6)';
    ctx.textAlign = 'center';
    ctx.fillText(p.label, x, y - 58*s);

    ctx.restore();
}

// ===== 场景绘制 =====
function drawScene() {
    ctx.clearRect(0, 0, W, H);

    // 天空（淡灰，冬日）
    const sky = ctx.createLinearGradient(0,0,0,H*0.6);
    sky.addColorStop(0, '#d4d8dc');
    sky.addColorStop(1, '#c8c0b4');
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, W, H*0.6);

    // 地面（月台）
    ctx.fillStyle = '#a89078';
    ctx.fillRect(0, H*0.6, W, H*0.4);

    // 铁道（简单两条线）
    ctx.strokeStyle = '#5c4030';
    ctx.lineWidth = 3;
    ctx.setLineDash([16, 8]);
    ctx.beginPath();
    ctx.moveTo(0, H*0.6);
    ctx.lineTo(W, H*0.6);
    ctx.stroke();
    ctx.setLineDash([]);

    // 火车（极简：一个长方形 + 几个窗）
    ctx.fillStyle = '#4b5563';
    ctx.beginPath();
    ctx.roundRect(500, 50, 360, 120, 8);
    ctx.fill();
    // 车窗（暖黄色小方块）
    ctx.fillStyle = '#fef3c7';
    for (let i = 0; i < 5; i++) {
        ctx.fillRect(520 + i*65, 75, 40, 30);
    }

    // 月台边缘标线
    ctx.fillStyle = '#f5e6c8';
    ctx.fillRect(0, H*0.6 - 4, W, 4);

    // 远处几个小火柴人（人群暗影）
    ctx.globalAlpha = 0.2;
    for (let i = 0; i < 6; i++) {
        const px = 650 + i * 30 + Math.sin(i)*10;
        miniStick(ctx, px, 250, '#333');
    }
    ctx.globalAlpha = 1;
}

function miniStick(ctx, x, y, color) {
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.arc(x, y-10, 4, 0, Math.PI*2); ctx.fill();
    ctx.beginPath(); ctx.moveTo(x,y-6); ctx.lineTo(x,y+8); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x-5,y); ctx.lineTo(x+5,y); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x-4,y+14); ctx.lineTo(x,y+8); ctx.lineTo(x+4,y+14); ctx.stroke();
}

// ===== 橘子 =====
let oranges = { visible: false, x: 0, y: 0 };
function drawOranges() {
    if (!oranges.visible) return;
    ctx.save();
    // 三个圆 = 橘子
    const colors = ['#ea580c', '#f97316', '#dc2626'];
    for (let i = 0; i < 3; i++) {
        ctx.fillStyle = colors[i];
        ctx.beginPath();
        ctx.arc(oranges.x + i*12 - 12, oranges.y, 7, 0, Math.PI*2);
        ctx.fill();
        // 小绿蒂
        ctx.fillStyle = '#16a34a';
        ctx.fillRect(oranges.x + i*12 - 14, oranges.y - 8, 3, 3);
    }
    ctx.restore();
}

// ===== 剧本 =====
const SCENES = [
    { note:'车站送别', narr:'父亲因为事忙，本已说定不送我。他踌躇了一会，终于决定还是自己送我去。',
      emoji:'🤝', emoTarget:'father',
      father:{x:350,y:260,state:'standing'}, son:{x:560,y:260,state:'standing'},
      dialogue:'"不要紧，他们去不好！"', dur:5000 },

    { note:'照看行李', narr:'他给我拣定了靠车门的一张椅子。他嘱我路上小心，夜里警醒些，不要受凉。',
      emoji:'🧳', emoTarget:'father',
      father:{x:480,y:260,state:'walking'}, son:{x:560,y:260,state:'standing'},
      dialogue:'"路上小心，不要受凉。"', dur:5000 },

    { note:'买橘子', narr:'"我买几个橘子去。你就在此地，不要走动。"',
      emoji:'🍊', emoTarget:'father',
      father:{x:420,y:260,state:'standing'}, son:{x:560,y:260,state:'standing'},
      dialogue:'"我买几个橘子去。你就在此地，不要走动。"', dur:4500 },

    { note:'走向铁道', narr:'我看见他戴着黑布小帽，穿着黑布大马褂，蹒跚地走到铁道边。',
      emoji:'🚶', emoTarget:'father',
      father:{x:250,y:270,state:'walking',shake:2}, son:{x:560,y:260,state:'standing'},
      dialogue:'', dur:4500 },

    { note:'攀爬月台', narr:'他用两手攀着上面，两脚再向上缩；他肥胖的身子向左微倾，显出努力的样子。这时我看见他的背影，我的泪很快地流下来了。',
      emoji:'😢', emoTarget:'son',
      father:{x:180,y:230,state:'climbing',shake:3,scale:1.1}, son:{x:560,y:260,state:'standing'},
      dialogue:'', dur:6000 },

    { note:'橘子与搀扶', narr:'到这边时，我赶紧去搀他。他和我走到车上，将橘子一股脑儿放在我的皮大衣上。',
      emoji:'🍊', emoTarget:'son',
      father:{x:420,y:260,state:'carrying',shake:0,scale:1}, son:{x:460,y:260,state:'helping'},
      showOranges:{x:440,y:310}, dialogue:'', dur:5000 },

    { note:'离别', narr:'于是扑扑衣上的泥土，心里很轻松似的，过一会说，"我走了，到那边来信！"',
      emoji:'👋', emoTarget:'father',
      father:{x:480,y:260,state:'waving'}, son:{x:560,y:260,state:'standing'},
      dialogue:'"我走了，到那边来信！"', dur:5000 },

    { note:'背影远去', narr:'等他的背影混入来来往往的人里，再找不着了，我便进来坐下，我的眼泪又来了。',
      emoji:'😭', emoTarget:'son',
      father:{x:60,y:260,state:'walking',opacity:0.15,scale:0.6}, son:{x:560,y:260,state:'standing'},
      dialogue:'"进去吧，里边没人。"', dur:6500 }
];

// ===== 动画系统 =====
let currentIdx = 0;
let timer = null;
let fatherState = 'standing';
let sonState = 'standing';

// 平滑插值
const lerp = (a, b, t) => a + (b - a) * t;
let targetFather = {...father};
let targetSon = {...son};

function updatePositions() {
    const speed = 0.03;
    father.x = lerp(father.x, targetFather.x, speed);
    father.y = lerp(father.y, targetFather.y, speed);
    father.scale = lerp(father.scale, targetFather.scale || 1, speed);
    father.opacity = lerp(father.opacity, targetFather.opacity ?? 1, speed);
    father.shake = targetFather.shake || 0;

    son.x = lerp(son.x, targetSon.x, speed);
    son.y = lerp(son.y, targetSon.y, speed);
}

function showEmotion(emoji, target) {
    const ref = target === 'father' ? father : son;
    emotionEl.textContent = emoji;
    emotionEl.style.left = (ref.x / W * 100 - 2) + '%';
    emotionEl.style.top = ((ref.y - 80) / H * 100) + '%';
    emotionEl.classList.add('show');
    setTimeout(() => emotionEl.classList.remove('show'), 3000);
}

function showNarration(text) {
    narrationEl.textContent = text;
    narrationEl.classList.toggle('show', !!text);
}

// ===== 播放 =====
function playScene(idx) {
    if (idx >= SCENES.length) {
        directorLine.textContent = '🏁 唉！我不知何时再能与他相见！';
        showNarration('唉！我不知何时再能与他相见！');
        return;
    }
    currentIdx = idx;
    const s = SCENES[idx];

    sceneTag.textContent = `第${idx+1}幕`;
    directorLine.textContent = `🎬 ${s.note}` + (s.dialogue ? ` — ${s.dialogue}` : '');
    showNarration(s.narr);

    // 设置目标位置
    targetFather = { x:s.father.x, y:s.father.y, scale:s.father.scale||1, opacity:s.father.opacity??1, shake:s.father.shake||0 };
    fatherState = s.father.state || 'standing';
    targetSon = { x:s.son.x, y:s.son.y, scale:s.son.scale||1, opacity:s.son.opacity??1 };
    sonState = s.son.state || 'standing';

    // 橘子
    if (s.showOranges) { oranges.visible = true; oranges.x = s.showOranges.x; oranges.y = s.showOranges.y; }

    // 表情
    setTimeout(() => showEmotion(s.emoji, s.emoTarget), 800);

    if (timer) clearTimeout(timer);
    timer = setTimeout(() => playScene(idx+1), s.dur);
}

function reset() {
    if (timer) clearTimeout(timer);
    father.x = 350; father.y = 260; father.scale = 1; father.opacity = 1; father.shake = 0;
    son.x = 560; son.y = 260; son.scale = 1; son.opacity = 1;
    targetFather = {...father}; targetSon = {...son};
    fatherState = 'standing'; sonState = 'standing';
    oranges.visible = false;
    emotionEl.classList.remove('show');
    narrationEl.classList.remove('show');
    setTimeout(() => playScene(0), 400);
}

// ===== 渲染循环 =====
function render() {
    updatePositions();
    drawScene();
    drawOranges();
    drawStickman(father, fatherState);
    drawStickman(son, sonState);
    requestAnimationFrame(render);
}

// ===== 启动 =====
document.getElementById('btn-replay').addEventListener('click', reset);
render();
setTimeout(() => playScene(0), 800);
})();
