// A differential curl: inner contours wind faster than outer ones. At k=0
// every point is still on the source figure; no rigid image rotation or blobs.
const smooth = t => { t = Math.max(0, Math.min(1, t)); return t * t * (3 - 2 * t); };

export function vortexPoint(point, origin, extent, k) {
  const u = smooth(k);
  const dx = point[0] - origin[0], dy = point[1] - origin[1];
  const radius = Math.hypot(dx, dy);
  const depth = Math.min(1, radius / Math.max(1, extent));
  const angle = Math.atan2(dy, dx) + Math.PI * 3 * u * (1 - 0.8 * depth);
  const r = radius * (1 - u) + 32 * depth * u;
  return [
    origin[0] + (130 - origin[0]) * u + Math.cos(angle) * r,
    origin[1] + (110 - origin[1]) * u + Math.sin(angle) * r,
  ];
}
