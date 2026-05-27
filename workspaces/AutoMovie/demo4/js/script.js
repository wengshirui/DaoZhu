/**
 * 剧本定义 — 《背影》8 幕
 */
const SCRIPT = [
    {
        desc: '冬日午后，浦口车站。父亲执意要送我。',
        note: '第一幕 — 车站送别',
        narration: '父亲因为事忙，本已说定不送我。他踌躇了一会，终于决定还是自己送我去。我两三回劝他不必去；他只说，"不要紧，他们去不好！"',
        dialogue: { who: 'father', text: '"不要紧，他们去不好！"' },
        actions: [
            { target: 'father', set: { x: 340, y: 200, state: 'standing' } },
            { target: 'son', set: { x: 540, y: 210, state: 'standing' } }
        ],
        duration: 5000
    },
    {
        desc: '父亲忙着照看行李，嘱咐我路上小心。',
        note: '第二幕 — 照看行李',
        narration: '他给我拣定了靠车门的一张椅子；我将他给我做的紫毛大衣铺好坐位。他嘱我路上小心，夜里警醒些，不要受凉。',
        dialogue: { who: 'father', text: '"路上小心，夜里警醒些，不要受凉。"' },
        actions: [
            { target: 'father', set: { x: 480, state: 'walking' }, animate: true }
        ],
        duration: 5000
    },
    {
        desc: '父亲望向车外，决定去买橘子。',
        note: '第三幕 — 买橘子',
        narration: '我说道，"爸爸，你走吧。"他望车外看了看，说，"我买几个橘子去。你就在此地，不要走动。"',
        dialogue: { who: 'father', text: '"我买几个橘子去。你就在此地，不要走动。"' },
        actions: [
            { target: 'father', set: { x: 420, state: 'standing' } }
        ],
        duration: 4500
    },
    {
        desc: '父亲蹒跚地走到铁道边，慢慢探身下去。',
        note: '第四幕 — 走向铁道',
        narration: '我看见他戴着黑布小帽，穿着黑布大马褂，深青布棉袍，蹒跚地走到铁道边，慢慢探身下去，尚不大难。',
        actions: [
            { target: 'father', set: { x: 240, y: 230, state: 'walking' }, animate: true }
        ],
        duration: 4500
    },
    {
        desc: '父亲攀爬月台——肥胖的身子向左微倾，显出努力的样子。',
        note: '第五幕 — 攀爬月台（高潮）',
        narration: '他用两手攀着上面，两脚再向上缩；他肥胖的身子向左微倾，显出努力的样子。这时我看见他的背影，我的泪很快地流下来了。',
        actions: [
            { target: 'father', set: { x: 160, y: 180, state: 'climbing', scale: 1.1 }, animate: true },
            { target: 'son', set: { state: 'crying' } }
        ],
        duration: 6000
    },
    {
        desc: '父亲抱着朱红的橘子回来了。我赶紧去搀他。',
        note: '第六幕 — 橘子与搀扶',
        narration: '过铁道时，他先将橘子散放在地上，自己慢慢爬下，再抱起橘子走。到这边时，我赶紧去搀他。',
        actions: [
            { target: 'father', set: { x: 400, y: 200, state: 'walking', scale: 1 }, animate: true },
            { target: 'son', set: { x: 440, state: 'helping' }, animate: true, delay: 1500 },
            { target: 'oranges', set: { visible: true, x: 420, y: 290 }, delay: 800 }
        ],
        duration: 5500
    },
    {
        desc: '父亲将橘子放下，扑扑泥土，准备离去。',
        note: '第七幕 — 离别',
        narration: '他将橘子一股脑儿放在我的皮大衣上。于是扑扑衣上的泥土，心里很轻松似的，过一会说，"我走了，到那边来信！"',
        dialogue: { who: 'father', text: '"我走了，到那边来信！"' },
        actions: [
            { target: 'father', set: { x: 500, state: 'standing' } },
            { target: 'son', set: { x: 540, state: 'standing' } },
            { target: 'oranges', set: { x: 550, y: 280 } }
        ],
        duration: 5000
    },
    {
        desc: '父亲的背影混入来来往往的人里，再找不着了。',
        note: '第八幕 — 背影远去',
        narration: '他走了几步，回过头看见我，说，"进去吧，里边没人。"等他的背影混入来来往往的人里，再找不着了，我便进来坐下，我的眼泪又来了。',
        dialogue: { who: 'father', text: '"进去吧，里边没人。"' },
        actions: [
            { target: 'father', set: { x: 40, y: 210, opacity: 0.2, scale: 0.6, state: 'walking' }, animate: true },
            { target: 'son', set: { state: 'crying' }, delay: 2000 }
        ],
        duration: 6500
    }
];
