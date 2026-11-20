import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import type { CityPlan, Parcel } from '../types';
import type { BuildingIndex, Stall } from './building-anchors';
import { nightFactor } from './door-leaves';
import { BlobShadows, commitRig, makeRigMesh, writeCoat, writePose, type RigDef, type RigDraw, type RigOptions } from './rigid-rig';

/**
 * The town stable's horses (stable plan M3): six palfreys and four draught horses.
 *
 * Models: animal_horse / animal_horse_draught (build_animals.py), rigid parts drawn by
 * rigid-rig.ts with 24 pose channels per instance: a two-part neck (pivot low in the chest, so the
 * muzzle reaches the grass), head, jaw, ears, a two-part tail, and three segments per leg (upper, lower from the knee / hock, hoof from the fetlock). Tack parts
 * (saddle, bridle + reins, halter, lead rope, collar + harness) are shown by the instance's tack
 * mask (TACK). Coat and points (mane, tail, lower legs) are per-instance colours (COATS).
 *
 * Gaits: walk (four-beat lateral sequence, 1.6 m/s), trot (diagonal pairs, 3.5 m/s) and canter
 * (three-beat, left lead, 6 m/s) are blended by speed, so a horse speeding up or slowing down
 * passes through them. Each leg swings back through its stance and forward through its swing,
 * folding at the knee / hock and the fetlock; the body drops by the stance legs' arc so hooves
 * stay near the ground, and the head nods with the walk and rocks with the canter.
 * Standing: weight on three legs with a hind hoof tipped, tail swishes, ears flick, dozing
 * (head low, ears slack), grazing and eating (jaw chewing) and drinking.
 *
 * Their day: in the paddock (graze, wander, drink at the trough, eat at the hay rack, now and
 * then a trot or a canter) or in their stalls (Building.stalls of stable_long), dozing and
 * eating. The grooms move them (stable-crew.ts sets `managed`): out from about 5:40, in from
 * 19:20, the wagon's pair to the pole and back, a palfrey to the farrier's post. Unmanaged (no
 * crew), or on a clock jump, they are put in their place for the hour: the paddock from 7:00 to
 * 19:30 (PADDOCK_DAY), the stalls otherwise. Motion runs on real time, like the wildlife.
 *
 * Held (Horse.holder), their own day paused and drive() placing them every frame with a signed
 * speed (backing = the walk run backwards) and the travel speed-up (gait from v / travel, stride
 * quickened by its square root): 'wagon' in harness (hitch / unhitch, wagon.ts), 'lead' on a
 * groom's rope (take), 'tied' standing (tie: at the pole before a run and after it, at the
 * farrier's post). turnOut() lets one loose in the paddock, stable() puts one in its stall,
 * call() brings a loose one to the gate.
 *
 * Debug: __lublin.horses (.stats(), .lineup), hash `horses=lineup[,walk|trot|canter|graze|
 * drink|eat|doze|stand[,zoom]]` (six horses side by side off the paddock gate, every tack),
 * `horses=paddock[,,zoom]`, `horses=stable` and `horses=off` (perf before/after; installHorseDebug).
 */

// ------------------------------------------------------------------ rig

/** Pose channels (24 per instance). */
const NECK = 0, NECK_YAW = 1, HEAD = 2, HEAD_YAW = 3, JAW = 4, EAR_L = 5, EAR_R = 6, TAIL1 = 7, TAIL_YAW = 8,
  TAIL2 = 9, NECK2 = 10, TACK_CH = 11, LEG_U = 12, LEG_L = 16, HOOF = 20;
/** Tack mask bits (build_animals.py TACK_BITS). */
export const TACK = { saddle: 1, bridle: 2, halter: 4, lead: 8, harness: 16 } as const;
export const TACK_RIDING = TACK.saddle | TACK.bridle;
export const TACK_DRAUGHT = TACK.harness | TACK.bridle;
export const TACK_LED = TACK.halter | TACK.lead;

const LEGS = ['FL', 'FR', 'BL', 'BR'];
const HORSE_RIG: RigDef = {
  body: [-1, -1, -1, ''], neck: [NECK, NECK_YAW, -1, ''], neck2: [NECK2, -1, -1, 'neck'],
  head: [HEAD, HEAD_YAW, -1, 'neck2'], jaw: [JAW, -1, -1, 'head'],
  ear_L: [EAR_L, -1, -1, 'head'], ear_R: [EAR_R, -1, -1, 'head'],
  // the hair swings with the dock's yaw (compounded: the tip swishes further)
  tail1: [TAIL1, TAIL_YAW, -1, ''], tail2: [TAIL2, TAIL_YAW, -1, 'tail1'],
  saddle: [-1, -1, -1, ''], bridle: [-1, -1, -1, 'head'], reins: [-1, -1, -1, 'neck'], halter: [-1, -1, -1, 'head'],
  lead: [-1, -1, -1, 'head'], collar: [-1, -1, -1, 'neck'], harness: [-1, -1, -1, ''],
};
LEGS.forEach((l, k) => {
  HORSE_RIG[`legU_${l}`] = [LEG_U + k, -1, -1, ''];
  HORSE_RIG[`legL_${l}`] = [LEG_L + k, -1, -1, `legU_${l}`];
  HORSE_RIG[`hoof_${l}`] = [HOOF + k, -1, -1, `legL_${l}`];
});
/** depth 5: bridle -> head -> neck2 -> neck. */
const RIG_OPTS: RigOptions = { key: 'horses-v1', nPart: 29, nChan: 24, depth: 5, tagChan: TACK_CH, coat: true };

