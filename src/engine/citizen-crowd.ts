import * as THREE from 'three';
import type { Citizen } from '../types';
import { WORK_ANIMS, type WorkAnim, type WorkPose } from './work-anims';

/**
 * Draws all citizens with one InstancedMesh per (archetype, body part): 14 kits x 6 parts.
 *
 * Kit GLBs (build_characters.py `export_kit`) carry, per mesh node, extras
 * `part` (body/head/arm_L/arm_R/leg_L/leg_R) and `variant` ("" or "group:opt+group:opt"),
 * plus scene extras `kit` = JSON {pivots, groups, slots, anim}. Each citizen gets a
 * deterministic look from its id: one option per variant group, one palette colour per
 * Slot_* material. Parts swing about their pivots for walking and work loops.
 *
 * Merging: every mesh of a part (all variants, all materials) is baked into one geometry with
 * per-vertex base colour, roughness, metalness, slot column and variant index. Per instance:
 * the part matrix, the citizen's row in `slotTex` (its slot colours) and a bitmask of the
 * variants it wears; the vertex shader collapses triangles of variants it does not wear, in
 * the colour and the shadow pass alike. Each frame only citizens in view are packed into the
 * front of the instance buffers; instance indices are not stable.
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

/** Columns of slotTex: one per slot of a kit, the last holds the citizen's wear tint. */
const SLOT_COLS = 32;
const GRIME_COL = SLOT_COLS - 1;
/** Variants per part: two 24-bit words per instance (floats hold 24-bit integers exactly). */
const MAX_VARIANTS = 48;

interface PartBatch {
  part: PartIdx;
  geometry: THREE.BufferGeometry;
  variants: [string, string][][]; // per variant index: its conditions
}

interface Archetype {
  name: string;
  meta: KitMeta | null;
  batches: PartBatch[];
  pivots: [number, number][]; // per PartIdx: (y, z) in model space
}

interface Look {
  choices: Record<string, string>;
  colors: Record<string, THREE.Color>;
  girth: number;
  height: number;
}

interface Motion {
  yaw: number;
  phase: number;
  amp: number;
  px: number;
  pz: number;
}

/** One instanced mesh and its per-instance buffers. */
interface Batch {
  mesh: THREE.InstancedMesh;
  part: PartIdx;
  mats: Float32Array;
  cits: Float32Array;
  masks: Float32Array;
  count: number;
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
const _pose: WorkPose = { armL: 0, armR: 0, headPitch: 0, headYaw: 0, lean: 0 };

/** out = T(0,py,pz) * R(pitch about X, yaw about Y) * T(0,-py,-pz) */
function pivotRotation(out: THREE.Matrix4, py: number, pz: number, pitch: number, yaw: number): void {
  _e.set(pitch, yaw, 0, 'YXZ');
  out.makeRotationFromEuler(_e);
  const e = out.elements;
  e[12] = -(e[4] * py + e[8] * pz);
  e[13] = py - (e[5] * py + e[9] * pz);
  e[14] = pz - (e[6] * py + e[10] * pz);
}

// --- shaders ------------------------------------------------------------------------

const VERTEX_HEAD = /* glsl */ `
attribute float aSlot;
attribute float aVariant;
attribute float aRough;
attribute float aMetal;
attribute float iCitizen;
attribute vec2 iMask;
bool crowdWorn() {
  if (aVariant < 0.0) return true;
  int v = int(aVariant + 0.5);
  int word = v < 24 ? int(iMask.x) : int(iMask.y);
  return ((word >> (v < 24 ? v : v - 24)) & 1) == 1;
}
`;
const COLLAPSE = '\nif (!crowdWorn()) transformed = vec3(0.0);';

function injectCrowd(shader: THREE.WebGLProgramParametersWithUniforms, slotTex: { value: THREE.Texture | null }, colour: boolean): void {
  shader.uniforms.uSlotTex = slotTex;
  let vs = VERTEX_HEAD + (colour ? 'uniform sampler2D uSlotTex;\nvarying float vRough;\nvarying float vMetal;\n' : '') + shader.vertexShader;
  vs = vs.replace('#include <begin_vertex>', '#include <begin_vertex>' + COLLAPSE);
  if (colour) {
    vs = vs.replace('#include <color_vertex>', `#include <color_vertex>
{
  int col = aSlot < 0.0 ? ${GRIME_COL} : int(aSlot + 0.5);
  vColor.rgb *= texelFetch(uSlotTex, ivec2(col, int(iCitizen + 0.5)), 0).rgb;
}
vRough = aRough;
vMetal = aMetal;`);
    shader.fragmentShader = 'varying float vRough;\nvarying float vMetal;\n' + shader.fragmentShader
      .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\nroughnessFactor = vRough;')
      .replace('#include <metalnessmap_fragment>', '#include <metalnessmap_fragment>\nmetalnessFactor = vMetal;');
  }
  shader.vertexShader = vs;
}

export class CitizenCrowd {
  private archetypes = new Map<string, Archetype>();
  private batches: Batch[] = [];
  /** Per citizen: per PartIdx its batch index (-1 = none) and variant mask words. */
  private wear: { batch: Int32Array; mask: Float32Array }[] = [];
  private motion: Motion[] = [];
  private builtFor: Citizen[] | null = null;
  private workAnim: (WorkAnim | null)[] = [];
  private phaseOffset: number[] = [];
  private looks: ({ arch: Archetype; look: Look } | undefined)[] = [];
  private posed: { ids: Set<string>; yaw: number; walk: boolean } | null = null;

