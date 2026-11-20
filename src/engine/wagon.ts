import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import type { CityPlan, Citizen } from '../types';
import type { BuildingIndex, Stall } from './building-anchors';
import type { SimulationEngine, Vehicle } from './simulation';
import type { Horse, Horses } from './horses';
import { nightFactor } from './door-leaves';
import { BlobShadows, commitRig, makeRigMesh, writePose, type RigDef, type RigDraw, type RigOptions } from './rigid-rig';

/**
 * The stable's travelling wagon (stable plan M4): twice a day (DEPART, 8:30 and 15:30) a pair
 * of draught horses draws it from the carriage house along the wagon road (plan path
 * road_stable) to the Kraków Gate, where it stands GATE_WAIT minutes, turns and comes back,
 * and is backed into its place. The postilion rides the near (left) horse.
 *
 * Travellers are foreign merchants. Those who left town on the last run are "away" (carried,
 * hidden) and get down at the gate; one or two merchants in town are called to the wagon's
 * step (simulation summon, activity 'travel'), board it there (carried, hidden) and are away
 * until a later run brings them back. At load two merchants start away.
 *
 * Route (built once at load, buildTrack): out of the stall straight, a curve onto the road,
 * the road to the gate; a U-turn there (an arc and a curve back onto the road: the place,
 * side and radius searched along the road's last 40 m for room on the walkable grid); the
 * road back; a curve past the carriage house and a reverse curve into the stall. The pole tip
 * (between the horses' collars) follows the route forward and the rear axle backing: the
 * other axle trails the leading point at the axle distance (tractrix), as a wagon does.
 * Speed: walk in the suburb, the yard and at the gate, trot on the open road, slower in tight
 * curves; shown sped up like the citizens' walking (TRAVEL), one trip ~1 h of the clock.
 * Position is a function of the clock (minus the time it waited for people in its way), so a
 * clock jump puts it where it would be.
 *
 * Citizens: the wagon is a moving obstacle (simulation vehicles: two capsules, wagon and
 * team, avoided by time to collision); people standing or chatting in its way are asked to
 * step aside and it waits for them (vehicleSweep), giving up waiting after BLOCK_GIVEUP s.
 *
 * Model: vehicle_wagon (build_animals.py build_wagon; WAGON here mirrors its dimensions),
 * rigid parts on the shared rig (rigid-rig.ts): body, the fore carriage (front axle, pole)
 * turning on the king pin, wheels spinning by the distance their axle rolled.
 *
 * Debug: __lublin.wagon (.stats()), hash `wagon=run` (set off now), `wagon=off`,
 * `follow=wagon[,zoom]` (camera on the postilion, or the wagon while parked).
 */

/** Dimensions of the model (build_animals.py WAGON): axles from the body origin, wheel radii, pole tip. */
const WAGON = { axleB: -1.35, axleF: 1.35, rB: 0.62, rF: 0.48, poleTip: 4.2 };
const L1 = WAGON.poleTip - WAGON.axleF;   // pole tip -> front axle (king pin)
const L2 = WAGON.axleF - WAGON.axleB;     // front axle -> rear axle
/** Horses: centre behind the pole tip, either side of the pole. */
const TEAM_BACK = 0.72, TEAM_SIDE = 0.75;
/** The citizens' travel speed-up (simulation TRAVEL_SCALE). */
const TRAVEL = 2.2;
/** Shown speeds, m/s: draught horses' walk and trot (gait speed x 1.07 size x TRAVEL), backing. */
const V_WALK = 1.75 * 1.07 * TRAVEL, V_TROT = 3.3 * 1.07 * TRAVEL, V_BACK = 0.9;
const ACC = 1.0, BRAKE = 1.4, A_LAT = 2.2;
/** Departures (day hours) and the stand at the gate (real seconds = sim minutes). */
const DEPART = [8.5, 15.5];
const GATE_WAIT = 40, SWITCH_WAIT = 2.5;
const TEAMS = [['Mocarz', 'Kruk'], ['Rudy', 'Szpak']];
const SAMPLE = 0.25;
const BLOCK_GIVEUP = 8;

const RIG: RigDef = {
  body: [-1, -1, -1, ''], fore: [-1, 0, -1, ''],
  wheel_FL: [1, -1, -1, 'fore'], wheel_FR: [1, -1, -1, 'fore'],
  wheel_BL: [2, -1, -1, ''], wheel_BR: [2, -1, -1, ''],
};
const RIG_OPTS: RigOptions = { key: 'wagon-v1', nPart: 6, nChan: 4, depth: 2 };

type P2 = [number, number];
const hyp = Math.hypot;
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const wrapPi = (a: number) => Math.atan2(Math.sin(a), Math.cos(a));

function bezier(a: P2, b: P2, c: P2, d: P2, n = 80): P2[] {
  const out: P2[] = [];
  for (let k = 0; k <= n; k++) {
    const t = k / n, u = 1 - t;
    const w0 = u * u * u, w1 = 3 * u * u * t, w2 = 3 * u * t * t, w3 = t * t * t;
    out.push([a[0] * w0 + b[0] * w1 + c[0] * w2 + d[0] * w3, a[1] * w0 + b[1] * w1 + c[1] * w2 + d[1] * w3]);
  }
  return out;
}

