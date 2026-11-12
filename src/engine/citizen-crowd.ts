import * as THREE from 'three';
import type { Citizen } from '../types';

/**
 * Draws all citizens with one InstancedMesh per (archetype, mesh piece).
 *
 * Kit GLBs (build_characters.py `export_kit`) carry, per mesh node, extras
 * `part` (body/head/arm_L/arm_R/leg_L/leg_R) and `variant` ("" or "group:opt+group:opt"),
 * plus scene extras `kit` = JSON {pivots, groups, slots, anim}. Each citizen gets a
 * deterministic look from its id: one option per variant group, one palette colour per
 * Slot_* material. Parts swing about their pivots for walking and work loops.
 * Each frame only citizens in view are packed into the front of the instance buffers
 * (Slot holds each piece's tint so colours move with them); instance indices are not stable.
 * Legacy single-mesh GLBs (no extras) are drawn as one rigid `body` part.
 */

type Palette = [string, number, string][];
interface KitMeta {
  pivots: Record<string, [number, number]>;
  groups: Record<string, Record<string, [number, number]>>;
  slots: Record<string, Palette>;
  anim: { work: string };
}

const PARTS = ['body', 'head', 'arm_L', 'arm_R', 'leg_L', 'leg_R'] as const;
type PartIdx = number;

interface Piece {
  part: PartIdx;
  conds: [string, string][];
  geometry: THREE.BufferGeometry;
  material: THREE.Material;
  slot: string | null;
}

interface Archetype {
  name: string;
  meta: KitMeta | null;
  pieces: Piece[];
  pivots: [number, number][]; // per PartIdx: (y, z) in model space
}

interface Look {
  choices: Record<string, string>;
  colors: Record<string, THREE.Color>;
  girth: number;
  height: number;
}

/** One mesh piece a citizen wears: which InstancedMesh, which part it moves with, its tint. */
interface Slot {
  mesh: number;
  part: PartIdx;
  r: number;
  g: number;
  b: number;
}

interface Motion {
  yaw: number;
  phase: number;
  amp: number;
  px: number;
  pz: number;
}

const TIER: Record<string, string> = { plebeian: 'p', artisan: 'a', burgher: 'b', patrician: 'r' };
const STRIDE = 1.5; // metres per full gait cycle (two steps)
// Citizens whose bounding sphere misses the view are not drawn. The radius covers the
// figure plus its shadow reaching into the view from just off-screen.
const CULL_RADIUS = 3.5;

function hashId(id: string): number {
  let h = 2166136261;
  for (let i = 0; i < id.length; i++) h = Math.imul(h ^ id.charCodeAt(i), 16777619);
  return h >>> 0;
}

