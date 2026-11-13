import * as THREE from 'three';
import type { Building, Interior, Room } from './building-anchors';
import type { PlacedPart } from './static-batches';

/**
 * Interiors (M6): walking inside a building, and the furniture you see when it is cut away.
 *
 * The data comes from the model (build_assets.py furnish / fill_sleepers / anchor_ladder,
 * parsed in building-anchors.ts): rooms per storey, furniture, slots (beds, seats,
 * workbenches, hearth) and ladders between storeys.
 *
 * Walking: each room of a model gets a CELL-metre occupancy grid in model space (walls,
 * furniture footprints grown by a body radius, stairwell holes), built once per model and
 * shared by all its placements. routeInside() is grid A* plus string pulling; between
 * storeys it goes by the ladder (foot -> straight up -> step off beside the hole).
 *
 * Drawing (InteriorProps): furniture is drawn only in a building being looked into. Its
 * parts (shared props from interior_props.glb, a plank floor per storey with the stairwell
 * left open, ladders stacked from 1 m segments) are made on demand and kept for the last
 * CACHE buildings. Props are placed by position and heading only: a placement's slight
 * non-uniform scale would stretch them.
 */

const CELL = 0.25;
const BODY = 0.18;      // furniture footprints grow by this (a person's radius)
const WALL = 0.2;       // keep this far from the walls
const CACHE = 6;

interface Grid { x0: number; z0: number; w: number; h: number; free: Uint8Array }

const grids = new Map<string, Grid>();

function gridOf(model: string, it: Interior, k: number): Grid {
  const key = `${model}|${k}`;
  let g = grids.get(key);
  if (g) return g;
  const r = it.rooms[k].r;
  const x0 = r[0], z0 = r[1];
  const w = Math.max(1, Math.round((r[2] - r[0]) / CELL)), h = Math.max(1, Math.round((r[3] - r[1]) / CELL));
  const free = new Uint8Array(w * h);
  const block = (bx0: number, bz0: number, bx1: number, bz1: number) => {
    const i0 = Math.max(0, Math.floor((bx0 - x0) / CELL)), i1 = Math.min(w - 1, Math.floor((bx1 - x0) / CELL));
    const j0 = Math.max(0, Math.floor((bz0 - z0) / CELL)), j1 = Math.min(h - 1, Math.floor((bz1 - z0) / CELL));
    for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) free[j * w + i] = 0;
  };
  for (let j = 0; j < h; j++) {
    for (let i = 0; i < w; i++) {
      const cx = x0 + (i + 0.5) * CELL, cz = z0 + (j + 0.5) * CELL;
      free[j * w + i] = cx > r[0] + WALL && cx < r[2] - WALL && cz > r[1] + WALL && cz < r[3] - WALL ? 1 : 0;
    }
  }
  for (const f of it.furniture) {
    if (f.room !== k) continue;
    const c = Math.abs(Math.cos(f.yaw)), s = Math.abs(Math.sin(f.yaw));
    const ex = (c * f.w + s * f.d) * 0.5 + BODY, ez = (s * f.w + c * f.d) * 0.5 + BODY;
    block(f.p[0] - ex, f.p[2] - ez, f.p[0] + ex, f.p[2] + ez);
  }
  for (const hole of it.rooms[k].holes) block(hole[0] - BODY, hole[1] - BODY, hole[2] + BODY, hole[3] + BODY);
  g = { x0, z0, w, h, free };
  grids.set(key, g);
  return g;
}

const _v = new THREE.Vector3();

/** World point -> model space (x, z). */
function local(it: Interior, x: number, y: number, z: number): [number, number] {
  _v.set(x, y, z).applyMatrix4(it.inv);
  return [_v.x, _v.z];
}

/** Model space (x, room floor, z) -> world, appended to out as x, y, z. */
function pushWorld(it: Interior, room: Room, x: number, z: number, out: number[]): void {
  _v.set(x, room.y, z).applyMatrix4(it.matrix);
  out.push(_v.x, _v.y, _v.z);
}

function cellOf(g: Grid, x: number, z: number): number {
  const i = Math.min(g.w - 1, Math.max(0, Math.floor((x - g.x0) / CELL)));
  const j = Math.min(g.h - 1, Math.max(0, Math.floor((z - g.z0) / CELL)));
  return j * g.w + i;
}

