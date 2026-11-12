import * as THREE from 'three';

/**
 * Walkable ground for citizens: a 0.5 m occupancy grid over the whole map, built from the
 * placed models' own triangles, plus weighted A* over it.
 *
 * Build (once, after the scene is populated):
 *  1. Per template, every triangle is clipped to the body slab (BODY_LO..BODY_HI above the
 *     model origin) and kept as a 2D polygon in model space (footprintOf, cached).
 *  2. Per placement those polygons are transformed into the world and rasterised: edges with
 *     a supercover walk (walls are vertical, so their projection is a line), areas by
 *     cell-centre fill. Anything a person would bump into between knee and head blocks.
 *  3. Flood fill from the map border and from caller-supplied seeds (door approach points,
 *     work spots, squares); free cells not reached are enclosed (building interiors,
 *     closed courtyards) and are blocked too, so nobody is ever routed into a sealed room.
 *  4. Chamfer distance to the nearest blocked cell (in cells, capped): A* pays extra next
 *     to walls, so people keep to the middle of lanes, and path smoothing keeps clearance.
 *
 * Interiors are not walked on the grid: a route ends at a door's approach point outside and
 * the simulation scripts the door / stair legs (building-anchors.ts).
 */

export const CELL = 0.5;
/** Below this (m above the model origin) things are stepped onto, not walked around:
 *  plinths, sills, the Kraków drawbridge deck and its 0.6 m abutment. */
const BODY_LO = 0.7;
const BODY_HI = 1.9;
const DIST_CAP = 6;
/** Extra cost factor per step by distance (cells) to the nearest wall. */
const WALL_COST = [0, 1.2, 0.35, 0.1, 0, 0, 0];
const HEURISTIC_W = 2.2;
/** One search gives up after this many expansions (unreachable goal in a huge component). */
const MAX_EXPANSIONS = 80_000;
/** Walkable pockets smaller than this (cells; 4 per m²) cut off from the main area are sealed. */
const POCKET_MIN = 4000;
/** Waypoint graph: one node per square of this many cells (4 m). */
const GRAPH_BLOCK = 8;

type Footprint = { pts: Float32Array; starts: Uint32Array };

export interface NavPlacement { template: THREE.Object3D; matrix: THREE.Matrix4 }

export interface RouteResult { pts: Float32Array; length: number; expanded: number }

export class NavGrid {
  readonly minX: number;
  readonly minZ: number;
  readonly w: number;
  readonly h: number;
  /** 1 = blocked. */
  readonly blocked: Uint8Array;
  /** Cells to the nearest blocked cell, capped at DIST_CAP. */
  readonly dist: Uint8Array;
  private footprints = new Map<THREE.Object3D, Footprint>();

  // A* scratch, reused by every search (generation stamps instead of clearing).
  private g: Float32Array;
  private parent: Int32Array;
  private seen: Uint32Array;
  private closed: Uint32Array;
  private gen = 0;
  private heapIdx = new Int32Array(1 << 14);
  private heapF = new Float32Array(1 << 14);
  private heapN = 0;

  readonly buildMs: number;
  enclosedCells = 0;
  /** Walkable components left (1 = every street connects). */
  components = 0;

  constructor(minX: number, minZ: number, maxX: number, maxZ: number, placements: NavPlacement[], seeds: { x: number; z: number }[]) {
    const t0 = performance.now();
    this.minX = minX;
    this.minZ = minZ;
    this.w = Math.ceil((maxX - minX) / CELL);
    this.h = Math.ceil((maxZ - minZ) / CELL);
    const n = this.w * this.h;
    this.blocked = new Uint8Array(n);
    this.dist = new Uint8Array(n);
    this.g = new Float32Array(n);
    this.parent = new Int32Array(n);
    this.seen = new Uint32Array(n);
    this.closed = new Uint32Array(n);
    for (const p of placements) this.stamp(p);
    this.sealEnclosed(seeds);
    this.distanceField();
    this.buildGraph();
    this.buildMs = performance.now() - t0;
  }

  // ---------------------------------------------------------------- waypoint graph
  //
  // Grid A* over 1.5 M cells is slow whenever the way round is long (gates, closed blocks):
  // ~8 ms and up to 120 ms per route. Routes are searched on a coarse graph instead: one
  // node per GRAPH_BLOCK square (its cell with the most clearance), edges to nearby nodes in
  // straight sight. Grid A* stays as the fallback when the graph has no answer.

