import * as THREE from 'three';
import type { River, RiverPoint, VegetationElement } from '../types';
import { riverFrames } from './river-course';

/**
 * The world past the town's ground plane (700 x 550 m): a ring of meadow under it and, a few
 * metres out, the canopy of an endless forest as one lumpy heightfield, darkening with distance
 * like a vignette, with a clearing where the Bystrzyca runs on off the map (extendRiver: the
 * water ribbon, the banks in this ring's splat mask and the clearing all use the same course).
 *
 * The camera's centre is clamped to the ground plane (three-renderer.ts clampTarget), so at the
 * widest zoom (90 m) the view reaches ~115-135 m past the edge: the ring is SKIRT wide.
 * Cost: the canopy is cut in CHUNK-metre tiles, so only the few in view are drawn
 * (~1.5k triangles per 1000 m2); it casts and receives no shadows.
 */

/** The town's ground plane, half extents (m). */
export const GROUND_HALF: readonly [number, number] = [350, 275];
/** Width of the ring past the ground plane (m). */
export const SKIRT = 170;
/** Size of the ring's splat-mask canvas (px). */
export const EDGE_MASK_PX = 2048;
const GRID = 1.5;     // canopy vertex spacing (m)
const CHUNK = 60;     // canopy tile (m)
const CELL = 6.5;     // one crown per cell (m)
/** The forest's first row: real trees (placed by the renderer like the plan's vegetation). */
const TREES = ['tree_oak', 'tree_oak_b', 'tree_oak_c', 'tree_alder', 'tree_hornbeam', 'tree_lime', 'tree_birch', 'tree_oak', 'tree_hornbeam', 'tree_alder_b'];

interface Crown { x: number; z: number; kind: number; d: number; r: number; h: number; sp: number }

/** The river's course run on past both ends of the plan's (gentle bends, same width). */
export function extendRiver(river: River, len = SKIRT + 40): River {
  const p = river.points;
  if (p.length < 6) return river;
  const run = (from: RiverPoint, back: RiverPoint, phase: number): RiverPoint[] => {
    const out: RiverPoint[] = [];
    const h0 = Math.atan2(from.z - back.z, from.x - back.x);
    let x = from.x, z = from.z;
    for (let s = 3; s <= len; s += 3) {
      // heading swings +-0.42 rad on a ~240 m wavelength: meanders ~15 m to either side
      const h = h0 + 0.42 * Math.sin(s / 38 + phase) * Math.min(1, s / 30) - 0.42 * Math.sin(phase) * Math.max(0, 1 - s / 30);
      x += Math.cos(h) * 3; z += Math.sin(h) * 3;
      out.push({ x, z, width: from.width });
    }
    return out;
  };
  const up = run(p[0], p[4], 0).reverse();
  const down = run(p[p.length - 1], p[p.length - 5], 0);
  return { ...river, points: [...up, ...p, ...down] };
}