function nearestFree(g: Grid, c: number): number {
  if (g.free[c]) return c;
  const ci = c % g.w, cj = (c / g.w) | 0;
  for (let r = 1; r < Math.max(g.w, g.h); r++) {
    let best = -1, bestD = Infinity;
    for (let j = cj - r; j <= cj + r; j++) {
      if (j < 0 || j >= g.h) continue;
      for (let i = ci - r; i <= ci + r; i++) {
        if (i < 0 || i >= g.w || (Math.abs(i - ci) !== r && Math.abs(j - cj) !== r)) continue;
        const k = j * g.w + i;
        const d = (i - ci) ** 2 + (j - cj) ** 2;
        if (g.free[k] && d < bestD) { bestD = d; best = k; }
      }
    }
    if (best >= 0) return best;
  }
  return c;
}

function lineFree(g: Grid, ax: number, az: number, bx: number, bz: number): boolean {
  const n = Math.ceil(Math.hypot(bx - ax, bz - az) / (CELL * 0.5));
  for (let s = 1; s < n; s++) {
    const t = s / n;
    if (!g.free[cellOf(g, ax + (bx - ax) * t, az + (bz - az) * t)]) return false;
  }
  return true;
}

// A* scratch, grown as needed.
let gScore = new Float32Array(0);
let came = new Int32Array(0);
let stamp = new Uint32Array(0);
let closed = new Uint32Array(0);
let round = 0;

/** Model-space path within one room, from (ax, az) to (bx, bz), excluding the start. */
function roomPath(g: Grid, ax: number, az: number, bx: number, bz: number): number[] {
  if (lineFree(g, ax, az, bx, bz)) return [bx, bz];
  const n = g.w * g.h;
  if (gScore.length < n) {
    gScore = new Float32Array(n); came = new Int32Array(n); stamp = new Uint32Array(n); closed = new Uint32Array(n);
  }
  round++;
  const s = nearestFree(g, cellOf(g, ax, az)), t = nearestFree(g, cellOf(g, bx, bz));
  const ti = t % g.w, tj = (t / g.w) | 0;
  const open: number[] = [s];
  const f = new Map<number, number>();
  stamp[s] = round; gScore[s] = 0; came[s] = -1;
  f.set(s, 0);
  let found = s === t;
  while (open.length && !found) {
    // Small grids (a few hundred cells): a linear scan for the best open node is fine.
    let bi = 0;
    for (let k = 1; k < open.length; k++) if (f.get(open[k])! < f.get(open[bi])!) bi = k;
    const c = open[bi];
    open[bi] = open[open.length - 1];
    open.pop();
    if (closed[c] === round) continue;
    closed[c] = round;
    if (c === t) { found = true; break; }
    const ci = c % g.w, cj = (c / g.w) | 0;
    for (let dj = -1; dj <= 1; dj++) {
      for (let di = -1; di <= 1; di++) {
        if (!di && !dj) continue;
        const i = ci + di, j = cj + dj;
        if (i < 0 || j < 0 || i >= g.w || j >= g.h) continue;
        const k = j * g.w + i;
        if (!g.free[k] || closed[k] === round) continue;
        if (di && dj && (!g.free[cj * g.w + i] || !g.free[j * g.w + ci])) continue; // no corner cutting
        const cost = gScore[c] + (di && dj ? 1.4142 : 1);
        if (stamp[k] === round && cost >= gScore[k]) continue;
        stamp[k] = round; gScore[k] = cost; came[k] = c;
        f.set(k, cost + Math.hypot(i - ti, j - tj));
        open.push(k);
      }
    }
  }
  if (!found) return [bx, bz];
  const cells: number[] = [];
  for (let c = t; c >= 0; c = came[c]) cells.push(c);
  cells.reverse();
  const pts: number[] = [ax, az];
  for (const c of cells) pts.push(g.x0 + ((c % g.w) + 0.5) * CELL, g.z0 + (((c / g.w) | 0) + 0.5) * CELL);
  pts.push(bx, bz);
  // String pulling: from each kept point, jump to the farthest point still in sight.
  const out: number[] = [];
  let k = 0;
  const last = pts.length / 2 - 1;
  while (k < last) {
    let j = last;
    while (j > k + 1 && !lineFree(g, pts[k * 2], pts[k * 2 + 1], pts[j * 2], pts[j * 2 + 1])) j--;
    out.push(pts[j * 2], pts[j * 2 + 1]);
    k = j;
  }
  return out;
}

/** Which room (storey) a world height is on. */
export function roomAt(it: Interior, y: number): number {
  let best = 0;
  _v.set(0, 0, 0);
  for (let k = 0; k < it.rooms.length; k++) {
    _v.set(0, it.rooms[k].y, 0).applyMatrix4(it.matrix);
    if (y > _v.y - 0.6) best = k;
  }
  return best;
}

/**
 * World path (x, y, z triples, excluding the start) inside a building, from a point in room
 * `fromRoom` to a point in room `toRoom` (by ladder if the rooms differ).
 */