  private gNodeCell = new Int32Array(0);
  private gBlock = new Int32Array(0);
  private gBw = 0;
  private gBh = 0;
  private gAdjStart = new Int32Array(0);
  private gAdj = new Int32Array(0);
  private gAdjW = new Float32Array(0);
  private gG = new Float32Array(0);
  private gParent = new Int32Array(0);
  private gSeen = new Uint32Array(0);
  private gClosed = new Uint32Array(0);
  private gGoalD = new Float32Array(0);
  private gGoalGen = new Uint32Array(0);
  graphNodes = 0;
  graphEdges = 0;

  private buildGraph(): void {
    const B = GRAPH_BLOCK;
    const bw = Math.ceil(this.w / B), bh = Math.ceil(this.h / B);
    const block = new Int32Array(bw * bh).fill(-1);
    const cells: number[] = [];
    for (let bz = 0; bz < bh; bz++) for (let bx = 0; bx < bw; bx++) {
      let best = -1, bestD = 0, bestOff = Infinity;
      for (let z = bz * B; z < Math.min(this.h, bz * B + B); z++) for (let x = bx * B; x < Math.min(this.w, bx * B + B); x++) {
        const i = z * this.w + x;
        const d = this.dist[i];
        if (d === 0) continue;
        const off = Math.abs(x - bx * B - B / 2) + Math.abs(z - bz * B - B / 2);
        if (d > bestD || (d === bestD && off < bestOff)) { best = i; bestD = d; bestOff = off; }
      }
      if (best >= 0) { block[bz * bw + bx] = cells.length; cells.push(best); }
    }
    const n = cells.length;
    const adj: number[][] = Array.from({ length: n }, () => []);
    const wts: number[][] = Array.from({ length: n }, () => []);
    const OFFS = [[1, 0], [0, 1], [1, 1], [1, -1], [2, 1], [1, 2], [2, -1], [1, -2], [2, 0], [0, 2]];
    let edges = 0;
    for (let bz = 0; bz < bh; bz++) for (let bx = 0; bx < bw; bx++) {
      const a = block[bz * bw + bx];
      if (a < 0) continue;
      const ax = this.cx(cells[a]), az = this.cz(cells[a]);
      for (const [ox, oz] of OFFS) {
        const nx = bx + ox, nz = bz + oz;
        if (nx < 0 || nz < 0 || nx >= bw || nz >= bh) continue;
        const b = block[nz * bw + nx];
        if (b < 0) continue;
        const bx2 = this.cx(cells[b]), bz2 = this.cz(cells[b]);
        if (!this.lineFree(ax, az, bx2, bz2, 1)) continue;
        const len = Math.hypot(bx2 - ax, bz2 - az);
        const tight = Math.min(this.dist[cells[a]], this.dist[cells[b]]) < 2 ? 1.4 : 1;
        adj[a].push(b); wts[a].push(len * tight);
        adj[b].push(a); wts[b].push(len * tight);
        edges++;
      }
    }
    this.gNodeCell = new Int32Array(cells);
    this.gBlock = block; this.gBw = bw; this.gBh = bh;
    this.gAdjStart = new Int32Array(n + 1);
    for (let k = 0; k < n; k++) this.gAdjStart[k + 1] = this.gAdjStart[k] + adj[k].length;
    this.gAdj = new Int32Array(this.gAdjStart[n]);
    this.gAdjW = new Float32Array(this.gAdjStart[n]);
    for (let k = 0; k < n; k++) { this.gAdj.set(adj[k], this.gAdjStart[k]); this.gAdjW.set(wts[k], this.gAdjStart[k]); }
    this.gG = new Float32Array(n); this.gParent = new Int32Array(n);
    this.gSeen = new Uint32Array(n); this.gClosed = new Uint32Array(n);
    this.gGoalD = new Float32Array(n); this.gGoalGen = new Uint32Array(n);
    this.graphNodes = n;
    this.graphEdges = edges;
  }

