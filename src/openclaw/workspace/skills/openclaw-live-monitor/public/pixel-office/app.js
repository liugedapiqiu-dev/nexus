const terminalEl = document.getElementById('terminalText');
const scene = document.getElementById('scene');

const terminalFrames = [
  '$ sudo rm -rf /*',
  '> scanning /srv/app',
  '> deleting node_modules',
  '> wiping /tmp/cache',
  '> ERROR: root angry',
  '> retry --force --no-mercy'
];
let terminalIndex = 0;
let terminalCursor = 0;

function tickTerminal() {
  const full = terminalFrames[terminalIndex];
  terminalCursor++;
  const shown = full.slice(0, terminalCursor);
  terminalEl.textContent = shown + (terminalCursor % 2 ? '▊' : ' ');
  if (terminalCursor > full.length + 5) {
    terminalIndex = (terminalIndex + 1) % terminalFrames.length;
    terminalCursor = 0;
  }
}
setInterval(tickTerminal, 80);
tickTerminal();

const patrolActors = [
  { el: document.getElementById('cat'), zone: { x1: 18, y1: 14, x2: 28, y2: 18 } },
  { el: document.getElementById('lobster1'), zone: { x1: 16, y1: 15, x2: 24, y2: 18 } },
  { el: document.getElementById('lobster2'), zone: { x1: 22, y1: 13, x2: 29, y2: 18 } }
];

function rand(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function setActorCell(actor, x, y) {
  actor.el.style.setProperty('--x', x);
  actor.el.style.setProperty('--y', y);
  actor.el.style.left = `calc(${x} * var(--cell))`;
  actor.el.style.top = `calc(${y} * var(--cell))`;
}

function moveActor(actor) {
  const x = rand(actor.zone.x1, actor.zone.x2);
  const y = rand(actor.zone.y1, actor.zone.y2);
  setActorCell(actor, x, y);

  const sprite = actor.el.querySelector('.sprite');
  const bubble = actor.el.querySelector('.bubble');
  if (sprite) sprite.style.transform = Math.random() > 0.5 ? 'scaleX(-1)' : 'scaleX(1)';
  if (bubble) {
    const texts = actor.el.id === 'cat'
      ? ['橘猫巡逻', '闻了闻冰箱', '沙发占领中', '假装在抓包']
      : ['夹线缆', '巡边角', '贴地前进', '发现碎屑'];
    bubble.textContent = texts[rand(0, texts.length - 1)];
  }
}

patrolActors.forEach((actor, idx) => {
  moveActor(actor);
  setInterval(() => moveActor(actor), 1800 + idx * 650);
});

const statusBubbles = [
  ['主控', ['拆需求中', '切分模块', '验收对齐']],
  ['删库哥', ['终端暴走', '危险试跑', '命令未收敛']],
  ['摸鱼位', ['窗口最小化', '偷偷看群', '伪装忙碌']],
  ['前机', ['卡点梳理', '重排依赖', '更新排期']],
  ['情报台', ['监听进展', '同步情报', '汇总动态']],
  ['警戒员', ['盯风险中', '冒烟测试', '边界检查']],
  ['值班 SRE', ['机柜红灯!', '告警处理中', '盯着负载']] 
];

function rotateCharacterBubbles() {
  statusBubbles.forEach(([name, texts]) => {
    const el = [...document.querySelectorAll('.character')].find(n => n.dataset.name === name);
    if (!el) return;
    const bubble = el.querySelector('.bubble');
    if (!bubble) return;
    bubble.textContent = texts[rand(0, texts.length - 1)];
  });
}
setInterval(rotateCharacterBubbles, 2600);
rotateCharacterBubbles();

// 小幅呼吸位移，让静态人物更有生命感
[...document.querySelectorAll('.character')].forEach((el, idx) => {
  let t = 0;
  setInterval(() => {
    t += 0.3;
    const bob = Math.sin(t + idx) * 2;
    el.style.transform = `translate(calc(var(--cell) * 0.05), ${bob}px)`;
  }, 120);
});

// 点击角色时高亮状态，方便验收
scene.addEventListener('click', (e) => {
  const actor = e.target.closest('.character, .critter, .server-rack, .terminal-screen');
  document.querySelectorAll('.focus').forEach(el => el.classList.remove('focus'));
  if (actor) actor.classList.add('focus');
});

const style = document.createElement('style');
style.textContent = `
  .focus { filter: drop-shadow(0 0 10px rgba(255,255,255,.55)); }
  .focus::before { border-color: #fff59d !important; }
`;
document.head.appendChild(style);