/** Points every `step` metres along a polyline (from its first point; the last one kept). */
function resample(pts: P2[], step: number): P2[] {
  const out: P2[] = [pts[0]];
  let need = step, [x, z] = pts[0];
  for (let k = 1; k < pts.length; k++) {
    const [tx, tz] = pts[k];
    let l = hyp(tx - x, tz - z);
    while (l >= need) {
      x += ((tx - x) * need) / l; z += ((tz - z) * need) / l;
      out.push([x, z]);
      l -= need; need = step;
    }
    need -= l; x = tx; z = tz;
  }
  const last = pts[pts.length - 1], o = out[out.length - 1];
  if (hyp(last[0] - o[0], last[1] - o[1]) > step * 0.3) out.push([last[0], last[1]]);
  return out;
}

/** The point at distance L from (lx, lz) toward where (cx, cz) was: a trailing axle. */
function trail(cx: number, cz: number, lx: number, lz: number, L: number): P2 {
  const dx = cx - lx, dz = cz - lz, d = hyp(dx, dz) || 1;
  return [lx + (dx / d) * L, lz + (dz / d) * L];
}

/** Wagon kinematics while building the track: pole tip P, front axle F, rear axle B. */
class Kin {
  P: P2 = [0, 0]; F: P2 = [0, 0]; B: P2 = [0, 0];
  dF = 0; dB = 0;
  /** Lined up at P heading (hx, hz). */
  align(P: P2, hx: number, hz: number): void {
    this.P = [P[0], P[1]];
    this.F = [P[0] - hx * L1, P[1] - hz * L1];
    this.B = [this.F[0] - hx * L2, this.F[1] - hz * L2];
  }
  /** The leading point (P forward, B backing) moves to (x, z); the rest trails. */
  lead(x: number, z: number, rev: boolean): void {
    const { F, B } = this;
    if (!rev) {
      this.P = [x, z];
      const f = trail(F[0], F[1], x, z, L1), b = trail(B[0], B[1], f[0], f[1], L2);
      this.dF += hyp(f[0] - F[0], f[1] - F[1]); this.dB += hyp(b[0] - B[0], b[1] - B[1]);
      this.F = f; this.B = b;
    } else {
      this.B = [x, z];
      const f = trail(F[0], F[1], x, z, L2), p = trail(this.P[0], this.P[1], f[0], f[1], L1);
      this.dF -= hyp(f[0] - F[0], f[1] - F[1]); this.dB -= hyp(x - B[0], z - B[1]);
      this.F = f; this.P = p;
    }
  }
}

/** One day run, sampled every SAMPLE m of the leading point: positions, wheels, speed, times. */
interface Track {
  n: number;
  px: Float32Array; pz: Float32Array; fx: Float32Array; fz: Float32Array; bx: Float32Array; bz: Float32Array;
  dF: Float32Array; dB: Float32Array; rev: Uint8Array;
  /** Speed (m/s, >= 0) and arrival / departure time (real s since the start) per sample. */
  v: Float32Array; tA: Float32Array; tD: Float32Array;
  /** Real seconds: at the gate, leaving it, the whole run. */
  tArrive: number; tLeave: number; T: number;
  /** Where travellers step down and wait to board (beside the wagon's back at the gate). */
  step: P2;
  gate: { s: number; side: number; R: number; margin: number };
  margins: { out: number; yard: number };
  /** Metres of the run walked through the suburb; the road's length. */
  townM: number; length: number;
}

class TrackBuilder {
  k = new Kin();
  P: number[] = []; F: number[] = []; B: number[] = []; dF: number[] = []; dB: number[] = []; rev: number[] = [];
  marks: Record<string, number> = {};
  get n(): number { return this.rev.length; }
  push(): void {
    const k = this.k;
    this.P.push(k.P[0], k.P[1]); this.F.push(k.F[0], k.F[1]); this.B.push(k.B[0], k.B[1]);
    this.dF.push(k.dF); this.dB.push(k.dB); this.rev.push(0);
  }
  /** Lead along pts (first point = where the lead is now: skipped). */
  add(pts: P2[], rev: boolean): void {
    const r = resample(pts, SAMPLE);
    for (let i = 1; i < r.length; i++) {
      this.k.lead(r[i][0], r[i][1], rev);
      this.push();
      this.rev[this.rev.length - 1] = rev ? 1 : 0;
    }
  }
}

export class Wagon {
  enabled = true;
  /** Postilion and the travellers now away (citizen indices). */
  postilion = -1;
  private away = new Set<number>();
  private arriving: number[] = [];
  private called: number[] = [];
  private dropped = false;

  private track: Track | null = null;
  private stall: Stall | null = null;
  private sx = 0; private sz = 0; private dx = 0; private dz = 1;
  private draw: RigDraw | null = null;
  private blobs: BlobShadows;
  private ch = new Float32Array(4);
  private team: Horse[] | null = null;
  private run = -1;
  private debugDep: number | null = null;
  private delay = 0;
  private lastTau = NaN;
  private hour = 12;
  private slow = 0;
  private blockedFor = 0;
  private ghost = 0;
  private stat = { runs: 0, longestBlock: 0, blockedS: 0, boarded: 0, alighted: 0, buildMs: 0 };
  private now = { x: 0, z: 0, yaw: 0, v: 0, te: 0 };
  private vehicles: Vehicle[] = [
    { ax: 0, az: 0, bx: 0, bz: 0, r: 1.0, vx: 0, vz: 0 },
    { ax: 0, az: 0, bx: 0, bz: 0, r: 1.15, vx: 0, vz: 0 },
  ];
  private m4 = new THREE.Matrix4();
  private q = new THREE.Quaternion();
  private p = new THREE.Vector3();
  private one = new THREE.Vector3(1, 1, 1);
  private yAxis = new THREE.Vector3(0, 1, 0);
  private rnd: () => number;

