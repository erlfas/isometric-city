import * as THREE from 'three';
import type { PlacedModel } from './static-batches';

/**
 * Doors and work spots of placed buildings, in world space.
 *
 * build_assets.py writes them per model as glTF scene extras ("anchors", a JSON string;
 * GLTFLoader puts it on the template's userData) in model space:
 *   doors: { p: sill centre on the outer wall face, n: outward normal, w: width, h: height,
 *            stair?: points from the stair foot (outside, on the ground) up to the landing }
 *   spots: { p, yaw (facing, atan2(dx, dz)), tag: work | sell | stand | guard }
 *   rooms, furniture, slots, ladders: the interior (houses and workshops; format in
 *            build_assets.py above PROPS). Slots and ladders go to the world here; rooms and
 *            furniture stay in model space (interiors.ts grids and draws them).
 * Here each placement's matrix takes them to the world.
 */

export interface Door {
  /** Sill centre on the outer face. */
  x: number; y: number; z: number;
  /** Outward unit normal (ground plane). */
  nx: number; nz: number;
  w: number;
  /** Where a route ends outside: in front of the door, or at the stair foot. */
  ax: number; az: number;
  /** Where people stand once inside (hidden there). */
  ix: number; iz: number;
  /** World stair polyline, foot first, ending at the landing in front of the door. */
  stair?: THREE.Vector3[];
  /** Opening height (the leaf and the dark doorway are drawn this tall). */
  h: number;
  // Runtime state, owned by simulation.ts (door leaves and sounds read it).
  /** 0 shut .. 1 open. */
  open: number;
  /** People passing through now; their direction (+1 in, -1 out); real s of the last pass. */
  users: number; dir: number; gateT: number;
  /** How many may walk through side by side (1 for a house door). */
  lanes: number;
  /** Agents waiting outside to go in; inside waiting to come out (they go first). */
  queue: number[]; exitQ: number[];
  /** s the door stays open after the last person. */
  hold: number;
  active: boolean;
  /** Held open regardless of people (debug hook `door=`). */
  pinned?: boolean;
}

export interface Spot { x: number; y: number; z: number; yaw: number; tag: string; taken: number }

/** One storey's floor. r and holes are model-space rectangles [minx, minz, maxx, maxz]. */
export interface Room { y: number; r: number[]; holes: number[][] }
/** A piece of furniture: model-space centre of its footprint, yaw, footprint w x d. */
export interface Furn { prop: string; p: number[]; yaw: number; room: number; w: number; d: number; h?: number }
/** A place a person uses (world space): lie in a bed, sit at a table, stand at a bench. */
export interface Slot {
  kind: 'sleep' | 'seat' | 'work' | 'hearth';
  pose: 'lie' | 'sit' | 'stand';
  x: number; y: number; z: number;
  /** Facing (for lie: from head to feet). */
  yaw: number;
  /** World point to walk to before taking the slot. */
  ax: number; az: number;
  room: number;
  taken: number;
}
/** Ladder from room `from` up to `to` (world points): foot -> top (same x z) -> off. */
export interface Ladder { from: number; to: number; foot: THREE.Vector3; top: THREE.Vector3; off: THREE.Vector3 }
export interface Interior {
  rooms: Room[]; furniture: Furn[]; slots: Slot[]; ladders: Ladder[];
  /** Placement matrix (model -> world) and its inverse. */
  matrix: THREE.Matrix4; inv: THREE.Matrix4;
}

export interface Building {
  name: string;
  /** Placement index (StaticBatches order): the cutaway hides and redraws it. */
  index: number;
  parcelId?: string;
  x: number; y: number; z: number;
  doors: Door[];
  spots: Spot[];
  /** Rooms, furniture and slots (houses and workshops, M6). */
  interior?: Interior;
}

interface RawAnchors {
  doors?: { p: number[]; n: number[]; w: number; h?: number; stair?: number[][] }[];
  spots?: { p: number[]; yaw: number; tag: string }[];
  rooms?: Room[];
  furniture?: { prop: string; p: number[]; yaw: number; room: number; s: number[]; h?: number }[];
  slots?: { k: Slot['kind']; pose: Slot['pose']; p: number[]; yaw: number; a: number[]; room: number }[];
  ladders?: { from: number; to: number; foot: number[]; top: number[]; off: number[] }[];
}

/** Schedule location ids that name a landmark rather than a parcel. */
export const LANDMARK_MODEL: Record<string, string> = {
  town_hall: 'town_hall',
  szmatruz: 'szmatruz',
  parish_fara: 'church_gothic',
  dominican_monastery: 'monastery_cloister',
  castle_donjon: 'castle_donjon',
  gate_krakow: 'gate_krakow',
  gate_grodzka: 'gate_grodzka',
};

