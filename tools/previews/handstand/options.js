import {mountHandstandCycle} from '/static/js/components/handstand-motion.js';

const root = document.documentElement;
const pause = document.querySelector('[data-pause]');
const theme = document.querySelector('[data-theme-toggle]');
const dialog = document.querySelector('[data-preview]');
const stage = dialog.querySelector('[data-stage]');
const motion = matchMedia('(prefers-reduced-motion: reduce)');

function setPaused(value) {
  root.dataset.paused = String(value);
  pause.setAttribute('aria-pressed', String(value));
  pause.textContent = value ? 'Відтворити' : 'Пауза';
}
setPaused(motion.matches);
for (const svg of document.querySelectorAll('[data-handstand-cycle]')) mountHandstandCycle(svg);
let disposeCycle;
motion.addEventListener('change', event => setPaused(event.matches));
pause.addEventListener('click', () => setPaused(root.dataset.paused !== 'true'));
theme.addEventListener('click', () => {
  root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
  theme.textContent = root.dataset.theme === 'dark' ? 'Світла тема' : 'Темна тема';
});

function setPlacement(value) {
  dialog.dataset.placement = value;
  for (const button of dialog.querySelectorAll('button[data-placement]')) {
    button.setAttribute('aria-pressed', String(button.dataset.placement === value));
  }
}
for (const button of document.querySelectorAll('[data-open]')) {
  button.addEventListener('click', () => {
    const card = button.closest('[data-option]');
    stage.replaceChildren(card.querySelector('svg').cloneNode(true));
    disposeCycle?.();
    const cycle=stage.querySelector('[data-handstand-cycle]');
    disposeCycle=cycle ? mountHandstandCycle(cycle) : null;
    dialog.querySelector('#preview-title').textContent = `0${card.dataset.option} / ${card.querySelector('h2').textContent}`;
    setPlacement('center');
    dialog.showModal();
    document.body.classList.add('preview-open');
  });
}
dialog.querySelector('[data-close]').addEventListener('click', () => dialog.close());
dialog.addEventListener('close', () => {
  disposeCycle?.(); disposeCycle=null;
  stage.replaceChildren();
  document.body.classList.remove('preview-open');
});
for (const button of dialog.querySelectorAll('button[data-placement]')) {
  button.addEventListener('click', () => setPlacement(button.dataset.placement));
}
