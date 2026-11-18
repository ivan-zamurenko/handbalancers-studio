// Save result: the hero, facing us on two hands, shifts onto one hand and holds.
// Success → vortex into a white check on a green disc. Error → loses balance and falls
// (physical rig in acro-rig.js), then vortex into a white cross on a red disc.
// Runs only for a real server save.
import {balanceParams, holdParams, pose, simulateFall, SEG} from './acro-rig.js';

const clamp = t => Math.max(0, Math.min(1, t));

export const timings = {
  full: {fadeForm: 180, appear: 180, shift: 560, hold: 1000, vortex: 650, mark: 380, result: 1100},
  short: {fadeForm: 140, appear: 120, shift: 380, hold: 200, vortex: 420, mark: 240, result: 650},
};

// World (y up, support wrist at origin) → SVG.
const ORIGIN = [112, 196];
const screen = ([x, y]) => [ORIGIN[0] + x, ORIGIN[1] - y];
let fallFrames = null;
const fallAt = seconds => {
  fallFrames ??= simulateFall();
  return fallFrames.find(frame => frame.t >= seconds) ?? fallFrames.at(-1);
};
const fallDuration = () => { fallFrames ??= simulateFall(); return fallFrames.at(-1).t; };

const NS = 'http://www.w3.org/2000/svg';
const svgEl = (name, attrs = {}) => {
  const node = document.createElementNS(NS, name);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  return node;
};

function build() {
  const root = document.createElement('div');
  root.className = 'save-feedback';
  root.dataset.saveFeedback = '';
  root.hidden = true;
  const svg = svgEl('svg', {viewBox: '0 0 260 220', 'aria-hidden': 'true', focusable: 'false'});
  svg.append(svgEl('path', {class: 'sf-floor', d: 'M14 197H246'}));
  const figure = svgEl('g', {class: 'sf-figure', 'data-sf-figure': ''});
  for (const bone of ['arm-l', 'legs', 'torso', 'shoulders', 'hips', 'neck', 'arm-r']) {
    figure.append(svgEl('path', {'data-bone': bone}));
  }
  figure.append(svgEl('circle', {class: 'sf-head', r: '9.5'}));
  figure.append(svgEl('path', {class: 'sf-eyes', 'data-bone': 'eyes'}));
  const swirl = svgEl('g', {class: 'sf-swirl'});
  for (const [r, len] of [[46, 150], [34, 110], [22, 70]]) {
    swirl.append(svgEl('circle', {cx: 130, cy: 110, r, 'stroke-dasharray': `${len} 400`}));
  }
  const badge = svgEl('g', {class: 'sf-badge'});
  badge.append(svgEl('circle', {cx: 130, cy: 110, r: 44}));
  badge.append(svgEl('path', {class: 'sf-mark', pathLength: 1}));
  svg.append(figure, swirl, badge);
  const text = document.createElement('p');
  text.className = 'sf-text';
  text.dataset.sfText = '';
  text.setAttribute('role', 'status');
  text.setAttribute('aria-live', 'polite');
  root.append(svg, text);
  document.body.append(root);
  return {root, svg, figure, swirl, badge, mark: badge.querySelector('.sf-mark'), text};
}

function draw(parts, params) {
  const j = pose(params);
  const P = name => screen(j[name]);
  const fmt = p => `${p[0].toFixed(2)} ${p[1].toFixed(2)}`;
  const line = (...names) => names.map((name, i) => `${i ? 'L' : 'M'}${fmt(P(name))}`).join('');
  const set = (bone, d) => parts.figure.querySelector(`[data-bone="${bone}"]`).setAttribute('d', d);
  set('arm-l', line('shoulderL', 'elbowL', 'handL'));
  set('arm-r', line('shoulderR', 'elbowR', 'handR'));
  set('shoulders', line('shoulderL', 'neck', 'shoulderR'));
  set('hips', line('hipL', 'pelvis', 'hipR'));
  set('torso', line('neck', 'pelvis'));
  set('legs', `${line('hipR', 'kneeR', 'footR')}${line('hipL', 'kneeL', 'footL')}`);
  const head = P('head'), neck = P('neck');
  const axis = [head[0] - neck[0], head[1] - neck[1]];
  const length = Math.hypot(...axis);
  const along = [axis[0] / length, axis[1] / length], across = [-along[1], along[0]];
  // The neck meets the head at its edge, not its centre.
  set('neck', `M${fmt(neck)}L${fmt([head[0] - along[0] * SEG.head, head[1] - along[1] * SEG.head])}`);
  const circle = parts.figure.querySelector('.sf-head');
  circle.setAttribute('cx', head[0].toFixed(2));
  circle.setAttribute('cy', head[1].toFixed(2));
  // Face towards us: eyes sit slightly towards the crown, either side of the head's axis.
  const eye = side => [head[0] + along[0] * 2 + across[0] * 3.3 * side, head[1] + along[1] * 2 + across[1] * 3.3 * side];
  set('eyes', `M${fmt(eye(-1))}h.2M${fmt(eye(1))}h.2`);
}

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