  private slotTex = { value: null as THREE.DataTexture | null };
  private material: THREE.MeshStandardMaterial;
  private depthMaterial: THREE.MeshDepthMaterial;

  /** Triangles submitted for citizens last frame, one pass (the shadow pass draws them again).
   *  Includes the collapsed triangles of variants a citizen does not wear. */
  drawnTriangles(): number {
    let t = 0;
    for (const b of this.batches) {
      const g = b.mesh.geometry;
      t += b.mesh.count * (g.index ? g.index.count : g.attributes.position.count) / 3;
    }
    return t;
  }

  /** Debug: hold these citizens at a fixed heading, optionally walking in place (lineups). */
  pose(ids: Set<string>, yaw: number, walk: boolean): void {
    this.posed = { ids, yaw, walk };
  }

  private scene: THREE.Scene;

  constructor(scene: THREE.Scene) {
    this.scene = scene;
    this.material = new THREE.MeshStandardMaterial({ vertexColors: true, side: THREE.DoubleSide });
    this.material.onBeforeCompile = (s) => injectCrowd(s, this.slotTex, true);
    this.material.customProgramCacheKey = () => 'citizen-crowd';
    this.depthMaterial = new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking, side: THREE.DoubleSide });
    this.depthMaterial.onBeforeCompile = (s) => injectCrowd(s, this.slotTex, false);
    this.depthMaterial.customProgramCacheKey = () => 'citizen-crowd-depth';
  }

  addArchetype(name: string, template: THREE.Object3D): void {
    template.updateMatrixWorld(true);
    let meta: KitMeta | null = null;
    if (typeof template.userData?.kit === 'string') meta = JSON.parse(template.userData.kit) as KitMeta;
    const pivots = PARTS.map((p) => (meta?.pivots[p] ?? [0, 0]) as [number, number]);
    const slotNames = Object.keys(meta?.slots ?? {});

    // Gather every mesh by part, then bake each part into one geometry.
    const byPart = PARTS.map(() => [] as { mesh: THREE.Mesh; variant: string }[]);
    template.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      if (!mesh.isMesh) return;
      let node: THREE.Object3D | null = mesh;
      while (node && node !== template && node.userData?.part === undefined) node = node.parent;
      const ud = node && node !== template ? node.userData : {};
      const part = Math.max(0, PARTS.indexOf((ud.part ?? 'body') as (typeof PARTS)[number]));
      byPart[part].push({ mesh, variant: ud.variant ?? '' });
    });

    const batches: PartBatch[] = [];
    byPart.forEach((list, part) => {
      if (!list.length) return;
      const variantIdx = new Map<string, number>();
      for (const { variant } of list) if (variant && !variantIdx.has(variant)) variantIdx.set(variant, variantIdx.size);
      if (variantIdx.size > MAX_VARIANTS) {
        throw new Error(`${name}.${PARTS[part]}: ${variantIdx.size} variants (max ${MAX_VARIANTS})`);
      }
      const pos: number[] = [], nrm: number[] = [], col: number[] = [];
      const slot: number[] = [], vari: number[] = [], rough: number[] = [], metal: number[] = [];
      const index: number[] = [];
      for (const { mesh, variant } of list) {
        const g = mesh.geometry.clone().applyMatrix4(mesh.matrixWorld);
        const m = mesh.material as THREE.MeshStandardMaterial;
        const s = m.name.startsWith('Slot_') ? slotNames.indexOf(m.name.slice(5)) : -1;
        if (s >= GRIME_COL) throw new Error(`${name}: more than ${GRIME_COL} colour slots`);
        const v = variant ? variantIdx.get(variant)! : -1;
        const base = pos.length / 3;
        const p = g.attributes.position, n = g.attributes.normal;
        for (let i = 0; i < p.count; i++) {
          pos.push(p.getX(i), p.getY(i), p.getZ(i));
          nrm.push(n.getX(i), n.getY(i), n.getZ(i));
          col.push(m.color.r, m.color.g, m.color.b);
          slot.push(s);
          vari.push(v);
          rough.push(m.roughness);
          metal.push(m.metalness);
        }
        if (g.index) for (let i = 0; i < g.index.count; i++) index.push(base + g.index.getX(i));
        else for (let i = 0; i < p.count; i++) index.push(base + i);
        g.dispose();
      }
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
      geometry.setAttribute('normal', new THREE.Float32BufferAttribute(nrm, 3));
      geometry.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
      geometry.setAttribute('aSlot', new THREE.Float32BufferAttribute(slot, 1));
      geometry.setAttribute('aVariant', new THREE.Float32BufferAttribute(vari, 1));
      geometry.setAttribute('aRough', new THREE.Float32BufferAttribute(rough, 1));
      geometry.setAttribute('aMetal', new THREE.Float32BufferAttribute(metal, 1));
      geometry.setIndex(index);
      const variants = [...variantIdx.keys()].map((v) => v.split('+').map((c) => c.split(':') as [string, string]));
      batches.push({ part, geometry, variants });
    });
    this.archetypes.set(name, { name, meta, batches, pivots });
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
    for (const b of this.batches) {
      this.scene.remove(b.mesh);
      b.mesh.dispose();
    }
    this.batches = [];
    this.workAnim = [];
    this.phaseOffset = [];
    this.looks = [];

    // One batch per (archetype, part), sized for every citizen of the archetype.
    const members = new Map<Archetype, number>();
    citizens.forEach((c, i) => {
      const arch = this.archetypes.get(archetypeOf(c));
      const rnd = mulberry32(hashId(c.id));
      this.phaseOffset[i] = rnd() * 100;
      if (!arch) return;
      this.looks[i] = { arch, look: this.look(c, arch.meta, rnd) };
      this.workAnim[i] = WORK_ANIMS[arch.meta?.anim.work ?? ''] ?? null;
      members.set(arch, (members.get(arch) ?? 0) + 1);
    });
    const batchOf = new Map<Archetype, number[]>(); // per PartIdx
    for (const [arch, n] of members) {
      const idx = PARTS.map(() => -1);
      for (const pb of arch.batches) {
        const geometry = pb.geometry.clone();
        const cits = new Float32Array(n);
        const masks = new Float32Array(n * 2);
        geometry.setAttribute('iCitizen', new THREE.InstancedBufferAttribute(cits, 1).setUsage(THREE.DynamicDrawUsage));
        geometry.setAttribute('iMask', new THREE.InstancedBufferAttribute(masks, 2).setUsage(THREE.DynamicDrawUsage));
        const mesh = new THREE.InstancedMesh(geometry, this.material, n);
        mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        mesh.customDepthMaterial = this.depthMaterial;
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        mesh.frustumCulled = false;
        mesh.name = `${arch.name}:${PARTS[pb.part]}`;
        this.scene.add(mesh);
        idx[pb.part] = this.batches.length;
        this.batches.push({ mesh, part: pb.part, mats: mesh.instanceMatrix.array as Float32Array, cits, masks, count: 0 });
      }
      batchOf.set(arch, idx);
    }

    // Per citizen: which variants it wears per part, and its colours in slotTex.
    const tex = new Float32Array(SLOT_COLS * Math.max(1, citizens.length) * 4);
    this.wear = citizens.map((_, i) => {
      const entry = this.looks[i];
      const batch = new Int32Array(PARTS.length).fill(-1);
      const mask = new Float32Array(PARTS.length * 2);
      if (!entry) return { batch, mask };
      const { arch, look } = entry;
      batch.set(batchOf.get(arch)!);
      for (const pb of arch.batches) {
        let lo = 0, hi = 0;
        pb.variants.forEach((conds, v) => {
          if (!conds.every(([g, o]) => look.choices[g] === o)) return;
          if (v < 24) lo |= 1 << v; else hi |= 1 << (v - 24);
        });
        mask[pb.part * 2] = lo;
        mask[pb.part * 2 + 1] = hi;
      }
      const row = i * SLOT_COLS * 4;
      Object.keys(arch.meta?.slots ?? {}).forEach((slot, s) => {
        const col = look.colors[slot];
        tex.set(col ? [col.r, col.g, col.b, 1] : [1, 1, 1, 1], row + s * 4);
      });
      const v = 0.92 + ((i * 2654435761) % 1000) / 1000 * 0.12; // grime / wear on fixed materials
      tex.set([v, v, v, 1], row + GRIME_COL * 4);
      return { batch, mask };
    });
    this.slotTex.value?.dispose();
    const dt = new THREE.DataTexture(tex, SLOT_COLS, Math.max(1, citizens.length), THREE.RGBAFormat, THREE.FloatType);
    dt.needsUpdate = true;
    this.slotTex.value = dt;

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
    const batches = this.batches;
    const k = Math.min(1, dt * 12);
    _frustum.setFromProjectionMatrix(_viewProj.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse));
    for (const b of batches) b.count = 0;

    for (let i = 0; i < citizens.length; i++) {
      const entry = looks[i];
      if (!entry) continue;
      const c = citizens[i];
      const m = this.motion[i];
      const { arch, look } = entry;
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
        const w = _pose;
        w.armL = breathe; w.armR = -breathe; w.headPitch = 0; w.headYaw = Math.sin(t * 0.37) * 0.35; w.lean = 0;
        if (c.state === 'WORKING' || c.state === 'PATROLLING') this.workAnim[i]?.(t, w); // guards work by patrolling
        armL = armL * m.amp + w.armL * still;
        armR = armR * m.amp + w.armR * still;
        headPitch = w.headPitch * still;
        headYaw = w.headYaw * still;
        lean = w.lean * still;
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
      const wear = this.wear[i];
      for (let p = 0; p < PARTS.length; p++) {
        const bi = wear.batch[p];
        if (bi < 0) continue;
        const b = batches[bi];
        const n = b.count++;
        b.mats.set(_parts[p].elements, n * 16);
        b.cits[n] = i;
        b.masks[n * 2] = wear.mask[p * 2];
        b.masks[n * 2 + 1] = wear.mask[p * 2 + 1];
      }
    }
    for (const b of batches) {
      const n = b.count;
      b.mesh.count = n;
      b.mesh.visible = n > 0;
      b.mesh.instanceMatrix.clearUpdateRanges();
      b.mesh.instanceMatrix.addUpdateRange(0, n * 16);
      b.mesh.instanceMatrix.needsUpdate = true;
      for (const [name, size] of [['iCitizen', 1], ['iMask', 2]] as const) {
        const a = b.mesh.geometry.attributes[name] as THREE.InstancedBufferAttribute;
        a.clearUpdateRanges();
        a.addUpdateRange(0, n * size);
        a.needsUpdate = true;
      }
    }
  }
}
