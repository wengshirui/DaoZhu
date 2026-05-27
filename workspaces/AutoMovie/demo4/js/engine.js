/**
 * 混合引擎 — Canvas 手绘角色 + SVG 装饰 + CSS UI
 */
(function () {
    'use strict';

    const bubble = document.getElementById('bubble');
    const narrationEl = document.getElementById('narration');
    const sceneInfo = document.getElementById('scene-info');
    const panelScene = document.getElementById('panel-scene');
    const panelNote = document.getElementById('panel-note');
    const btnReplay = document.getElementById('btn-replay');

    let timer = null;
    let animFrame = null;
    let currentScene = 0;

    // 全局状态
    const state = {
        orangeVisible: false,
        orangeX: 0,
        orangeY: 0
    };

    // 动画插值
    const tweens = [];

    function tween(obj, props, duration, delay) {
        const start = {};
        const end = {};
        for (const [k, v] of Object.entries(props)) {
            if (typeof v === 'number') {
                start[k] = obj[k] || 0;
                end[k] = v;
            } else {
                obj[k] = v; // 非数字直接设置（如 state）
            }
        }
        const t = { obj, start, end, duration, delay: delay||0, elapsed: 0, started: false };
        tweens.push(t);
    }

    function updateTweens(dt) {
        for (let i = tweens.length - 1; i >= 0; i--) {
            const t = tweens[i];
            if (t.delay > 0) { t.delay -= dt; continue; }
            if (!t.started) { t.started = true; }
            t.elapsed += dt;
            const progress = Math.min(1, t.elapsed / t.duration);
            const ease = easeInOutCubic(progress);
            for (const [k, sv] of Object.entries(t.start)) {
                t.obj[k] = sv + (t.end[k] - sv) * ease;
            }
            if (progress >= 1) tweens.splice(i, 1);
        }
    }

    function easeInOutCubic(x) {
        return x < 0.5 ? 4*x*x*x : 1 - Math.pow(-2*x+2, 3)/2;
    }

    // 执行动作
    function executeAction(action) {
        const delay = action.delay || 0;
        const duration = action.animate ? 2500 : 500;

        if (action.target === 'father') {
            tween(Renderer.father, action.set, duration, delay);
        } else if (action.target === 'son') {
            tween(Renderer.son, action.set, duration, delay);
        } else if (action.target === 'oranges') {
            setTimeout(() => {
                if (action.set.visible !== undefined) state.orangeVisible = action.set.visible;
                if (action.set.x !== undefined) state.orangeX = action.set.x;
                if (action.set.y !== undefined) state.orangeY = action.set.y;
            }, delay);
        }
    }

    // 气泡
    function showBubble(d) {
        if (!d) { bubble.classList.remove('bubble--visible'); return; }
        const ref = d.who === 'father' ? Renderer.father : Renderer.son;
        const pctX = (ref.x / Renderer.W * 100) - 3;
        const pctY = (ref.y / Renderer.H * 100) - 14;
        bubble.style.left = Math.max(2, pctX) + '%';
        bubble.style.top = Math.max(2, pctY) + '%';
        bubble.textContent = d.text;
        bubble.classList.add('bubble--visible');
    }

    function showNarration(t) {
        if (!t) { narrationEl.classList.remove('narration--visible'); return; }
        narrationEl.textContent = t;
        narrationEl.classList.add('narration--visible');
    }

    // 播放一幕
    function playScene(index) {
        if (index >= SCRIPT.length) {
            panelNote.textContent = '🏁 唉！我不知何时再能与他相见！';
            showBubble(null);
            showNarration('唉！我不知何时再能与他相见！');
            return;
        }
        currentScene = index;
        const scene = SCRIPT[index];
        panelScene.textContent = `${index+1}/${SCRIPT.length}`;
        panelNote.textContent = `🎬 ${scene.note}`;
        sceneInfo.textContent = `第${index+1}幕 · ${scene.desc}`;
        showNarration(scene.narration || '');

        for (const action of scene.actions) {
            executeAction(action);
        }
        setTimeout(() => showBubble(scene.dialogue || null), 1200);

        if (timer) clearTimeout(timer);
        timer = setTimeout(() => playScene(index+1), scene.duration);
    }

    // 重置
    function reset() {
        if (timer) clearTimeout(timer);
        tweens.length = 0;
        Renderer.father = { x:340, y:200, state:'standing', opacity:1, scale:1 };
        Renderer.son = { x:540, y:210, state:'standing', opacity:1 };
        state.orangeVisible = false;
        bubble.classList.remove('bubble--visible');
        narrationEl.classList.remove('narration--visible');
        setTimeout(() => playScene(0), 500);
    }

    // 渲染循环
    let lastTime = 0;
    function loop(time) {
        const dt = lastTime ? time - lastTime : 16;
        lastTime = time;
        updateTweens(dt);
        Renderer.render(state);
        animFrame = requestAnimationFrame(loop);
    }

    // 启动
    function init() {
        Renderer.init();
        btnReplay.addEventListener('click', reset);
        animFrame = requestAnimationFrame(loop);
        setTimeout(() => playScene(0), 1000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else { init(); }
})();
