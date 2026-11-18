import test from 'node:test';
import assert from 'node:assert/strict';
import * as R from '../../server/static/js/components/acro-rig.js';

const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
const angleOf = (a, b) => Math.atan2(b[0] - a[0], b[1] - a[1]) * 180 / Math.PI; // 0 = up
const lengthsKept = j => R.LENGTHS.every(([a, b, l]) => Math.abs(dist(j[a], j[b]) - l) < 1e-6);
const toSegment = (p, a, b) => {
  const [vx, vy] = [b[0] - a[0], b[1] - a[1]];
  const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / (vx * vx + vy * vy)));
  return dist(p, [a[0] + vx * t, a[1] + vy * t]);
};
const transition = Array.from({length: 401}, (_, i) => R.pose(R.balanceParams(i / 400)));
const hold = Array.from({length: 301}, (_, i) => R.pose(R.holdParams(i / 100)));
const fall = R.simulateFall();

test('rigid_segments_everywhere', () => {
  for (const j of [...transition, ...hold, ...fall.map(f => R.pose(f.params))]) assert.ok(lengthsKept(j));
});

test('two_hands_balanced_between_hands', () => {
  const j = transition[0];
  assert.equal(j.handR[1], 0);
  assert.equal(j.handL[1], 0);
  assert.ok(Math.abs(R.centerOfMass(j)[0] - (j.handL[0] + j.handR[0]) / 2) < 0.5);
});

test('free_hand_lifts_only_with_com_over_support_palm', () => {
  let lifted = false;
  for (const j of [...transition, ...hold]) {
    assert.equal(dist(j.handR, [0, 0]), 0, 'support hand never moves');
    if (j.handL[1] > 0.05) {
      lifted = true;
      assert.ok(Math.abs(R.centerOfMass(j)[0]) <= R.PALM, `COM ${R.centerOfMass(j)[0]} off the palm`);
    } else {
      assert.ok(dist(j.handL, R.FREE_PLANT) < 0.05, 'planted free hand does not slide');
    }
  }
  assert.ok(lifted);
});

test('one_arm_shape_matches_reference', () => {
  const j = transition.at(-1);
  assert.ok(Math.abs(angleOf(j.handR, j.shoulderR)) <= 6, 'support arm vertical');
  assert.ok(Math.abs(Math.abs(angleOf(j.shoulderL, j.handL)) - 90) <= 15, 'free arm out to the side');
  const legR = angleOf(j.hipR, j.footR), legL = angleOf(j.hipL, j.footL);
  assert.ok(legR - legL >= 100, 'wide straddle');
  assert.ok(Math.abs(Math.abs(legR) - 90) <= 15 || Math.abs(Math.abs(legL) - 90) <= 15, 'one leg horizontal');
  assert.ok(toSegment(j.head, j.handR, j.shoulderR) <= R.SEG.head + 3, 'head next to the support arm');
  assert.ok(j.head[1] - R.SEG.head > 0 && j.head[1] < j.shoulderR[1], 'head between shoulders and floor');
});

test('fall_follows_gravity_and_never_goes_through_floor', () => {
  const tip = fall.filter(f => f.phase === 'tip');
  for (const f of fall) assert.ok(R.lowestPoint(R.pose(f.params)) >= -1e-6, `${f.phase} ${f.t} below floor`);
  for (const f of fall.filter(f => f.phase !== 'collapse' && f.phase !== 'rest')) {
    assert.equal(dist(R.pose(f.params).handR, [0, 0]), 0, 'pivot wrist fixed while tipping');
  }
  // Inverted pendulum: angular speed grows while tipping.
  for (let i = 1; i < tip.length - 1; i++) assert.ok(tip[i].omega > tip[i - 1].omega);
  const height = fall.filter(f => f.phase === 'tip' || f.phase === 'collapse').map(f => R.centerOfMass(R.pose(f.params))[1]);
  for (let i = 1; i < height.length; i++) assert.ok(height[i] <= height[i - 1] + 0.05, 'COM keeps dropping');
  const rest = R.pose(fall.at(-1).params);
  assert.ok(Math.abs(Math.abs(angleOf(rest.neck, rest.pelvis)) - 90) <= 15, 'lies on the side');
  assert.ok(Object.values(rest).every(([, y]) => y <= 46), 'body on the floor');
  const duration = fall.at(-1).t;
  assert.ok(duration > 0.8 && duration < 2.0, `fall takes ${duration}s`);
});

test('free_arm_opens_without_swinging_overhead', () => {
  // The free hand goes out to the side; it never passes above shoulder height + a little.
  for (const j of transition) assert.ok(j.handL[1] <= j.shoulderL[1] + 8, `hand ${j.handL[1]} above shoulder ${j.shoulderL[1]}`);
});
