import * as THREE from 'three';
import type { PlacedModel } from './static-batches';

/**
 * Doors and work spots of placed buildings, in world space.
 *
 * build_assets.py writes them per model as glTF scene extras ("anchors", a JSON string;
 * GLTFLoader puts it on the template's userData) in model space:
 *   doors: { p: sill centre on the outer wall face, n: outward normal, w: width,
 *            stair?: points from the stair foot (outside, on the ground) up to the landing }
 *   spots: { p, yaw (facing, atan2(dx, dz)), tag: work | sell | stand | guard }
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
}

export interface Spot { x: number; y: number; z: number; yaw: number; tag: string; taken: number }

export interface Building {
  name: string;
  parcelId?: string;
  x: number; y: number; z: number;
  doors: Door[];
  spots: Spot[];
}

interface RawAnchors {
  doors?: { p: number[]; n: number[]; w: number; stair?: number[][] }[];
  spots?: { p: number[]; yaw: number; tag: string }[];
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
    for (const pm of placed) {
      const raw = parse(pm.template.userData?.anchors);
      if (!raw) continue;
      const e = pm.matrix.elements;
      const dir = (x: number, z: number): [number, number] => {
        const wx = e[0] * x + e[8] * z, wz = e[2] * x + e[10] * z;
        const l = Math.hypot(wx, wz) || 1;
        return [wx / l, wz / l];
      };
      v.setFromMatrixPosition(pm.matrix);
      const b: Building = { name: pm.template.name, parcelId: pm.parcelId, x: v.x, y: v.y, z: v.z, doors: [], spots: [] };
      for (const d of raw.doors ?? []) {
        v.fromArray(d.p).applyMatrix4(pm.matrix);
        const [nx, nz] = dir(d.n[0], d.n[2]);
        const door: Door = {
          x: v.x, y: v.y, z: v.z, nx, nz, w: d.w,
          ax: v.x + nx * APPROACH, az: v.z + nz * APPROACH,
          ix: v.x - nx * INSIDE, iz: v.z - nz * INSIDE,
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
