// Stylised front-view acrobat: fixed bone lengths, balanced support and staged ground contact.
// This is animation choreography with constraints, not a human biomechanics simulation.
// World units: px, y up, support wrist fixed until landing, then released. Angles in degrees,
// 0 = straight up, positive = clockwise (towards +x). Segment lengths never change.
const rad = Math.PI / 180;
const dir = a => [Math.sin(a * rad), Math.cos(a * rad)];
const add = (p, v, s = 1) => [p[0] + v[0] * s, p[1] + v[1] * s];
const mix = (a, b, t) => a + (b - a) * t;
const clamp = t => Math.max(0, Math.min(1, t));
const smooth = t => { t = clamp(t); return t * t * (3 - 2 * t); };

export const SEG = {upper: 24, fore: 24, shoulder: 17, neck: 6, head: 9.5, spine: 58, hip: 7, thigh: 33, shank: 33};
// Fraction of body mass per segment (Dempster-style anthropometrics). Sums to 1.
export const MASS = {head: 0.081, trunk: 0.497, upper: 0.028, fore: 0.022, thigh: 0.100, shank: 0.061};
export const G = 843; // px/s²: 9.81 m/s² at ~86 px per metre for this figure.
const ELEVATION = 12; // scapular lift towards the ears, present before the transfer
const SHOULDER_HALF_WIDTH = Math.sqrt(SEG.shoulder ** 2 - ELEVATION ** 2);
export const FREE_PLANT = [-2 * SHOULDER_HALF_WIDTH, 0];
export const PALM = 4; // half-width of the support base (palm + fingers) in px

// Forward kinematics. Free arm is either IK'd to a planted hand or given absolute angles.
export function pose(p) {
  const j = {handR: [0, 0]};
  j.elbowR = add(j.handR, dir(p.foreS ?? p.aS), SEG.fore);
  j.shoulderR = add(j.elbowR, dir(p.upperS ?? p.aS), SEG.upper);
  // The shoulder girdle and trunk have separate angles. Load transfer happens
  // through the ribcage/hips; it must not lean the supporting arm off its wrist.
  // In an inverted shrug the shoulder joints are towards the ears (below the
  // neck in world space), with constant clavicle lengths.
  const girdle = p.aC ?? p.aT;
  const left = dir(girdle - 90), up = dir(girdle);
  // Extra unilateral scapular elevation lifts the ribcage relative to the
  // planted, straight support arm. Clavicles keep their length; no arm stretch.
  const elevation = ELEVATION + 3.3 * (p.push ?? 0);
  const supportWidth = Math.sqrt(SEG.shoulder ** 2 - elevation ** 2);
  j.neck = add(add(j.shoulderR, left, supportWidth), up, elevation);
  j.shoulderL = add(add(j.neck, left, SHOULDER_HALF_WIDTH), up, -ELEVATION);
  j.head = add(j.neck, dir(girdle + 180 + (p.headTilt ?? 0)), SEG.neck + SEG.head);
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
  if (p.rootX || p.rootY) {
    for (const point of Object.values(j)) { point[0] += p.rootX ?? 0; point[1] += p.rootY ?? 0; }
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
  for (const key of ['aS', 'foreS', 'upperS', 'aT', 'aC', 'legR', 'legL', 'armL']) if (q[key] != null) q[key] += by;
  return q;
}

// Solve the lateral trunk/hip position while the supporting wrist, elbow and
// shoulder remain exactly stacked. Both hands stay planted until load is over
// the support palm; the lifted arm then counterbalances through the trunk.
export function balance(p, targetX = 0) {
  let lo = -35, hi = 50;
  for (let i = 0; i < 45; i++) {
    const aT = (lo + hi) / 2;
    if (centerOfMass(pose({...p, aT}))[0] > targetX) hi = aT; else lo = aT;
  }
  return {...p, aT: (lo + hi) / 2};
}

const TWO_HANDS = {aS: 0, aC: 0, aT: 0, legR: 2, legL: -2, armL: null, headTilt: 0, push: 0};
const ONE_ARM = {...TWO_HANDS, aT: 18, push: 1, legR: 88, legL: -35, armL: -98, elbowL: 4};
const LOADED = {...TWO_HANDS, legR: 70, legL: -35};
const SHIFT_END = 0.55;
const PEEL = 0.25;

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
    return balance(blend(TWO_HANDS, LOADED, u), mix(FREE_PLANT[0] / 2, 0, u));
  }
  // Free hand off: it first lifts straight up, then the arm opens to the side while the
  // straddle and trunk lean develop. The COM stays on the support palm throughout.
  const u = (k - SHIFT_END) / (1 - SHIFT_END);
  const loaded = balance(LOADED, 0);
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
// wrist until the first body point touches the floor, then a choreographed knee/forearm
// landing with contact constraints. Precomputed frames, ~240 Hz.
const LYING = {push: 0, foreS: 90, upperS: 70, aT: 90, aC: 90, headTilt: -30, legR: 102, kneeR: -12, legL: 82, kneeL: 24, armL: -95, elbowL: -10};

export function simulateFall({lossSeconds = 0.38} = {}) {
  const dt = 1 / 240;
  const frames = [];
  // 1) Loss of balance: growing correction wobble, then the COM leaves the palm.
  for (let t = 0; t <= lossSeconds; t += dt) {
    const u = t / lossSeconds;
    const target = 1.6 * u * Math.sin(t * 2 * Math.PI / 0.16) + (PALM + 2.5) * u ** 2;
    // Two increasingly urgent scissor corrections. Their envelope starts at
    // zero so the failed attempt flows directly out of the transfer pose.
    const kick = Math.sin(u * Math.PI * 4) * Math.sin(u * Math.PI) * 15;
    frames.push({t, phase: 'loss', params: balance({...ONE_ARM,
      legR: ONE_ARM.legR + kick, legL: ONE_ARM.legL - kick * 0.8,
      kneeL: Math.max(0, -kick) * 0.35}, target)});
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
  // 3) The leading foot contacts first. Release the wrist, fold the landing knee,
  // lower the hip and settle on the forearm/side. Keep the landed foot horizontally
  // anchored; ground clearance is solved after posing, not by stretching bones.
  const from = {...rotated, foreS: rotated.aS, upperS: rotated.aS, kneeR: 0, kneeL: 0};
  delete from.aS;
  const landingX = pose(from).footR[0];
  const grounded = params => {
    const j = pose(params);
    return {...params, rootX: landingX - j.footR[0], rootY: -lowestPoint(j)};
  };
  const fold = {...from, foreS: 70, upperS: 55, aT: 72, aC: 72, headTilt: -30,
    legR: 132, kneeR: -55, legL: 30, kneeL: 35, armL: -100, elbowL: -10};
  // The body decelerates as the foot/knee/forearm accept the landing. Unlike the
  // old wrist-pinned interpolation, the shoulder can travel with the falling body.
  const stages = [[from, fold, 0.24], [fold, LYING, 0.34]];
  for (const [a, b, duration] of stages) {
    const start = t;
    const count = Math.ceil(duration / dt);
    for (let i = 1; i <= count; i++) {
      t = start + duration * i / count;
      frames.push({t, phase: 'collapse', params: grounded(blend(a, b, smooth(i / count)))});
    }
  }
  frames.push({t: t + dt, phase: 'rest', params: grounded(LYING)});
  return frames;
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
