// Front-view acrobat rig with real constraints, used by the save feedback animation.
// World units: px, y up, support (right) wrist fixed at (0, 0). Absolute angles in degrees,
// 0 = straight up, positive = clockwise (towards +x). Segment lengths never change.
const rad = Math.PI / 180;
const dir = a => [Math.sin(a * rad), Math.cos(a * rad)];
const add = (p, v, s = 1) => [p[0] + v[0] * s, p[1] + v[1] * s];
const mix = (a, b, t) => a + (b - a) * t;
const clamp = t => Math.max(0, Math.min(1, t));
const smooth = t => { t = clamp(t); return t * t * (3 - 2 * t); };

export const SEG = {upper: 24, fore: 24, shoulder: 15, neck: 6, head: 9.5, spine: 58, hip: 7, thigh: 33, shank: 33};
// Fraction of body mass per segment (Dempster-style anthropometrics). Sums to 1.
export const MASS = {head: 0.081, trunk: 0.497, upper: 0.028, fore: 0.022, thigh: 0.100, shank: 0.061};
export const G = 843; // px/s²: 9.81 m/s² at ~86 px per metre for this figure.
export const FREE_PLANT = [-30, 0]; // free hand under its shoulder in the two-hand stand
export const PALM = 4; // half-width of the support base (palm + fingers) in px

// Forward kinematics. Free arm is either IK'd to a planted hand or given absolute angles.
export function pose(p) {
  const j = {handR: [0, 0]};
  j.elbowR = add(j.handR, dir(p.foreS ?? p.aS), SEG.fore);
  j.shoulderR = add(j.elbowR, dir(p.upperS ?? p.aS), SEG.upper);
  const left = dir(p.aT - 90);
  j.neck = add(j.shoulderR, left, SEG.shoulder);
  j.shoulderL = add(j.neck, left, SEG.shoulder);
  j.head = add(j.neck, dir(p.aT + 180 + (p.headTilt ?? 0)), SEG.neck + SEG.head);
  j.pelvis = add(j.neck, dir(p.aT), SEG.spine);
  j.hipR = add(j.pelvis, dir(p.aT + 90), SEG.hip);
  j.hipL = add(j.pelvis, dir(p.aT - 90), SEG.hip);
  j.kneeR = add(j.hipR, dir(p.legR), SEG.thigh);
  j.footR = add(j.kneeR, dir(p.legR + (p.kneeR ?? 0)), SEG.shank);
  j.kneeL = add(j.hipL, dir(p.legL), SEG.thigh);
  j.footL = add(j.kneeL, dir(p.legL + (p.kneeL ?? 0)), SEG.shank);
  if (p.armL == null) {
    // Planted free hand: two-bone IK; if out of reach the hand leaves the floor (straight arm).
    // liftL raises the free hand straight up off its spot (fingers peel off, no sliding).
    const target = [FREE_PLANT[0], FREE_PLANT[1] + (p.liftL ?? 0)];
    const [dx, dy] = [target[0] - j.shoulderL[0], target[1] - j.shoulderL[1]];
    const d = Math.hypot(dx, dy), reach = SEG.upper + SEG.fore;
    if (d >= reach) {
      j.handL = add(j.shoulderL, [dx / d, dy / d], reach);
      j.elbowL = add(j.shoulderL, [dx / d, dy / d], SEG.upper);
    } else {
      j.handL = target;
      const h = Math.sqrt(SEG.upper ** 2 - (d / 2) ** 2);
      // Elbow bends outward (away from the body, to the left), as a real arm does.
      const a = [j.shoulderL[0] + dx / 2 - (dy / d) * h, j.shoulderL[1] + dy / 2 + (dx / d) * h];
      const b = [j.shoulderL[0] + dx / 2 + (dy / d) * h, j.shoulderL[1] + dy / 2 - (dx / d) * h];
      j.elbowL = a[0] <= b[0] ? a : b;
    }
  } else {
    j.elbowL = add(j.shoulderL, dir(p.armL), SEG.upper);
    j.handL = add(j.elbowL, dir(p.armL + (p.elbowL ?? 0)), SEG.fore);
  }
  return j;
}

const segments = j => [
  [MASS.head, j.head, 0], [MASS.trunk, mid(j.neck, j.pelvis), SEG.spine],
  [MASS.upper, mid(j.shoulderR, j.elbowR), SEG.upper], [MASS.fore, mid(j.elbowR, j.handR), SEG.fore],
  [MASS.upper, mid(j.shoulderL, j.elbowL), SEG.upper], [MASS.fore, mid(j.elbowL, j.handL), SEG.fore],
  [MASS.thigh, mid(j.hipR, j.kneeR), SEG.thigh], [MASS.shank, mid(j.kneeR, j.footR), SEG.shank],
  [MASS.thigh, mid(j.hipL, j.kneeL), SEG.thigh], [MASS.shank, mid(j.kneeL, j.footL), SEG.shank],
];
function mid(a, b) { return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]; }

