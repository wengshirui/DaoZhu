/**
 * 话剧导演 v3 — SVG 实体引擎
 * 通过 inline SVG 注入实现颜色自定义 + 百分比尺寸
 */
(function () {
    'use strict';

    const ASSET_BASE = '../assets/';

    // 实体定义 — x/y/w/h 均为百分比
    const ENTITIES = {
        sun: { type:'prop', src:'nature/sky/sun.svg', x:5,y:3,w:6,h:8, color:'#F59E0B', fill:'#FDE68A', label:'太阳' },
        window: { type:'prop', src:'nature/sky/sunrise.svg', x:8,y:8,w:12,h:18, color:'#92400E', fill:'#FEF3C7', label:'窗户' },
        clock: { type:'prop', src:'props/items/clock.svg', x:45,y:6,w:5,h:7, color:'#78350F', fill:'#FDE68A', label:'时钟' },
        bed: { type:'prop', src:'props/furniture/bed.svg', x:15,y:52,w:16,h:18, color:'#78350F', fill:'#D97706', label:'床' },
        lamp: { type:'prop', src:'props/furniture/lamp.svg', x:10,y:40,w:5,h:12, color:'#92400E', fill:'#FBBF24', label:'台灯' },
        plant: { type:'prop', src:'nature/trees/plant.svg', x:58,y:48,w:6,h:12, color:'#166534', fill:'#4ADE80', label:'盆栽' },
        book: { type:'prop', src:'props/items/book.svg', x:35,y:60,w:4,h:5, color:'#1E3A5F', fill:'#60A5FA', label:'书' },
        door: {
            type:'prop', src:'props/doors/door-closed.svg', x:76,y:25,w:10,h:32,
            color:'#78350F', fill:'#A16207', label:'门',
            states: { closed:{src:'props/doors/door-closed.svg',fill:'#A16207'}, open:{src:'props/doors/door-open.svg',fill:'#D97706'} }
        },
        xiaoming: {
            type:'actor', src:'characters/people/person-standing.svg', x:22,y:38,w:7,h:20,
            color:'#1E40AF', fill:'#60A5FA', label:'小明',
            states: {
                standing:{src:'characters/people/person-standing.svg',color:'#1E40AF',fill:'#60A5FA'},
                walking:{src:'characters/people/person-walking.svg',color:'#1E40AF',fill:'#60A5FA'},
                running:{src:'characters/people/person-running.svg',color:'#1E40AF',fill:'#3B82F6'}
            }
        }
    };

    // 剧本
    const SCRIPT = [
        { desc:'清晨，阳光透过窗户洒进卧室。', note:'幕起 — 清晨的卧室', thought:'💤 再睡五分钟...',
          actions:[{entity:'xiaoming',set:{x:20,y:45,w:6,h:15,opacity:0.5}}], duration:2200 },
        { desc:'闹钟响了，小明醒来坐起身。', note:'小明被闹钟吵醒', thought:'😴 今天周几来着...',
          actions:[{entity:'xiaoming',set:{opacity:1,y:40,h:18}}], duration:1800 },
        { desc:'小明站起来，伸了个懒腰。', note:'小明起身', thought:'🙆 伸个懒腰~',
          actions:[{entity:'xiaoming',set:{y:36,h:22,state:'standing'}}], duration:1500 },
        { desc:'小明走向房门。', note:'小明走向门口', thought:'🚶 去看看外面',
          actions:[{entity:'xiaoming',set:{x:66,state:'walking'},animate:true}], duration:2800 },
        { desc:'小明打开了门，光线涌入。', note:'开门 — 光线涌入', thought:'🔓 咔嗒...',
          actions:[{entity:'xiaoming',set:{state:'standing'}},{entity:'door',set:{state:'open'}},{fx:'light-beam',at:{x:78,y:28}}], duration:2000 },
        { desc:'新的一天开始了。', note:'🏁 全剧终 — 谢幕', thought:'☀️ 早安，世界！',
          actions:[{entity:'xiaoming',set:{x:82},animate:true}], duration:2000 }
    ];

    // DOM 引用
    const stage = document.getElementById('stage');
    const propsLayer = document.getElementById('props-layer');
    const actorsLayer = document.getElementById('actors-layer');
    const fxLayer = document.getElementById('fx-layer');
    const bubble = document.getElementById('bubble');
    const sceneInfo = document.getElementById('scene-info');
    const panelScene = document.getElementById('panel-scene');
    const panelNote = document.getElementById('panel-note');
    const btnReplay = document.getElementById('btn-replay');

    const entityEls = {};
    let currentScene = 0;
    let timer = null;

    // 加载 SVG 并注入颜色
    async function loadSVG(url, color, fill) {
        try {
            const resp = await fetch(url);
            if (!resp.ok) return null;
            let svg = await resp.text();
            // 替换 stroke 颜色
            if (color) {
                svg = svg.replace(/stroke="currentColor"/g, `stroke="${color}"`);
                svg = svg.replace(/stroke="#[0-9a-fA-F]{3,8}"/g, `stroke="${color}"`);
            }
            // 注入 fill（将 fill="none" 替换为半透明填充）
            if (fill) {
                svg = svg.replace(/fill="none"/g, `fill="${fill}" fill-opacity="0.35"`);
            }
            // 加粗线条让图标更醒目
            svg = svg.replace(/stroke-width="2"/g, 'stroke-width="1.5"');
            return svg;
        } catch (e) { return null; }
    }

    // 将 SVG 内容设置到实体 DOM
    function setSVGContent(el, svgText) {
        el.innerHTML = svgText;
        const svgEl = el.querySelector('svg');
        if (svgEl) {
            svgEl.style.width = '100%';
            svgEl.style.height = '100%';
            svgEl.removeAttribute('width');
            svgEl.removeAttribute('height');
        }
    }

    // 初始化舞台
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

            const svgContent = await loadSVG(ASSET_BASE + ent.src, ent.color, ent.fill);
            if (svgContent) {
                setSVGContent(el, svgContent);
            } else {
                el.innerHTML = `<img src="${ASSET_BASE+ent.src}" alt="${ent.label}" style="width:100%;height:100%">`;
            }

            (ent.type === 'actor' ? actorsLayer : propsLayer).appendChild(el);
            entityEls[id] = { el, config: {...ent} };
        }
    }

    // 更新实体属性
    async function updateEntity(id, props, animate) {
        const entry = entityEls[id];
        if (!entry) return;
        const { el, config } = entry;

        el.style.transition = animate
            ? 'left 2.5s ease-in-out, top 0.4s, width 0.3s, height 0.3s, opacity 0.5s'
            : 'left 0.4s ease, top 0.4s, width 0.3s, height 0.3s, opacity 0.5s';

        if (props.x !== undefined) el.style.left = props.x + '%';
        if (props.y !== undefined) el.style.top = props.y + '%';
        if (props.w !== undefined) el.style.width = props.w + '%';
        if (props.h !== undefined) el.style.height = props.h + '%';
        if (props.opacity !== undefined) el.style.opacity = props.opacity;

        // 状态切换
        if (props.state && config.states && config.states[props.state]) {
            const st = config.states[props.state];
            const c = st.color || config.color;
            const f = st.fill || config.fill;
            const svg = await loadSVG(ASSET_BASE + st.src, c, f);
            if (svg) setSVGContent(el, svg);
            el.classList.toggle('entity--walking', props.state === 'walking');
        }
    }

    // 气泡
    function showBubble(text, entityId) {
        if (!text) { bubble.classList.remove('bubble--visible'); return; }
        const entry = entityEls[entityId || 'xiaoming'];
        if (entry) {
            bubble.style.left = Math.max(2, parseFloat(entry.el.style.left) - 3) + '%';
            bubble.style.top = Math.max(2, parseFloat(entry.el.style.top) - 12) + '%';
        }
        bubble.textContent = text;
        bubble.classList.add('bubble--visible');
    }

    // 光线特效
    function addLightBeam(pos) {
        const beam = document.createElement('div');
        beam.className = 'light-beam';
        beam.style.left = pos.x + '%';
        beam.style.top = pos.y + '%';
        fxLayer.appendChild(beam);
        requestAnimationFrame(() => beam.classList.add('light-beam--visible'));
    }

    // 执行一幕
    async function playScene(index) {
        if (index >= SCRIPT.length) {
            panelNote.textContent = '🏁 全剧终 — 感谢观看！';
            showBubble('', null);
            return;
        }
        currentScene = index;
        const scene = SCRIPT[index];
        panelScene.textContent = `${index+1}/${SCRIPT.length}`;
        panelNote.textContent = `🎬 ${scene.note}`;
        sceneInfo.textContent = `第${index+1}幕 · ${scene.desc}`;

        for (const action of scene.actions) {
            if (action.entity) await updateEntity(action.entity, action.set, action.animate);
            if (action.fx === 'light-beam') addLightBeam(action.at);
        }
        setTimeout(() => showBubble(scene.thought, 'xiaoming'), 400);
        // 气泡跟随
        if (scene.actions.some(a => a.entity==='xiaoming' && a.set.x!==undefined)) {
            setTimeout(() => {
                const e = entityEls['xiaoming'];
                if (e) {
                    bubble.style.left = (parseFloat(e.el.style.left)-3)+'%';
                    bubble.style.top = (parseFloat(e.el.style.top)-12)+'%';
                }
            }, 1500);
        }
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => playScene(index+1), scene.duration);
    }

    // 重置
    async function reset() {
        if (timer) clearTimeout(timer);
        fxLayer.innerHTML = '';
        bubble.classList.remove('bubble--visible');
        for (const [id, ent] of Object.entries(ENTITIES)) {
            const entry = entityEls[id];
            if (!entry) continue;
            entry.el.style.transition = 'none';
            entry.el.style.left = ent.x + '%';
            entry.el.style.top = ent.y + '%';
            entry.el.style.width = ent.w + '%';
            entry.el.style.height = ent.h + '%';
            entry.el.style.opacity = 1;
            entry.el.classList.remove('entity--walking');
            const svg = await loadSVG(ASSET_BASE + ent.src, ent.color, ent.fill);
            if (svg) setSVGContent(entry.el, svg);
        }
        void stage.offsetHeight;
        for (const entry of Object.values(entityEls)) entry.el.style.transition = '';
        setTimeout(() => playScene(0), 400);
    }

    // 启动
    async function init() {
        await initStage();
        btnReplay.addEventListener('click', reset);
        setTimeout(() => playScene(0), 800);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else { init(); }
})();