  /** Graph nodes within two blocks of a cell that it sees in a straight line, with distances. */
  private visibleNodes(cell: number, out: number[]): void {
    out.length = 0;
    const x = this.cx(cell), z = this.cz(cell);
    const bx = Math.floor((cell % this.w) / GRAPH_BLOCK), bz = Math.floor(cell / this.w / GRAPH_BLOCK);
    for (let r = 1; r <= 2 && out.length === 0; r++) {
      for (let oz = -r; oz <= r; oz++) for (let ox = -r; ox <= r; ox++) {
        const nx = bx + ox, nz = bz + oz;
        if (nx < 0 || nz < 0 || nx >= this.gBw || nz >= this.gBh) continue;
        const k = this.gBlock[nz * this.gBw + nx];
        if (k < 0) continue;
        const c = this.gNodeCell[k];
        const px = this.cx(c), pz = this.cz(c);
        if (this.lineFree(x, z, px, pz, 1) || (k >= 0 && c === cell)) out.push(k, Math.hypot(px - x, pz - z));
      }
    }
  }

  private routeGraph(a: number, b: number): RouteResult | null {
    const starts: number[] = [], goals: number[] = [];
    this.visibleNodes(a, starts);
    this.visibleNodes(b, goals);
    if (!starts.length || !goals.length) return null;
    const gen = ++this.gen;
    const { gG, gParent, gSeen, gClosed, gGoalD, gGoalGen, gNodeCell } = this;
    for (let k = 0; k < goals.length; k += 2) { gGoalGen[goals[k]] = gen; gGoalD[goals[k]] = goals[k + 1]; }
    const tx = this.cx(b), tz = this.cz(b);
    const hOf = (k: number) => Math.hypot(this.cx(gNodeCell[k]) - tx, this.cz(gNodeCell[k]) - tz) * 1.2;
    this.heapN = 0;
    for (let k = 0; k < starts.length; k += 2) {
      const s = starts[k];
      gG[s] = starts[k + 1]; gParent[s] = -1; gSeen[s] = gen;
      this.push(s, gG[s] + hOf(s));
    }
    let best = -1, bestCost = Infinity, expanded = 0;
    while (this.heapN > 0) {
      const f = this.heapF[0];
      if (f >= bestCost) break;
      const cur = this.pop();
      if (gClosed[cur] === gen) continue;
      gClosed[cur] = gen;
      expanded++;
      if (gGoalGen[cur] === gen && gG[cur] + gGoalD[cur] < bestCost) { bestCost = gG[cur] + gGoalD[cur]; best = cur; }
      for (let e = this.gAdjStart[cur]; e < this.gAdjStart[cur + 1]; e++) {
        const nb = this.gAdj[e];
        if (gClosed[nb] === gen) continue;
        const ng = gG[cur] + this.gAdjW[e];
        if (gSeen[nb] === gen && ng >= gG[nb]) continue;
        gSeen[nb] = gen; gG[nb] = ng; gParent[nb] = cur;
        this.push(nb, ng + hOf(nb));
      }
    }
    if (best < 0) return null;
    const nodes: number[] = [];
    for (let k = best; k !== -1; k = gParent[k]) nodes.push(k);
    nodes.reverse();
    const raw = [this.cx(a), this.cz(a)];
    for (const k of nodes) raw.push(this.cx(gNodeCell[k]), this.cz(gNodeCell[k]));
    raw.push(tx, tz);
    return this.pull(raw, expanded);
  }

  /** String-pull a polyline: keep only points needed to stay in straight sight. */
  private pull(raw: number[], expanded: number): RouteResult {
    const out = [raw[0], raw[1]];
    const n = raw.length / 2;
    let a = 0;
    while (a < n - 1) {
      let best = a + 1;
      for (let k = Math.min(n - 1, a + 12); k > a + 1; k--) {
        if (this.lineFree(raw[a * 2], raw[a * 2 + 1], raw[k * 2], raw[k * 2 + 1], 1)) { best = k; break; }
      }
      out.push(raw[best * 2], raw[best * 2 + 1]);
      a = best;
    }
    let length = 0;
    for (let k = 2; k < out.length; k += 2) length += Math.hypot(out[k] - out[k - 2], out[k + 1] - out[k - 1]);
    return { pts: new Float32Array(out), length, expanded };
  }

  // ---------------------------------------------------------------- queries

  cellOf(x: number, z: number): number {
    const cx = Math.floor((x - this.minX) / CELL), cz = Math.floor((z - this.minZ) / CELL);
    if (cx < 0 || cz < 0 || cx >= this.w || cz >= this.h) return -1;
    return cz * this.w + cx;
  }
  cx(i: number): number { return this.minX + ((i % this.w) + 0.5) * CELL; }
  cz(i: number): number { return this.minZ + (Math.floor(i / this.w) + 0.5) * CELL; }