function tween(ms, step, signal) {
  return new Promise(resolve => {
    const start = performance.now();
    const frame = now => {
      const t = signal.skip ? 1 : clamp((now - start) / ms);
      step(t);
      if (t >= 1) resolve();
      else requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
  });
}

const wait = (ms, signal) => new Promise(resolve => {
  if (signal.skip) return resolve();
  const timer = setTimeout(resolve, ms);
  signal.onSkip = () => { clearTimeout(timer); resolve(); };
});

let parts = null;

/**
 * Plays the save feedback while `request` settles. `request` resolves to true (saved)
 * or false/throws (error). Returns the boolean outcome after the overlay closes.
 */
export async function playSaveFeedback({request, variant = 'short', form, labels}) {
  parts ??= build();
  const t = timings[variant] ?? timings.short;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const signal = {skip: false, onSkip: null};
  const skip = () => { signal.skip = true; signal.onSkip?.(); };
  const onKey = event => { if (event.key === 'Escape') skip(); };
  const {root, figure, swirl, badge, mark, text} = parts;
  const floor = root.querySelector('.sf-floor');
  const outcome = Promise.resolve(request).then(Boolean, () => false);

  root.hidden = false;
  root.dataset.outcome = 'pending';
  root.dataset.mode = reduced ? 'static' : 'motion';
  text.textContent = '';
  figure.style.cssText = '';
  floor.style.cssText = '';
  badge.style.cssText = 'opacity:0';
  swirl.style.cssText = 'opacity:0';
  mark.style.strokeDashoffset = '1';
  root.addEventListener('click', skip);
  document.addEventListener('keydown', onKey);
  if (form) form.inert = true;

  let ok;
  if (reduced) {
    ok = await outcome;
  } else {
    form?.animate([{opacity: 1}, {opacity: 0}], {duration: t.fadeForm, fill: 'forwards', easing: 'ease-out'});
    draw(parts, balanceParams(0));
    root.animate([{opacity: 0}, {opacity: 1}], {duration: t.appear, easing: 'ease-out'});
    await wait(t.appear, signal);
    // Quick, physical transfer: weight shift on both hands, free hand peels off, arm opens.
    await tween(t.shift, k => draw(parts, balanceParams(k)), signal);
    const holdStart = performance.now();
    let settled = false;
    outcome.then(() => { settled = true; });
    // Hold at least the configured time and until the server has answered.
    await new Promise(resolve => {
      const frame = now => {
        const elapsed = (now - holdStart) / 1000;
        draw(parts, holdParams(elapsed));
        if ((elapsed * 1000 >= t.hold || signal.skip) && settled) resolve();
        else requestAnimationFrame(frame);
      };
      requestAnimationFrame(frame);
    });
    ok = await outcome;
    if (!ok) {
      // Real-time playback of the simulated fall (balance lost → tip over → lie on the side).
      await tween(fallDuration() * 1000, k => draw(parts, fallAt(k * fallDuration()).params), signal);
      await wait(180, signal);
    }
    // Vortex: the figure spins down into the centre while the disc spins up.
    const spin = {duration: signal.skip ? 1 : t.vortex, fill: 'forwards'};
    floor.animate([{opacity: 0.16}, {opacity: 0}], {...spin, easing: 'ease-in'});
    figure.animate([{transform: 'rotate(0deg) scale(1)', opacity: 1},
      {transform: 'rotate(600deg) scale(0.04)', opacity: 0}], {...spin, easing: 'cubic-bezier(.55,0,.8,.25)'});
    swirl.animate([{transform: 'rotate(0deg) scale(1.15)', opacity: 0}, {opacity: 0.9, offset: 0.4},
      {transform: 'rotate(-480deg) scale(0.2)', opacity: 0}], {...spin, easing: 'ease-in'});
    await wait(t.vortex * 0.55, signal);
  }

  root.dataset.outcome = ok ? 'success' : 'error';
  mark.setAttribute('d', ok ? 'M109 111L124 126L152 95' : 'M115 95L145 125M145 95L115 125');
  figure.style.opacity = '0';
  floor.style.opacity = '0';
  if (reduced || signal.skip) {
    badge.style.opacity = '1';
    mark.style.strokeDashoffset = '0';
  } else {
    badge.animate([{transform: 'rotate(-220deg) scale(0)', opacity: 0},
      {transform: 'rotate(0deg) scale(1)', opacity: 1}],
    {duration: t.vortex * 0.6, easing: 'cubic-bezier(.2,1.4,.4,1)', fill: 'forwards'});
    await wait(t.vortex * 0.45, signal);
    mark.animate([{strokeDashoffset: 1}, {strokeDashoffset: 0}],
      {duration: t.mark, easing: 'ease-out', fill: 'forwards'});
    await wait(t.mark, signal);
  }
  text.textContent = ok ? labels.saved : labels.error;
  await wait(signal.skip ? 350 : t.result, {skip: false});

  root.removeEventListener('click', skip);
  document.removeEventListener('keydown', onKey);
  for (const node of [figure, swirl, badge, mark]) node.getAnimations().forEach(a => a.cancel());
  if (!reduced) await root.animate([{opacity: 1}, {opacity: 0}], {duration: 200, easing: 'ease-in'}).finished;
  root.hidden = true;
  if (form) {
    form.getAnimations().forEach(a => a.cancel());
    form.inert = false;
    if (!reduced) form.animate([{opacity: 0}, {opacity: 1}], {duration: 200, easing: 'ease-out'});
  }
  return ok;
}

// Static frame for design review (tools/previews/save-feedback): no timers, no server.
export function previewPose(params) {
  parts ??= build();
  parts.root.hidden = false;
  parts.root.dataset.outcome = 'pending';
  parts.root.dataset.mode = 'motion';
  parts.badge.style.opacity = '0';
  draw(parts, params);
}
