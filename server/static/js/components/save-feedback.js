// Save result: the hero, facing us on two hands, shifts onto one hand and holds.
// Success holds; failure makes leg corrections and falls. Both dissolve into
// its own contours, curled into a fluid vortex that settles into the result disc.
// Runs only for a real server save.
import {vortexPoint} from './save-vortex.js';
import {balanceParams, holdParams, pose, simulateFall, centerOfMass, lowestPoint, SEG} from './acro-rig.js';

const clamp = t => Math.max(0, Math.min(1, t));

export const timings = {
  full: {fadeForm: 180, appear: 180, shift: 560, hold: 1000, paint: 1000, mark: 380, result: 1100},
  short: {fadeForm: 140, appear: 120, shift: 560, hold: 1000, paint: 900, mark: 240, result: 650},
};

// World (y up, support wrist at origin) → SVG.
const ORIGIN = [112, 196];
const screen = ([x, y]) => [ORIGIN[0] + x, ORIGIN[1] - y];
let fallFrames = null;
function airborneFall() {
  if (!fallFrames) {
    const frames = simulateFall();
    // End in the late tipping phase, with 12 px of clearance under the body.
    // The same final pose feeds both the drawing and the contour vortex;
    // the landing/collapse is deliberately not played for save feedback.
    const end = frames.findLastIndex(frame => frame.phase === 'tip'
      && lowestPoint(pose(frame.params), ['handR']) >= 12);
    fallFrames = frames.slice(0, end + 1);
  }
  return fallFrames;
}
const fallAt = seconds => airborneFall().find(frame => frame.t >= seconds) ?? airborneFall().at(-1);
const fallDuration = () => airborneFall().at(-1).t;

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
  const paint = svgEl('g', {class: 'sf-paint'});
  paint.append(svgEl('circle', {class: 'sf-flow-disc', cx: 130, cy: 110, r: 0}));
  paint.append(svgEl('g', {class: 'sf-flow-lines'}));
  const badge = svgEl('g', {class: 'sf-badge'});
  badge.append(svgEl('circle', {cx: 130, cy: 110, r: 44}));
  badge.append(svgEl('path', {class: 'sf-mark', pathLength: 1}));
  svg.append(figure, paint, badge);
  const text = document.createElement('p');
  text.className = 'sf-text';
  text.dataset.sfText = '';
  text.setAttribute('role', 'status');
  text.setAttribute('aria-live', 'polite');
  const dismiss = document.createElement('button');
  dismiss.type = 'button';
  dismiss.className = 'sf-dismiss';
  root.append(svg, text, dismiss);
  document.body.append(root);
  return {root, svg, figure, paint, badge, mark: badge.querySelector('.sf-mark'), text, dismiss};
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

const ease = t => { t = clamp(t); return t * t * (3 - 2 * t); };

// Sample each subpath separately so a pen-up between legs or eyes never
// becomes a new connecting line. These are the actual last drawn contours.
function captureFlow(parts, origin) {
  const group = parts.paint.querySelector('.sf-flow-lines');
  group.replaceChildren();
  const strokes = [];
  for (const source of parts.figure.querySelectorAll('path, circle')) {
    const style = getComputedStyle(source);
    const isHead = source.tagName.toLowerCase() === 'circle';
    const contours = isHead ? [null] : source.getAttribute('d').split(/(?=M)/).filter(Boolean);
    for (const d of contours) {
      const path = svgEl('path', d ? {d} : {});
      group.append(path);
      let points;
      if (isHead) {
        const x = Number(source.getAttribute('cx')), y = Number(source.getAttribute('cy'));
        const r = Number(source.getAttribute('r'));
        points = Array.from({length: 49}, (_, i) => [x + r * Math.cos(i * Math.PI / 24), y + r * Math.sin(i * Math.PI / 24)]);
      } else {
        const length = path.getTotalLength(), count = Math.max(2, Math.ceil(length / 1.5));
        points = Array.from({length: count + 1}, (_, i) => {
          const p = path.getPointAtLength(length * i / count);
          return [p.x, p.y];
        });
      }
      strokes.push({path, points, width: parseFloat(style.strokeWidth), fill: isHead ? style.fill : null,
        color: style.stroke.match(/[\d.]+/g).slice(0, 3).map(Number), opacity: Number(style.opacity)});
    }
  }
  const extent = Math.max(...strokes.flatMap(s => s.points.map(p => Math.hypot(p[0] - origin[0], p[1] - origin[1]))));
  return {strokes, origin, extent};
}