export function centerOfMass(j) {
  let x = 0, y = 0;
  for (const [m, c] of segments(j)) { x += m * c[0]; y += m * c[1]; }
  return [x, y];
}

// Moment of inertia about the support wrist (segments as rods, head as a sphere).
export function inertiaAboutWrist(j) {
  let total = 0;
  for (const [m, c, length] of segments(j)) {
    total += m * (c[0] ** 2 + c[1] ** 2) + (length ? m * length ** 2 / 12 : 0.4 * m * SEG.head ** 2);
  }
  return total;
}

// Rotate the whole body about the wrist (wrist/fingers control): every absolute angle shifts.
export function rotate(p, by) {
  const q = {...p};
  for (const key of ['aS', 'foreS', 'upperS', 'aT', 'legR', 'legL', 'armL']) if (q[key] != null) q[key] += by;
  return q;
}

// Lean the body about the wrist until the centre of mass is at targetX (bisection).
export function balance(p, targetX = 0) {
  let lo = -40, hi = 40;
  for (let i = 0; i < 50; i++) {
    const m = (lo + hi) / 2;
    if (centerOfMass(pose(rotate(p, m)))[0] > targetX) hi = m; else lo = m;
  }
  return rotate(p, (lo + hi) / 2);
}

// Two hands planted: lean the arms as a parallelogram (both arms tilt by the same angle,
// shoulders stay level), which moves the body sideways without lifting the free hand.
export function lean(p, targetX) {
  let lo = -30, hi = 30;
  for (let i = 0; i < 50; i++) {
    const m = (lo + hi) / 2;
    if (centerOfMass(pose({...p, aS: m})).at(0) > targetX) hi = m; else lo = m;
  }
  return {...p, aS: (lo + hi) / 2};
}

// Key shapes. Two hands: arms vertical under the shoulders, legs together.
const TWO_HANDS = {aS: 0, aT: 0, legR: 2, legL: -2, armL: null};
// One arm (owner's reference photo): free arm out to the side, wide straddle with one leg
// horizontal and the other diagonal, trunk leaning towards the horizontal leg.
const ONE_ARM = {aS: 0, aT: 18, legR: 88, legL: -35, armL: -98, elbowL: 4, headTilt: -28};
const LOADED = {aS: 0, aT: 0, legR: 30, legL: -10, armL: null, headTilt: 0};
const SHIFT_END = 0.55; // share of the transition spent shifting weight with both hands down
const PEEL = 0.25; // share of the lift spent raising the free hand straight up

function blend(a, b, t) {
  const out = {};
  for (const key of new Set([...Object.keys(a), ...Object.keys(b)])) {
    out[key] = a[key] == null || b[key] == null ? (t < 1 ? a[key] : b[key]) : mix(a[key], b[key], t);
  }
  return out;
}

// k: 0 → 1 over the whole two-hands → one-arm transition.
export function balanceParams(k) {
  if (k <= SHIFT_END) {
    // Weight shift: COM travels from between the hands to over the support palm,
    // legs start to open; the free hand stays planted while it can still reach.
    const u = smooth(k / SHIFT_END);
    return lean(blend({...TWO_HANDS, headTilt: 0}, LOADED, u), mix(-15, 0, u));
  }
  // Free hand off: it first lifts straight up, then the arm opens to the side while the
  // straddle and trunk lean develop. The COM stays on the support palm throughout.
  const u = (k - SHIFT_END) / (1 - SHIFT_END);
  const loaded = lean(LOADED, 0);
  if (u <= PEEL) return balance({...loaded, liftL: 10 * smooth(u / PEEL)}, 0);
  const peeled = balance({...loaded, liftL: 10}, 0);
  const j = pose(peeled);
  const angle = (a, b) => Math.atan2(b[0] - a[0], b[1] - a[1]) / rad;
  // Take the short way round to the target angles (no full spins of a joint).
  const near = (a, target) => a + 360 * Math.round((target - a) / 360);
  const armL = near(angle(j.shoulderL, j.elbowL), ONE_ARM.armL);
  const start = {...peeled, liftL: undefined, armL, elbowL: near(angle(j.elbowL, j.handL) - armL, ONE_ARM.elbowL)};
  return balance(blend(start, ONE_ARM, smooth((u - PEEL) / (1 - PEEL))), 0);
}

