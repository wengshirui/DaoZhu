/**
 * demo6 — 宫廷日记 · 火柴人 + emoji + Limited Animation
 * 多角色、对话密集、情绪丰富
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

// ===== 角色定义 =====
const CHARS = {
    liuzhu: { x:420, y:280, color:'#ec4899', label:'江映柳', emoji:'😊' },
    shufei: { x:250, y:270, color:'#7c3aed', label:'淑妃', emoji:'🍳' },
    princess: { x:500, y:310, color:'#f59e0b', label:'三公主', emoji:'👶', scale:0.7 },
    empress: { x:350, y:260, color:'#dc2626', label:'皇后', emoji:'👑' },
    wenzhaoyi: { x:600, y:270, color:'#0891b2', label:'温昭仪', emoji:'🧵' },
    chenguifei: { x:150, y:270, color:'#991b1b', label:'陈贵妃', emoji:'😤' },
};

// 当前在场角色
let onStage = [];
let charStates = {};

// ===== 火柴人绘制 =====
function drawChar(id) {
    const c = CHARS[id];
    const st = charStates[id] || {};
    const x = st.x ?? c.x;
    const y = st.y ?? c.y;
    const s = (c.scale || 1) * (st.scale || 1);
    const opacity = st.opacity ?? 1;
    if (opacity < 0.05) return;

    ctx.save();
    ctx.globalAlpha = opacity;

    // 头
    ctx.fillStyle = c.color;
    ctx.beginPath();
    ctx.arc(x, y - 36*s, 12*s, 0, Math.PI*2);
    ctx.fill();

    // 身体
    ctx.strokeStyle = c.color;
    ctx.lineWidth = 2.5*s;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(x, y - 24*s);
    ctx.lineTo(x, y + 16*s);
    ctx.stroke();

    // 手臂（根据状态）
    ctx.beginPath();
    const arm = st.arm || 'normal';
    if (arm === 'up') {
        ctx.moveTo(x-16*s, y-20*s); ctx.lineTo(x, y-12*s); ctx.lineTo(x+16*s, y-20*s);
    } else if (arm === 'hip') {
        ctx.moveTo(x-14*s, y); ctx.lineTo(x-6*s, y-10*s);
        ctx.moveTo(x+6*s, y-10*s); ctx.lineTo(x+14*s, y);
    } else if (arm === 'point') {
        ctx.moveTo(x-14*s, y+2*s); ctx.lineTo(x, y-10*s); ctx.lineTo(x+22*s, y-14*s);
    } else if (arm === 'hug') {
        ctx.moveTo(x-18*s, y-4*s); ctx.lineTo(x, y-10*s); ctx.lineTo(x+18*s, y-4*s);
    } else {
        ctx.moveTo(x-14*s, y+4*s); ctx.lineTo(x, y-10*s); ctx.lineTo(x+14*s, y+4*s);
    }
    ctx.stroke();

    // 腿
    ctx.beginPath();
    ctx.moveTo(x-10*s, y+34*s); ctx.lineTo(x, y+16*s); ctx.lineTo(x+10*s, y+34*s);
    ctx.stroke();

    // 名牌
    ctx.font = `bold ${9*s}px "ZCOOL KuaiLe", sans-serif`;
    ctx.textAlign = 'center';
    ctx.fillStyle = 'rgba(0,0,0,0.5)';
    ctx.fillText(c.label, x, y - 52*s);

    ctx.restore();
}

// ===== 场景背景 =====
function drawBg(scene) {
    ctx.clearRect(0, 0, W, H);
    const bg = scene.bg || 'palace';

    if (bg === 'palace') {
        // 宫殿内景 — 暖色
        const g = ctx.createLinearGradient(0,0,0,H);
        g.addColorStop(0, '#fef3c7');
        g.addColorStop(0.6, '#fde68a');
        g.addColorStop(1, '#d97706');
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, W, H);

        // 柱子
        ctx.fillStyle = '#92400e';
        ctx.fillRect(60, 40, 16, H-80);
        ctx.fillRect(W-76, 40, 16, H-80);

        // 地面
        ctx.fillStyle = '#78350f';
        ctx.fillRect(0, H*0.72, W, H*0.28);
        // 地砖
        ctx.strokeStyle = 'rgba(0,0,0,0.06)';
        ctx.lineWidth = 1;
        for (let x = 0; x < W; x += 50) {
            ctx.beginPath(); ctx.moveTo(x, H*0.72); ctx.lineTo(x, H); ctx.stroke();
        }

        // 屏风/装饰
        ctx.fillStyle = 'rgba(139,26,26,0.15)';
        ctx.fillRect(W/2-80, 50, 160, 100);
        ctx.strokeStyle = '#b91c1c';
        ctx.lineWidth = 2;
        ctx.strokeRect(W/2-80, 50, 160, 100);
    } else if (bg === 'garden') {
        // 花园
        const g = ctx.createLinearGradient(0,0,0,H);
        g.addColorStop(0, '#bae6fd');
        g.addColorStop(0.5, '#e0f2fe');
        g.addColorStop(1, '#4ade80');
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, W, H);
        // 草地
        ctx.fillStyle = '#16a34a';
        ctx.fillRect(0, H*0.7, W, H*0.3);
    }
}

// ===== emoji 弹出 =====
function popEmoji(emoji, x, y) {
    const el = document.createElement('div');
    el.className = 'emoji-pop';
    el.textContent = emoji;
    el.style.left = (x/W*100) + '%';
    el.style.top = (y/H*100 - 18) + '%';
    emojiLayer.appendChild(el);
    setTimeout(() => el.remove(), 2600);
}

// ===== 对话 =====
function showDialogue(who, text) {
    if (!text) { dialogueBox.classList.remove('show'); return; }
    dialogueWho.textContent = who + '：';
    dialogueText.textContent = text;
    dialogueBox.classList.add('show');
}

function showNarration(text) {
    narrationEl.textContent = text || '';
    narrationEl.classList.toggle('show', !!text);
}

// ===== 剧本 =====
const SCENES = [
    {
        bg:'palace', note:'入宫', label:'怡华宫',
        narr:'我叫江映柳，今年十四岁。万万没想到，选秀前夕两个姐姐出了状况，我被赶鸭子上架进了宫。',
        cast:['liuzhu','shufei'],
        states:{ liuzhu:{x:450,y:280}, shufei:{x:250,y:270} },
        emojis:[{e:'😵‍💫',id:'liuzhu',delay:500},{e:'🍳',id:'shufei',delay:1500}],
        dialogue:{who:'旁白',text:'封了美人，住进怡华宫。淑妃爱做饭，我凭衷心赞美获得了她的欢心。'},
        dur:5500
    },
    {
        bg:'palace', note:'三公主吃饭', label:'怡华宫',
        narr:'淑妃在中气十足地大骂三公主："李嘉乐！你给我好好吃饭！"',
        cast:['shufei','princess','liuzhu'],
        states:{ shufei:{x:200,y:260,arm:'point'}, princess:{x:420,y:310}, liuzhu:{x:550,y:280} },
        emojis:[{e:'😤',id:'shufei',delay:300},{e:'😭',id:'princess',delay:1200},{e:'😅',id:'liuzhu',delay:2000}],
        dialogue:{who:'三公主',text:'"美人姐姐救命！我母妃疯了！"'},
        dur:5500
    },
    {
        bg:'palace', note:'请安', label:'未央宫',
        narr:'皇后娘娘真好看啊，跟天上的仙女儿似的。对比之下，全场找茬的陈贵妃就十分不和谐。',
        cast:['empress','chenguifei','liuzhu','shufei'],
        states:{ empress:{x:350,y:250}, chenguifei:{x:150,y:270,arm:'point'}, liuzhu:{x:550,y:290}, shufei:{x:650,y:280} },
        emojis:[{e:'👑',id:'empress',delay:400},{e:'😤',id:'chenguifei',delay:1200},{e:'😍',id:'liuzhu',delay:800}],
        dialogue:{who:'陈贵妃',text:'"你们进宫一个月了连皇上的面也没见着，丢不丢人！"'},
        dur:6000
    },
    {
        bg:'palace', note:'淑妃吐槽', label:'怡华宫',
        narr:'回到怡华宫，淑妃瘫在躺椅上骂道——',
        cast:['shufei','liuzhu'],
        states:{ shufei:{x:300,y:280,arm:'hip'}, liuzhu:{x:500,y:290} },
        emojis:[{e:'🤬',id:'shufei',delay:500},{e:'😶',id:'liuzhu',delay:1500}],
        dialogue:{who:'淑妃',text:'"陈彩容那个蠢货！找咱们茬做什么！喜欢皇上是不会有好下场的！"'},
        dur:5500
    },
    {
        bg:'palace', note:'淑妃教导', label:'怡华宫',
        narr:'淑妃把我当半个女儿半个妹妹看，语重心长地叮嘱我。',
        cast:['shufei','liuzhu'],
        states:{ shufei:{x:320,y:270,arm:'hug'}, liuzhu:{x:450,y:285} },
        emojis:[{e:'💕',id:'shufei',delay:600},{e:'🥺',id:'liuzhu',delay:1400}],
        dialogue:{who:'淑妃',text:'"小柳儿千万不要喜欢皇上！这不是有病么？"'},
        dur:5000
    },
    {
        bg:'palace', note:'皇后留话', label:'未央宫',
        narr:'皇后娘娘解释了皇上晾着我的原因——他觉得我家推托，看不上皇家。',
        cast:['empress','shufei','liuzhu'],
        states:{ empress:{x:300,y:255}, shufei:{x:480,y:275,arm:'hip'}, liuzhu:{x:600,y:285} },
        emojis:[{e:'🤔',id:'empress',delay:400},{e:'😒',id:'shufei',delay:1200},{e:'😰',id:'liuzhu',delay:1800}],
        dialogue:{who:'淑妃',text:'"呸，小心眼的玩意儿！"'},
        dur:5500
    },
    {
        bg:'palace', note:'温昭仪登场', label:'未央宫',
        narr:'温昭仪正在绣花，一脸厌恶地说要给皇帝送绣坏了的东西。',
        cast:['wenzhaoyi','shufei','empress','liuzhu'],
        states:{ wenzhaoyi:{x:200,y:270}, shufei:{x:380,y:275}, empress:{x:520,y:260}, liuzhu:{x:680,y:285} },
        emojis:[{e:'🧵',id:'wenzhaoyi',delay:400},{e:'😂',id:'shufei',delay:1500},{e:'😅',id:'empress',delay:2000}],
        dialogue:{who:'温昭仪',text:'"我绣坏了的东西比别人绣好的还要好十倍！给皇帝老儿真是便宜他了。"'},
        dur:6000
    },
    {
        bg:'palace', note:'大餐', label:'未央宫',
        narr:'淑妃做了一桌好菜：鹅掌鸭信火腿炖肘子鸡髓笋拔丝山药……我跟三公主吃得连头都顾不上抬。',
        cast:['shufei','liuzhu','princess','wenzhaoyi','empress'],
        states:{ shufei:{x:150,y:265,arm:'up'}, liuzhu:{x:350,y:290}, princess:{x:480,y:310}, wenzhaoyi:{x:620,y:275}, empress:{x:750,y:260} },
        emojis:[{e:'🍲',id:'shufei',delay:300},{e:'😋',id:'liuzhu',delay:800},{e:'😋',id:'princess',delay:1200},{e:'👍',id:'wenzhaoyi',delay:1800},{e:'😊',id:'empress',delay:2200}],
        dialogue:{who:'温昭仪',text:'"阿柔你别的不行，做菜还是顶好吃的。"'},
        dur:6000
    },
    {
        bg:'palace', note:'温昭仪被召', label:'怡华宫',
        narr:'温昭仪的掌事姑姑来报：皇上传了口谕让您晚上侍寝。温昭仪瞬间变脸。',
        cast:['wenzhaoyi','shufei','liuzhu'],
        states:{ wenzhaoyi:{x:350,y:265,arm:'up'}, shufei:{x:550,y:275}, liuzhu:{x:680,y:285} },
        emojis:[{e:'🤯',id:'wenzhaoyi',delay:500},{e:'😂',id:'shufei',delay:1500},{e:'😶',id:'liuzhu',delay:2000}],
        dialogue:{who:'温昭仪',text:'"皇帝老儿做甚要这么招人讨厌！我的鹤腿还差两条就绣好了！"'},
        dur:5500
    },
];

// ===== 动画引擎 =====
let currentIdx = 0;
let timer = null;
let targets = {};

function lerp(a, b, t) { return a + (b-a) * t; }

function updatePositions() {
    for (const id of onStage) {
        const st = charStates[id] || {};
        const tgt = targets[id] || {};
        if (tgt.x !== undefined) st.x = lerp(st.x ?? CHARS[id].x, tgt.x, 0.04);
        if (tgt.y !== undefined) st.y = lerp(st.y ?? CHARS[id].y, tgt.y, 0.04);
        charStates[id] = st;
    }
}

function playScene(idx) {
    if (idx >= SCENES.length) {
        directorLine.textContent = '🏁 全剧终 — 可喜可贺，打入高层！';
        showNarration('我就这样成了高层小圈子中的一员，真是可喜可贺。');
        showDialogue('', '');
        return;
    }
    currentIdx = idx;
    const s = SCENES[idx];

    sceneTag.textContent = `第${idx+1}幕`;
    sceneLabel.textContent = `📍 ${s.label}`;
    directorLine.textContent = `🎬 ${s.note}`;
    showNarration(s.narr);

    // 设置在场角色
    onStage = s.cast;
    targets = {};
    for (const id of s.cast) {
        const st = s.states[id] || {};
        charStates[id] = { x: st.x ?? CHARS[id].x, y: st.y ?? CHARS[id].y, arm: st.arm || 'normal', opacity: 1 };
        targets[id] = { x: st.x, y: st.y };
    }

    // emoji 弹出
    if (s.emojis) {
        for (const em of s.emojis) {
            setTimeout(() => {
                const c = charStates[em.id] || CHARS[em.id];
                popEmoji(em.e, c.x || CHARS[em.id].x, (c.y || CHARS[em.id].y) - 40);
            }, em.delay || 0);
        }
    }

    // 对话
    setTimeout(() => {
        if (s.dialogue) showDialogue(s.dialogue.who, s.dialogue.text);
        else showDialogue('','');
    }, 1000);

    if (timer) clearTimeout(timer);
    timer = setTimeout(() => playScene(idx+1), s.dur);
}

function reset() {
    if (timer) clearTimeout(timer);
    emojiLayer.innerHTML = '';
    onStage = [];
    charStates = {};
    targets = {};
    showDialogue('','');
    showNarration('');
    setTimeout(() => playScene(0), 400);
}

// ===== 渲染循环 =====
function render() {
    const scene = SCENES[currentIdx] || SCENES[0];
    drawBg(scene);
    updatePositions();
    for (const id of onStage) {
        drawChar(id);
    }
    requestAnimationFrame(render);
}

// ===== 启动 =====
document.getElementById('btn-replay').addEventListener('click', reset);
render();
setTimeout(() => playScene(0), 800);
})();