function drawPaint(parts, flow, k, ok) {
  const color = ok ? [31, 157, 85] : [217, 59, 59];
  const tint = ease(k / 0.65), merge = ease((k - 0.62) / 0.38);
  // Substitute identical contours at k=0, then deform them point by point.
  parts.figure.style.opacity = '0';
  parts.root.querySelector('.sf-floor').style.opacity = String(0.16 * (1 - ease(k / 0.25)));
  parts.paint.style.opacity = '1';
  const disc = parts.paint.querySelector('.sf-flow-disc');
  disc.setAttribute('r', String(44 * merge));
  for (const stroke of flow.strokes) {
    const points = stroke.points.map(p => vortexPoint(p, flow.origin, flow.extent, k));
    stroke.path.setAttribute('d', points.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(2)} ${p[1].toFixed(2)}`).join(''));
    stroke.path.style.stroke = `rgb(${stroke.color.map((c, i) => Math.round(c + (color[i] - c) * tint)).join(',')})`;
    stroke.path.style.strokeWidth = String(stroke.width + (10 - stroke.width) * ease(k / 0.8));
    stroke.path.style.opacity = String(stroke.opacity * (1 - ease((k - 0.8) / 0.2)));
    // Keep the head's occlusion at the hand-off, then let it dissolve as it curls.
    if (stroke.fill) stroke.path.style.fill = `color-mix(in srgb, ${stroke.fill} ${100 * (1 - ease(k / 0.25))}%, transparent)`;
  }
}

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

/** Result feedback only: no figure while the request is pending or on page load. */
export async function playSaveFeedback({request, variant = 'short', form, labels}) {
  const wasInert = form?.inert ?? false;
  if (form) form.inert = true;
  const ok = await Promise.resolve(request).then(Boolean, () => false);
  parts ??= build();
  const t = timings[variant] ?? timings.short;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const signal = {skip: false, onSkip: null};
  const activeAnimations = [];
  const animate = (node, frames, options) => {
    if (!node) return;
    const animation = node.animate(frames, options);
    activeAnimations.push(animation);
    return animation;
  };
  const skip = () => {
    signal.skip = true;
    signal.onSkip?.();
    for (const animation of activeAnimations) {
      if (animation.playState === 'running') animation.finish();
    }
  };
  const onKey = event => {
    if (event.key === 'Escape') { event.preventDefault(); skip(); }
    if (event.key === 'Tab') { event.preventDefault(); parts.dismiss.focus({preventScroll: true}); }
  };
  const {root, figure, paint, badge, mark, text, dismiss} = parts;
  const floor = root.querySelector('.sf-floor');
  document.dispatchEvent(new Event('studio:close-menu'));
  const previousFocus = document.activeElement;
  const background = [...document.querySelectorAll('header, main, footer, .skip-link')].map(node => [node, node.inert]);
  for (const [node] of background) node.inert = true;
  root.hidden = false;
  root.setAttribute('role', 'dialog');
  root.setAttribute('aria-modal', 'true');
  const uk = document.documentElement.lang !== 'en';
  root.setAttribute('aria-label', uk ? 'Результат збереження' : 'Save result');
  dismiss.textContent = uk ? 'Пропустити' : 'Skip';
  root.tabIndex = -1;
  root.focus({preventScroll: true});
  root.dataset.outcome = 'pending';
  root.dataset.phase = 'shift';
  root.dataset.mode = reduced ? 'static' : 'motion';
  text.textContent = '';
  figure.style.cssText = '';
  floor.style.cssText = '';
  badge.style.cssText = 'opacity:0';
  paint.style.cssText = 'opacity:0';
  mark.style.strokeDashoffset = '1';
  root.addEventListener('click', skip);
  document.addEventListener('keydown', onKey);
  try {
    if (!reduced) {
      animate(form, [{opacity: 1}, {opacity: 0}], {duration: t.fadeForm, fill: 'forwards', easing: 'ease-out'});
      draw(parts, balanceParams(0));
      animate(root, [{opacity: 0}, {opacity: 1}], {duration: t.appear, easing: 'ease-out'});
      await wait(t.appear, signal);
      await tween(t.shift, k => draw(parts, balanceParams(k)), signal);
      if (ok) {
        root.dataset.phase = 'hold';
        await tween(t.hold, k => draw(parts, holdParams(Math.sin(Math.PI * k) * 0.08)), signal);
      } else if (!signal.skip) {
        root.dataset.phase = 'fall';
        // No successful hold in a failed attempt: the legs try to correct the
        // balance immediately. Merge from the late airborne pose, before landing.
        await tween(fallDuration() * 1000, k => draw(parts, fallAt(k * fallDuration()).params), signal);
      }
      root.dataset.phase = 'paint';
      root.dataset.resultColor = ok ? 'success' : 'error';
      if (!signal.skip) {
        const lastPose = ok ? balanceParams(1) : fallAt(fallDuration()).params;
        const source = screen(centerOfMass(pose(lastPose)));
        const flow = captureFlow(parts, source);
        await tween(t.paint, k => drawPaint(parts, flow, k, ok), signal);
      }
    }
    root.dataset.phase = 'result';
    root.dataset.outcome = ok ? 'success' : 'error';
    mark.setAttribute('d', ok ? 'M109 111L124 126L152 95' : 'M115 95L145 125M145 95L115 125');
    figure.style.opacity = '0';
    floor.style.opacity = '0';
    paint.style.opacity = '0';
    if (reduced || signal.skip) {
      badge.style.opacity = '1';
      mark.style.strokeDashoffset = '0';
    } else {
      // The curled contours have merged into this exact circle; no replacement pop.
      badge.style.opacity = '1';
      animate(mark, [{strokeDashoffset: 1}, {strokeDashoffset: 0}],
        {duration: t.mark, easing: 'ease-out', fill: 'forwards'});
      await wait(t.mark, signal);
    }
    text.textContent = ok ? labels.saved : labels.error;
    dismiss.textContent = uk ? 'Повернутися до форми' : 'Back to form';
    if (signal.skip) await new Promise(resolve => setTimeout(resolve, 350));
    else await wait(t.result, signal);
    if (!reduced && !signal.skip) {
      animate(root, [{opacity: 1}, {opacity: 0}], {duration: 160});
      await wait(160, signal);
    }
  } finally {
    root.removeEventListener('click', skip);
    document.removeEventListener('keydown', onKey);
    activeAnimations.forEach(animation => animation.cancel());
    root.hidden = true;
    for (const [node, inert] of background) node.inert = inert;
    if (form) form.inert = wasInert;
    if (previousFocus?.isConnected) previousFocus.focus({preventScroll: true});
  }
  return ok;
}