type Kind = 'horse' | 'horse_draught';
const KINDS: Kind[] = ['horse', 'horse_draught'];

// ------------------------------------------------------------------ gaits

interface GaitDef {
  v: number; f: number; duty: number; amp: number;
  knee: [number, number]; fet: [number, number]; off: number[];
}
/** Speed (m/s), stride frequency (Hz), stance share, hip swing (rad), knee / hock fold and
 *  fetlock fold in the swing [front, hind], footfall offsets [FL, FR, BL, BR]. */
const GAITS: GaitDef[] = [
  { v: 1.6, f: 0.95, duty: 0.62, amp: 0.36, knee: [1.0, -0.8], fet: [0.75, 0.6], off: [0.25, 0.75, 0, 0.5] },
  { v: 3.5, f: 1.4, duty: 0.42, amp: 0.42, knee: [1.4, -1.05], fet: [1.0, 0.8], off: [0, 0.5, 0.5, 0] },
  { v: 6.0, f: 1.75, duty: 0.38, amp: 0.5, knee: [1.3, -1.0], fet: [1.0, 0.8], off: [0.55, 0.3, 0.3, 0] },
];
export type GaitName = 'stand' | 'walk' | 'trot' | 'canter';
const GAIT_SPEED: Record<GaitName, number> = { stand: 0, walk: 1.6, trot: 3.5, canter: 6.0 };
const LEG_LEN = 1.0; // pivot height of the legs above the hooves

/** Gait weights [walk, trot, canter] at speed v (the remainder stands). */
function gaitWeights(v: number, out: number[]): void {
  out[0] = out[1] = out[2] = 0;
  if (v <= GAITS[0].v) out[0] = v / GAITS[0].v;
  else if (v <= GAITS[1].v) { const t = (v - GAITS[0].v) / (GAITS[1].v - GAITS[0].v); out[0] = 1 - t; out[1] = t; }
  else if (v <= GAITS[2].v) { const t = (v - GAITS[1].v) / (GAITS[2].v - GAITS[1].v); out[1] = 1 - t; out[2] = t; }
  else out[2] = 1;
}

// ------------------------------------------------------------------ coats

const COATS: Record<string, [string, string]> = {
  bay: ['#7a4426', '#1d1714'], darkbay: ['#4e2e1e', '#171210'], chestnut: ['#8e4c22', '#74401e'],
  grey: ['#bdb8b0', '#7a7670'], black: ['#2a231f', '#161210'], dun: ['#b08a58', '#2a2018'],
};

/** The stable's ten horses (default herd: 6 palfreys, 4 draught horses). Siwek is the council's palfrey. */
const HERD: { name: string; kind: Kind; coat: string }[] = [
  { name: 'Siwek', kind: 'horse', coat: 'grey' }, { name: 'Kasztanka', kind: 'horse', coat: 'chestnut' },
  { name: 'Gniady', kind: 'horse', coat: 'bay' }, { name: 'Bułanek', kind: 'horse', coat: 'dun' },
  { name: 'Wrona', kind: 'horse', coat: 'black' }, { name: 'Karmazyn', kind: 'horse', coat: 'darkbay' },
  { name: 'Mocarz', kind: 'horse_draught', coat: 'bay' }, { name: 'Kruk', kind: 'horse_draught', coat: 'black' },
  { name: 'Rudy', kind: 'horse_draught', coat: 'chestnut' }, { name: 'Szpak', kind: 'horse_draught', coat: 'grey' },
];

const PADDOCK_DAY: [number, number] = [7.0, 19.5];
const VIEW_MARGIN = 10;

// ------------------------------------------------------------------ state

type Act = 'stand' | 'doze' | 'graze' | 'drink' | 'eat';

export interface Horse {
  name: string; kind: Kind; coat: THREE.Color; pts: THREE.Color;
  x: number; z: number; y: number; yaw: number; pitch: number; roll: number; scale: number;
  ch: Float32Array; tack: number; vis: boolean; seed: number;
  /** Speed now (m/s), the stride phase (cycles) and the gait weights [walk, trot, canter]. */
  v: number; u: number; w: number[];
  act: Act; actT: number;
  /** Walking to (tx, tz) at speed goV; face tyaw on arrival. */
  go: boolean; tx: number; tz: number; goV: number; tyaw: number | null; then: Act;
  stall: Stall | null; inStall: boolean;
  /** Resting hind leg (2 = BL, 3 = BR, -1 none) and its weight. */
  rest: number; restW: number;
  earT: [number, number]; swishT: number; stepT: number;
  /** Debug lineup: run in place at this gait / act. */
  fixed: { gait: GaitName; act: Act } | null;
  /** Out of its own day: in harness (the wagon, wagon.ts), on a groom's lead, or tied up
   *  (stable-crew.ts); placed by drive() every frame while held, its own day paused. */
  held: boolean;
  holder: 'wagon' | 'lead' | 'tied' | null;
  /** Shown speed-up of its travel (the wagon goes at TRAVEL_SCALE like the citizens): the gait
   *  is chosen from v / travel and the stride quickened by its square root. */
  travel: number;
}

