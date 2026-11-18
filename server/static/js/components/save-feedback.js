// Save result: the hero, facing us on two hands, shifts onto one hand and holds.
// Success → vortex into a white check on a green disc. Error → falls sideways,
// then vortex into a white cross on a red disc. Runs only for a real server save.
const rad = Math.PI / 180;
const clamp = t => Math.max(0, Math.min(1, t));
const mix = (a, b, t) => a + (b - a) * t;
const lerp = (p, q, t) => [mix(p[0], q[0], t), mix(p[1], q[1], t)];
const easeOut = t => 1 - (1 - t) ** 3;
const easeInOut = t => (t < 0.5 ? 4 * t ** 3 : 1 - (-2 * t + 2) ** 3 / 2);

export const FLOOR = 196;
const PLANT_L = [79, FLOOR];
const PLANT_R = [121, FLOOR];
const SHOULDER_HALF = 17;
const ARM = Math.hypot(PLANT_L[0] - (100 - SHOULDER_HALF), PLANT_L[1] - 148);

// Front-view rig. shift/lift 0..1 → one-arm balance; fall 0..1 → topples around the support hand.
export function frontPose({shift = 0, lift = 0, fall = 0, wobble = 0} = {}) {
  const cx = 100 + 4 * shift + wobble;
  const pose = {
    shoulderL: [cx - SHOULDER_HALF, 148], shoulderR: [cx + SHOULDER_HALF, 148],
    hipL: [cx - 6, 86], hipR: [cx + 6, 86],
    footL: [cx - 5 - 9 * shift, 30], footR: [cx + 5 + 3 * shift, 30],
    head: [cx, 170], neck: [cx, 159], chest: [cx, 148], pelvis: [cx, 86],
    handR: [...PLANT_R],
  };
  // Free arm opens to the side; while falling it flails up instead of catching the floor.
  const out = (172 + 75 * fall) * rad;
  pose.handL = lerp(PLANT_L, [pose.shoulderL[0] + ARM * Math.cos(out), pose.shoulderL[1] + ARM * Math.sin(out)], lift);
  if (fall > 0) {
    // Gravity: accelerate, then a small rebound when the body meets the floor.
    const angle = -84 * fall * rad;
    const [px, py] = PLANT_R;
    for (const key of Object.keys(pose)) {
      const [x, y] = pose[key];
      const dx = x - px, dy = y - py;
      pose[key] = [px + dx * Math.cos(angle) - dy * Math.sin(angle), py + dx * Math.sin(angle) + dy * Math.cos(angle)];
    }
    // Keep every joint on or above the floor after the rotation.
    const lowest = Math.max(...Object.values(pose).map(p => p[1]));
    if (lowest > FLOOR) for (const key of Object.keys(pose)) pose[key][1] -= lowest - FLOOR;
  }
  return pose;
}

export const timings = {
  full: {fadeForm: 180, appear: 180, shift: 380, hold: 1000, fall: 520, vortex: 650, mark: 380, result: 1100},
  short: {fadeForm: 140, appear: 120, shift: 220, hold: 200, fall: 380, vortex: 420, mark: 240, result: 650},
};

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
  const svg = svgEl('svg', {viewBox: '-70 0 340 220', 'aria-hidden': 'true', focusable: 'false'});
  svg.append(svgEl('path', {class: 'sf-floor', d: 'M30 197H170'}));
  const figure = svgEl('g', {class: 'sf-figure', 'data-sf-figure': ''});
  for (const bone of ['arm-l', 'legs', 'torso', 'shoulders', 'hips', 'arm-r', 'neck']) {
    figure.append(svgEl('path', {'data-bone': bone}));
  }
  figure.append(svgEl('circle', {class: 'sf-head', r: '9.5'}));
  figure.append(svgEl('path', {class: 'sf-eyes', 'data-bone': 'eyes'}));
  const swirl = svgEl('g', {class: 'sf-swirl'});
  for (const [r, len] of [[46, 150], [34, 110], [22, 70]]) {
    swirl.append(svgEl('circle', {cx: 100, cy: 120, r, 'stroke-dasharray': `${len} 400`}));
  }
  const badge = svgEl('g', {class: 'sf-badge'});
  badge.append(svgEl('circle', {cx: 100, cy: 120, r: 44}));
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

function draw(parts, pose) {
  const fmt = p => `${p[0].toFixed(2)} ${p[1].toFixed(2)}`;
  const set = (bone, d) => parts.figure.querySelector(`[data-bone="${bone}"]`).setAttribute('d', d);
  set('arm-l', `M${fmt(pose.shoulderL)}L${fmt(pose.handL)}`);
  set('arm-r', `M${fmt(pose.shoulderR)}L${fmt(pose.handR)}`);
  set('shoulders', `M${fmt(pose.shoulderL)}L${fmt(pose.shoulderR)}`);
  set('hips', `M${fmt(pose.hipL)}L${fmt(pose.hipR)}`);
  set('torso', `M${fmt(pose.chest)}L${fmt(pose.pelvis)}`);
  set('legs', `M${fmt(pose.hipL)}L${fmt(pose.footL)}M${fmt(pose.hipR)}L${fmt(pose.footR)}`);
  set('neck', `M${fmt(pose.chest)}L${fmt(pose.neck)}`);
  const head = parts.figure.querySelector('.sf-head');
  head.setAttribute('cx', pose.head[0].toFixed(2));
  head.setAttribute('cy', pose.head[1].toFixed(2));
  // Upside-down face: eyes sit below the head centre, along the head's own axis.
  const axis = Math.atan2(pose.head[1] - pose.neck[1], pose.head[0] - pose.neck[0]);
  const along = [Math.cos(axis), Math.sin(axis)], across = [-along[1], along[0]];
  const eye = side => [pose.head[0] + along[0] * 2.5 + across[0] * 3.4 * side, pose.head[1] + along[1] * 2.5 + across[1] * 3.4 * side];
  const [l, r] = [eye(-1), eye(1)];
  set('eyes', `M${fmt(l)}h.2M${fmt(r)}h.2`);
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
    draw(parts, frontPose());
    root.animate([{opacity: 0}, {opacity: 1}], {duration: t.appear, easing: 'ease-out'});
    await wait(t.appear, signal);
    // Quick weight shift onto the right hand; the free arm opens to the side.
    await tween(t.shift, k => draw(parts, frontPose({shift: easeInOut(k), lift: easeOut(k)})), signal);
    const holdStart = performance.now();
    let settled = false;
    outcome.then(() => { settled = true; });
    // Hold for at least the configured time and until the server has answered.
    await new Promise(resolve => {
      const frame = now => {
        const elapsed = now - holdStart;
        const wobble = signal.skip ? 0 : 0.8 * Math.sin(elapsed / 140);
        draw(parts, frontPose({shift: 1, lift: 1, wobble}));
        if ((elapsed >= t.hold || signal.skip) && settled) resolve();
        else requestAnimationFrame(frame);
      };
      requestAnimationFrame(frame);
    });
    ok = await outcome;
    if (!ok) {
      await tween(t.fall, k => draw(parts, frontPose({shift: 1, lift: 1, fall: k ** 2})), signal);
      await wait(120, signal);
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
  mark.setAttribute('d', ok ? 'M79 121L94 136L122 105' : 'M85 105L115 135M115 105L85 135');
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