  private scene: THREE.Scene;
  private plan: CityPlan;
  private sim: SimulationEngine;
  private horses: Horses;

  constructor(scene: THREE.Scene, plan: CityPlan, buildings: BuildingIndex, sim: SimulationEngine, horses: Horses) {
    this.scene = scene; this.plan = plan; this.sim = sim; this.horses = horses;
    let seed = 1392 * 17;
    this.rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
    this.blobs = new BlobShadows(scene, 2, 'wagon_blobs');
    this.stall = (buildings.byModel.get('carriage_house') ?? []).flatMap((b) => b.stalls).find((s) => s.tag === 'wagon') ?? null;
    const road = (plan.paths ?? []).find((p) => p.id === 'road_stable');
    if (!this.stall || !road || road.points.length < 4) return;
    this.sx = this.stall.x; this.sz = this.stall.z;
    this.dx = Math.sin(this.stall.yaw); this.dz = Math.cos(this.stall.yaw);
    const t0 = performance.now();
    this.track = this.buildTrack(road.points.map((p) => [p.x, p.z] as P2));
    this.stat.buildMs = Math.round(performance.now() - t0);
    const tr = this.track;
    console.info(`[wagon] run ${Math.round(tr.T)} s (gate at ${Math.round(tr.tArrive)} s, leaves ${Math.round(tr.tLeave)} s); `
      + `U-turn ${tr.gate.s.toFixed(0)} m from the road's end, side ${tr.gate.side}, R ${tr.gate.R} m, margin ${tr.gate.margin.toFixed(2)} m; `
      + `margins out ${tr.margins.out.toFixed(2)}, yard ${tr.margins.yard.toFixed(2)} (${this.stat.buildMs} ms)`);
    this.postilion = sim.citizens.findIndex((c) => c.trade === 'Postilion');
    // Two merchants are away at the start; a run brings them.
    for (const i of this.pickTravellers(2, null)) { sim.carry(i); this.away.add(i); }
    void this.load();
  }

  private async load(): Promise<void> {
    try {
      const gltf = await new GLTFLoader().loadAsync('/models/vehicle_wagon.glb');
      this.draw = makeRigMesh(gltf, RIG, RIG_OPTS, 1, 'wagon');
      this.scene.add(this.draw.mesh);
    } catch (e) {
      console.warn('[wagon] vehicle_wagon.glb', e);
    }
  }

  // ---------------------------------------------------------------- route