export function routeInside(b: Building, from: THREE.Vector3, fromRoom: number, tx: number, ty: number, tz: number,
  toRoom: number): number[] {
  const it = b.interior!;
  const out: number[] = [];
  let [ax, az] = local(it, from.x, from.y, from.z);
  let room = fromRoom;
  for (let guard = 0; room !== toRoom && guard < 4; guard++) {
    const up = toRoom > room;
    const lad = it.ladders.find((l) => (up ? l.from === room : l.to === room));
    if (!lad) break;
    const R = it.rooms[room];
    const g = gridOf(b.name, it, room);
    // Walk to the ladder's foot (up) or the step-off point (down), then climb.
    const [ex, ez] = up ? local(it, lad.foot.x, lad.foot.y, lad.foot.z) : local(it, lad.off.x, lad.off.y, lad.off.z);
    const p = roomPath(g, ax, az, ex, ez);
    for (let k = 0; k < p.length; k += 2) pushWorld(it, R, p[k], p[k + 1], out);
    const seq = up ? [lad.top, lad.off] : [lad.top, lad.foot];
    for (const q of seq) out.push(q.x, q.y, q.z);
    room = up ? lad.to : lad.from;
    const end = seq[seq.length - 1];
    [ax, az] = local(it, end.x, end.y, end.z);
  }
  const [bx, bz] = local(it, tx, ty, tz);
  const p = roomPath(gridOf(b.name, it, room), ax, az, bx, bz);
  const R = it.rooms[room];
  for (let k = 0; k < p.length - 2; k += 2) pushWorld(it, R, p[k], p[k + 1], out);
  out.push(tx, ty, tz); // the target keeps its own height (a bed's mattress, a seat)
  return out;
}

/** A free floor point (world) in a room, for someone with no slot: deterministic from r in [0,1). */
export function freePoint(b: Building, room: number, r: number, out: THREE.Vector3): THREE.Vector3 {
  const it = b.interior!;
  const g = gridOf(b.name, it, room);
  let c = Math.floor(r * g.w * g.h);
  for (let k = 0; k < g.w * g.h && !g.free[c]; k++) c = (c + 37) % (g.w * g.h);
  return out.set(g.x0 + ((c % g.w) + 0.5) * CELL, it.rooms[room].y, g.z0 + (((c / g.w) | 0) + 0.5) * CELL).applyMatrix4(it.matrix);
}

/** Centre of a room's floor in world space. */
export function roomCentre(it: Interior, room: number, out: THREE.Vector3): THREE.Vector3 {
  const r = it.rooms[room].r;
  return out.set((r[0] + r[2]) * 0.5, it.rooms[room].y, (r[1] + r[3]) * 0.5).applyMatrix4(it.matrix);
}

// ------------------------------------------------------------------------------- drawing

interface PropPart { geometry: THREE.BufferGeometry; material: THREE.Material; local: THREE.Matrix4 }

const WHITE = new THREE.Color(1, 1, 1);
const FLOOR_LIFT = 0.015;
const FLOOR_OUT = 0.13;   // rooms stop short of the wall face; the floor runs on under it

export class InteriorProps {
  private props = new Map<string, PropPart[]>();
  private floorMat: THREE.Material;
  private cache = new Map<number, PlacedPart[]>();

  constructor(template: THREE.Object3D | undefined) {
    let plank: THREE.Material | null = null;
    if (template) {
      template.updateMatrixWorld(true);
      template.traverse((o) => {
        const mesh = o as THREE.Mesh;
        if (!mesh.isMesh) return;
        let node: THREE.Object3D | null = mesh;
        while (node && !node.name.startsWith('prop_')) node = node.parent;
        if (!node) return;
        const name = node.name.slice(5);
        const list = this.props.get(name) ?? [];
        const local = new THREE.Matrix4().copy(node.matrixWorld).invert().multiply(mesh.matrixWorld);
        list.push({ geometry: mesh.geometry, material: mesh.material as THREE.Material, local });
        this.props.set(name, list);
        if ((mesh.material as THREE.Material).name === 'TimberPlank') plank = mesh.material as THREE.Material;
      });
    }
    this.floorMat = plank ?? new THREE.MeshStandardMaterial({ name: 'TimberPlank', color: 0x7a5a3c, roughness: 0.9 });
  }

  /** One part of every prop (to compile the cutaway shader for their materials up front). */
  samples(): PlacedPart[] {
    const out: PlacedPart[] = [];
    const seen = new Set<THREE.Material>([this.floorMat]);
    out.push({ geometry: new THREE.PlaneGeometry(1, 1), material: this.floorMat, matrix: new THREE.Matrix4(), tint: WHITE, cast: false, receive: true });
    for (const list of this.props.values()) {
      for (const p of list) {
        if (seen.has(p.material)) continue;
        seen.add(p.material);
        out.push({ geometry: p.geometry, material: p.material, matrix: new THREE.Matrix4(), tint: WHITE, cast: true, receive: true });
      }
    }
    return out;
  }

