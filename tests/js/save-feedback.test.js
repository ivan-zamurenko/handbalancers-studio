import test from 'node:test';
import assert from 'node:assert/strict';
import {FLOOR, frontPose, timings} from '../../server/static/js/components/save-feedback.js';

const near = (a, b, d = 0.5) => Math.abs(a - b) <= d;

test('two_hands_front_view', () => {
  const pose = frontPose();
  for (const hand of [pose.handL, pose.handR]) assert.ok(near(hand[1], FLOOR), 'both hands on the floor');
  assert.ok(pose.handL[0] < pose.head[0] && pose.head[0] < pose.handR[0], 'head between the hands');
  assert.ok(pose.head[1] > pose.shoulderL[1] && pose.head[1] < FLOOR, 'head below shoulders, above floor');
  assert.ok(pose.footL[1] < pose.hipL[1] && pose.hipL[1] < pose.shoulderL[1], 'legs up, upside down');
});

test('one_arm_balance', () => {
  const pose = frontPose({shift:1, lift:1});
  assert.ok(near(pose.handR[1], FLOOR), 'support hand stays planted');
  assert.ok(near(pose.shoulderR[0], pose.handR[0], 1), 'support shoulder stacked over the hand');
  assert.ok(pose.handL[1] < FLOOR - 25, 'free hand lifted off the floor');
});

test('fall_lands_on_floor_sideways', () => {
  const pose = frontPose({shift:1, lift:1, fall:1});
  const points = Object.values(pose);
  assert.ok(points.every(([, y]) => y <= FLOOR + 1), 'nothing below the floor');
  assert.ok(pose.footL[0] < pose.handR[0] - 100, 'body lies to the side');
  assert.ok(Math.abs(pose.footL[1] - pose.hipL[1]) < 40, 'body roughly horizontal');
});

test('full_vs_short_timing', () => {
  const sum = t => t.shift + t.hold + t.vortex + t.mark;
  assert.ok(sum(timings.full) >= 2300 && timings.full.hold >= 1000, 'full keeps the 1 s hold');
  assert.ok(sum(timings.short) <= 1300, 'short stays brief');
});
