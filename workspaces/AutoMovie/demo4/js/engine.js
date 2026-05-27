/**
 * 背影 · 朱自清 — SVG 实体剧场引擎
 * 基于 demo3 架构，演绎散文经典场景
 */
(function () {
    'use strict';

    const ASSET_BASE = '../assets/';

    // 实体定义（火车站月台场景）
    const ENTITIES = {
        train: { type:'prop', src:'vehicles/transport/train.svg', x:60,y:10,w:38,h:45,
            color:'#374151', fill:'#6B7280', label:'火车' },
        fence: { type:'prop', src:'buildings/structures/fence.svg', x:0,y:52,w:100,h:5,
            color:'#78350F', fill:'#92400E', label:'栅栏/铁道' },
        bag: { type:'prop', src:'props/items/book.svg', x:52,y:55,w:4,h:5,
            color:'#78350F', fill:'#D97706', label:'行李' },
        coat: { type:'prop', src:'props/items/umbrella.svg', x:56,y:52,w:3,h:6,
            color:'#4B0082', fill:'#7C3AED', label:'紫毛大衣' },
        oranges: { type:'prop', src:'effects/emotions/heart.svg', x:20,y:56,w:4,h:5,
            color:'#EA580C', fill:'#FB923C', label:'橘子', opacity:0 },
        father: { type:'actor', src:'characters/people/man.svg', x:35,y:35,w:8,h:22,
            color:'#1F2937', fill:'#374151', label:'父亲',
            states: {
                standing:{src:'characters/people/man.svg',color:'#1F2937',fill:'#374151'},
                walking:{src:'characters/people/person-walking.svg',color:'#1F2937',fill:'#374151'}
            }
        },
        son: { type:'actor', src:'characters/people/person-standing.svg', x:55,y:35,w:7,h:20,
            color:'#1E40AF', fill:'#60A5FA', label:'我（儿子）' }
    };

    // 剧本 — 《背影》核心段落
    const SCRIPT = [
        {
            desc: '南京浦口车站，冬日午后。',
            note: '第一幕 — 车站送别',
            narration: '到南京时，父亲因为事忙，本已说定不送我。他踌躇了一会，终于决定还是自己送我去。',
            dialogue: { who:'father', text:'"不要紧，他们去不好！"' },
            actions: [],
            duration: 4000
        },
        {
            desc: '父亲忙着照看行李，和脚夫讲价钱。',
            note: '第二幕 — 照看行李',
            narration: '我买票，他忙着照看行李。他便又忙着和他们讲价钱。他给我拣定了靠车门的一张椅子。',
            dialogue: { who:'father', text:'"路上小心，夜里警醒些，不要受凉。"' },
            actions: [
                { entity:'father', set:{x:48, state:'walking'}, animate:true }
            ],
            duration: 4500
        },
        {
            desc: '父亲要去买橘子。',
            note: '第三幕 — 买橘子',
            narration: '他望车外看了看，说，"我买几个橘子去。你就在此地，不要走动。"',
            dialogue: { who:'father', text:'"我买几个橘子去。你就在此地，不要走动。"' },
            actions: [
                { entity:'father', set:{x:45, state:'standing'} }
            ],
            duration: 4000
        },
        {
            desc: '父亲蹒跚地走到铁道边。',
            note: '第四幕 — 走向铁道',
            narration: '我看见他戴着黑布小帽，穿着黑布大马褂，深青布棉袍，蹒跚地走到铁道边，慢慢探身下去。',
            actions: [
                { entity:'father', set:{x:25, y:45, state:'walking'}, animate:true }
            ],
            duration: 4000
        },
        {
            desc: '父亲攀爬月台 — 这是全文最动人的画面。',
            note: '第五幕 — 攀爬月台（高潮）',
            narration: '他用两手攀着上面，两脚再向上缩；他肥胖的身子向左微倾，显出努力的样子。这时我看见他的背影，我的泪很快地流下来了。',
            actions: [
                { entity:'father', set:{x:18, y:38, w:9, h:24}, animate:true },
                { fx:'tear', at:{x:57, y:38} }
            ],
            duration: 5000
        },
        {
            desc: '父亲抱着朱红的橘子回来了。',
            note: '第六幕 — 橘子',
            narration: '过铁道时，他先将橘子散放在地上，自己慢慢爬下，再抱起橘子走。到这边时，我赶紧去搀他。',
            actions: [
                { entity:'father', set:{x:45, y:35, state:'walking'}, animate:true },
                { entity:'oranges', set:{opacity:1, x:42, y:48} }
            ],
            duration: 4500
        },
        {
            desc: '父亲将橘子放下，准备离去。',
            note: '第七幕 — 离别',
            narration: '他将橘子一股脑儿放在我的皮大衣上。于是扑扑衣上的泥土，心里很轻松似的。',
            dialogue: { who:'father', text:'"我走了，到那边来信！"' },
            actions: [
                { entity:'father', set:{x:50, state:'standing'} },
                { entity:'oranges', set:{x:54, y:52} }
            ],
            duration: 4000
        },
        {
            desc: '父亲的背影消失在人群中。',
            note: '第八幕 — 背影远去',
            narration: '等他的背影混入来来往往的人里，再找不着了，我便进来坐下，我的眼泪又来了。',
            actions: [
                { entity:'father', set:{x:5, y:38, opacity:0.2, w:5, h:14}, animate:true },
                { fx:'tear', at:{x:57, y:37} }
            ],
            duration: 5000
        }
    ];

    // DOM
    const stage = document.getElementById('stage');
    const propsLayer = document.getElementById('props-layer');
    const actorsLayer = document.getElementById('actors-layer');
    const fxLayer = document.getElementById('fx-layer');
    const bubble = document.getElementById('bubble');
    const narrationEl = document.getElementById('narration');
    const sceneInfo = document.getElementById('scene-info');
    const panelScene = document.getElementById('panel-scene');
    const panelNote = document.getElementById('panel-note');
    const btnReplay = document.getElementById('btn-replay');

    const entityEls = {};
    let timer = null;

    // SVG 加载 + 颜色注入
    async function loadSVG(url, color, fill) {
        try {
            const resp = await fetch(url);
            if (!resp.ok) return null;
            let svg = await resp.text();
            if (color) {
                svg = svg.replace(/stroke="currentColor"/g, `stroke="${color}"`);
                svg = svg.replace(/stroke="#[0-9a-fA-F]{3,8}"/g, `stroke="${color}"`);
            }
            if (fill) {
                svg = svg.replace(/fill="none"/g, `fill="${fill}" fill-opacity="0.35"`);
            }
            return svg;
        } catch (e) { return null; }
    }

    function setSVG(el, svgText) {
        el.innerHTML = svgText;
        const s = el.querySelector('svg');
        if (s) { s.style.width='100%'; s.style.height='100%'; s.removeAttribute('width'); s.removeAttribute('height'); }
    }

    // 初始化
    async function initStage() {
        propsLayer.innerHTML = '';
        actorsLayer.innerHTML = '';
        fxLayer.innerHTML = '';
        for (const [id, ent] of Object.entries(ENTITIES)) {
            const el = document.createElement('div');
            el.className = `entity entity--${ent.type==='actor'?'actor':'prop'} fade-in`;
            el.style.left = ent.x + '%';
            el.style.top = ent.y + '%';
            el.style.width = ent.w + '%';
            el.style.height = ent.h + '%';
            if (ent.opacity !== undefined) el.style.opacity = ent.opacity;
            const svg = await loadSVG(ASSET_BASE + ent.src, ent.color, ent.fill);
            if (svg) setSVG(el, svg);
            else el.innerHTML = `<img src="${ASSET_BASE+ent.src}" alt="${ent.label}" style="width:100%;height:100%">`;
            (ent.type === 'actor' ? actorsLayer : propsLayer).appendChild(el);
            entityEls[id] = { el, config:{...ent} };
        }
    }

    // 更新实体
    async function updateEntity(id, props, animate) {
        const entry = entityEls[id];
        if (!entry) return;
        const { el, config } = entry;
        el.style.transition = animate
            ? 'left 3s ease-in-out, top 2s ease, width 1s, height 1s, opacity 1.5s'
            : 'left 0.5s ease, top 0.5s, width 0.4s, height 0.4s, opacity 0.8s';
        if (props.x !== undefined) el.style.left = props.x + '%';
        if (props.y !== undefined) el.style.top = props.y + '%';
        if (props.w !== undefined) el.style.width = props.w + '%';
        if (props.h !== undefined) el.style.height = props.h + '%';
        if (props.opacity !== undefined) el.style.opacity = props.opacity;
        if (props.state && config.states && config.states[props.state]) {
            const st = config.states[props.state];
            const svg = await loadSVG(ASSET_BASE + st.src, st.color||config.color, st.fill||config.fill);
            if (svg) setSVG(el, svg);
            el.classList.toggle('entity--walking', props.state === 'walking');
        }
    }

    // 气泡
    function showBubble(dialogue) {
        if (!dialogue) { bubble.classList.remove('bubble--visible'); return; }
        const entry = entityEls[dialogue.who];
        if (entry) {
            bubble.style.left = Math.max(2, parseFloat(entry.el.style.left) - 2) + '%';
            bubble.style.top = Math.max(2, parseFloat(entry.el.style.top) - 10) + '%';
        }
        bubble.textContent = dialogue.text;
        bubble.classList.add('bubble--visible');
    }

    // 旁白
    function showNarration(text) {
        if (!text) { narrationEl.classList.remove('narration--visible'); return; }
        narrationEl.textContent = text;
        narrationEl.classList.add('narration--visible');
    }

    // 泪水特效
    function addTear(pos) {
        for (let i = 0; i < 3; i++) {
            setTimeout(() => {
                const tear = document.createElement('div');
                tear.className = 'tear';
                tear.style.left = (pos.x + Math.random() * 2) + '%';
                tear.style.top = pos.y + '%';
                fxLayer.appendChild(tear);
                setTimeout(() => tear.remove(), 1600);
            }, i * 400);
        }
    }

    // 执行一幕
    async function playScene(index) {
        if (index >= SCRIPT.length) {
            panelNote.textContent = '🏁 全剧终 — 唉！我不知何时再能与他相见！';
            showBubble(null);
            showNarration('唉！我不知何时再能与他相见！');
            return;
        }
        const scene = SCRIPT[index];
        panelScene.textContent = `${index+1}/${SCRIPT.length}`;
        panelNote.textContent = `🎬 ${scene.note}`;
        sceneInfo.textContent = `第${index+1}幕 · ${scene.desc}`;

        // 旁白
        showNarration(scene.narration || '');

        // 动作
        for (const action of scene.actions) {
            if (action.entity) await updateEntity(action.entity, action.set, action.animate);
            if (action.fx === 'tear') addTear(action.at);
        }

        // 对话（延迟显示）
        setTimeout(() => showBubble(scene.dialogue || null), 800);

        if (timer) clearTimeout(timer);
        timer = setTimeout(() => playScene(index + 1), scene.duration);
    }

    // 重置
    async function reset() {
        if (timer) clearTimeout(timer);
        fxLayer.innerHTML = '';
        bubble.classList.remove('bubble--visible');
        narrationEl.classList.remove('narration--visible');
        for (const [id, ent] of Object.entries(ENTITIES)) {
            const entry = entityEls[id];
            if (!entry) continue;
            entry.el.style.transition = 'none';
            entry.el.style.left = ent.x + '%';
            entry.el.style.top = ent.y + '%';
            entry.el.style.width = ent.w + '%';
            entry.el.style.height = ent.h + '%';
            entry.el.style.opacity = ent.opacity !== undefined ? ent.opacity : 1;
            entry.el.classList.remove('entity--walking');
            const svg = await loadSVG(ASSET_BASE + ent.src, ent.color, ent.fill);
            if (svg) setSVG(entry.el, svg);
        }
        void stage.offsetHeight;
        for (const entry of Object.values(entityEls)) entry.el.style.transition = '';
        setTimeout(() => playScene(0), 500);
    }

    // 启动
    async function init() {
        await initStage();
        btnReplay.addEventListener('click', reset);
        setTimeout(() => playScene(0), 1000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else { init(); }
})();