  isFree(x: number, z: number): boolean {
    const i = this.cellOf(x, z);
    return i >= 0 && this.blocked[i] === 0;
  }

  /** Clearance in metres at a point (0 inside walls, capped at DIST_CAP cells). */
  clearance(x: number, z: number): number {
    const i = this.cellOf(x, z);
    return i < 0 ? 0 : this.dist[i] * CELL;
  }

  /** Nearest free cell to (x, z) within `radius` metres, preferring cells with clearance >= 2. */
  nearestFree(x: number, z: number, radius = 6): number {
    const c0 = this.cellOf(x, z);
    if (c0 >= 0 && this.dist[c0] >= 2) return c0;
    const r = Math.ceil(radius / CELL);
    const ox = Math.floor((x - this.minX) / CELL), oz = Math.floor((z - this.minZ) / CELL);
    let best = -1, bestScore = Infinity;
    for (let dz = -r; dz <= r; dz++) {
      const cz = oz + dz;
      if (cz < 0 || cz >= this.h) continue;
      for (let dx = -r; dx <= r; dx++) {
        const cx = ox + dx;
        if (cx < 0 || cx >= this.w) continue;
        const i = cz * this.w + cx;
        if (this.blocked[i]) continue;
        const d2 = dx * dx + dz * dz;
        if (d2 > r * r) continue;
        const score = d2 + (this.dist[i] >= 2 ? 0 : 6);
        if (score < bestScore) { bestScore = score; best = i; }
      }
    }
    return best;
  }

  /** Straight walk from a to b stays on free cells (with clearance >= minDist cells). */
  lineFree(ax: number, az: number, bx: number, bz: number, minDist = 1): boolean {
    const len = Math.hypot(bx - ax, bz - az);
    const steps = Math.max(1, Math.ceil(len / (CELL * 0.5)));
    for (let s = 0; s <= steps; s++) {
      const t = s / steps;
      const i = this.cellOf(ax + (bx - ax) * t, az + (bz - az) * t);
      if (i < 0 || this.blocked[i] || this.dist[i] < minDist) return false;
    }
    return true;
  }

  /** Route from cell a to cell b as a few waypoints (graph first, grid A* fallback); null if unreachable. */
  route(a: number, b: number): RouteResult | null {
    if (a < 0 || b < 0 || this.blocked[a] || this.blocked[b]) return null;
    const r = this.routeGraph(a, b);
    if (r) return r;
    this.gridFallbacks++;
    return this.routeGrid(a, b);
  }

  gridFallbacks = 0;

  /**
   * Weighted A* (8-connected, no corner cutting) from cell a to cell b, then string-pulled
   * to a few waypoints. Returns null when b cannot be reached.
   */
  routeGrid(a: number, b: number): RouteResult | null {
    if (a < 0 || b < 0 || this.blocked[a] || this.blocked[b]) return null;
    const gen = ++this.gen;
    const { w, g, parent, seen, closed, dist } = this;
    const bx = b % w, bz = (b / w) | 0;
    const hOf = (i: number) => {
      const dx = Math.abs((i % w) - bx), dz = Math.abs(((i / w) | 0) - bz);
      return (Math.max(dx, dz) + 0.41421356 * Math.min(dx, dz)) * HEURISTIC_W;
    };
    this.heapN = 0;
    g[a] = 0; parent[a] = -1; seen[a] = gen;
    this.push(a, hOf(a));
    let expanded = 0;
    let found = false;
    while (this.heapN > 0) {
      const cur = this.pop();
      if (closed[cur] === gen) continue;
      closed[cur] = gen;
      if (cur === b) { found = true; break; }
      if (++expanded > MAX_EXPANSIONS) break;
      const cx = cur % w, cz = (cur / w) | 0;
      const gc = g[cur];
      for (let k = 0; k < 8; k++) {
        const dx = DX[k], dz = DZ[k];
        const nx = cx + dx, nz = cz + dz;
        if (nx < 0 || nz < 0 || nx >= w || nz >= this.h) continue;
        const ni = nz * w + nx;
        if (this.blocked[ni] || closed[ni] === gen) continue;
        if (dx !== 0 && dz !== 0 && (this.blocked[cz * w + nx] || this.blocked[nz * w + cx])) continue;
        const step = (dx !== 0 && dz !== 0 ? 1.41421356 : 1) * (1 + WALL_COST[dist[ni]]);
        const ng = gc + step;
        if (seen[ni] === gen && ng >= g[ni]) continue;
        seen[ni] = gen; g[ni] = ng; parent[ni] = cur;
        this.push(ni, ng + hOf(ni));
      }
    }
    if (!found) return null;
    const cells: number[] = [];
    for (let i = b; i !== -1; i = parent[i]) cells.push(i);
    cells.reverse();
    return this.smooth(cells, expanded);
  }