// Tiny finger corrections while holding: COM moves about a pixel, always within the palm.
export function holdParams(seconds) {
  return balance(ONE_ARM, 1.1 * Math.sin(seconds * 2 * Math.PI / 0.9) + 0.5 * Math.sin(seconds * 2 * Math.PI / 0.37));
}

// Fall: balance lost (COM drifts past the palm), rigid inverted-pendulum rotation about the
// wrist until the first body point touches the floor, then the support elbow buckles and the
// body drops onto its side under gravity. Precomputed frames, ~240 Hz.
const LYING = {foreS: 90, upperS: -50, aT: 100, headTilt: -70, legR: 100, legL: 98, armL: -210, elbowL: 20};

export function simulateFall({lossSeconds = 0.32} = {}) {
  const dt = 1 / 240;
  const frames = [];
  // 1) Loss of balance: growing correction wobble, then the COM leaves the palm.
  for (let t = 0; t <= lossSeconds; t += dt) {
    const u = t / lossSeconds;
    const target = 1.6 * u * Math.sin(t * 2 * Math.PI / 0.16) + (PALM + 2.5) * u ** 2;
    frames.push({t, phase: 'loss', params: balance(ONE_ARM, target)});
  }
  // 2) Inverted pendulum about the wrist: I·θ'' = M·g·r·sin θ (M = 1).
  const base = frames.at(-1).params;
  const body = pose(base);
  const [cx, cy] = centerOfMass(body);
  const r = Math.hypot(cx, cy);
  const inertia = inertiaAboutWrist(body);
  let theta = Math.atan2(cx, cy);
  const theta0 = theta;
  let omega = 0.35;
  let t = frames.at(-1).t;
  let rotated = base;
  for (let i = 0; i < 2000; i++) {
    const before = theta;
    omega += (G * r * Math.sin(theta) / inertia) * dt;
    theta += omega * dt;
    t += dt;
    rotated = rotate(base, (theta - theta0) / rad);
    if (lowestPoint(pose(rotated), ['handR']) <= 0) {
      // Find the exact touchdown angle between the last two steps.
      let lo = before, hi = theta;
      for (let n = 0; n < 40; n++) {
        const m = (lo + hi) / 2;
        if (lowestPoint(pose(rotate(base, (m - theta0) / rad)), ['handR']) > 0) lo = m; else hi = m;
      }
      rotated = rotate(base, (lo - theta0) / rad);
      frames.push({t, phase: 'tip', params: rotated, omega});
      break;
    }
    frames.push({t, phase: 'tip', params: rotated, omega});
  }
  // 3) Collapse: from first contact to lying on the side, timed by free fall of the COM.
  const from = rotated;
  const drop = Math.max(1, centerOfMass(pose(from))[1] - centerOfMass(pose(LYING))[1]);
  const duration = Math.sqrt((2 * drop) / G);
  const start = t;
  const fromParams = {...from, foreS: from.aS, upperS: from.aS};
  delete fromParams.aS;
  for (let s = dt; s <= duration + 1e-9; s += dt) {
    const u = (s / duration) ** 2; // accelerating under gravity
    frames.push({t: start + s, phase: 'collapse', params: settle(blend(fromParams, LYING, u))});
  }
  frames.push({t: start + duration + dt, phase: 'rest', params: settle(LYING)});
  return frames;
}

function settle(p) {
  return p;
}

export function lowestPoint(j, exclude = []) {
  let lowest = Infinity;
  for (const [name, point] of Object.entries(j)) {
    if (exclude.includes(name)) continue;
    lowest = Math.min(lowest, name === 'head' ? point[1] - SEG.head : point[1]);
  }
  return lowest;
}

export const LENGTHS = [
  ['handR', 'elbowR', SEG.fore], ['elbowR', 'shoulderR', SEG.upper], ['shoulderR', 'neck', SEG.shoulder],
  ['neck', 'shoulderL', SEG.shoulder], ['shoulderL', 'elbowL', SEG.upper], ['elbowL', 'handL', SEG.fore],
  ['neck', 'pelvis', SEG.spine], ['pelvis', 'hipR', SEG.hip], ['pelvis', 'hipL', SEG.hip],
  ['hipR', 'kneeR', SEG.thigh], ['kneeR', 'footR', SEG.shank], ['hipL', 'kneeL', SEG.thigh], ['kneeL', 'footL', SEG.shank],
  ['neck', 'head', SEG.neck + SEG.head],
];