  private buildTrack(road: P2[]): Track {
    const nav = this.sim.nav;
    // the road by arc length (s = 0 at the gate end)
    const rs = [0];
    for (let k = 1; k < road.length; k++) rs.push(rs[k - 1] + hyp(road[k][0] - road[k - 1][0], road[k][1] - road[k - 1][1]));
    const len = rs[rs.length - 1];
    const at = (s: number): { x: number; z: number; tx: number; tz: number } => {
      s = clamp(s, 0, len);
      let k = 1;
      while (k < road.length - 1 && rs[k] < s) k++;
      const a = road[k - 1], b = road[k], l = rs[k] - rs[k - 1] || 1, f = (s - rs[k - 1]) / l;
      return { x: a[0] + (b[0] - a[0]) * f, z: a[1] + (b[1] - a[1]) * f, tx: (b[0] - a[0]) / l, tz: (b[1] - a[1]) / l };
    };
    const span = (s0: number, s1: number): P2[] => {
      const out: P2[] = [], n = Math.max(1, Math.ceil(Math.abs(s1 - s0) / 0.5));
      for (let k = 0; k <= n; k++) { const p = at(s0 + ((s1 - s0) * k) / n); out.push([p.x, p.z]); }
      return out;
    };
    const S: P2 = [this.sx, this.sz], d: P2 = [this.dx, this.dz], perp: P2 = [d[1], -d[0]];
    const stallP: P2 = [S[0] + d[0] * WAGON.poleTip, S[1] + d[1] * WAGON.poleTip];
    const stallB: P2 = [S[0] + d[0] * WAGON.axleB, S[1] + d[1] * WAGON.axleB];
    const nearStall = (x: number, z: number) => hyp(x - S[0], z - S[1]) < 7.5;
    // Room along a stretch of the built track: the least clearance of the axles and the two
    // horses less what each needs (wheels 0.85 m from the axle's middle, a horse 0.45 m).
    const margin = (tb: TrackBuilder, from: number): number => {
      let m = Infinity;
      for (let i = from; i < tb.n; i += 2) {
        const px = tb.P[i * 2], pz = tb.P[i * 2 + 1], fx = tb.F[i * 2], fz = tb.F[i * 2 + 1], bx = tb.B[i * 2], bz = tb.B[i * 2 + 1];
        const ul = hyp(px - fx, pz - fz) || 1, ux = (px - fx) / ul, uz = (pz - fz) / ul;
        const hx = px - ux * TEAM_BACK, hz = pz - uz * TEAM_BACK;
        const pts: [number, number, number][] = [[fx, fz, 1.0], [bx, bz, 1.0],
          [hx + uz * TEAM_SIDE, hz - ux * TEAM_SIDE, 0.6], [hx - uz * TEAM_SIDE, hz + ux * TEAM_SIDE, 0.6]];
        for (const [x, z, need] of pts) {
          if (nearStall(x, z)) continue;
          m = Math.min(m, nav.clearance(x, z) - need);
        }
      }
      return m;
    };
    const curve = (a: P2, ha: P2, b: P2, hb: P2, f = 0.38): P2[] => {
      const k = Math.max(2, hyp(b[0] - a[0], b[1] - a[1]) * f);
      return bezier(a, [a[0] + ha[0] * k, a[1] + ha[1] * k], [b[0] - hb[0] * k, b[1] - hb[1] * k], b);
    };

    // 1) out of the stall and onto the road (heading for the gate: -tangent)
    const outLeg = (tb: TrackBuilder, J: number) => {
      tb.k.align(stallP, d[0], d[1]);
      tb.push();
      const p1: P2 = [stallP[0] + d[0] * 6, stallP[1] + d[1] * 6];
      tb.add([stallP, p1], false);
      const r = at(len - J);
      tb.add(curve(p1, d, [r.x, r.z], [-r.tx, -r.tz]), false);
    };
    let bestJ = 20, bestOut = -Infinity;
    for (const J of [16, 20, 25, 30]) {
      const tb = new TrackBuilder();
      outLeg(tb, J);
      tb.add(span(len - J, len - J - 25), false);
      const m = margin(tb, 0);
      if (m > bestOut + 0.05) { bestOut = m; bestJ = J; }
    }

    // 2) the U-turn at the gate: stop at s, a half circle of radius R to one side, a curve
    //    back onto the road. The nearest place to the gate with room wins.
    const uTurn = (tb: TrackBuilder, s: number, side: number, R: number) => {
      const r = at(s);
      const nx = -r.tz * side, nz = r.tx * side; // the turning side, across the road
      const c: P2 = [r.x + nx * R, r.z + nz * R];
      const arc: P2[] = [];
      for (let k = 0; k <= 48; k++) {
        const t = (Math.PI * k) / 48;
        // from the road point (c - n R), heading -tangent, round to (c + n R) heading +tangent
        arc.push([c[0] - nx * R * Math.cos(t) - r.tx * R * Math.sin(t), c[1] - nz * R * Math.cos(t) - r.tz * R * Math.sin(t)]);
      }
      tb.add(arc, false);
      const e = arc[arc.length - 1], r2 = at(s + 18);
      tb.add(curve(e, [r.tx, r.tz], [r2.x, r2.z], [r2.tx, r2.tz], 0.42), false);
    };
    let gate = { s: 8, side: 1, R: 7.5, margin: -Infinity };
    for (let s = 3; s <= 45 && gate.margin < 0; s += 2) {
      for (const side of [1, -1]) {
        for (const R of [6.5, 7.5, 8.5]) {
          const tb = new TrackBuilder(), r = at(s);
          tb.k.align([r.x, r.z], -r.tx, -r.tz);
          tb.push();
          uTurn(tb, s, side, R);
          tb.add(span(s + 18, s + 30), false);
          const m = margin(tb, 0);
          if (m > gate.margin) gate = { s, side, R, margin: m };
        }
      }
    }

    // 3) into the yard: past the carriage house and back into the stall
    const yardLeg = (tb: TrackBuilder, fwd: number, lat: number, side: number) => {
      const r = at(len - 14);
      const q: P2 = [S[0] + d[0] * (WAGON.poleTip + fwd) + perp[0] * lat * side, S[1] + d[1] * (WAGON.poleTip + fwd) + perp[1] * lat * side];
      tb.add(curve([r.x, r.z], [r.tx, r.tz], q, d), false);
      tb.marks.switch = tb.n - 1;
      const b0 = tb.k.B, f0 = tb.k.F, bl = hyp(f0[0] - b0[0], f0[1] - b0[1]) || 1;
      const back: P2 = [-(f0[0] - b0[0]) / bl, -(f0[1] - b0[1]) / bl];
      // backing: the rear axle leads, arriving at its place moving -d
      tb.add(curve([b0[0], b0[1]], back, stallB, [-d[0], -d[1]], 0.42), true);
    };
    const end = at(len);
    const yardSide = (end.x - S[0]) * perp[0] + (end.z - S[1]) * perp[1] >= 0 ? 1 : -1;
    let yard = { fwd: 13, lat: 7, margin: -Infinity };
    for (const fwd of [10, 13, 16, 19]) {
      for (const lat of [4, 6, 8, 10]) {
        const tb = new TrackBuilder(), r = at(len - 30);
        tb.k.align([r.x, r.z], r.tx, r.tz);
        tb.add(span(len - 30, len - 14), false);
        const from = tb.n;
        yardLeg(tb, fwd, lat, yardSide);
        const m = margin(tb, from);
        if (m > yard.margin + 0.05) yard = { fwd, lat, margin: m };
      }
    }

    // the whole run
    const tb = new TrackBuilder();
    outLeg(tb, bestJ);
    tb.add(span(len - bestJ, gate.s), false);
    const gateIdx = tb.n - 1;
    uTurn(tb, gate.s, gate.side, gate.R);
    tb.add(span(gate.s + 18, len - 14), false);
    yardLeg(tb, yard.fwd, yard.lat, yardSide);
    const switchIdx = tb.marks.switch;
    const n = tb.n;

    // speed limits: backing; walk in the suburb, the yard and at the gate; else trot; curves
    const gp = at(gate.s);
    const towns = this.plan.parcels.filter((p) => p.site !== 'stable').map((p) => [p.x, p.z, Math.max(p.width, p.depth) / 2 + 7]);
    let townM = 0;
    const vmax = new Float32Array(n);
    let town = false;
    const lead = (i: number): P2 => (tb.rev[i] ? [tb.B[i * 2], tb.B[i * 2 + 1]] : [tb.P[i * 2], tb.P[i * 2 + 1]]);
    for (let i = 0; i < n; i++) {
      const [x, z] = lead(i);
      if (tb.rev[i]) { vmax[i] = V_BACK; continue; }
      if (i % 8 === 0) town = towns.some(([cx, cz, r]) => hyp(x - cx, z - cz) < r);
      if (town) townM += SAMPLE;
      const slow = town || hyp(x - S[0], z - S[1]) < 30 || hyp(x - gp.x, z - gp.z) < 25;
      let v = slow ? V_WALK : V_TROT;
      const a = lead(Math.max(0, i - 6)), b = lead(Math.min(n - 1, i + 6));
      const h0 = Math.atan2(x - a[0], z - a[1]), h1 = Math.atan2(b[0] - x, b[1] - z);
      const span6 = hyp(x - a[0], z - a[1]) + hyp(b[0] - x, b[1] - z);
      const kappa = span6 > 0.5 ? Math.abs(wrapPi(h1 - h0)) / (span6 / 2) : 0;
      if (kappa > 1e-3) v = Math.min(v, Math.max(V_WALK * 0.7, Math.sqrt(A_LAT / kappa)));
      vmax[i] = v;
    }
    for (const i of [0, gateIdx, switchIdx, n - 1]) vmax[i] = 0;
    const ds = new Float32Array(n);
    for (let i = 1; i < n; i++) {
      const a = tb.rev[i] ? [tb.B[(i - 1) * 2], tb.B[(i - 1) * 2 + 1]] : [tb.P[(i - 1) * 2], tb.P[(i - 1) * 2 + 1]];
      const b = lead(i);
      ds[i] = Math.max(1e-3, hyp(b[0] - a[0], b[1] - a[1]));
    }
    const v = new Float32Array(vmax);
    for (let i = n - 2; i >= 0; i--) v[i] = Math.min(v[i], Math.sqrt(v[i + 1] * v[i + 1] + 2 * BRAKE * ds[i + 1]));
    for (let i = 1; i < n; i++) v[i] = Math.min(v[i], Math.sqrt(v[i - 1] * v[i - 1] + 2 * ACC * ds[i]));
    const tA = new Float32Array(n), tD = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      if (i > 0) tA[i] = tD[i - 1] + (2 * ds[i]) / Math.max(0.08, v[i - 1] + v[i]);
      tD[i] = tA[i] + (i === gateIdx ? GATE_WAIT : i === switchIdx ? SWITCH_WAIT : 0);
    }
    // the travellers' step: beside the back of the standing wagon, away from the turn
    const st = at(gate.s + 6.5), sn: P2 = [st.tz * gate.side, -st.tx * gate.side];
    const step: P2 = [st.x + sn[0] * 2.4, st.z + sn[1] * 2.4];
    const cell = nav.nearestFree(step[0], step[1], 6);
    if (cell >= 0) { step[0] = nav.cx(cell); step[1] = nav.cz(cell); }
    const f32 = (a: number[], o: number) => Float32Array.from({ length: n }, (_, i) => a[i * 2 + o]);
    return {
      n, px: f32(tb.P, 0), pz: f32(tb.P, 1), fx: f32(tb.F, 0), fz: f32(tb.F, 1), bx: f32(tb.B, 0), bz: f32(tb.B, 1),
      dF: Float32Array.from(tb.dF), dB: Float32Array.from(tb.dB), rev: Uint8Array.from(tb.rev),
      v, tA, tD, tArrive: tA[gateIdx], tLeave: tD[gateIdx], T: tD[n - 1], step,
      gate, margins: { out: bestOut, yard: yard.margin }, townM: Math.round(townM), length: Math.round(len),
    };
  }

  // ---------------------------------------------------------------- travellers

  /** Foreign merchants about (not away, not called), nearest the gate step first, `count` of the nearest 10. */
  private pickTravellers(count: number, near: P2 | null): number[] {
    const sim = this.sim;
    const list: [number, number][] = [];
    sim.citizens.forEach((c, i) => {
      if (c.guildRank !== 'foreign_merchant' || this.away.has(i) || this.called.includes(i) || sim.isCarried(i)) return;
      if (c.state === 'SLEEPING') return;
      const [x, z] = sim.posOf(i);
      list.push([i, near ? hyp(x - near[0], z - near[1]) : this.rnd()]);
    });
    list.sort((a, b) => a[1] - b[1]);
    const pool = list.slice(0, 10).map((e) => e[0]), out: number[] = [];
    while (out.length < count && pool.length) out.push(pool.splice(Math.floor(this.rnd() * pool.length), 1)[0]);
    return out;
  }

  // ---------------------------------------------------------------- update

  /** Per frame, after the simulation's update: hour = sim clock. */
  update(hour: number): void {
    const tr = this.track;
    if (!tr) return;
    this.hour = hour;
    if (!this.enabled) {
      if (this.run >= 0) this.endRun(hour);
      this.run = -1;
      this.sim.vehicles = [];
      if (this.draw) this.draw.mesh.visible = false;
      this.blobs.hide();
      return;
    }
    // which run is on, and how far into it (real seconds = sim minutes)
    let run = -1, tau = 0;
    const into = (dep: number) => ((((hour - dep) % 24) + 24) % 24) * 60;
    if (this.debugDep !== null) {
      tau = into(this.debugDep);
      if (tau < tr.T + this.delay + 0.5) run = 2; else this.debugDep = null;
    }
    if (run < 0) {
      DEPART.forEach((dep, k) => {
        const t = into(dep);
        if (t < tr.T + (k === this.run ? this.delay : 0)) { run = k; tau = t; }
      });
    }
    if (run !== this.run) {
      if (this.run >= 0) this.endRun(hour);
      this.delay = 0; this.slow = 0; this.blockedFor = 0;
      this.run = run;
      if (run >= 0) this.startRun(run, tau);
    }
    let dtau = Number.isNaN(this.lastTau) ? 0 : tau - this.lastTau;
    if (dtau < 0 || dtau > 5) { dtau = 0; if (run >= 0) this.delay = 0; } // clock jump: re-sync
    this.lastTau = tau;

    if (run < 0) {
      this.pose(0, 0);
      this.sim.vehicles = [];
      this.carryRiders(0);
      return;
    }
    // waiting for people in the way: the wagon's own time stands still
    this.delay += dtau * this.slow;
    const te = clamp(tau - this.delay, 0, tr.T);
    const k = this.sampleAt(te);
    const vNow = this.speedAt(k, te);
    let blocked = false;
    if (vNow > 0.05 && this.ghost <= 0) blocked = this.sweep(k, vNow) > 0;
    this.ghost = Math.max(0, this.ghost - dtau);
    if (blocked) {
      this.blockedFor += dtau;
      this.stat.blockedS += dtau;
      this.stat.longestBlock = Math.max(this.stat.longestBlock, this.blockedFor);
      if (this.blockedFor > BLOCK_GIVEUP) { this.ghost = 4; this.blockedFor = 0; }
    } else this.blockedFor = 0;
    this.slow = clamp(this.slow + (blocked ? 3 : -2) * dtau, 0, 1);
    this.pose(te, vNow * (1 - this.slow));

    // the gate: travellers down, the called ones up
    if (te >= tr.tArrive && !this.dropped) {
      this.dropped = true;
      for (const i of this.arriving) {
        if (!this.away.has(i)) continue;
        this.sim.release(i, tr.step[0] + (this.rnd() - 0.5) * 1.2, tr.step[1] + (this.rnd() - 0.5) * 1.2);
        this.away.delete(i);
        this.stat.alighted++;
      }
      this.arriving = [];
    }
    if (te >= tr.tArrive && te < tr.tLeave) {
      for (let c = this.called.length - 1; c >= 0; c--) {
        const i = this.called[c];
        const [x, z] = this.sim.posOf(i);
        if (!this.sim.waiting(i) || hyp(x - tr.step[0], z - tr.step[1]) > 3) continue;
        this.sim.carry(i);
        this.away.add(i);
        this.called.splice(c, 1);
        this.stat.boarded++;
      }
    } else if (te >= tr.tLeave && this.called.length) {
      for (const i of this.called) this.sim.unsummon(i);
      this.called = [];
    }
    this.carryRiders(vNow * (1 - this.slow));
  }

  /** A run on the road now (its team in harness). */
  get running(): boolean { return this.run >= 0; }

  /** The run leaving within `ahead` hours of `hour`: its team and departure hour (stable-crew.ts
   *  leads the pair to the pole beforehand); null while a run is on. */
  nextRun(hour: number, ahead: number): { names: string[]; dep: number } | null {
    if (!this.track || !this.enabled || this.run >= 0) return null;
    for (let k = 0; k < DEPART.length; k++) {
      const dt = (((DEPART[k] - hour) % 24) + 24) % 24;
      if (dt < ahead) return { names: TEAMS[k % 2], dep: DEPART[k] };
    }
    return null;
  }

  /** Where the team stands put to the pole in the stall (run time 0): near horse, off horse. */
  teamPlaces(): { x: number; z: number; yaw: number }[] {
    const tr = this.track;
    if (!tr) return [];
    const px = tr.px[0], pz = tr.pz[0], yaw = Math.atan2(px - tr.fx[0], pz - tr.fz[0]);
    const ux = Math.sin(yaw), uz = Math.cos(yaw);
    return [TEAM_SIDE, -TEAM_SIDE].map((side) => ({ x: px - ux * TEAM_BACK + uz * side, z: pz - uz * TEAM_BACK - ux * side, yaw }));
  }

  private startRun(run: number, tau: number): void {
    const tr = this.track!;
    this.stat.runs++;
    this.team = this.horses.hitch(TEAMS[run % 2]);
    if (this.postilion >= 0) this.sim.carry(this.postilion);
    this.arriving = [...this.away];
    this.dropped = false;
    if (tau < tr.tArrive - 20) {
      // called now to be at the step by the time the wagon is there
      const due = this.sim.simClock + (tr.tArrive - tau) / 60;
      for (const i of this.pickTravellers(1 + Math.floor(this.rnd() * 2), tr.step)) {
        if (this.sim.summon(i, tr.step[0], tr.step[1], due, 'Travelling on the posting wagon')) this.called.push(i);
      }
    }
  }

  private endRun(hour: number): void {
    if (this.team) this.horses.unhitch(this.team, hour);
    this.team = null;
    // the postilion gets down beside the carriage house
    if (this.postilion >= 0 && this.sim.isCarried(this.postilion)) {
      this.sim.release(this.postilion, this.sx + this.dx * 5.5 - this.dz * 2.2, this.sz + this.dz * 5.5 + this.dx * 2.2);
    }
    for (const i of this.called) this.sim.unsummon(i);
    this.called = [];
    // a run cut short (clock jump): those still on board are away again
    this.arriving = [];
    this.dropped = false;
    this.sim.vehicles = [];
  }

  private sampleAt(te: number): number {
    const tA = this.track!.tA;
    let lo = 0, hi = tA.length - 1;
    while (lo < hi) { const m = (lo + hi + 1) >> 1; if (tA[m] <= te) lo = m; else hi = m - 1; }
    return lo;
  }

  /** Planned speed at time te in sample k's span (0 while standing). */
  private speedAt(k: number, te: number): number {
    const tr = this.track!;
    if (te < tr.tD[k] || k >= tr.n - 1) return 0;
    const f = (te - tr.tD[k]) / Math.max(1e-3, tr.tA[k + 1] - tr.tD[k]);
    return tr.v[k] + (tr.v[k + 1] - tr.v[k]) * f;
  }

  /** People in the way of the leading end: count (and ask them aside). */
  private sweep(k: number, v: number): number {
    const tr = this.track!;
    const len = (v * v) / (2 * BRAKE) + 2.5;
    if (tr.rev[k]) {
      const bx = tr.bx[k], bz = tr.bz[k], ul = hyp(tr.fx[k] - bx, tr.fz[k] - bz) || 1;
      const ux = -(tr.fx[k] - bx) / ul, uz = -(tr.fz[k] - bz) / ul;
      return this.sim.vehicleSweep(bx + ux * 1.1, bz + uz * 1.1, ux, uz, Math.min(len, 3), 1.0);
    }
    const px = tr.px[k], pz = tr.pz[k], ul = hyp(px - tr.fx[k], pz - tr.fz[k]) || 1;
    const ux = (px - tr.fx[k]) / ul, uz = (pz - tr.fz[k]) / ul;
    return this.sim.vehicleSweep(px - ux * 0.5, pz - uz * 0.5, ux, uz, len, 1.35);
  }

  // ---------------------------------------------------------------- pose

  /** Wagon, team and obstacle capsules at run time te (0 = in the stall), moving at v. */
  private pose(te: number, v: number): void {
    const tr = this.track!;
    const k = this.sampleAt(te), k1 = Math.min(tr.n - 1, k + 1);
    let f = 0;
    if (k1 > k && te > tr.tD[k]) f = clamp((te - tr.tD[k]) / Math.max(1e-3, tr.tA[k1] - tr.tD[k]), 0, 1);
    const L = (a: Float32Array) => a[k] + (a[k1] - a[k]) * f;
    const px = L(tr.px), pz = L(tr.pz), fx = L(tr.fx), fz = L(tr.fz), bx = L(tr.bx), bz = L(tr.bz);
    const yaw = Math.atan2(fx - bx, fz - bz);
    const pyaw = Math.atan2(px - fx, pz - fz);
    const rev = tr.rev[k1] === 1 && te > tr.tD[k];
    const cx = (fx + bx) / 2, cz = (fz + bz) / 2;
    this.now = { x: cx, z: cz, yaw, v: rev ? -v : v, te };
    this.ch[0] = clamp(wrapPi(pyaw - yaw), -0.75, 0.75);
    this.ch[1] = L(tr.dF) / WAGON.rF;
    this.ch[2] = L(tr.dB) / WAGON.rB;

    // the team: either side of the pole, behind its tip, facing along it
    const ux = Math.sin(pyaw), uz = Math.cos(pyaw);
    const night = nightFactor(this.hour);
    if (this.team) {
      this.team.forEach((h, s) => {
        const side = s === 0 ? TEAM_SIDE : -TEAM_SIDE; // first = near (left) horse
        this.horses.drive(h, px - ux * TEAM_BACK + uz * side, pz - uz * TEAM_BACK - ux * side, pyaw, rev ? -v : v, TRAVEL);
      });
    }
    // obstacle capsules: wagon (rear to the front axle) and team (pole to the horses' heads)
    if (te > 0 && te < tr.T) {
      const wx = Math.sin(yaw), wz = Math.cos(yaw), sv = rev ? -v : v;
      const a = this.vehicles[0], b = this.vehicles[1];
      a.ax = bx - wx * 1.1; a.az = bz - wz * 1.1; a.bx = fx + wx * 0.3; a.bz = fz + wz * 0.3;
      a.vx = wx * sv; a.vz = wz * sv;
      b.ax = fx + ux * 1.4; b.az = fz + uz * 1.4; b.bx = px + ux * 0.9; b.bz = pz + uz * 0.9;
      b.vx = ux * sv; b.vz = uz * sv;
      this.sim.vehicles = this.vehicles;
    } else this.sim.vehicles = [];

    if (!this.draw) return;
    const d = this.draw;
    this.q.setFromAxisAngle(this.yAxis, yaw);
    this.p.set(cx, 0, cz);
    d.mesh.setMatrixAt(0, this.m4.compose(this.p, this.q, this.one));
    writePose(d, 0, this.ch);
    commitRig(d, 1);
    // under the wagon (not in the carriage house)
    const out = te > 0 && te < tr.T - 4;
    this.blobs.begin();
    if (out) {
      const a = 0.4 * (1 - 0.75 * night);
      this.blobs.add(fx * 0.7 + bx * 0.3, fz * 0.7 + bz * 0.3, 1.25, a, yaw);
      this.blobs.add(fx * 0.25 + bx * 0.75, fz * 0.25 + bz * 0.75, 1.35, a, yaw);
    }
    this.blobs.end();
  }

  /** The postilion astride the near horse; travellers inside (hidden), and the away ones with the wagon. */
  private carryRiders(v: number): void {
    const sim = this.sim, n = this.now;
    if (this.postilion >= 0 && sim.isCarried(this.postilion)) {
      const h = this.team?.[0];
      if (h) {
        const ux = Math.sin(h.yaw), uz = Math.cos(h.yaw);
        // a light rise to the trot
        const bob = Math.max(0, Math.sin(h.u * Math.PI * 4)) * 0.05 * clamp((Math.abs(v) - V_WALK) / (V_TROT - V_WALK), 0, 1);
        sim.setCarried(this.postilion, h.x - ux * 0.12, 1.5 * h.scale + h.y, h.z - uz * 0.12, h.yaw, 'ride', true, bob);
      } else sim.setCarried(this.postilion, n.x, 0, n.z, n.yaw, undefined, false);
    }
    for (const i of this.away) sim.setCarried(i, n.x, 0.9, n.z, n.yaw, 'sit', false);
  }

  // ---------------------------------------------------------------- debug

  /** Set off now (debug: hash wagon=run). */
  runNow(hour: number): void { this.debugDep = hour; }

  /** Where to look: the postilion while riding, else the wagon. */
  followTarget(): { citizen: Citizen | null; x: number; z: number } {
    const c = this.postilion >= 0 && this.run >= 0 ? this.sim.citizens[this.postilion] : null;
    return { citizen: c, x: this.now.x, z: this.now.z };
  }

  stats() {
    const tr = this.track;
    return {
      ok: !!tr, enabled: this.enabled, run: this.run, te: +this.now.te.toFixed(1), v: +this.now.v.toFixed(2),
      x: +this.now.x.toFixed(1), z: +this.now.z.toFixed(1), delay: +this.delay.toFixed(1),
      T: tr ? Math.round(tr.T) : 0, tArrive: tr ? Math.round(tr.tArrive) : 0, tLeave: tr ? Math.round(tr.tLeave) : 0,
      gate: tr?.gate, margins: tr?.margins, step: tr?.step, townM: tr?.townM, length: tr?.length,
      team: this.team?.map((h) => h.name) ?? [], postilion: this.postilion,
      postilionPhase: this.postilion >= 0 ? this.sim.phaseOf(this.postilion) : null,
      away: [...this.away], called: [...this.called], ...this.stat,
    };
  }
}

/** __lublin.wagon and the wagon= / follow=wagon hashes (dev only). */
export function installWagonDebug(w: Wagon, sim: SimulationEngine, follow: (c: Citizen | null, x: number, z: number, zoom: number) => void): void {
  const g = window as unknown as { __lublin?: Record<string, unknown> };
  if (g.__lublin) g.__lublin.wagon = w;
  let timer = 0;
  const apply = () => {
    const params = new URLSearchParams(location.hash.slice(1));
    const v = params.get('wagon');
    const f = params.get('follow');
    requestAnimationFrame(() => requestAnimationFrame(() => {
      w.enabled = v !== 'off';
      if (v === 'run') w.runNow(sim.simTimeHours);
      clearInterval(timer);
      if (f?.startsWith('wagon')) {
        const zoom = Number(f.split(',')[1]) || 18;
        // the postilion once the run is on (re-checked: a jump or wagon=run starts it a frame later)
        let n = 0;
        timer = window.setInterval(() => {
          const t = w.followTarget();
          follow(t.citizen, t.x, t.z, zoom);
          if (t.citizen || ++n > 8) clearInterval(timer);
        }, 250);
      }
    }));
  };
  window.addEventListener('hashchange', apply);
  apply();
}
