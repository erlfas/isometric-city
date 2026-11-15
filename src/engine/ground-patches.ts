import * as THREE from 'three';
import type { PlacedModel } from './static-batches';

/**
 * Ground patches: walkable surfaces above the flat ground plane that a model carries itself,
 * such as the quarry's benches and ramps (M2 of the quarry & ironworks plan).
 *
 * build_assets.py `anchor_ground` raycasts the model's terrain straight down on a grid and
 * writes it into the GLB anchors (glTF model space, Y up):
 *   ground: { x0, z0, cell, w, h, y: heights in cm, row-major (row = z), -32768 = no surface,
 *             mats: material names of the terrain mesh itself }
 * Users:
 *   - nav-grid.ts: the terrain's own triangles do not block. Every other triangle of the model
 *     (cranes, blocks, sheds) is measured from the surface under it, not from the model origin.
 *     Steps of more than STEP_MAX between neighbouring cells block (cliffs; ramps stay open).
 *   - simulation.ts groundAt(): feet height on a patch.
 * Patches assume an unscaled placement rotated about Y only (industry parcels are placed so).
 */

export const NO_SURFACE = -32768;
/** Highest step (m) between neighbouring 0.5 m cells that people walk up (ramps ~42 deg max). */
export const STEP_MAX = 0.45;

export interface RawGround { x0: number; z0: number; cell: number; w: number; h: number; y: number[]; mats?: string[] }

/** Heights in metres, NaN where the model has no surface. */
export interface Ground { x0: number; z0: number; cell: number; w: number; h: number; y: Float32Array; mats: Set<string> }

const cache = new WeakMap<THREE.Object3D, Ground | null>();

/** The template's ground grid (model space), or null. */
export function groundOf(template: THREE.Object3D): Ground | null {
  const hit = cache.get(template);
  if (hit !== undefined) return hit;
  let g: Ground | null = null;
  let a: unknown = template.userData?.anchors;
  if (typeof a === 'string') {
    try { a = JSON.parse(a); } catch { a = null; }
  }
  const raw = (a as { ground?: RawGround } | null)?.ground;
  if (raw && raw.w > 1 && raw.h > 1 && raw.y.length === raw.w * raw.h) {
    const y = new Float32Array(raw.y.length);
    for (let i = 0; i < y.length; i++) y[i] = raw.y[i] === NO_SURFACE ? NaN : raw.y[i] / 100;
    g = { x0: raw.x0, z0: raw.z0, cell: raw.cell, w: raw.w, h: raw.h, y, mats: new Set(raw.mats ?? []) };
  }
  cache.set(template, g);
  return g;
}

/** Surface height at model-space (x, z): bilinear over the samples that exist, NaN off the grid
 *  or where none of the four corners has a surface. */
export function sampleGround(g: Ground, x: number, z: number): number {
  const fx = (x - g.x0) / g.cell, fz = (z - g.z0) / g.cell;
  if (fx < 0 || fz < 0 || fx > g.w - 1 || fz > g.h - 1) return NaN;
  const i = Math.min(g.w - 2, Math.floor(fx)), j = Math.min(g.h - 2, Math.floor(fz));
  const tx = fx - i, tz = fz - j;
  const k = j * g.w + i;
  const c = [g.y[k], g.y[k + 1], g.y[k + g.w], g.y[k + g.w + 1]];
  const wt = [(1 - tx) * (1 - tz), tx * (1 - tz), (1 - tx) * tz, tx * tz];
  let s = 0, ws = 0;
  for (let q = 0; q < 4; q++) {
    if (Number.isNaN(c[q])) continue;
    s += c[q] * wt[q];
    ws += wt[q];
  }
  return ws > 1e-4 ? s / ws : NaN;
}

interface Patch {
  g: Ground;
  /** World -> model (x, z), placement height. */
  inv: THREE.Matrix4;
  oy: number;
  /** World bounds. */
  x0: number; z0: number; x1: number; z1: number;
}

const _v = new THREE.Vector3();

export class GroundPatches {
  readonly patches: Patch[] = [];

  constructor(placed: readonly PlacedModel[]) {
    for (const pm of placed) {
      const g = groundOf(pm.template);
      if (!g) continue;
      let x0 = Infinity, z0 = Infinity, x1 = -Infinity, z1 = -Infinity;
      for (const [lx, lz] of [[g.x0, g.z0], [g.x0 + (g.w - 1) * g.cell, g.z0], [g.x0, g.z0 + (g.h - 1) * g.cell],
        [g.x0 + (g.w - 1) * g.cell, g.z0 + (g.h - 1) * g.cell]]) {
        _v.set(lx, 0, lz).applyMatrix4(pm.matrix);
        x0 = Math.min(x0, _v.x); x1 = Math.max(x1, _v.x);
        z0 = Math.min(z0, _v.z); z1 = Math.max(z1, _v.z);
      }
      _v.setFromMatrixPosition(pm.matrix);
      this.patches.push({ g, inv: pm.matrix.clone().invert(), oy: _v.y, x0, z0, x1, z1 });
    }
  }

  /** World height of a patch surface at (x, z), or null where no patch has one. */
  heightAt(x: number, z: number): number | null {
    for (const p of this.patches) {
      if (x < p.x0 || x > p.x1 || z < p.z0 || z > p.z1) continue;
      _v.set(x, 0, z).applyMatrix4(p.inv);
      const h = sampleGround(p.g, _v.x, _v.z);
      if (!Number.isNaN(h)) return h + p.oy;
    }
    return null;
  }
}