function hash2(i: number, j: number, k = 0): number {
  let h = Math.imul(i, 374761393) ^ Math.imul(j, 668265263) ^ Math.imul(k, 2147483647);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

/** Smooth value noise, 0..1. */
function vnoise(x: number, z: number, seed: number): number {
  const i = Math.floor(x), j = Math.floor(z), fx = x - i, fz = z - j;
  const u = fx * fx * (3 - 2 * fx), v = fz * fz * (3 - 2 * fz);
  const a = hash2(i, j, seed), b = hash2(i + 1, j, seed), c = hash2(i, j + 1, seed), d = hash2(i + 1, j + 1, seed);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}

/** Crown colours (sRGB) of the woods' species, multiplied by the leaf texture. */
const CROWNS = ['#5f8236', '#4e7430', '#6c8f3a', '#86a246', '#3f6034', '#73933e', '#58792f', '#4a6a35'];

export class WorldEdge {
  /** The meadow ring under the ground plane; its map is the splat mask (painted by the renderer). */
  readonly ground: THREE.Mesh;
  readonly mask: HTMLCanvasElement;
  readonly maskTex: THREE.CanvasTexture;
  readonly canopy = new THREE.Group();
  /** The forest's front row along the canopy (to place as vegetation). */
  readonly trees: VegetationElement[] = [];
  private crowns = new Map<number, Crown>();
  private river: { x: number; z: number; half: number }[] = [];

  constructor(scene: THREE.Scene, river: River | null, leaves: THREE.Texture | undefined) {
    const [hx, hz] = GROUND_HALF;
    const ex = hx + SKIRT, ez = hz + SKIRT;
    this.mask = document.createElement('canvas');
    this.mask.width = this.mask.height = EDGE_MASK_PX;
    const ctx = this.mask.getContext('2d')!;
    ctx.fillStyle = 'rgb(0,128,0)';
    ctx.fillRect(0, 0, EDGE_MASK_PX, EDGE_MASK_PX);
    // The same large-scale tone blobs as the ground plane, at its density per square metre.
    const blobs = document.createElement('canvas');
    blobs.width = blobs.height = EDGE_MASK_PX;
    const b = blobs.getContext('2d')!;
    const pxPerM = EDGE_MASK_PX / (2 * ex);
    for (let i = 0; i < 4000 * (4 * ex * ez) / (4 * hx * hz); i++) {
      b.fillStyle = Math.random() < 0.5 ? 'rgb(0,104,0)' : 'rgb(0,152,0)';
      b.beginPath();
      b.arc(Math.random() * EDGE_MASK_PX, Math.random() * EDGE_MASK_PX, (Math.random() * 14 + 6) * pxPerM / 3.3, 0, Math.PI * 2);
      b.fill();
    }
    ctx.filter = 'blur(4px)';
    ctx.drawImage(blobs, 0, 0);
    ctx.filter = 'none';
    this.maskTex = new THREE.CanvasTexture(this.mask);
    this.maskTex.wrapS = this.maskTex.wrapT = THREE.ClampToEdgeWrapping;

    const geo = new THREE.PlaneGeometry(2 * ex, 2 * ez, 8, 8);
    this.ground = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ map: this.maskTex, roughness: 0.92, metalness: 0.04 }));
    this.ground.name = 'world_edge_ground';
    this.ground.rotation.x = -Math.PI / 2;
    this.ground.position.y = -0.04; // under the ground plane
    this.ground.receiveShadow = true;
    scene.add(this.ground);

    if (river) {
      for (const f of riverFrames(river)) {
        // only the stretches out in the ring matter to the canopy
        if (Math.abs(f.x) > hx - 30 || Math.abs(f.z) > hz - 30) this.river.push({ x: f.x, z: f.z, half: f.w * 0.5 });
      }
    }
    const mat = new THREE.MeshStandardMaterial({ name: 'EdgeCanopy', vertexColors: true, map: leaves ?? null, roughness: 0.95 });
    for (let x0 = -ex; x0 < ex; x0 += CHUNK) {
      for (let z0 = -ez; z0 < ez; z0 += CHUNK) {
        const g = this.chunk(x0, z0, Math.min(ex, x0 + CHUNK), Math.min(ez, z0 + CHUNK));
        if (!g) continue;
        const mesh = new THREE.Mesh(g, mat);
        mesh.name = 'world_edge_canopy';
        this.canopy.add(mesh);
      }
    }
    scene.add(this.canopy);
  }

  /** Metres from (x, z) to the extended river's water's edge (Infinity with no river near). */
  private riverGap(x: number, z: number): number {
    let best = Infinity;
    const r = this.river;
    for (let i = 0; i + 1 < r.length; i++) {
      const a = r[i], c = r[i + 1];
      const ex = c.x - a.x, ez = c.z - a.z, l2 = ex * ex + ez * ez;
      if (l2 > 50) continue; // a gap between the two ends of the list
      const t = Math.max(0, Math.min(1, ((x - a.x) * ex + (z - a.z) * ez) / (l2 || 1)));
      const d = Math.hypot(a.x + ex * t - x, a.z + ez * t - z) - a.half;
      if (d < best) best = d;
    }
    return best;
  }

  /**
   * The crown in cell (i, j): kind 0 = none (meadow, river), 1 = the forest's first row (a
   * real tree, see `trees`), 2 = canopy. Cached: every vertex looks at its 3 x 3 cells.
   */
  private crown(i: number, j: number): Crown {
    const key = i * 4096 + j;
    let c = this.crowns.get(key);
    if (c) return c;
    const [hx, hz] = GROUND_HALF;
    const cx = (i + 0.2 + 0.6 * hash2(i, j, 5)) * CELL, cz = (j + 0.2 + 0.6 * hash2(i, j, 6)) * CELL;
    const d = Math.max(Math.abs(cx) - hx, Math.abs(cz) - hz); // metres past the edge
    const start = 4 + 16 * vnoise(cx / 30, cz / 30, 1) + 5 * vnoise(cx / 11, cz / 11, 2);
    let kind = d < start ? 0 : d < start + CELL ? 1 : 2;
    if (kind && this.river.length) {
      const gap = this.riverGap(cx, cz), clear = 4 + 7 * vnoise(cx / 20, cz / 20, 3);
      if (gap < clear) kind = 0;
      else if (gap < clear + CELL) kind = 1;
    }
    c = {
      x: cx, z: cz, kind, d,
      r: 3.2 + 2.2 * hash2(i, j, 7),
      h: 11 + 4.5 * hash2(i, j, 8),
      sp: Math.floor(hash2(i, j, 9) * CROWNS.length),
    };
    this.crowns.set(key, c);
    if (kind === 1) {
      const t = TREES[Math.floor(hash2(i, j, 10) * TREES.length)];
      this.trees.push({ id: `edge_${i}_${j}`, type: t, x: cx, z: cz,
        rotation: hash2(i, j, 11) * 360, scale: 0.95 + 0.3 * hash2(i, j, 12) });
    }
    return c;
  }

  /** Canopy height (m, <= 0 = none), crown colour index, how central in its crown (0..1), metres past the edge, 0..1 up the crown. */
  private sample(x: number, z: number, out: number[]): void {
    const [hx, hz] = GROUND_HALF;
    let top = 0, sp = 0, core = 0, h = 1;
    const ci = Math.floor(x / CELL), cj = Math.floor(z / CELL);
    for (let i = ci - 1; i <= ci + 1; i++) {
      for (let j = cj - 1; j <= cj + 1; j++) {
        const c = this.crown(i, j);
        if (c.kind !== 2) continue;
        const q = ((x - c.x) ** 2 + (z - c.z) ** 2) / (c.r * c.r);
        // a rounded dome (ellipsoid cap 4 m deep), falling steeply past its rim
        const y = q < 1 ? c.h - 4 * (1 - Math.sqrt(1 - q)) : c.h - 4 - 14 * (q - 1);
        if (y > top) { top = y; sp = c.sp; core = Math.max(0, 1 - q); h = c.h; }
      }
    }
    out[0] = top; out[1] = sp; out[2] = core;
    out[3] = Math.max(Math.abs(x) - hx, Math.abs(z) - hz);
    out[4] = top / h;
  }

  private chunk(x0: number, z0: number, x1: number, z1: number): THREE.BufferGeometry | null {
    const nx = Math.round((x1 - x0) / GRID), nz = Math.round((z1 - z0) / GRID);
    const pos: number[] = [], col: number[] = [], uv: number[] = [], idx: number[] = [];
    const H: number[] = [];
    const s = [0, 0, 0, 0, 0], c = new THREE.Color(), dark = new THREE.Color('#2e3a22');
    const crowns = CROWNS.map((h) => new THREE.Color(h));
    for (let j = 0; j <= nz; j++) {
      for (let i = 0; i <= nx; i++) {
        // jitter the grid a little so the canopy's edge and crowns do not read as a lattice
        const jx = (hash2(i + x0, j + z0, 11) - 0.5) * GRID * 0.5, jz = (hash2(i + x0, j + z0, 12) - 0.5) * GRID * 0.5;
        const onRim = i === 0 || j === 0 || i === nx || j === nz;
        const x = x0 + i * GRID + (onRim ? 0 : jx), z = z0 + j * GRID + (onRim ? 0 : jz);
        this.sample(x, z, s);
        const y = s[0];
        H.push(y);
        pos.push(x, y > 0 ? y : -0.1, z);
        uv.push(x, z); // metres (the leaf texture's repeat sets its tile)
        // lit crown tops, dark hollows between crowns and dark trunks/undergrowth at the forest's edge
        c.copy(crowns[s[1]]).multiplyScalar(0.62 + 0.45 * Math.sqrt(s[2]));
        c.lerp(dark, 1 - Math.min(1, Math.max(0, s[4]) * 1.5));
        c.multiplyScalar(1 - 0.5 * Math.min(1, Math.max(0, (s[3] - 20) / 130)));
        col.push(c.r, c.g, c.b);
      }
    }
    const W = nx + 1;
    for (let j = 0; j < nz; j++) {
      for (let i = 0; i < nx; i++) {
        const a = j * W + i, b = a + 1, d = a + W, e = d + 1;
        if (H[a] <= 0 && H[b] <= 0 && H[d] <= 0 && H[e] <= 0) continue;
        idx.push(a, d, b, b, d, e);
      }
    }
    if (!idx.length) return null;
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    g.setIndex(idx);
    g.computeVertexNormals();
    g.computeBoundingSphere();
    return g;
  }
}