interface Draw { rig: RigDraw; list: Horse[] }

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const wrapPi = (a: number) => { while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return a; };
const smooth = (cur: number, to: number, rate: number, dt: number) => cur + (to - cur) * (1 - Math.exp(-rate * dt));
const inWin = (h: number, w: [number, number]) => h >= w[0] && h < w[1];

function mulberry32(seed: number): () => number {
  return () => {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** A parcel's model frame: Blender (bx, by) of its model to world x-z. */
class SiteFrame {
  readonly x: number; readonly z: number;
  private c: number; private s: number;
  constructor(x: number, z: number, rotDeg: number) {
    this.x = x; this.z = z;
    const t = (rotDeg * Math.PI) / 180;
    this.c = Math.cos(t); this.s = Math.sin(t);
  }
  world(bx: number, by: number): { x: number; z: number } {
    const lx = bx, lz = -by;
    return { x: this.x + lx * this.c + lz * this.s, z: this.z - lx * this.s + lz * this.c };
  }
  local(x: number, z: number): { bx: number; by: number } {
    const dx = x - this.x, dz = z - this.z;
    return { bx: dx * this.c - dz * this.s, by: -(dx * this.s + dz * this.c) };
  }
  /** World yaw of a Blender direction. */
  yaw(dbx: number, dby: number): number {
    const p = this.world(dbx, dby);
    return Math.atan2(p.x - this.x, p.z - this.z);
  }
}

/** Paddock (build_paddock in build_assets.py): 30 x 44 m, trough and hay rack inside. */
const PADDOCK = { hw: 15, hd: 22, margin: 2.2, trough: { bx: -13, by: -16 }, rack: { bx: 12, by: 0 } };

export class Horses {
  readonly horses: Horse[] = [];
  /** Debug lineup (horses=lineup): every kind and tack side by side here. */
  lineup: { x: number; z: number; gait: GaitName; act: Act } | null = null;
  enabled = true;
  /** The grooms move the horses (stable-crew.ts): no change of place at 7:00 and 19:30, and
   *  a team out of harness stays tied where it stands. */
  managed = false;
  /** Clock jumps seen (every horse re-placed for the hour; the crew drops its jobs). */
  jumps = 0;

  private rnd = mulberry32(1392 * 11);
  private draws = new Map<Kind, Draw>();
  private blobs: BlobShadows;
  private paddock: SiteFrame | null = null;
  private time = 0;
  private last = -1;
  private lastHour = NaN;
  private view = [0, 0, 0, 0];
  private updateMs = 0;
  private loaded = false;
  private m4 = new THREE.Matrix4();
  private q = new THREE.Quaternion();
  private e = new THREE.Euler(0, 0, 0, 'YXZ');
  private p = new THREE.Vector3();
  private sc = new THREE.Vector3();
  private wTmp = [0, 0, 0];

  private scene: THREE.Scene;

  constructor(scene: THREE.Scene, plan: CityPlan, buildings: BuildingIndex) {
    this.scene = scene;
    const pad = (plan.parcels ?? []).find((p: Parcel) => p.model === 'paddock');
    if (pad) this.paddock = new SiteFrame(pad.x, pad.z, pad.orientation ?? 0);
    const stalls = (buildings.byModel.get('stable_long') ?? []).flatMap((b) => b.stalls.filter((s) => s.tag === 'horse'));
    if (!this.paddock && !stalls.length) { this.blobs = new BlobShadows(scene, 1, 'horse_blobs'); return; }
    HERD.forEach((d, i) => {
      const [c, p] = COATS[d.coat];
      const h: Horse = {
        name: d.name, kind: d.kind, coat: new THREE.Color(c), pts: new THREE.Color(p),
        x: 0, z: 0, y: 0, yaw: 0, pitch: 0, roll: 0, scale: 0.97 + this.rnd() * 0.06,
        ch: new Float32Array(24), tack: TACK.halter, vis: false, seed: this.rnd() * 100,
        v: 0, u: this.rnd(), w: [0, 0, 0], act: 'stand', actT: this.rnd() * 10,
        go: false, tx: 0, tz: 0, goV: 0, tyaw: null, then: 'graze',
        stall: stalls[i] ?? null, inStall: false, rest: -1, restW: 0,
        earT: [this.rnd() * 4, this.rnd() * 4], swishT: this.rnd() * 5, stepT: 0, fixed: null,
        held: false, holder: null, travel: 1,
      };
      if (h.stall) h.stall.taken++;
      this.horses.push(h);
    });
    this.blobs = new BlobShadows(scene, this.horses.length, 'horse_blobs');
    void this.load();
  }

  private async load(): Promise<void> {
    const loader = new GLTFLoader();
    await Promise.all(KINDS.map(async (kind) => {
      const list = this.horses.filter((h) => h.kind === kind);
      if (!list.length) return;
      try {
        const gltf = await loader.loadAsync(`/models/animal_${kind}.glb`);
        const rig = makeRigMesh(gltf, HORSE_RIG, RIG_OPTS, list.length, `horses_${kind}`);
        this.scene.add(rig.mesh);
        this.draws.set(kind, { rig, list });
      } catch (e) {
        console.warn(`[horses] animal_${kind}.glb`, e);
      }
    }));
    this.loaded = true;
  }

  // ---------------------------------------------------------------- places

  private paddockPoint(): { x: number; z: number } {
    const P = PADDOCK;
    const bx = (this.rnd() * 2 - 1) * (P.hw - P.margin), by = (this.rnd() * 2 - 1) * (P.hd - P.margin);
    return this.paddock!.world(bx, by);
  }

  /** A place beside the trough or the hay rack, and the yaw facing it. */
  private feedPlace(what: 'trough' | 'rack'): { x: number; z: number; yaw: number } {
    const f = this.paddock!, c = what === 'trough' ? PADDOCK.trough : PADDOCK.rack;
    const side = this.rnd() < 0.5 ? -1 : 1;
    const bx = c.bx + side * 1.35, by = c.by + (this.rnd() - 0.5) * 1.6;
    const p = f.world(bx, by);
    return { ...p, yaw: f.yaw(-side, 0) };
  }

  private placeAll(hour: number): void {
    const night = !inWin(hour, PADDOCK_DAY);
    for (const h of this.horses) {
      if (h.holder === 'lead' || h.holder === 'tied') this.letGo(h);
      this.place(h, night);
    }
  }

  private letGo(h: Horse): void {
    h.held = false; h.holder = null; h.travel = 1; h.v = 0; h.go = false;
  }

  private place(h: Horse, night: boolean): void {
    if (h.held) return;
    h.go = false; h.v = 0; h.tyaw = null;
    if ((night || !this.paddock) && h.stall) {
      h.inStall = true; h.x = h.stall.x; h.z = h.stall.z; h.yaw = h.stall.yaw;
      h.act = this.rnd() < 0.5 ? 'doze' : 'eat'; h.actT = 20 + this.rnd() * 40;
    } else if (this.paddock) {
      h.inStall = false;
      const p = this.paddockPoint();
      h.x = p.x; h.z = p.z; h.yaw = this.rnd() * Math.PI * 2;
      h.act = this.rnd() < 0.7 ? 'graze' : 'stand'; h.actT = 10 + this.rnd() * 40;
    }
    h.tack = TACK.halter;
  }

  // ---------------------------------------------------------------- update

  /** Per frame: hour = sim clock, view = the camera's ground rectangle (renderer.groundView). */
  update(hour: number, view: number[]): void {
    const t0 = performance.now();
    const now = t0 * 0.001;
    const dt = this.last < 0 ? 0 : Math.min(0.1, now - this.last);
    this.last = now;
    this.time += dt;
    for (let k = 0; k < 4; k++) this.view[k] = view[k];
    if (!this.enabled || !this.horses.length) {
      for (const d of this.draws.values()) d.rig.mesh.visible = false;
      this.blobs.hide();
      return;
    }
    const jump = Number.isNaN(this.lastHour) || Math.abs(wrapPi((hour - this.lastHour) / 24 * 2 * Math.PI)) > 0.35 * 2 * Math.PI / 24;
    const night = !inWin(hour, PADDOCK_DAY);
    const wasNight = !inWin(this.lastHour, PADDOCK_DAY);
    this.lastHour = hour;
    if (this.lineup) this.poseLineup(dt);
    else {
      if (jump) { this.placeAll(hour); this.jumps++; }
      else if (night !== wasNight && !this.managed) for (const h of this.horses) { h.fixed = null; this.place(h, night); }
      for (const h of this.horses) {
        if (!h.held) {
          if (h.inStall) this.stallLife(h, dt);
          else this.paddockLife(h, dt);
          this.move(h, dt);
        }
        this.animate(h, dt);
      }
    }
    if (this.loaded) this.pack(hour);
    this.updateMs = this.updateMs * 0.9 + (performance.now() - t0) * 0.1;
  }

  private stallLife(h: Horse, dt: number): void {
    h.actT -= dt;
    if (h.actT <= 0) {
      h.act = h.act === 'eat' ? (this.rnd() < 0.6 ? 'doze' : 'stand') : this.rnd() < 0.5 ? 'eat' : 'doze';
      h.actT = 25 + this.rnd() * 50;
    }
    if (h.stall) { h.x = h.stall.x; h.z = h.stall.z; h.tyaw = h.stall.yaw; }
  }

  private paddockLife(h: Horse, dt: number): void {
    h.actT -= dt;
    if (h.go) return;
    if (h.act === 'graze') {
      // grazing: a step or two forward now and then
      h.stepT -= dt;
      if (h.stepT <= 0) {
        h.stepT = 6 + this.rnd() * 10;
        const d = 0.6 + this.rnd() * 1.2, a = h.yaw + (this.rnd() - 0.5) * 1.2;
        this.walkTo(h, h.x + Math.sin(a) * d, h.z + Math.cos(a) * d, 0.55, 'graze');
        return;
      }
    }
    if (h.actT > 0) return;
    const r = this.rnd();
    if (r < 0.5) {
      const p = this.paddockPoint();
      this.walkTo(h, p.x, p.z, GAIT_SPEED.walk * (0.8 + this.rnd() * 0.2), 'graze');
      h.actT = 40 + this.rnd() * 60;
    } else if (r < 0.62) {
      const p = this.feedPlace('trough');
      this.walkTo(h, p.x, p.z, GAIT_SPEED.walk, 'drink', p.yaw);
      h.actT = 12 + this.rnd() * 10;
    } else if (r < 0.74) {
      const p = this.feedPlace('rack');
      this.walkTo(h, p.x, p.z, GAIT_SPEED.walk, 'eat', p.yaw);
      h.actT = 30 + this.rnd() * 40;
    } else if (r < 0.92) {
      h.act = this.rnd() < 0.5 ? 'stand' : 'doze'; h.actT = 20 + this.rnd() * 40;
    } else {
      // a burst of play: trot or canter to the far side
      const p = this.paddockPoint();
      this.walkTo(h, p.x, p.z, this.rnd() < 0.7 ? GAIT_SPEED.trot : GAIT_SPEED.canter, 'stand');
      h.actT = 8 + this.rnd() * 10;
    }
  }

  private walkTo(h: Horse, x: number, z: number, v: number, then: Act, yaw: number | null = null): void {
    if (this.paddock && !h.inStall) {
      const P = PADDOCK, l = this.paddock.local(x, z);
      const q = this.paddock.world(clamp(l.bx, -P.hw + P.margin, P.hw - P.margin), clamp(l.by, -P.hd + P.margin, P.hd - P.margin));
      x = q.x; z = q.z;
    }
    h.go = true; h.tx = x; h.tz = z; h.goV = v; h.then = then; h.tyaw = yaw;
  }

  private move(h: Horse, dt: number): void {
    let want = 0;
    if (h.go) {
      const dx = h.tx - h.x, dz = h.tz - h.z, dist = Math.hypot(dx, dz);
      if (dist < 0.25 || (dist < 1.2 && h.goV > 2)) { h.go = false; h.act = h.then; }
      else {
        const turn = h.goV > 4 ? 1.1 : h.goV > 2 ? 1.5 : 1.8;
        const head = Math.atan2(dx, dz);
        h.yaw += clamp(wrapPi(head - h.yaw), -turn * dt, turn * dt);
        const facing = Math.cos(wrapPi(head - h.yaw));
        // slow down to stop: brake from the gait's speed at ~1.5 m/s^2
        want = Math.min(h.goV, Math.sqrt(2 * 1.5 * dist)) * clamp(facing, 0.2, 1);
        if (h.act !== 'graze' || h.goV > 1) h.act = 'stand';
      }
    }
    if (!h.go && h.tyaw !== null) h.yaw += clamp(wrapPi(h.tyaw - h.yaw), -1.0 * dt, 1.0 * dt);
    // accelerate ~2 m/s^2, brake ~3 m/s^2
    h.v = want > h.v ? Math.min(want, h.v + 2 * dt) : Math.max(want, h.v - 3 * dt);
    h.x += Math.sin(h.yaw) * h.v * dt;
    h.z += Math.cos(h.yaw) * h.v * dt;
    if (h.inStall) return;
    // keep a little apart from the others in the paddock, and inside the fence
    for (const o of this.horses) {
      if (o === h || o.inStall || o.held) continue;
      const ox = h.x - o.x, oz = h.z - o.z, l = Math.hypot(ox, oz), min = 1.7;
      if (l > 1e-3 && l < min) { const k = (min - l) * 0.5 * Math.min(1, dt * 3); h.x += (ox / l) * k; h.z += (oz / l) * k; }
    }
    if (this.paddock) {
      const P = PADDOCK, l = this.paddock.local(h.x, h.z), m = 1.4;
      const bx = clamp(l.bx, -P.hw + m, P.hw - m), by = clamp(l.by, -P.hd + m, P.hd - m);
      if (bx !== l.bx || by !== l.by) { const q = this.paddock.world(bx, by); h.x = q.x; h.z = q.z; }
    }
  }

  private inView(x: number, z: number): boolean {
    const v = this.view, m = VIEW_MARGIN;
    return x > v[0] - m && x < v[2] + m && z > v[1] - m && z < v[3] + m;
  }

  // ---------------------------------------------------------------- pose

  /** Procedural pose from the speed (gait blend) and the act. */
  private animate(h: Horse, dt: number): void {
    h.vis = h.fixed !== null || this.inView(h.x, h.z);
    const sc = h.scale * (h.kind === 'horse_draught' ? 1.07 : 1);
    const w = h.w;
    // backing (the wagon into its place): the walk run backwards
    const av = Math.abs(h.v) / h.travel;
    gaitWeights(av / sc, this.wTmp);
    for (let g = 0; g < 3; g++) w[g] = smooth(w[g], this.wTmp[g], 6, dt);
    const moving = w[0] + w[1] + w[2];
    let f = 0;
    for (let g = 0; g < 3; g++) f += w[g] * GAITS[g].f;
    // stride frequency follows the speed (a slow walk is a slower walk, not a shuffle)
    const vg = w[0] * GAITS[0].v + w[1] * GAITS[1].v + w[2] * GAITS[2].v;
    if (moving > 0.01 && vg > 0.01) f *= clamp(av / sc / vg, 0.5, 1.4);
    f *= Math.sqrt(h.travel);
    h.u = (h.u + (h.v < 0 ? -f : f) * dt + 1) % 1;
    if (!h.vis) return;
    const ch = h.ch, u = h.u, T = this.time;

    // legs
    let drop = 0, stanceN = 0;
    for (let k = 0; k < 4; k++) {
      const front = k < 2, fi = front ? 0 : 1;
      let up = 0, lo = 0, ho = 0, inStance = 0;
      for (let g = 0; g < 3; g++) {
        if (w[g] < 0.005) continue;
        const G = GAITS[g];
        const lu = (u - G.off[k] + 2) % 1;
        let a: number, b = 0, c: number;
        if (lu < G.duty) {
          const s = lu / G.duty;                    // stance: the hoof planted, the leg sweeps back
          a = -G.amp + 2 * G.amp * s;
          c = -0.18 * Math.sin(Math.PI * s);       // fetlock sinks under the weight
          inStance += w[g];
        } else {
          const s = (lu - G.duty) / (1 - G.duty);  // swing: folded, carried forward
          a = G.amp - 2 * G.amp * (0.5 - 0.5 * Math.cos(Math.PI * s));
          b = G.knee[fi] * Math.sin(Math.PI * Math.pow(s, front ? 0.75 : 0.9));
          c = G.fet[fi] * Math.sin(Math.PI * Math.min(1, s * 1.15));
        }
        up += a * w[g]; lo += b * w[g]; ho += c * w[g];
      }
      // standing on three legs: one hind hoof tipped, its leg relaxed
      if (k === h.rest) { const r = h.restW * (1 - moving); up += -0.06 * r; lo += -0.25 * r; ho += 0.75 * r; }
      ch[LEG_U + k] = up; ch[LEG_L + k] = lo; ch[HOOF + k] = ho;
      if (inStance > 0.5) { drop += LEG_LEN * (1 - Math.cos(up)); stanceN++; }
    }
    const bodyDrop = stanceN ? drop / stanceN : 0;

    // body: trot bounce, canter rocking
    const ph = u * Math.PI * 2;
    let bob = -bodyDrop * sc + 0.012 * Math.cos(2 * ph) * w[0] * sc + 0.03 * Math.cos(2 * ph) * w[1] * sc
      + 0.05 * Math.sin(ph + 0.6) * w[2] * sc;
    h.pitch = 0.06 * Math.sin(ph + 2.2) * w[2];
    h.roll = smooth(h.roll, h.rest >= 0 ? (h.rest === 2 ? 0.015 : -0.015) * h.restW * (1 - moving) : 0, 3, dt);
    bob += -0.015 * h.restW * (1 - moving) * sc;
    h.y = bob;

    // resting a hind leg now and then while standing
    if (moving < 0.1 && (h.act === 'stand' || h.act === 'doze' || h.act === 'eat')) {
      if (h.rest < 0 && this.rnd() < dt * 0.08) h.rest = this.rnd() < 0.5 ? 2 : 3;
      else if (h.rest >= 0 && this.rnd() < dt * 0.02) h.rest = -1;
    } else if (moving > 0.2) h.rest = -1;
    h.restW = smooth(h.restW, h.rest >= 0 ? 1 : 0, 2, dt);
    if (h.rest < 0 && h.restW < 0.02) h.restW = 0;

    // head and neck (lower neck from the chest, upper neck, head at the poll): the act, and the
    // gait's nod. Angles solved for the muzzle: on the grass (graze), at the trough's water (0.7 m),
    // in the manger or hay rack (~1 m).
    let neck = 0, neck2 = 0, head = 0, nyaw = 0, jaw = 0, ears = 0.1;
    switch (h.act) {
      case 'graze': neck = 1.6; head = -0.45; nyaw = Math.sin(T * 0.4 + h.seed) * 0.2; jaw = 0.08 * (0.5 + 0.5 * Math.sin(T * 8 + h.seed)); ears = -0.1; break;
      case 'drink': neck = 0.5; neck2 = 0.6; head = -0.1; jaw = 0.03 * (0.5 + 0.5 * Math.sin(T * 5)); break;
      case 'eat': neck = 0.05; neck2 = 0.5; nyaw = Math.sin(T * 0.3 + h.seed) * 0.12; jaw = 0.08 * (0.5 + 0.5 * Math.sin(T * 7 + h.seed)); break;
      case 'doze': neck = 0.45; neck2 = -0.1; head = 0.15; ears = -0.45; break;
      default: neck = 0.05; head = 0.05; nyaw = Math.sin(T * 0.23 + h.seed) * 0.3 * (1 - moving);
    }
    const still = 1 - moving;
    neck = neck * still + (0.15 - 0.06 * w[2]) * moving;
    neck2 = neck2 * still;
    head = head * still + 0.05 * moving;
    nyaw *= still;
    neck2 += 0.08 * Math.sin(2 * ph + 1.2) * w[0] + 0.14 * Math.sin(ph + 1.4) * w[2];
    neck += 0.05 * Math.sin(ph + 1.4) * w[2];
    const hr = moving > 0.2 ? 12 : 2;
    ch[NECK] = smooth(ch[NECK], neck, hr, dt);
    ch[NECK2] = smooth(ch[NECK2], neck2, hr, dt);
    ch[HEAD] = smooth(ch[HEAD], head, hr, dt);
    ch[NECK_YAW] = smooth(ch[NECK_YAW], nyaw, 2, dt);
    ch[HEAD_YAW] = ch[NECK_YAW] * 0.5;
    ch[JAW] = jaw;
    // ears: forward when moving fast, slack when dozing, flicking now and then
    for (const k of [0, 1]) {
      h.earT[k] -= dt;
      if (h.earT[k] < -0.25) h.earT[k] = 1.5 + this.rnd() * 6;
      const flick = h.earT[k] < 0 ? Math.sin((-h.earT[k] / 0.25) * Math.PI) * -0.6 : 0;
      ch[EAR_L + k] = smooth(ch[EAR_L + k], ears + 0.25 * moving, 4, dt) + flick * 0.5;
    }
    // tail: swishes at flies standing, carried higher at the trot and canter
    h.swishT -= dt;
    if (h.swishT < -1.2) h.swishT = 3 + this.rnd() * 8;
    const swish = h.swishT < 0 ? Math.sin((-h.swishT / 1.2) * Math.PI * 3) * 0.3 * (1 - moving) : 0;
    ch[TAIL1] = smooth(ch[TAIL1], 0.05 + 0.25 * w[1] + 0.45 * w[2], 4, dt);
    ch[TAIL_YAW] = swish + Math.sin(ph) * 0.06 * moving;
    ch[TAIL2] = smooth(ch[TAIL2], -0.05 + 0.35 * w[2], 4, dt) + 0.08 * Math.sin(2 * ph) * (w[1] + w[2]);
    ch[TACK_CH] = h.tack;
  }

  // ---------------------------------------------------------------- debug lineup

  /** Six horses side by side (every tack), running in place at one gait or doing one act. */
  private poseLineup(dt: number): void {
    const l = this.lineup!;
    const show: [number, number][] = [[0, TACK_RIDING], [2, TACK_LED], [1, 0], [6, 0], [7, TACK_DRAUGHT], [9, TACK.halter]];
    for (const h of this.horses) h.vis = false;
    show.forEach(([i, tack], k) => {
      const h = this.horses[i];
      if (!h) return;
      h.fixed = { gait: l.gait, act: l.act };
      h.x = l.x; h.z = l.z + (k - 2.5) * 2.2; h.yaw = Math.PI / 2; h.tack = tack; h.inStall = false;
      h.v = GAIT_SPEED[l.gait] * h.scale * (h.kind === 'horse_draught' ? 1.07 : 1);
      h.act = l.act;
      if (l.act === 'stand' && l.gait === 'stand' && h.rest < 0 && k % 2) h.rest = 3;
      this.animate(h, dt);
      h.vis = true;
    });
  }

  // ---------------------------------------------------------------- draw

  private pack(hour: number): void {
    const night = nightFactor(hour);
    this.blobs.begin();
    for (const dr of this.draws.values()) {
      let n = 0;
      const mesh = dr.rig.mesh;
      for (const h of dr.list) {
        if (!h.vis) continue;
        this.e.set(h.pitch, h.yaw, h.roll, 'YXZ');
        this.q.setFromEuler(this.e);
        this.p.set(h.x, h.y, h.z);
        this.sc.setScalar(h.scale);
        mesh.setMatrixAt(n, this.m4.compose(this.p, this.q, this.sc));
        writeCoat(dr.rig, n, h.coat, h.pts);
        writePose(dr.rig, n, h.ch);
        n++;
        if (!h.inStall) this.blobs.add(h.x, h.z, 1.25 * h.scale, 0.42 * (1 - 0.75 * night), h.yaw);
      }
      commitRig(dr.rig, n);
    }
    this.blobs.end();
  }

  // ---------------------------------------------------------------- harness (wagon.ts)

  /** Take these horses out of their day into harness (draught tack); null if one is missing. */
  hitch(names: string[]): Horse[] | null {
    const team = names.map((n) => this.horses.find((h) => h.name === n));
    if (team.some((h) => !h)) return null;
    for (const h of team as Horse[]) {
      this.hold(h, 'wagon', TACK_DRAUGHT);
      h.inStall = false;
    }
    return team as Horse[];
  }

  private hold(h: Horse, holder: Horse['holder'], tack: number): void {
    h.held = true; h.holder = holder; h.go = false; h.tyaw = null; h.fixed = null;
    h.act = 'stand'; h.rest = -1; h.tack = tack;
  }

  /** A horse in harness this frame: where, heading, signed speed (m/s shown; < 0 backing) and travel scale. */
  drive(h: Horse, x: number, z: number, yaw: number, v: number, travel: number): void {
    h.x = x; h.z = z; h.yaw = yaw; h.v = v; h.travel = travel;
  }

  /** Out of harness, back to its day (put in its stall or the paddock for the hour). */
  unhitch(team: Horse[], hour: number): void {
    for (const h of team) {
      if (this.managed) { this.tie(h); continue; }
      this.letGo(h);
      this.place(h, !inWin(hour, PADDOCK_DAY));
    }
  }

  // ---------------------------------------------------------------- the grooms (stable-crew.ts)

  /** On a groom's lead (halter and rope): out of its stall or the paddock, placed by drive(). */
  take(h: Horse): void {
    this.hold(h, 'lead', TACK_LED);
    h.inStall = false;
  }

  /** Tied up where it stands (before the wagon, at the farrier's post): halter only, standing. */
  tie(h: Horse): void {
    this.hold(h, 'tied', TACK.halter);
    h.v = 0; h.travel = 1;
    h.act = this.rnd() < 0.5 ? 'stand' : 'doze';
  }

  /** Let loose inside the paddock gate: it wanders off to graze. */
  turnOut(h: Horse): void {
    this.letGo(h);
    h.inStall = false; h.tack = TACK.halter;
    const p = this.paddockPoint();
    this.walkTo(h, p.x, p.z, GAIT_SPEED.walk * 0.8, 'graze');
    h.actT = 30 + this.rnd() * 40;
  }

  /** Into its stall (the groom took it through the door). */
  stable(h: Horse): void {
    this.letGo(h);
    this.place(h, true);
  }

  /** A loose horse in the paddock comes to (x, z) (the groom at the gate) and stands. */
  call(h: Horse, x: number, z: number): void {
    if (h.held || h.inStall) return;
    this.walkTo(h, x, z, GAIT_SPEED.walk, 'stand');
    h.actT = 60;
  }

  /** Loose in the paddock (not held, not stalled). */
  loose(h: Horse): boolean { return !h.held && !h.inStall; }

  /** A point inside the paddock gate, `inside` m in, and the yaw facing out of it. */
  gate(inside: number): { x: number; z: number; yaw: number } | null {
    const f = this.paddock;
    if (!f) return null;
    return { ...f.world(0, -PADDOCK.hd + inside), yaw: f.yaw(0, -1) };
  }

  // ---------------------------------------------------------------- debug

  focus(what: string): { x: number; z: number } | null {
    if (what === 'stable') {
      const s = this.horses.find((h) => h.stall)?.stall;
      return s ? { x: s.x, z: s.z } : null;
    }
    return this.paddock ? { x: this.paddock.x, z: this.paddock.z } : null;
  }

  /** Back to their day: everyone re-placed for the hour. */
  endLineup(): void {
    this.lineup = null;
    for (const h of this.horses) h.fixed = null;
    this.lastHour = NaN;
  }

  /** Where the lineup stands: the open ground just off the paddock's gate side. */
  lineupSpot(): { x: number; z: number } {
    return this.paddock ? this.paddock.world(0, -PADDOCK.hd - 9) : { x: 0, z: 0 };
  }

  stats() {
    let drawn = 0, calls = 0;
    for (const d of this.draws.values()) { drawn += d.rig.mesh.count; if (d.rig.mesh.visible) calls++; }
    return {
      horses: this.horses.length, drawn, drawCalls: calls + (this.blobs.mesh.visible ? 1 : 0),
      updateMs: +this.updateMs.toFixed(3),
      list: this.horses.map((h) => ({ name: h.name, kind: h.kind, x: Math.round(h.x), z: Math.round(h.z), act: h.act,
        v: +h.v.toFixed(2), stall: h.inStall })),
    };
  }
}

/** __lublin.horses and the horses= hash (dev only). */
export function installHorseDebug(hs: Horses, snapTo: (x: number, z: number, zoom?: number) => void): void {
  const g = window as unknown as { __lublin?: Record<string, unknown> };
  if (g.__lublin) g.__lublin.horses = hs;
  const apply = () => {
    const params = new URLSearchParams(location.hash.slice(1));
    const v = params.get('horses');
    requestAnimationFrame(() => requestAnimationFrame(() => {
      hs.enabled = v !== 'off';
      if (!v || v === 'off') { if (hs.lineup) hs.endLineup(); return; }
      const [what, arg, zoom] = v.split(',');
      if (what === 'lineup') {
        const p = hs.lineupSpot();
        const gaits: GaitName[] = ['stand', 'walk', 'trot', 'canter'];
        const gait = (gaits.includes(arg as GaitName) ? arg : 'stand') as GaitName;
        const act = (['graze', 'drink', 'doze', 'eat'].includes(arg) ? arg : 'stand') as Act;
        hs.lineup = { x: p.x, z: p.z, gait, act };
        snapTo(p.x, p.z, zoom ? Number(zoom) : 12);
      } else {
        const p = hs.focus(what);
        if (p) snapTo(p.x, p.z, zoom ? Number(zoom) : what === 'stable' ? 14 : 30);
      }
    }));
  };
  window.addEventListener('hashchange', apply);
  apply();
}