  /** Furniture, floors and ladders of a building (world matrices). Empty without an interior. */
  parts(b: Building): readonly PlacedPart[] {
    const hit = this.cache.get(b.index);
    if (hit) {
      this.cache.delete(b.index);
      this.cache.set(b.index, hit);
      return hit;
    }
    const it = b.interior;
    if (!it) return [];
    const out: PlacedPart[] = [];
    const m = it.matrix;
    const sy = new THREE.Vector3().setFromMatrixColumn(m, 1).length();
    const pos = new THREE.Vector3(), dirv = new THREE.Vector3(), q = new THREE.Quaternion(), one = new THREE.Vector3(1, 1, 1);
    const place = (name: string, p: THREE.Vector3, yaw: number, scaleY = 1) => {
      const world = new THREE.Matrix4().compose(p, q.setFromAxisAngle(THREE.Object3D.DEFAULT_UP, yaw), one.set(1, scaleY, 1));
      for (const part of this.props.get(name) ?? []) {
        out.push({ geometry: part.geometry, material: part.material, matrix: new THREE.Matrix4().multiplyMatrices(world, part.local),
          tint: WHITE, cast: true, receive: true });
      }
    };
    for (const f of it.furniture) {
      pos.fromArray(f.p).applyMatrix4(m);
      // Model-space heading -> world heading (rotation and mirror-free scale of the placement).
      dirv.set(Math.sin(f.yaw), 0, Math.cos(f.yaw)).transformDirection(m);
      const yaw = Math.atan2(dirv.x, dirv.z);
      if (f.prop === 'ladder') {
        const h = (f.h ?? 3) * sy;
        const n = Math.max(1, Math.ceil(h - 0.2));
        for (let k = 0; k < n; k++) place('ladder', pos.clone().setY(pos.y + (k * h) / n), yaw, h / n);
      } else place(f.prop, pos, yaw);
    }
    for (let k = 0; k < it.rooms.length; k++) out.push(this.floor(it, k));
    this.cache.set(b.index, out);
    if (this.cache.size > CACHE) {
      const [oldest, parts] = this.cache.entries().next().value!;
      this.cache.delete(oldest);
      for (const p of parts) if (p.material === this.floorMat) p.geometry.dispose();
    }
    return out;
  }

  /** Plank floor of a room, running under the walls, with the stairwells left open. */
  private floor(it: Interior, k: number): PlacedPart {
    const room = it.rooms[k];
    const r = [room.r[0] - FLOOR_OUT, room.r[1] - FLOOR_OUT, room.r[2] + FLOOR_OUT, room.r[3] + FLOOR_OUT];
    let rects: number[][] = [r];
    for (const h of room.holes) {
      const next: number[][] = [];
      for (const a of rects) {
        if (h[0] >= a[2] || h[2] <= a[0] || h[1] >= a[3] || h[3] <= a[1]) { next.push(a); continue; }
        const x0 = Math.max(a[0], h[0]), x1 = Math.min(a[2], h[2]);
        if (h[0] > a[0]) next.push([a[0], a[1], h[0], a[3]]);
        if (h[2] < a[2]) next.push([h[2], a[1], a[2], a[3]]);
        if (h[1] > a[1]) next.push([x0, a[1], x1, h[1]]);
        if (h[3] < a[3]) next.push([x0, h[3], x1, a[3]]);
      }
      rects = next;
    }
    const posA: number[] = [], nrm: number[] = [], uv: number[] = [];
    const v = new THREE.Vector3();
    for (const a of rects) {
      // Two triangles, wound counter-clockwise seen from above (+y normal).
      const corners = [[a[0], a[1]], [a[0], a[3]], [a[2], a[3]], [a[0], a[1]], [a[2], a[3]], [a[2], a[1]]];
      for (const [x, z] of corners) {
        v.set(x, room.y + FLOOR_LIFT, z).applyMatrix4(it.matrix);
        posA.push(v.x, v.y, v.z);
        nrm.push(0, 1, 0);
        uv.push(v.x, v.z); // metres: the texture repeats every tile_m
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(posA, 3));
    g.setAttribute('normal', new THREE.Float32BufferAttribute(nrm, 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    g.computeBoundingSphere();
    return { geometry: g, material: this.floorMat, matrix: new THREE.Matrix4(), tint: WHITE, cast: false, receive: true };
  }
}
