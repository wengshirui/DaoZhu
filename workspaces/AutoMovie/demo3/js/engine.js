/**
 * 话剧导演 v3 — SVG 实体引擎
 * 使用 assets/ 目录中的 SVG 素材，通过 DOM 定位实现动画
 */

(function () {
    'use strict';

    // 素材路径（相对于 demo3/）
    const ASSET_BASE = '../assets/';

    // ===== 舞台实体定义 =====
    const ENTITIES = {
        // 场景道具
        window: {
            type: 'prop',
            src: 'nature/sky/sunrise.svg',
            x: 60, y: 40, w: 100, h: 100,
            label: '窗户'
        },
        bed: {
            type: 'prop',
            src: 'props/furniture/bed.svg',
            x: 140, y: 280, w: 120, h: 90,
            label: '床'
        },
        lamp: {
            type: 'prop',
            src: 'props/furniture/lamp.svg',
            x: 90, y: 220, w: 40, h: 60,
            label: '台灯'
        },
        door: {
            type: 'prop',
            src: 'props/doors/door-closed.svg',
            x: 700, y: 140, w: 80, h: 160,
            label: '门',
            states: {
                closed: 'props/doors/door-closed.svg',
                open: 'props/doors/door-open.svg'
            }
        },
        clock: {
            type: 'prop',
            src: 'props/items/clock.svg',
            x: 420, y: 50, w: 50, h: 50,
            label: '时钟'
        },
        book: {
            type: 'prop',
            src: 'props/items/book.svg',
            x: 320, y: 310, w: 35, h: 35,
            label: '书'
        },
        // 主角
        xiaoming: {
            type: 'actor',
            src: 'characters/people/person-standing.svg',
            x: 200, y: 240, w: 60, h: 100,
            label: '小明',
            states: {
                lying: 'characters/people/person-standing.svg',
                standing: 'characters/people/person-standing.svg',
                walking: 'characters/people/person-walking.svg',
                running: 'characters/people/person-running.svg'
            }
        },
        // 装饰
        sun: {
            type: 'prop',
            src: 'nature/sky/sun.svg',
            x: 30, y: 10, w: 40, h: 40,
            label: '太阳'
        },
        plant: {
            type: 'prop',
            src: 'nature/trees/plant.svg',
            x: 550, y: 270, w: 50, h: 70,
            label: '盆栽'
        }
    };

    // ===== 剧本 =====
    const SCRIPT = [
        {
            desc: '清晨，阳光透过窗户洒进卧室。小明还在沉睡。',
            note: '幕起 — 清晨的卧室',
            thought: '💤 再睡五分钟...',
            actions: [
                { entity: 'xiaoming', set: { x: 180, y: 270, w: 50, h: 70, src: 'characters/people/person-standing.svg', opacity: 0.5 } }
            ],
            duration: 2000
        },
        {
            desc: '闹钟响了，小明醒来坐起身。',
            note: '小明被闹钟吵醒',
            thought: '😴 今天周几来着...',
            actions: [
                { entity: 'xiaoming', set: { opacity: 1, y: 250, h: 90 } }
            ],
            duration: 1800
        },
        {
            desc: '小明站起来，伸了个懒腰。',
            note: '小明起身',
            thought: '🙆 伸个懒腰~',
            actions: [
                { entity: 'xiaoming', set: { y: 220, h: 110, src: 'characters/people/person-standing.svg' } }
            ],
            duration: 1500
        },
        {
            desc: '小明走向房门。',
            note: '小明走向门口',
            thought: '🚶 去看看外面',
            actions: [
                { entity: 'xiaoming', set: { x: 620, src: 'characters/people/person-walking.svg' }, animate: true }
            ],
            duration: 2500
        },
        {
            desc: '小明打开了门，清晨的光线涌入。',
            note: '开门 — 光线涌入',
            thought: '🔓 咔嗒...',
            actions: [
                { entity: 'xiaoming', set: { src: 'characters/people/person-standing.svg' } },
                { entity: 'door', set: { src: 'props/doors/door-open.svg' } },
                { fx: 'light-beam', at: { x: 720, y: 160 } }
            ],
            duration: 2000
        },
        {
            desc: '新的一天开始了。',
            note: '🏁 全剧终 — 谢幕',
            thought: '☀️ 早安，世界！',
            actions: [
                { entity: 'xiaoming', set: { x: 750 }, animate: true }
            ],
            duration: 2000
        }
    ];

    // ===== DOM 引用 =====
    const stage = document.getElementById('stage');
    const propsLayer = document.getElementById('props-layer');
    const actorsLayer = document.getElementById('actors-layer');
    const fxLayer = document.getElementById('fx-layer');
    const bubble = document.getElementById('bubble');
    const sceneInfo = document.getElementById('scene-info');
    const panelScene = document.getElementById('panel-scene');
    const panelNote = document.getElementById('panel-note');
    const btnReplay = document.getElementById('btn-replay');

    // 实体 DOM 元素映射
    const entityEls = {};
    let currentScene = 0;
    let timer = null;
    let takeCount = 1;

    // ===== 初始化舞台 =====
    function initStage() {
        // 清空
        propsLayer.innerHTML = '';
        actorsLayer.innerHTML = '';
        fxLayer.innerHTML = '';

        // 创建实体 DOM
        for (const [id, ent] of Object.entries(ENTITIES)) {
            const el = document.createElement('div');
            el.className = `entity entity--${ent.type === 'actor' ? 'actor' : 'prop'} fade-in`;
            el.style.left = ent.x + 'px';
            el.style.top = ent.y + 'px';
            el.style.width = ent.w + 'px';
            el.style.height = ent.h + 'px';

            const img = document.createElement('img');
            img.src = ASSET_BASE + ent.src;
            img.alt = ent.label;
            img.draggable = false;
            el.appendChild(img);

            if (ent.type === 'actor') {
                actorsLayer.appendChild(el);
            } else {
                propsLayer.appendChild(el);
            }

            entityEls[id] = { el, img, config: { ...ent } };
        }
    }

    // ===== 更新实体 =====
    function updateEntity(id, props, animate) {
        const entry = entityEls[id];
        if (!entry) return;

        const { el, img } = entry;

        if (props.x !== undefined) {
            if (animate) {
                el.style.transition = 'left 2s ease-in-out, top 0.3s ease';
            } else {
                el.style.transition = 'left 0.3s ease, top 0.3s ease';
            }
            el.style.left = props.x + 'px';
        }
        if (props.y !== undefined) el.style.top = props.y + 'px';
        if (props.w !== undefined) el.style.width = props.w + 'px';
        if (props.h !== undefined) el.style.height = props.h + 'px';
        if (props.opacity !== undefined) el.style.opacity = props.opacity;
        if (props.src !== undefined) img.src = ASSET_BASE + props.src;

        // 走路动画 class
        if (props.src && props.src.includes('walking')) {
            el.classList.add('entity--walking');
        } else {
            el.classList.remove('entity--walking');
        }
    }

    // ===== 显示气泡 =====
    function showBubble(text, entityId) {
        if (!text) {
            bubble.classList.remove('bubble--visible');
            return;
        }
        const entry = entityEls[entityId || 'xiaoming'];
        if (entry) {
            const x = parseInt(entry.el.style.left) - 20;
            const y = parseInt(entry.el.style.top) - 50;
            bubble.style.left = Math.max(10, x) + 'px';
            bubble.style.top = Math.max(10, y) + 'px';
        }
        bubble.textContent = text;
        bubble.classList.add('bubble--visible');
    }

    // ===== 执行一幕 =====
    function playScene(index) {
        if (index >= SCRIPT.length) {
            panelNote.textContent = '🏁 全剧终 — 感谢观看！';
            showBubble('', null);
            return;
        }

        currentScene = index;
        const scene = SCRIPT[index];

        // 更新 UI
        panelScene.textContent = `${index + 1}/${SCRIPT.length}`;
        panelNote.textContent = `🎬 ${scene.note}`;
        sceneInfo.textContent = `第${index + 1}幕 · ${scene.desc}`;

        // 执行动作
        for (const action of scene.actions) {
            if (action.entity) {
                updateEntity(action.entity, action.set, action.animate);
            }
            if (action.fx === 'light-beam') {
                addLightBeam(action.at);
            }
        }

        // 显示气泡（延迟一点让动画先开始）
        setTimeout(() => showBubble(scene.thought, 'xiaoming'), 300);

        // 气泡跟随角色位置
        if (scene.actions.some(a => a.entity === 'xiaoming' && a.set.x !== undefined)) {
            setTimeout(() => {
                const entry = entityEls['xiaoming'];
                if (entry) {
                    bubble.style.left = (parseInt(entry.el.style.left) - 20) + 'px';
                    bubble.style.top = (parseInt(entry.el.style.top) - 50) + 'px';
                }
            }, 1200);
        }

        // 下一幕
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => playScene(index + 1), scene.duration);
    }

    // ===== 光线特效 =====
    function addLightBeam(pos) {
        const beam = document.createElement('div');
        beam.className = 'light-beam';
        beam.style.left = pos.x + 'px';
        beam.style.top = pos.y + 'px';
        fxLayer.appendChild(beam);
        requestAnimationFrame(() => beam.classList.add('light-beam--visible'));
    }

    // ===== 重置 =====
    function reset() {
        if (timer) clearTimeout(timer);
        takeCount++;
        fxLayer.innerHTML = '';
        bubble.classList.remove('bubble--visible');

        // 重置实体位置
        for (const [id, ent] of Object.entries(ENTITIES)) {
            const entry = entityEls[id];
            if (!entry) continue;
            entry.el.style.transition = 'none';
            entry.el.style.left = ent.x + 'px';
            entry.el.style.top = ent.y + 'px';
            entry.el.style.width = ent.w + 'px';
            entry.el.style.height = ent.h + 'px';
            entry.el.style.opacity = 1;
            entry.img.src = ASSET_BASE + ent.src;
            entry.el.classList.remove('entity--walking');
        }

        // 强制 reflow 后恢复 transition
        void stage.offsetHeight;
        for (const entry of Object.values(entityEls)) {
            entry.el.style.transition = '';
        }

        setTimeout(() => playScene(0), 300);
    }

    // ===== 启动 =====
    function init() {
        initStage();
        btnReplay.addEventListener('click', reset);
        setTimeout(() => playScene(0), 800);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
