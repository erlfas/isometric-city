import type { River } from '../types';

/**
 * Geometry of the plan's river (CityPlan.river, generate_city_plan.py generate_river): the
 * centreline with a frame per point, and polygons offset from it. Shared by the ground
 * splat (banks), the nav grid (the channel is blocked) and the soundscape (running water).
 */

export interface RiverFrame {
  x: number;
  z: number;
  /** Water width (m). */
  w: number;
  /** Unit normal to the left of the flow (x-z plane, rotated +90 deg from the direction). */
  nx: number;
  nz: number;
  /** Signed curvature (1/m), smoothed over ~40 m; > 0 = the course turns towards +n. */
  curv: number;
}

export interface XZ { x: number; z: number }

export function riverFrames(river: River): RiverFrame[] {
  const p = river.points;
  const n = p.length;
  const raw = new Float64Array(n);
  const out: RiverFrame[] = [];
  for (let i = 0; i < n; i++) {
    const a = p[Math.max(0, i - 1)], b = p[Math.min(n - 1, i + 1)];
    const dx = b.x - a.x, dz = b.z - a.z;
    const len = Math.hypot(dx, dz) || 1;
    out.push({ x: p[i].x, z: p[i].z, w: p[i].width, nx: -dz / len, nz: dx / len, curv: 0 });
    if (i > 0 && i < n - 1) {
      const h1 = Math.atan2(p[i].z - p[i - 1].z, p[i].x - p[i - 1].x);
      const h2 = Math.atan2(p[i + 1].z - p[i].z, p[i + 1].x - p[i].x);
      let dh = h2 - h1;
      if (dh > Math.PI) dh -= 2 * Math.PI;
      if (dh < -Math.PI) dh += 2 * Math.PI;
      raw[i] = dh / (Math.hypot(p[i + 1].x - p[i].x, p[i + 1].z - p[i].z) || 1);
    }
  }
  const K = 6;
  for (let i = 0; i < n; i++) {
    let s = 0, c = 0;
    for (let j = Math.max(0, i - K); j <= Math.min(n - 1, i + K); j++) { s += raw[j]; c++; }
    out[i].curv = s / c;
  }
  return out;
}

/** Closed ring between two signed offsets along the normal (from < to across the flow),
 *  e.g. (-(w/2 + 5), w/2 + 5) = the channel plus 5 m of bank on both sides. */
export function riverBand(frames: RiverFrame[], from: (f: RiverFrame) => number, to: (f: RiverFrame) => number,
  i0 = 0, i1 = frames.length - 1): XZ[] {
  const ring: XZ[] = [];
  for (let i = i0; i <= i1; i++) { const f = frames[i], o = to(f); ring.push({ x: f.x + f.nx * o, z: f.z + f.nz * o }); }
  for (let i = i1; i >= i0; i--) { const f = frames[i], o = from(f); ring.push({ x: f.x + f.nx * o, z: f.z + f.nz * o }); }
  return ring;
}

/** The channel as one quad per centreline segment (for rasterising), widened by `extra` per bank. */
export function channelQuads(frames: RiverFrame[], extra = 0): XZ[][] {
  const quads: XZ[][] = [];
  const side = (f: RiverFrame, s: number): XZ => {
    const o = s * (f.w * 0.5 + extra);
    return { x: f.x + f.nx * o, z: f.z + f.nz * o };
  };
  for (let i = 0; i + 1 < frames.length; i++) {
    const a = frames[i], b = frames[i + 1];
    quads.push([side(a, 1), side(b, 1), side(b, -1), side(a, -1)]);
  }
  return quads;
}

/** Centreline points every `step` metres of arc. */
export function resampleRiver(river: River, step: number): XZ[] {
  const p = river.points;
  if (p.length === 0) return [];
  const out: XZ[] = [{ x: p[0].x, z: p[0].z }];
  let need = step;
  for (let i = 0; i + 1 < p.length; i++) {
    const seg = Math.hypot(p[i + 1].x - p[i].x, p[i + 1].z - p[i].z);
    let pos = 0;
    while (seg - pos >= need) {
      pos += need;
      const t = pos / seg;
      out.push({ x: p[i].x + (p[i + 1].x - p[i].x) * t, z: p[i].z + (p[i + 1].z - p[i].z) * t });
      need = step;
    }
    need -= seg - pos;
  }
  return out;
}