  // ---------------------------------------------------------------- build

  private footprintOf(template: THREE.Object3D): Footprint {
    const hit = this.footprints.get(template);
    if (hit) return hit;
    const pts: number[] = [];
    const starts: number[] = [0];
    template.updateMatrixWorld(true);
    const inv = new THREE.Matrix4().copy(template.matrixWorld).invert();
    const m = new THREE.Matrix4();
    const v = [new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3()];
    const poly: number[] = [];
    const tmp: number[] = [];
    template.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh) return;
      m.multiplyMatrices(inv, mesh.matrixWorld);
      const pos = mesh.geometry.attributes.position;
      const idx = mesh.geometry.index;
      const nTri = (idx ? idx.count : pos.count) / 3;
      for (let t = 0; t < nTri; t++) {
        for (let k = 0; k < 3; k++) {
          const vi = idx ? idx.getX(t * 3 + k) : t * 3 + k;
          v[k].fromBufferAttribute(pos, vi).applyMatrix4(m);
        }
        const ylo = Math.min(v[0].y, v[1].y, v[2].y), yhi = Math.max(v[0].y, v[1].y, v[2].y);
        if (yhi < BODY_LO || ylo > BODY_HI) continue;
        // Clip the triangle to BODY_LO <= y <= BODY_HI (x, y, z triples).
        poly.length = 0;
        for (const p of v) poly.push(p.x, p.y, p.z);
        clipY(poly, tmp, BODY_LO, 1);
        clipY(tmp, poly, BODY_HI, -1);
        if (poly.length < 6) continue;
        for (let k = 0; k < poly.length; k += 3) pts.push(poly[k], poly[k + 2]);
        starts.push(pts.length / 2);
      }
    });
    const fp = { pts: new Float32Array(pts), starts: new Uint32Array(starts) };
    this.footprints.set(template, fp);
    return fp;
  }

  private stamp(p: NavPlacement): void {
    const fp = this.footprintOf(p.template);
    const e = p.matrix.elements;
    // World x/z of a model-space (x, z) point (the slab is thin: ignore the y column).
    const a = e[0], b = e[8], c = e[12], d = e[2], f = e[10], g = e[14];
    const xs: number[] = [], zs: number[] = [];
    for (let k = 0; k + 1 < fp.starts.length; k++) {
      xs.length = 0; zs.length = 0;
      for (let j = fp.starts[k]; j < fp.starts[k + 1]; j++) {
        const lx = fp.pts[j * 2], lz = fp.pts[j * 2 + 1];
        xs.push(a * lx + b * lz + c);
        zs.push(d * lx + f * lz + g);
      }
      this.rasterPoly(xs, zs);
    }
  }

  private rasterPoly(xs: number[], zs: number[]): void {
    const n = xs.length;
    for (let k = 0; k < n; k++) this.rasterLine(xs[k], zs[k], xs[(k + 1) % n], zs[(k + 1) % n]);
    // Area fill by cell centres (only polygons wider than a cell can cover a centre the edges missed).
    let x0 = Infinity, x1 = -Infinity, z0 = Infinity, z1 = -Infinity;
    for (let k = 0; k < n; k++) {
      x0 = Math.min(x0, xs[k]); x1 = Math.max(x1, xs[k]);
      z0 = Math.min(z0, zs[k]); z1 = Math.max(z1, zs[k]);
    }
    if (x1 - x0 < CELL && z1 - z0 < CELL) return;
    let area = 0;
    for (let k = 0; k < n; k++) area += xs[k] * zs[(k + 1) % n] - xs[(k + 1) % n] * zs[k];
    if (Math.abs(area) < CELL * CELL * 0.5) return;
    const cx0 = Math.max(0, Math.floor((x0 - this.minX) / CELL)), cx1 = Math.min(this.w - 1, Math.floor((x1 - this.minX) / CELL));
    const cz0 = Math.max(0, Math.floor((z0 - this.minZ) / CELL)), cz1 = Math.min(this.h - 1, Math.floor((z1 - this.minZ) / CELL));
    for (let cz = cz0; cz <= cz1; cz++) {
      const pz = this.minZ + (cz + 0.5) * CELL;
      for (let cx = cx0; cx <= cx1; cx++) {
        const px = this.minX + (cx + 0.5) * CELL;
        let inside = false;
        for (let k = 0, j = n - 1; k < n; j = k++) {
          if ((zs[k] > pz) !== (zs[j] > pz) && px < ((xs[j] - xs[k]) * (pz - zs[k])) / (zs[j] - zs[k]) + xs[k]) inside = !inside;
        }
        if (inside) this.blocked[cz * this.w + cx] = 1;
      }
    }
  }

  private rasterLine(ax: number, az: number, bx: number, bz: number): void {
    const len = Math.hypot(bx - ax, bz - az);
    const steps = Math.max(1, Math.ceil(len / (CELL * 0.35)));
    for (let s = 0; s <= steps; s++) {
      const t = s / steps;
      const i = this.cellOf(ax + (bx - ax) * t, az + (bz - az) * t);
      if (i >= 0) this.blocked[i] = 1;
    }
  }

  private sealEnclosed(seeds: { x: number; z: number }[]): void {
    const { w, h, blocked } = this;
    const reached = new Uint8Array(w * h);
    const stack = new Int32Array(w * h);
    let sp = 0;
    const seed = (i: number) => {
      if (i >= 0 && !blocked[i] && !reached[i]) { reached[i] = 1; stack[sp++] = i; }
    };
    for (let x = 0; x < w; x++) { seed(x); seed((h - 1) * w + x); }
    for (let z = 0; z < h; z++) { seed(z * w); seed(z * w + w - 1); }
    for (const s of seeds) seed(this.nearestFree(s.x, s.z, 2));
    while (sp > 0) {
      const i = stack[--sp];
      const x = i % w;
      if (x > 0) seed(i - 1);
      if (x < w - 1) seed(i + 1);
      if (i >= w) seed(i - w);
      if (i < (h - 1) * w) seed(i + w);
    }
    let sealed = 0;
    for (let i = 0; i < w * h; i++) if (!blocked[i] && !reached[i]) { blocked[i] = 1; sealed++; }
    // A seed can sit in a pocket closed off from the streets (a house whose door faces a
    // walled gap): keep only components big enough to matter, and remember the largest.
    const label = new Int32Array(w * h).fill(-1);
    const sizes: number[] = [];
    for (let s = 0; s < w * h; s++) {
      if (blocked[s] || label[s] >= 0) continue;
      const id = sizes.length;
      let n = 0;
      sp = 0;
      stack[sp++] = s; label[s] = id;
      while (sp > 0) {
        const i = stack[--sp];
        n++;
        const x = i % w;
        if (x > 0 && !blocked[i - 1] && label[i - 1] < 0) { label[i - 1] = id; stack[sp++] = i - 1; }
        if (x < w - 1 && !blocked[i + 1] && label[i + 1] < 0) { label[i + 1] = id; stack[sp++] = i + 1; }
        if (i >= w && !blocked[i - w] && label[i - w] < 0) { label[i - w] = id; stack[sp++] = i - w; }
        if (i < (h - 1) * w && !blocked[i + w] && label[i + w] < 0) { label[i + w] = id; stack[sp++] = i + w; }
      }
      sizes.push(n);
    }
    const main = sizes.indexOf(Math.max(...sizes));
    for (let i = 0; i < w * h; i++) {
      if (label[i] >= 0 && label[i] !== main && sizes[label[i]] < POCKET_MIN) { blocked[i] = 1; sealed++; }
    }
    this.components = sizes.filter((n) => n >= POCKET_MIN).length;
    this.enclosedCells = sealed;
  }

  private distanceField(): void {
    const { w, h, blocked, dist } = this;
    // Two-pass chamfer (1 / 1.4 rounded up to whole cells: 1 and 2 would be too coarse, use x2 scale).
    const d = new Uint16Array(w * h);
    const BIG = 60000;
    for (let i = 0; i < w * h; i++) d[i] = blocked[i] ? 0 : BIG;
    for (let z = 0; z < h; z++) for (let x = 0; x < w; x++) {
      const i = z * w + x;
      if (d[i] === 0) continue;
      let v = d[i];
      if (x > 0) v = Math.min(v, d[i - 1] + 2);
      if (z > 0) {
        v = Math.min(v, d[i - w] + 2);
        if (x > 0) v = Math.min(v, d[i - w - 1] + 3);
        if (x < w - 1) v = Math.min(v, d[i - w + 1] + 3);
      }
      d[i] = v;
    }
    for (let z = h - 1; z >= 0; z--) for (let x = w - 1; x >= 0; x--) {
      const i = z * w + x;
      if (d[i] === 0) continue;
      let v = d[i];
      if (x < w - 1) v = Math.min(v, d[i + 1] + 2);
      if (z < h - 1) {
        v = Math.min(v, d[i + w] + 2);
        if (x < w - 1) v = Math.min(v, d[i + w + 1] + 3);
        if (x > 0) v = Math.min(v, d[i + w - 1] + 3);
      }
      d[i] = v;
    }
    for (let i = 0; i < w * h; i++) dist[i] = Math.min(DIST_CAP, Math.ceil(d[i] / 2));
  }

  // ---------------------------------------------------------------- A* helpers

  private smooth(cells: number[], expanded: number): RouteResult {
    const out: number[] = [this.cx(cells[0]), this.cz(cells[0])];
    let a = 0;
    while (a < cells.length - 1) {
      // Furthest cell (within 60 cells) reachable in a straight line with clearance.
      let best = a + 1;
      const ax = this.cx(cells[a]), az = this.cz(cells[a]);
      const limit = Math.min(cells.length - 1, a + 60);
      for (let k = limit; k > a + 1; k--) {
        const minD = Math.min(2, this.dist[cells[a]], this.dist[cells[k]]);
        if (this.lineFree(ax, az, this.cx(cells[k]), this.cz(cells[k]), minD)) { best = k; break; }
      }
      out.push(this.cx(cells[best]), this.cz(cells[best]));
      a = best;
    }
    let length = 0;
    for (let k = 2; k < out.length; k += 2) length += Math.hypot(out[k] - out[k - 2], out[k + 1] - out[k - 1]);
    return { pts: new Float32Array(out), length, expanded };
  }

  private push(i: number, f: number): void {
    if (this.heapN === this.heapIdx.length) {
      const ni = new Int32Array(this.heapN * 2); ni.set(this.heapIdx); this.heapIdx = ni;
      const nf = new Float32Array(this.heapN * 2); nf.set(this.heapF); this.heapF = nf;
    }
    const hi = this.heapIdx, hf = this.heapF;
    let k = this.heapN++;
    while (k > 0) {
      const p = (k - 1) >> 1;
      if (hf[p] <= f) break;
      hi[k] = hi[p]; hf[k] = hf[p]; k = p;
    }
    hi[k] = i; hf[k] = f;
  }

  private pop(): number {
    const hi = this.heapIdx, hf = this.heapF;
    const top = hi[0];
    const n = --this.heapN;
    if (n > 0) {
      const li = hi[n], lf = hf[n];
      let k = 0;
      for (;;) {
        let c = 2 * k + 1;
        if (c >= n) break;
        if (c + 1 < n && hf[c + 1] < hf[c]) c++;
        if (hf[c] >= lf) break;
        hi[k] = hi[c]; hf[k] = hf[c]; k = c;
      }
      hi[k] = li; hf[k] = lf;
    }
    return top;
  }
}

const DX = [1, -1, 0, 0, 1, 1, -1, -1];
const DZ = [0, 0, 1, -1, 1, -1, 1, -1];

/** Sutherland–Hodgman against the plane y = lim (keep y >= lim when sign 1, y <= lim when -1). */
function clipY(src: number[], dst: number[], lim: number, sign: number): void {
  dst.length = 0;
  const n = src.length / 3;
  for (let k = 0; k < n; k++) {
    const j = (k + 1) % n;
    const ay = src[k * 3 + 1], by = src[j * 3 + 1];
    const ain = (ay - lim) * sign >= 0, bin = (by - lim) * sign >= 0;
    if (ain) dst.push(src[k * 3], ay, src[k * 3 + 2]);
    if (ain !== bin) {
      const t = (lim - ay) / (by - ay);
      dst.push(src[k * 3] + (src[j * 3] - src[k * 3]) * t, lim, src[k * 3 + 2] + (src[j * 3 + 2] - src[k * 3 + 2]) * t);
    }
  }
}