function mulberry32(seed: number): () => number {
  let a = seed;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function weighted<T>(items: [T, number][], rnd: number): T | null {
  const total = items.reduce((s, [, w]) => s + w, 0);
  if (total <= 0) return null;
  let r = rnd * total;
  for (const [v, w] of items) {
    r -= w;
    if (r < 0) return v;
  }
  return items[items.length - 1][0];
}

const _e = new THREE.Euler();
const _q = new THREE.Quaternion();
const _p = new THREE.Vector3();
const _s = new THREE.Vector3();
const _root = new THREE.Matrix4();
const _local = new THREE.Matrix4();
const _parts = PARTS.map(() => new THREE.Matrix4());
const _frustum = new THREE.Frustum();
const _viewProj = new THREE.Matrix4();
const _sphere = new THREE.Sphere(new THREE.Vector3(), CULL_RADIUS);

/** out = T(0,py,pz) * R(pitch about X, yaw about Y) * T(0,-py,-pz) */
function pivotRotation(out: THREE.Matrix4, py: number, pz: number, pitch: number, yaw: number): void {
  _e.set(pitch, yaw, 0, 'YXZ');
  out.makeRotationFromEuler(_e);
  const e = out.elements;
  e[12] = -(e[4] * py + e[8] * pz);
  e[13] = py - (e[5] * py + e[9] * pz);
  e[14] = pz - (e[6] * py + e[10] * pz);
}

export class CitizenCrowd {
  private archetypes = new Map<string, Archetype>();
  private meshes: THREE.InstancedMesh[] = [];
  private slots: Slot[][] = [];
  private motion: Motion[] = [];
  private builtFor: Citizen[] | null = null;
  private workAnim: string[] = [];
  private phaseOffset: number[] = [];
  private looks: { arch: Archetype; look: Look }[] = [];
  private posed: { ids: Set<string>; yaw: number; walk: boolean } | null = null;
  /** Per mesh: instances written this frame, and its matrix / colour arrays. */
  private buffers = { counts: new Int32Array(0), mats: [] as Float32Array[], cols: [] as Float32Array[] };

  /** Debug: hold these citizens at a fixed heading, optionally walking in place (lineups). */
  pose(ids: Set<string>, yaw: number, walk: boolean): void {
    this.posed = { ids, yaw, walk };
  }

  private scene: THREE.Scene;

  constructor(scene: THREE.Scene) {
    this.scene = scene;
  }

  addArchetype(name: string, template: THREE.Object3D): void {
    template.updateMatrixWorld(true);
    let meta: KitMeta | null = null;
    if (typeof template.userData?.kit === 'string') meta = JSON.parse(template.userData.kit) as KitMeta;
    const pivots = PARTS.map((p) => (meta?.pivots[p] ?? [0, 0]) as [number, number]);
    const pieces: Piece[] = [];
    template.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      if (!mesh.isMesh) return;
      let node: THREE.Object3D | null = mesh;
      while (node && node !== template && node.userData?.part === undefined) node = node.parent;
      const ud = node && node !== template ? node.userData : {};
      const part = Math.max(0, PARTS.indexOf((ud.part ?? 'body') as (typeof PARTS)[number]));
      const variant: string = ud.variant ?? '';
      const conds = variant
        ? variant.split('+').map((c) => c.split(':') as [string, string])
        : [];
      const material = mesh.material as THREE.Material;
      const slot = material.name.startsWith('Slot_') ? material.name.slice(5) : null;
      const geometry = mesh.geometry.clone().applyMatrix4(mesh.matrixWorld);
      pieces.push({ part, conds, geometry, material, slot });
    });
    this.archetypes.set(name, { name, meta, pieces, pivots });
    this.builtFor = null; // rebuild with the new archetype
  }

  /** Deterministic appearance of a citizen in a kit. */
  private look(c: Citizen, meta: KitMeta | null, rnd: () => number): Look {
    const female = c.gender === 'female';
    const age = rnd(); // < 0.2 young, > 0.8 old
    const choices: Record<string, string> = {};
    const colors: Record<string, THREE.Color> = {};
    if (meta) {
      const sexIdx = female ? 1 : 0;
      for (const [group, opts] of Object.entries(meta.groups)) {
        let pick = weighted(Object.entries(opts).map(([o, w]) => [o, w[sexIdx]]), rnd());
        if (group === 'beard' && age < 0.2) pick = 'none';
        if (group === 'hair' && age > 0.85 && !female && rnd() < 0.5) pick = 'bald';
        if (pick) choices[group] = pick;
      }
      const tier = TIER[c.wealthClass] ?? 'p';
      for (const [slot, palette] of Object.entries(meta.slots)) {
        const usable = palette.filter((e) => e[2].includes(tier));
        const hex = weighted((usable.length ? usable : palette).map((e) => [e[0], e[1]]), rnd()) ?? '#ffffff';
        colors[slot] = new THREE.Color(hex).offsetHSL(0, (rnd() - 0.5) * 0.06, (rnd() - 0.5) * 0.05);
      }
      if (age > 0.8) colors.hair = colors.hair_old ?? colors.hair;
    }
    const sexScale = female ? 0.94 : 1.0;
    const ageScale = age < 0.2 ? 0.96 : 1.0;
    return {
      choices,
      colors,
      girth: (0.94 + rnd() * 0.12) * (female ? 0.93 : 1.0),
      height: (0.95 + rnd() * 0.1) * sexScale * ageScale,
    };
  }

  private build(citizens: Citizen[], archetypeOf: (c: Citizen) => string): void {
    for (const m of this.meshes) {
      this.scene.remove(m);
      m.dispose();
    }
    this.meshes = [];
    this.slots = citizens.map(() => []);
    this.workAnim = [];
    this.phaseOffset = [];
    this.looks = [];

    // members[archetype][piece] = [citizen index, look]
    const members = new Map<Archetype, [number, Look][][]>();
    citizens.forEach((c, i) => {
      const arch = this.archetypes.get(archetypeOf(c));
      const rnd = mulberry32(hashId(c.id));
      this.phaseOffset[i] = rnd() * 100;
      if (!arch) return;
      const look = this.look(c, arch.meta, rnd);
      this.workAnim[i] = arch.meta?.anim.work ?? 'idle';
      if (!members.has(arch)) members.set(arch, arch.pieces.map(() => []));
      const lists = members.get(arch)!;
      arch.pieces.forEach((p, k) => {
        if (p.conds.every(([g, o]) => look.choices[g] === o)) lists[k].push([i, look]);
      });
      this.looks[i] = { arch, look };
    });

    const tint = new THREE.Color();
    for (const [arch, lists] of members) {
      arch.pieces.forEach((piece, k) => {
        const list = lists[k];
        if (!list.length) return;
        const mesh = new THREE.InstancedMesh(piece.geometry, piece.material, list.length);
        mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        mesh.frustumCulled = false;
        mesh.name = `${arch.name}:${PARTS[piece.part]}`;
        mesh.setColorAt(0, tint.set(0xffffff)); // allocates instanceColor; update() fills it
        const meshIdx = this.meshes.length;
        for (const [ci, look] of list) {
          if (piece.slot) {
            tint.set(0xffffff);
            const col = look.colors[piece.slot];
            if (col) tint.copy(col);
          } else {
            const v = 0.92 + ((ci * 2654435761) % 1000) / 1000 * 0.12; // grime / wear
            tint.setRGB(v, v, v);
          }
          this.slots[ci].push({ mesh: meshIdx, part: piece.part, r: tint.r, g: tint.g, b: tint.b });
        }
        this.scene.add(mesh);
        this.meshes.push(mesh);
      });
    }

    this.buffers = {
      counts: new Int32Array(this.meshes.length),
      mats: this.meshes.map((m) => m.instanceMatrix.array as Float32Array),
      cols: this.meshes.map((m) => m.instanceColor!.array as Float32Array),
    };
    this.motion = citizens.map((c, i) => this.motion[i] ?? {
      yaw: (this.phaseOffset[i] % 6.28),
      phase: 0,
      amp: 0,
      px: c.currentX ?? 0,
      pz: c.currentZ ?? 0,
    });
    this.builtFor = citizens;
  }

  /** Pose every citizen in view of `camera` and pack them into the instance buffers. */
  update(citizens: Citizen[], archetypeOf: (c: Citizen) => string, dt: number, now: number,
    camera: THREE.Camera): void {
    if (!this.archetypes.size) return;
    if (this.builtFor !== citizens) this.build(citizens, archetypeOf);
    const looks = this.looks;
    const k = Math.min(1, dt * 12);
    _frustum.setFromProjectionMatrix(_viewProj.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse));
    const { counts, mats, cols } = this.buffers;
    counts.fill(0);

    for (let i = 0; i < citizens.length; i++) {
      const slots = this.slots[i];
      if (!slots.length) continue;
      const c = citizens[i];
      const m = this.motion[i];
      const { arch, look } = looks[i];
      const x = c.currentX ?? 0;
      const z = c.currentZ ?? 0;
      const moved = Math.hypot(x - m.px, z - m.pz);
      m.px = x;
      m.pz = z;

      if (c.isMoving) {
        const dx = (c.targetX ?? x) - x;
        const dz = (c.targetZ ?? z) - z;
        if (Math.abs(dx) > 0.01 || Math.abs(dz) > 0.01) {
          let diff = Math.atan2(dx, dz) - m.yaw;
          diff = Math.atan2(Math.sin(diff), Math.cos(diff));
          m.yaw += diff * k;
        }
        if (moved < 3) m.phase += (moved / STRIDE) * Math.PI * 2;
      }
      let moving = !!c.isMoving;
      if (this.posed?.ids.has(c.id)) {
        m.yaw = this.posed.yaw;
        moving = this.posed.walk;
        if (moving) m.phase += dt * 1.3 / STRIDE * Math.PI * 2; // 1.3 m/s in place
      }
      m.amp += ((moving ? 1 : 0) - m.amp) * Math.min(1, dt * 6);

      _sphere.center.set(x, 0.9, z);
      if (!_frustum.intersectsSphere(_sphere)) continue;

      // Pose: angles in radians, negative pitch = swing forward.
      const t = now + this.phaseOffset[i];
      const s = Math.sin(m.phase) * m.amp;
      const female = look.choices.sex === 'f';
      const legAmp = female ? 0.3 : 0.4;
      let legL = -legAmp * s, legR = legAmp * s;
      let armL = 0.3 * s, armR = -0.3 * s;
      let headPitch = 0, headYaw = 0, lean = 0;
      let bob = 0.03 * (1 - Math.abs(Math.sin(m.phase))) * m.amp;
      const still = 1 - m.amp;
      if (still > 0.01) {
        const breathe = Math.sin(t * 2.2) * 0.03;
        let wl = breathe, wr = -breathe, hp = 0, hy = Math.sin(t * 0.37) * 0.35, ln = 0;
        if (c.state === 'WORKING') {
          const work = this.workAnim[i];
          if (work === 'hammer') {
            const u = (t / 1.25) % 1;
            wr = u < 0.7 ? -0.45 - 2.0 * Math.sin((u / 0.7) * Math.PI / 2) ** 2
                         : -2.45 + 1.75 * Math.min(1, (u - 0.7) / 0.1);
            wl = -0.8;
            hp = 0.3; hy = 0; ln = 0.08;
          } else if (work === 'scrape') {
            const sw = Math.sin(t * 2.6);
            wl = wr = -1.0 + 0.3 * sw;
            hp = 0.35; hy = 0; ln = 0.14 + 0.04 * sw;
          }
        }
        armL = armL * m.amp + wl * still;
        armR = armR * m.amp + wr * still;
        headPitch = hp * still;
        headYaw = hy * still;
        lean = ln * still;
        legL *= m.amp;
        legR *= m.amp;
        bob += Math.sin(t * 2.2) * 0.004 * still;
      }

      _e.set(0, m.yaw, s * 0.03, 'YXZ');
      _q.setFromEuler(_e);
      _p.set(x, bob, z);
      _s.set(look.girth, look.height, look.girth);
      _root.compose(_p, _q, _s);

      // The upper body leans at the hips; legs keep the feet planted.
      const pv = arch.pivots;
      pivotRotation(_local, pv[0][0], pv[0][1], lean, 0);
      _parts[0].multiplyMatrices(_root, _local);
      const angles: [number, number][] = [
        [0, 0], [headPitch, headYaw], [armL, 0], [armR, 0], [legL, 0], [legR, 0],
      ];
      for (let p = 1; p < PARTS.length; p++) {
        pivotRotation(_local, pv[p][0], pv[p][1], angles[p][0], angles[p][1]);
        _parts[p].multiplyMatrices(p >= 4 ? _root : _parts[0], _local);
      }
      for (const sl of slots) {
        const n = counts[sl.mesh]++;
        mats[sl.mesh].set(_parts[sl.part].elements, n * 16);
        const col = cols[sl.mesh];
        col[n * 3] = sl.r;
        col[n * 3 + 1] = sl.g;
        col[n * 3 + 2] = sl.b;
      }
    }
    this.meshes.forEach((mesh, j) => {
      mesh.count = counts[j];
      mesh.visible = counts[j] > 0;
      mesh.instanceMatrix.clearUpdateRanges();
      mesh.instanceMatrix.addUpdateRange(0, counts[j] * 16);
      mesh.instanceMatrix.needsUpdate = true;
      mesh.instanceColor!.clearUpdateRanges();
      mesh.instanceColor!.addUpdateRange(0, counts[j] * 3);
      mesh.instanceColor!.needsUpdate = true;
    });
  }
}