const APPROACH = 1.1; // metres in front of the door
const INSIDE = 1.6;   // metres behind the wall face

export class BuildingIndex {
  readonly all: Building[] = [];
  readonly byParcel = new Map<string, Building>();
  readonly byModel = new Map<string, Building[]>();

  constructor(placed: PlacedModel[]) {
    const v = new THREE.Vector3();
    for (let index = 0; index < placed.length; index++) {
      const pm = placed[index];
      const raw = parse(pm.template.userData?.anchors);
      if (!raw) continue;
      const e = pm.matrix.elements;
      const dir = (x: number, z: number): [number, number] => {
        const wx = e[0] * x + e[8] * z, wz = e[2] * x + e[10] * z;
        const l = Math.hypot(wx, wz) || 1;
        return [wx / l, wz / l];
      };
      v.setFromMatrixPosition(pm.matrix);
      const b: Building = { name: pm.template.name, index, parcelId: pm.parcelId, x: v.x, y: v.y, z: v.z, doors: [], spots: [] };
      for (const d of raw.doors ?? []) {
        v.fromArray(d.p).applyMatrix4(pm.matrix);
        const [nx, nz] = dir(d.n[0], d.n[2]);
        const door: Door = {
          x: v.x, y: v.y, z: v.z, nx, nz, w: d.w, h: d.h ?? 2.1,
          ax: v.x + nx * APPROACH, az: v.z + nz * APPROACH,
          ix: v.x - nx * INSIDE, iz: v.z - nz * INSIDE,
          open: 0, users: 0, dir: 0, gateT: -1e9, lanes: d.w >= 2.4 ? 3 : d.w >= 1.4 ? 2 : 1,
          queue: [], exitQ: [], hold: 0, active: false,
        };
        if (d.stair?.length) {
          door.stair = d.stair.map((s) => new THREE.Vector3().fromArray(s).applyMatrix4(pm.matrix));
          door.ax = door.stair[0].x;
          door.az = door.stair[0].z;
        }
        b.doors.push(door);
      }
      for (const s of raw.spots ?? []) {
        v.fromArray(s.p).applyMatrix4(pm.matrix);
        const [fx, fz] = dir(Math.sin(s.yaw), Math.cos(s.yaw));
        b.spots.push({ x: v.x, y: v.y, z: v.z, yaw: Math.atan2(fx, fz), tag: s.tag, taken: 0 });
      }
      if (raw.rooms?.length) {
        const w = (p: number[]) => new THREE.Vector3().fromArray(p).applyMatrix4(pm.matrix);
        const slots: Slot[] = (raw.slots ?? []).map((s) => {
          v.fromArray(s.p).applyMatrix4(pm.matrix);
          const [fx, fz] = dir(Math.sin(s.yaw), Math.cos(s.yaw));
          const a = w([s.a[0], s.p[1], s.a[1]]);
          return { kind: s.k, pose: s.pose, x: v.x, y: v.y, z: v.z, yaw: Math.atan2(fx, fz), ax: a.x, az: a.z,
            room: s.room, taken: 0 };
        });
        b.interior = {
          rooms: raw.rooms,
          furniture: (raw.furniture ?? []).map((f) => ({ prop: f.prop, p: f.p, yaw: f.yaw, room: f.room, w: f.s[0], d: f.s[1], h: f.h })),
          slots,
          ladders: (raw.ladders ?? []).map((l) => ({ from: l.from, to: l.to, foot: w(l.foot), top: w(l.top), off: w(l.off) })),
          matrix: pm.matrix,
          inv: pm.matrix.clone().invert(),
        };
      }
      this.all.push(b);
      if (pm.parcelId) this.byParcel.set(pm.parcelId, b);
      let list = this.byModel.get(b.name);
      if (!list) this.byModel.set(b.name, (list = []));
      list.push(b);
    }
  }

  /** Building a schedule location id refers to (parcel id or landmark id), if any. */
  resolve(location: string): Building | undefined {
    const model = LANDMARK_MODEL[location];
    if (model) return this.byModel.get(model)?.[0];
    return this.byParcel.get(location);
  }

  /** Every point the navigation grid must treat as outside (flood-fill seeds). */
  seeds(): { x: number; z: number }[] {
    const out: { x: number; z: number }[] = [];
    for (const b of this.all) {
      for (const d of b.doors) out.push({ x: d.ax, z: d.az });
      for (const s of b.spots) out.push({ x: s.x, z: s.z });
    }
    return out;
  }
}

function parse(a: unknown): RawAnchors | null {
  if (!a) return null;
  if (typeof a === 'string') {
    try { return JSON.parse(a) as RawAnchors; } catch { return null; }
  }
  return a as RawAnchors;
}
