import test from 'node:test';
import assert from 'node:assert/strict';
import {vortexPoint} from '../../server/static/js/components/save-vortex.js';

const origin = [108, 155], radius = 105;
const points = [[108, 50], [130, 100], [80, 150], [190, 190], [60, 190]];
const distance = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);

test('vortex starts on the actual figure contours without a replacement jump', () => {
  for (const point of points) assert.ok(distance(vortexPoint(point, origin, radius, 0), point) < 1e-8);
});

test('vortex deforms the contours rather than rotating the figure as a rigid image', () => {
  const center = vortexPoint(origin, origin, radius, 0.5);
  const inner = vortexPoint([origin[0] + 20, origin[1]], origin, radius, 0.5);
  const outer = vortexPoint([origin[0] + 90, origin[1]], origin, radius, 0.5);
  const angle = p => Math.atan2(p[1] - center[1], p[0] - center[0]);
  assert.ok(Math.abs(angle(inner) - angle(outer)) > 0.5, 'inner and outer contours curl at different rates');
});

test('standing and fallen contours flow continuously into the result disc', () => {
  for (const start of [[108, 100], [150, 185]]) {
    for (const point of points) {
      let last = point;
      for (let i = 1; i <= 120; i++) {
        const current = vortexPoint(point, start, 180, i / 120);
        assert.ok(current.every(Number.isFinite));
        assert.ok(distance(current, last) < 12, 'no teleport between frames');
        last = current;
      }
      assert.ok(distance(last, [130, 110]) < 40, 'contour settles inside the result circle');
    }
  }
});
