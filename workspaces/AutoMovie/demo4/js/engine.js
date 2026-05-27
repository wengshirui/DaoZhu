/**
 * 背影 · 朱自清 — SVG 实体剧场引擎 v2
 * 改进：名牌、攀爬、搀扶、丰富场景
 */
(function () {
    'use strict';
    const A = '../assets/';

    // 实体（百分比坐标）
    const ENTITIES = {
        // 远景
        mist: {type:'prop', src:'nature/sky/mist.svg', x:0,y:5,w:30,h:20, color:'#94A3B8',fill:'#CBD5E1',label:''},
        cloud: {type:'prop', src:'nature/sky/cloud.svg', x:65,y:3,w:12,h:8, color:'#94A3B8',fill:'#E2E8F0',label:''},
        tree1: {type:'prop', src:'nature/trees/tree-bare.svg', x:2,y:18,w:8,h:25, color:'#57534E',fill:'#78716C',label:''},
        tree2: {type:'prop', src:'nature/trees/tree-bare.svg', x:88,y:15,w:7,h:22, color:'#57534E',fill:'#78716C',label:''},
        // 车站结构
        pillar1: {type:'prop', src:'buildings/structures/pillars.svg', x:25,y:12,w:4,h:40, color:'#44403C',fill:'#57534E',label:''},
        pillar2: {type:'prop', src:'buildings/structures/pillars.svg', x:70,y:12,w:4,h:40, color:'#44403C',fill:'#57534E',label:''},
        barrier: {type:'prop', src:'buildings/structures/barrier.svg', x:5,y:50,w:90,h:5, color:'#78350F',fill:'#92400E',label:'栅栏'},
        train: {type:'prop', src:'vehicles/transport/train-side.svg', x:55,y:6,w:42,h:38, color:'#374151',fill:'#4B5563',label:''},
        // 道具
        suitcase: {type:'prop', src:'props/items/suitcase.svg', x:58,y:56,w:4,h:5, color:'#78350F',fill:'#A16207',label:''},
        jacket: {type:'prop', src:'props/items/jacket.svg', x:62,y:54,w:3,h:5, color:'#4B0082',fill:'#7C3AED',label:'紫毛大衣'},
        oranges: {type:'prop', src:'props/items/orange.svg', x:20,y:56,w:5,h:6, color:'#EA580C',fill:'#FB923C',label:'橘子',opacity:0},
        // 角色
        father: {type:'actor', src:'characters/people/man.svg', x:38,y:32,w:9,h:24,
            color:'#1F2937',fill:'#374151',label:'父亲',
            states:{
                standing:{src:'characters/people/man.svg',color:'#1F2937',fill:'#374151'},
                walking:{src:'characters/people/person-walking.svg',color:'#1F2937',fill:'#374151'},
                climbing:{src:'characters/people/person-climbing.svg',color:'#1F2937',fill:'#374151'},
                helping:{src:'characters/people/person-helping.svg',color:'#1F2937',fill:'#374151'}
            }
        },
        son: {type:'actor', src:'characters/people/person-standing.svg', x:60,y:34,w:7,h:20,
            color:'#1E3A5F',fill:'#60A5FA',label:'我'},
        // 背景人群（远处）
        crowd: {type:'prop', src:'characters/people/crowd.svg', x:78,y:38,w:14,h:14, color:'#6B7280',fill:'#9CA3AF',label:'',opacity:0.4}
    };

    // 剧本 — 8 幕
    const SCRIPT = [
        {
            desc:'冬日午后，浦口车站。父亲执意要送我。',
            note:'第一幕 — 车站',
            narration:'父亲因为事忙，本已说定不送我。他踌躇了一会，终于决定还是自己送我去。',
            dialogue:{who:'father',text:'"不要紧，他们去不好！"'},
            actions:[], duration:4500
        },
        {
            desc:'父亲忙着照看行李，嘱咐我路上小心。',
            note:'第二幕 — 照看行李',
            narration:'他给我拣定了靠车门的一张椅子。他嘱我路上小心，夜里警醒些，不要受凉。',
            dialogue:{who:'father',text:'"路上小心，夜里不要受凉。"'},
            actions:[
                {entity:'father',set:{x:52,state:'walking'},animate:true}
            ], duration:4500
        },
        {
            desc:'父亲望向车外，决定去买橘子。',
            note:'第三幕 — 买橘子',
            narration:'他望车外看了看，说，"我买几个橘子去。你就在此地，不要走动。"',
            dialogue:{who:'father',text:'"我买几个橘子去。你就在此地，不要走动。"'},
            actions:[
                {entity:'father',set:{x:48,state:'standing'}}
            ], duration:4000
        },
        {
            desc:'父亲蹒跚地走到铁道边，慢慢探身下去。',
            note:'第四幕 — 走向铁道',
            narration:'我看见他戴着黑布小帽，穿着黑布大马褂，深青布棉袍，蹒跚地走到铁道边，慢慢探身下去，尚不大难。',
            actions:[
                {entity:'father',set:{x:28,y:42,state:'walking'},animate:true}
            ], duration:4500
        },
        {
            desc:'父亲攀爬月台——他肥胖的身子向左微倾，显出努力的样子。',
            note:'第五幕 — 攀爬月台（高潮）',
            narration:'他用两手攀着上面，两脚再向上缩；他肥胖的身子向左微倾，显出努力的样子。这时我看见他的背影，我的泪很快地流下来了。',
            actions:[
                {entity:'father',set:{x:18,y:34,w:10,h:26,state:'climbing',addClass:'entity--climbing'},animate:true},
                {fx:'tear',at:{x:62,y:36}}
            ], duration:5500
        },
        {
            desc:'父亲抱着朱红的橘子回来了。我赶紧去搀他。',
            note:'第六幕 — 橘子与搀扶',
            narration:'过铁道时，他先将橘子散放在地上，自己慢慢爬下，再抱起橘子走。到这边时，我赶紧去搀他。',
            actions:[
                {entity:'father',set:{x:45,y:34,w:9,h:24,state:'walking',removeClass:'entity--climbing'},animate:true},
                {entity:'oranges',set:{opacity:1,x:43,y:50}},
                {entity:'son',set:{x:50,state:'helping'},animate:true,delay:1500}
            ], duration:5000
        },
        {
            desc:'父亲将橘子放在我的大衣上，扑扑泥土，准备离去。',
            note:'第七幕 — 离别',
            narration:'他将橘子一股脑儿放在我的皮大衣上。于是扑扑衣上的泥土，心里很轻松似的。',
            dialogue:{who:'father',text:'"我走了，到那边来信！"'},
            actions:[
                {entity:'father',set:{x:55,state:'standing'}},
                {entity:'son',set:{x:60,state:'standing'}},
                {entity:'oranges',set:{x:61,y:52}}
            ], duration:4500
        },
        {
            desc:'父亲的背影混入来来往往的人里，再找不着了。',
            note:'第八幕 — 背影远去',
            narration:'等他的背影混入来来往往的人里，再找不着了，我便进来坐下，我的眼泪又来了。',
            dialogue:{who:'father',text:'"进去吧，里边没人。"'},
            actions:[
                {entity:'father',set:{x:2,y:36,opacity:0.15,w:5,h:14,state:'walking'},animate:true},
                {entity:'crowd',set:{opacity:0.7}},
                {fx:'tear',at:{x:62,y:36},delay:2000}
            ], duration:6000
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
            const r = await fetch(url);
            if (!r.ok) return null;
            let s = await r.text();
            if (color) {
                s = s.replace(/stroke="currentColor"/g, `stroke="${color}"`);
                s = s.replace(/stroke="#[0-9a-fA-F]{3,8}"/g, `stroke="${color}"`);
            }
            if (fill) s = s.replace(/fill="none"/g, `fill="${fill}" fill-opacity="0.35"`);
            return s;
        } catch(e) { return null; }
    }

    function setSVG(el, svgText) {
        // 保留 label
        const label = el.querySelector('.entity__label');
        el.innerHTML = svgText;
        const svg = el.querySelector('svg');
        if (svg) { svg.style.width='100%'; svg.style.height='100%'; svg.removeAttribute('width'); svg.removeAttribute('height'); }
        if (label) el.appendChild(label);
    }

    // 初始化
    async function initStage() {
        propsLayer.innerHTML = '';
        actorsLayer.innerHTML = '';
        fxLayer.innerHTML = '';
        for (const [id, ent] of Object.entries(ENTITIES)) {
            const el = document.createElement('div');
            el.className = `entity entity--${ent.type==='actor'?'actor':'prop'} fade-in`;
            el.style.left = ent.x+'%'; el.style.top = ent.y+'%';
            el.style.width = ent.w+'%'; el.style.height = ent.h+'%';
            if (ent.opacity !== undefined) el.style.opacity = ent.opacity;

            const svg = await loadSVG(A + ent.src, ent.color, ent.fill);
            if (svg) setSVG(el, svg);
            else el.innerHTML = `<img src="${A+ent.src}" style="width:100%;height:100%">`;

            // 名牌（只给有 label 的角色）
            if (ent.label && ent.type === 'actor') {
                const lbl = document.createElement('div');
                lbl.className = 'entity__label';
                lbl.textContent = ent.label;
                el.appendChild(lbl);
            }

            (ent.type==='actor' ? actorsLayer : propsLayer).appendChild(el);
            entityEls[id] = { el, config:{...ent} };
        }
    }

    // 更新实体
    async function updateEntity(id, props, animate) {
        const entry = entityEls[id];
        if (!entry) return;
        const {el, config} = entry;
        el.style.transition = animate
            ? 'left 3s ease-in-out, top 2.5s ease, width 1.2s, height 1.2s, opacity 1.5s, transform 1s'
            : 'left 0.5s, top 0.5s, width 0.4s, height 0.4s, opacity 0.8s, transform 0.5s';
        if (props.x !== undefined) el.style.left = props.x+'%';
        if (props.y !== undefined) el.style.top = props.y+'%';
        if (props.w !== undefined) el.style.width = props.w+'%';
        if (props.h !== undefined) el.style.height = props.h+'%';
        if (props.opacity !== undefined) el.style.opacity = props.opacity;
        if (props.addClass) el.classList.add(props.addClass);
        if (props.removeClass) el.classList.remove(props.removeClass);
        if (props.state && config.states && config.states[props.state]) {
            const st = config.states[props.state];
            const svg = await loadSVG(A+st.src, st.color||config.color, st.fill||config.fill);
            if (svg) setSVG(el, svg);
            el.classList.toggle('entity--walking', props.state==='walking');
        }
    }

    // 气泡
    function showBubble(d) {
        if (!d) { bubble.classList.remove('bubble--visible'); return; }
        const e = entityEls[d.who];
        if (e) {
            bubble.style.left = Math.max(2, parseFloat(e.el.style.left)-2)+'%';
            bubble.style.top = Math.max(2, parseFloat(e.el.style.top)-11)+'%';
        }
        bubble.textContent = d.text;
        bubble.classList.add('bubble--visible');
    }

    // 旁白
    function showNarration(t) {
        if (!t) { narrationEl.classList.remove('narration--visible'); return; }
        narrationEl.textContent = t;
        narrationEl.classList.add('narration--visible');
    }

    // 泪水
    function addTear(pos, delay) {
        setTimeout(() => {
            for (let i=0;i<4;i++) {
                setTimeout(() => {
                    const t = document.createElement('div');
                    t.className = 'tear';
                    t.style.left = (pos.x + Math.random()*2 - 1)+'%';
                    t.style.top = pos.y+'%';
                    fxLayer.appendChild(t);
                    setTimeout(() => t.remove(), 2000);
                }, i*350);
            }
        }, delay||0);
    }

    // 播放一幕
    async function playScene(index) {
        if (index >= SCRIPT.length) {
            panelNote.textContent = '🏁 唉！我不知何时再能与他相见！';
            showBubble(null);
            showNarration('唉！我不知何时再能与他相见！');
            return;
        }
        const scene = SCRIPT[index];
        panelScene.textContent = `${index+1}/${SCRIPT.length}`;
        panelNote.textContent = `🎬 ${scene.note}`;
        sceneInfo.textContent = `第${index+1}幕 · ${scene.desc}`;
        showNarration(scene.narration || '');

        for (const action of scene.actions) {
            if (action.entity) {
                if (action.delay) {
                    setTimeout(() => updateEntity(action.entity, action.set, action.animate), action.delay);
                } else {
                    await updateEntity(action.entity, action.set, action.animate);
                }
            }
            if (action.fx === 'tear') addTear(action.at, action.delay);
        }
        setTimeout(() => showBubble(scene.dialogue || null), 1000);

        if (timer) clearTimeout(timer);
        timer = setTimeout(() => playScene(index+1), scene.duration);
    }

    // 重置
    async function reset() {
        if (timer) clearTimeout(timer);
        fxLayer.innerHTML = '';
        bubble.classList.remove('bubble--visible');
        narrationEl.classList.remove('narration--visible');
        for (const [id, ent] of Object.entries(ENTITIES)) {
            const e = entityEls[id];
            if (!e) continue;
            e.el.style.transition = 'none';
            e.el.style.left = ent.x+'%'; e.el.style.top = ent.y+'%';
            e.el.style.width = ent.w+'%'; e.el.style.height = ent.h+'%';
            e.el.style.opacity = ent.opacity !== undefined ? ent.opacity : 1;
            e.el.classList.remove('entity--walking','entity--climbing');
            const svg = await loadSVG(A+ent.src, ent.color, ent.fill);
            if (svg) setSVG(e.el, svg);
        }
        void stage.offsetHeight;
        for (const e of Object.values(entityEls)) e.el.style.transition = '';
        setTimeout(() => playScene(0), 500);
    }

    async function init() {
        await initStage();
        btnReplay.addEventListener('click', reset);
        setTimeout(() => playScene(0), 1000);
    }

    if (document.readyState==='loading') document.addEventListener('DOMContentLoaded',init);
    else init();
})();
