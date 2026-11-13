import * as THREE from 'three';
import type { Citizen } from '../types';
import { WORK_ANIMS, type WorkAnim, type WorkPose } from './work-anims';

/**
 * Draws all citizens, at two levels of detail.
 *
 * Kit GLBs (build_characters.py `export_kit`) carry, per mesh node, extras
 * `part` (body/head/arm_L/arm_R/leg_L/leg_R), `variant` ("" or "group:opt+group:opt") and
 * `lod` (absent = full detail, 1 = decimated twin for distant zoom), plus scene extras
 * `kit` = JSON {pivots, groups, slots, anim}. Each citizen gets a deterministic look from
 * its id: one option per variant group, one palette colour per Slot_* material. Every
 * mesh of a (part, variant), all materials merged, is baked with per-vertex base colour,
 * roughness, metalness and slot column; slot colours come from `slotTex` (row = citizen).
 *
 * Near (LOD0, figure >= LOD_OUT_PX tall): one BatchedMesh per kit. A citizen owns one
 * instance per piece it WEARS (its part's base piece plus the variants it chose), so unworn
 * clothing never reaches the GPU; instances of a part share that part's posed matrix and
 * the instance colour carries the citizen's slotTex row. Few citizens fit in a near view,
 * which matters: in WebGL a multi-draw is one GPU draw per instance (ANGLE loops it).
 *
 * Far (LOD1, figure < LOD_IN_PX tall): one InstancedMesh per (kit, part) holding every LOD1
 * variant of the part; the vertex shader collapses variants a citizen does not wear
 * (per-instance bitmask). A constant ~84 instanced draws however many citizens are in view
 * (the batched path cost 10 ms for the ~1,000 of a whole-city view), and the collapsed
 * triangles of decimated parts are cheap. Far citizens cast no shadow-map shadow; they get
 * a blob shadow. Culling is per citizen (one sphere).
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
/** Far variants per part: two 24-bit words per instance (floats hold 24-bit integers exactly). */
const MAX_VARIANTS = 48;

/** Near path: one (part, variant) mesh of a kit. */
interface PieceSrc {
  part: PartIdx;
  conds: [string, string][] | null; // null = base piece, always worn
  geometry: THREE.BufferGeometry;
}

/** Far path: one part of a kit with all its variants (aVariant per vertex, -1 = base). */
interface FarSrc {
  part: PartIdx;
  geometry: THREE.BufferGeometry;
  variants: [string, string][][]; // per variant index: its conditions
}

interface Archetype {
  name: string;
  meta: KitMeta | null;
  pieces: PieceSrc[];
  far: FarSrc[];
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
  /** 0 walk .. 1 run: blends stride, lean and arm swing. */
  run: number;
  px: number;
  pz: number;
}

interface KitBatch {
  mesh: THREE.BatchedMesh;
  tris: number[]; // per piece index
}

interface FarBatch {
  mesh: THREE.InstancedMesh;
  mats: Float32Array;
  cits: Float32Array;
  masks: Float32Array;
  count: number;
  tris: number;
}

/** One citizen's draw data on both paths. */
interface Wear {
  kit: KitBatch | null;
  inst: Int32Array; // near: instance ids in kit.mesh
  part: Uint8Array; // near: PartIdx per instance
  piece: Int32Array; // near: piece index per instance
  shown: boolean; // near: instances currently visible
  far: Int32Array; // far: per PartIdx its batch index (-1 = none)
  mask: Float32Array; // far: per PartIdx two variant mask words
}

const TIER: Record<string, string> = { plebeian: 'p', artisan: 'a', burgher: 'b', patrician: 'r' };
const STRIDE = 1.5; // metres per full gait cycle (two steps) at a walk
const RUN_STRIDE = 2.4; // ... at a run
// Citizens whose bounding sphere misses the view are not drawn. The radius covers the
// figure plus its shadow reaching into the view from just off-screen.
const CULL_RADIUS = 3.5;
/** Figure height on screen (px) below which citizens use the far path, and above which they
 *  return to the near one (hysteresis so zooming near the edge does not flicker). */
const LOD_IN_PX = 36;
const LOD_OUT_PX = 44;
const FIGURE_M = 1.75;
/** Bench height (m), and how far a lying figure's back is below its pivot after tipping. */
const SEAT_H = 0.45;
const LIE_BACK = 0.12;

export function hashId(id: string): number {
  let h = 2166136261;
  for (let i = 0; i < id.length; i++) h = Math.imul(h ^ id.charCodeAt(i), 16777619);
  return h >>> 0;
}

export function mulberry32(seed: number): () => number {
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
const _row = new THREE.Color();
const _blob = new THREE.Matrix4();

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

const VERTEX_ATTRS = 'attribute float aSlot;\nattribute float aRough;\nattribute float aMetal;\n' +
  'uniform sampler2D uSlotTex;\nvarying float vRough;\nvarying float vMetal;\n';

/** <color_vertex> for both paths: base colour times the citizen's slot colour. */
const colorVertex = (row: string) => /* glsl */ `
vColor = vec4( color, 1.0 );
{
  int col = aSlot < 0.0 ? ${GRIME_COL} : int( aSlot + 0.5 );
  vColor.rgb *= texelFetch( uSlotTex, ivec2( col, int( ${row} + 0.5 ) ), 0 ).rgb;
}
vRough = aRough;
vMetal = aMetal;
`;

/** Far path: variants a citizen does not wear collapse to a point. */
const FAR_HEAD = /* glsl */ `
attribute float aVariant;
attribute float iCitizen;
attribute vec2 iMask;
bool crowdWorn() {
  if (aVariant < 0.0) return true;
  int v = int(aVariant + 0.5);
  int word = v < 24 ? int(iMask.x) : int(iMask.y);
  return ((word >> (v < 24 ? v : v - 24)) & 1) == 1;
}
`;

function injectCrowd(shader: THREE.WebGLProgramParametersWithUniforms, slotTex: { value: THREE.Texture | null }, far: boolean): void {
  shader.uniforms.uSlotTex = slotTex;
  // Near: the batch's instance colour is not a tint, its red channel is the slotTex row.
  const row = far ? 'iCitizen' : 'getBatchingColor( getIndirectIndex( gl_DrawID ) ).r';
  let vs = shader.vertexShader.replace('#include <color_vertex>', colorVertex(row));
  if (far) vs = FAR_HEAD + vs.replace('#include <begin_vertex>', '#include <begin_vertex>\nif (!crowdWorn()) transformed = vec3(0.0);');
  shader.vertexShader = VERTEX_ATTRS + vs;
  shader.fragmentShader = 'varying float vRough;\nvarying float vMetal;\n' + shader.fragmentShader
    .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\nroughnessFactor = vRough;')
    .replace('#include <metalnessmap_fragment>', '#include <metalnessmap_fragment>\nmetalnessFactor = vMetal;');
}

/** Bake meshes into one geometry with the crowd's vertex attributes; variantOf gives each
 *  mesh's far-path variant index (omit for the near path: no aVariant attribute). */
function bake(list: THREE.Mesh[], slotNames: string[], kitName: string,
  variantOf?: (m: THREE.Mesh) => number): THREE.BufferGeometry | null {
  const pos: number[] = [], nrm: number[] = [], col: number[] = [];
  const slot: number[] = [], vari: number[] = [], rough: number[] = [], metal: number[] = [];
  const index: number[] = [];
  for (const mesh of list) {
    const g = mesh.geometry.clone().applyMatrix4(mesh.matrixWorld);
    const m = mesh.material as THREE.MeshStandardMaterial;
    const s = m.name.startsWith('Slot_') ? slotNames.indexOf(m.name.slice(5)) : -1;
    if (s >= GRIME_COL) throw new Error(`${kitName}: more than ${GRIME_COL} colour slots`);
    const v = variantOf?.(mesh) ?? -1;
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
  if (!index.length) return null;
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geometry.setAttribute('normal', new THREE.Float32BufferAttribute(nrm, 3));
  geometry.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  geometry.setAttribute('aSlot', new THREE.Float32BufferAttribute(slot, 1));
  if (variantOf) geometry.setAttribute('aVariant', new THREE.Float32BufferAttribute(vari, 1));
  geometry.setAttribute('aRough', new THREE.Float32BufferAttribute(rough, 1));
  geometry.setAttribute('aMetal', new THREE.Float32BufferAttribute(metal, 1));
  geometry.setIndex(index);
  return geometry;
}

export class CitizenCrowd {
  private archetypes = new Map<string, Archetype>();
  private kits = new Map<Archetype, KitBatch>();
  private farBatches: FarBatch[] = [];
  private wear: Wear[] = [];
  private motion: Motion[] = [];
  private builtFor: Citizen[] | null = null;
  private workAnim: (WorkAnim | null)[] = [];
  private phaseOffset: number[] = [];
  private looks: ({ arch: Archetype; look: Look } | undefined)[] = [];
  private posed: { ids: Set<string>; yaw: number; walk: boolean } | null = null;
  private lod = 0;
  private lastTris = 0;
  private lastShown = 0;

  private slotTex = { value: null as THREE.DataTexture | null };
  private nearMaterial: THREE.MeshStandardMaterial;
  private farMaterial: THREE.MeshStandardMaterial;
  private blobs: THREE.InstancedMesh | null = null;

  /** Triangles submitted for citizens last frame, one pass (near citizens are drawn again
   *  in the shadow pass; far ones cast no shadow-map shadow). Far triangles include the
   *  collapsed ones of variants a citizen does not wear. */
  drawnTriangles(): number {
    return this.lastTris;
  }

  /** Debug: detail level, citizens drawn last frame, triangles per pass. */
  stats(): { lod: number; drawn: number; triangles: number } {
    return { lod: this.lod, drawn: this.lastShown, triangles: this.lastTris };
  }

  /** Debug: hold these citizens at a fixed heading, optionally walking in place (lineups). */
  pose(ids: Set<string>, yaw: number, walk: boolean): void {
    this.posed = { ids, yaw, walk };
  }

  private scene: THREE.Scene;

  constructor(scene: THREE.Scene) {
    this.scene = scene;
    this.nearMaterial = new THREE.MeshStandardMaterial({ vertexColors: true, side: THREE.DoubleSide });
    this.nearMaterial.onBeforeCompile = (s) => injectCrowd(s, this.slotTex, false);
    this.nearMaterial.customProgramCacheKey = () => 'citizen-crowd-near';
    this.farMaterial = new THREE.MeshStandardMaterial({ vertexColors: true, side: THREE.DoubleSide });
    this.farMaterial.onBeforeCompile = (s) => injectCrowd(s, this.slotTex, true);
    this.farMaterial.customProgramCacheKey = () => 'citizen-crowd-far';
  }

  addArchetype(name: string, template: THREE.Object3D): void {
    template.updateMatrixWorld(true);
    let meta: KitMeta | null = null;
    if (typeof template.userData?.kit === 'string') meta = JSON.parse(template.userData.kit) as KitMeta;
    const pivots = PARTS.map((p) => (meta?.pivots[p] ?? [0, 0]) as [number, number]);
    const slotNames = Object.keys(meta?.slots ?? {});

    // Gather meshes by (part, variant) and level of detail.
    const groups = new Map<string, { part: PartIdx; variant: string; meshes: [THREE.Mesh[], THREE.Mesh[]] }>();
    template.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      if (!mesh.isMesh) return;
      let node: THREE.Object3D | null = mesh;
      while (node && node !== template && node.userData?.part === undefined) node = node.parent;
      const ud = node && node !== template ? node.userData : {};
      const part = Math.max(0, PARTS.indexOf((ud.part ?? 'body') as (typeof PARTS)[number]));
      const variant: string = ud.variant ?? '';
      const lod = ud.lod === 1 ? 1 : 0;
      const key = `${part}|${variant}`;
      let g = groups.get(key);
      if (!g) groups.set(key, (g = { part, variant, meshes: [[], []] }));
      g.meshes[lod].push(mesh);
    });

    const pieces: PieceSrc[] = [];
    const farMeshes = PARTS.map(() => [] as { mesh: THREE.Mesh; variant: string }[]);
    for (const { part, variant, meshes } of groups.values()) {
      const geometry = bake(meshes[0], slotNames, name);
      if (!geometry) continue;
      const conds = variant ? variant.split('+').map((c) => c.split(':') as [string, string]) : null;
      pieces.push({ part, conds, geometry });
      // Legacy GLBs without LOD1 draw full detail on the far path too.
      for (const mesh of meshes[1].length ? meshes[1] : meshes[0]) farMeshes[part].push({ mesh, variant });
    }

    const far: FarSrc[] = [];
    farMeshes.forEach((list, part) => {
      if (!list.length) return;
      const variantIdx = new Map<string, number>();
      for (const { variant } of list) if (variant && !variantIdx.has(variant)) variantIdx.set(variant, variantIdx.size);
      if (variantIdx.size > MAX_VARIANTS) {
        throw new Error(`${name}.${PARTS[part]}: ${variantIdx.size} variants (max ${MAX_VARIANTS})`);
      }
      const byMesh = new Map(list.map(({ mesh, variant }) => [mesh, variant ? variantIdx.get(variant)! : -1]));
      const geometry = bake(list.map((l) => l.mesh), slotNames, name, (m) => byMesh.get(m)!);
      if (!geometry) return;
      const variants = [...variantIdx.keys()].map((v) => v.split('+').map((c) => c.split(':') as [string, string]));
      far.push({ part, geometry, variants });
    });

    this.archetypes.set(name, { name, meta, pieces, far, pivots });
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
    for (const k of this.kits.values()) {
      this.scene.remove(k.mesh);
      k.mesh.dispose();
    }
    for (const b of this.farBatches) {
      this.scene.remove(b.mesh);
      b.mesh.dispose();
    }
    this.kits.clear();
    this.farBatches = [];
    this.workAnim = [];
    this.phaseOffset = [];
    this.looks = [];

    // Looks first: a kit batch is sized for exactly the pieces its citizens wear.
    const worn: number[][] = [];
    const sizes = new Map<Archetype, number>();
    const members = new Map<Archetype, number>();
    citizens.forEach((c, i) => {
      const arch = this.archetypes.get(archetypeOf(c));
      const rnd = mulberry32(hashId(c.id));
      this.phaseOffset[i] = rnd() * 100;
      worn[i] = [];
      if (!arch) return;
      const look = this.look(c, arch.meta, rnd);
      this.looks[i] = { arch, look };
      this.workAnim[i] = WORK_ANIMS[arch.meta?.anim.work ?? ''] ?? null;
      arch.pieces.forEach((pc, k) => {
        if (!pc.conds || pc.conds.every(([g, o]) => look.choices[g] === o)) worn[i].push(k);
      });
      sizes.set(arch, (sizes.get(arch) ?? 0) + worn[i].length);
      members.set(arch, (members.get(arch) ?? 0) + 1);
    });

    // Near: one BatchedMesh per kit.
    for (const [arch, instances] of sizes) {
      let verts = 0, idx = 0;
      for (const pc of arch.pieces) {
        verts += pc.geometry.attributes.position.count;
        idx += pc.geometry.index!.count;
      }
      const mesh = new THREE.BatchedMesh(instances, verts, idx, this.nearMaterial);
      mesh.perObjectFrustumCulled = false; // culled per citizen in update()
      mesh.sortObjects = false;
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      mesh.frustumCulled = false;
      mesh.name = arch.name;
      for (const pc of arch.pieces) mesh.addGeometry(pc.geometry);
      this.scene.add(mesh);
      this.kits.set(arch, { mesh, tris: arch.pieces.map((pc) => pc.geometry.index!.count / 3) });
    }

    // Far: one InstancedMesh per (kit, part), sized for every citizen of the kit.
    const farOf = new Map<Archetype, number[]>(); // per PartIdx
    for (const [arch, n] of members) {
      const idx = PARTS.map(() => -1);
      for (const fs of arch.far) {
        const geometry = fs.geometry.clone();
        const cits = new Float32Array(n);
        const masks = new Float32Array(n * 2);
        geometry.setAttribute('iCitizen', new THREE.InstancedBufferAttribute(cits, 1).setUsage(THREE.DynamicDrawUsage));
        geometry.setAttribute('iMask', new THREE.InstancedBufferAttribute(masks, 2).setUsage(THREE.DynamicDrawUsage));
        const mesh = new THREE.InstancedMesh(geometry, this.farMaterial, n);
        mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        mesh.castShadow = false;
        mesh.receiveShadow = true;
        mesh.frustumCulled = false;
        mesh.visible = false;
        mesh.name = `${arch.name}:${PARTS[fs.part]}:far`;
        this.scene.add(mesh);
        idx[fs.part] = this.farBatches.length;
        this.farBatches.push({ mesh, mats: mesh.instanceMatrix.array as Float32Array, cits, masks, count: 0,
          tris: geometry.index!.count / 3 });
      }
      farOf.set(arch, idx);
    }

    // Per citizen: near instances (row in the instance colour), far batch and masks, and
    // its colours in slotTex.
    const tex = new Float32Array(SLOT_COLS * Math.max(1, citizens.length) * 4);
    this.wear = citizens.map((_, i) => {
      const entry = this.looks[i];
      const far = new Int32Array(PARTS.length).fill(-1);
      const mask = new Float32Array(PARTS.length * 2);
      if (!entry) {
        return { kit: null, inst: new Int32Array(0), part: new Uint8Array(0), piece: new Int32Array(0), shown: false, far, mask };
      }
      const { arch, look } = entry;
      const kit = this.kits.get(arch)!;
      const ks = worn[i];
      const w: Wear = { kit, inst: new Int32Array(ks.length), part: new Uint8Array(ks.length), piece: new Int32Array(ks.length),
        shown: false, far, mask };
      _row.setRGB(i, 0, 0);
      ks.forEach((k, j) => {
        const id = kit.mesh.addInstance(k);
        kit.mesh.setColorAt(id, _row);
        kit.mesh.setVisibleAt(id, false);
        w.inst[j] = id;
        w.part[j] = arch.pieces[k].part;
        w.piece[j] = k;
      });
      far.set(farOf.get(arch)!);
      for (const fs of arch.far) {
        let lo = 0, hi = 0;
        fs.variants.forEach((conds, v) => {
          if (!conds.every(([g, o]) => look.choices[g] === o)) return;
          if (v < 24) lo |= 1 << v; else hi |= 1 << (v - 24);
        });
        mask[fs.part * 2] = lo;
        mask[fs.part * 2 + 1] = hi;
      }
      const row = i * SLOT_COLS * 4;
      Object.keys(arch.meta?.slots ?? {}).forEach((slot, s) => {
        const col = look.colors[slot];
        tex.set(col ? [col.r, col.g, col.b, 1] : [1, 1, 1, 1], row + s * 4);
      });
      const v = 0.92 + ((i * 2654435761) % 1000) / 1000 * 0.12; // grime / wear on fixed materials
      tex.set([v, v, v, 1], row + GRIME_COL * 4);
      return w;
    });
    this.slotTex.value?.dispose();
    const dt = new THREE.DataTexture(tex, SLOT_COLS, Math.max(1, citizens.length), THREE.RGBAFormat, THREE.FloatType);
    dt.needsUpdate = true;
    this.slotTex.value = dt;

    if (!this.blobs) {
      const disc = new THREE.CircleGeometry(0.42, 10).rotateX(-Math.PI / 2);
      const mat = new THREE.MeshBasicMaterial({ color: 0x140f0a, transparent: true, opacity: 0.32, depthWrite: false });
      this.blobs = new THREE.InstancedMesh(disc, mat, Math.max(1, citizens.length));
      this.blobs.frustumCulled = false;
      this.blobs.renderOrder = 1;
      this.blobs.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      this.blobs.count = 0;
      this.scene.add(this.blobs);
    }

    this.motion = citizens.map((c, i) => this.motion[i] ?? {
      yaw: (this.phaseOffset[i] % 6.28),
      phase: 0,
      amp: 0,
      run: 0,
      px: c.currentX ?? 0,
      pz: c.currentZ ?? 0,
    });
    this.lod = 0;
    this.builtFor = citizens;
  }

  private setLod(lod: number): void {
    this.lod = lod;
    for (const k of this.kits.values()) k.mesh.visible = lod === 0;
    if (lod === 0) for (const b of this.farBatches) b.mesh.visible = false;
    if (lod === 1 && this.blobs) this.blobs.visible = true;
    if (lod === 0 && this.blobs) this.blobs.visible = false;
  }

  /** Pose every citizen in view of `camera` and write their instances. viewportPx: canvas
   *  height in CSS pixels (for the detail level). */
  update(citizens: Citizen[], archetypeOf: (c: Citizen) => string, dt: number, now: number,
    camera: THREE.OrthographicCamera, viewportPx: number): void {
    if (!this.archetypes.size) return;
    if (this.builtFor !== citizens) this.build(citizens, archetypeOf);
    const looks = this.looks;
    const k = Math.min(1, dt * 12);
    _frustum.setFromProjectionMatrix(_viewProj.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse));

    const figurePx = FIGURE_M * viewportPx * camera.zoom / Math.max(1e-6, camera.top - camera.bottom);
    if (this.lod === 0 && figurePx < LOD_IN_PX) this.setLod(1);
    else if (this.lod === 1 && figurePx > LOD_OUT_PX) this.setLod(0);
    const far = this.lod === 1;
    const farBatches = this.farBatches;
    for (const b of farBatches) b.count = 0;
    let nBlobs = 0, tris = 0, shown = 0;

    for (let i = 0; i < citizens.length; i++) {
      const entry = looks[i];
      if (!entry) continue;
      const c = citizens[i];
      const w = this.wear[i];
      const m = this.motion[i];
      const { arch, look } = entry;
      const x = c.currentX ?? 0;
      const z = c.currentZ ?? 0;
      const y = c.y ?? 0;
      const moved = Math.hypot(x - m.px, z - m.pz);
      m.px = x;
      m.pz = z;

      // Face the way the citizen actually moves (velocity), else toward its target.
      let moving = !!c.isMoving && !c.hidden;
      if (moving) {
        let dx = c.vx ?? 0, dz = c.vz ?? 0;
        if (Math.abs(dx) + Math.abs(dz) < 1e-3) {
          dx = (c.targetX ?? x) - x;
          dz = (c.targetZ ?? z) - z;
        }
        if (Math.abs(dx) > 0.01 || Math.abs(dz) > 0.01) {
          let diff = Math.atan2(dx, dz) - m.yaw;
          diff = Math.atan2(Math.sin(diff), Math.cos(diff));
          m.yaw += diff * k;
        }
        const speed = moved / Math.max(dt, 1e-3);
        const runT = c.gait ?? THREE.MathUtils.clamp((speed - 2.2) / 1.3, 0, 1);
        m.run += (runT - m.run) * Math.min(1, dt * 5);
        const stride = (STRIDE + (RUN_STRIDE - STRIDE) * m.run) * (c.strideScale ?? 1);
        if (moved < 3) m.phase += (moved / stride) * Math.PI * 2;
      } else if (c.faceYaw !== undefined) {
        let diff = c.faceYaw - m.yaw;
        diff = Math.atan2(Math.sin(diff), Math.cos(diff));
        m.yaw += diff * k;
      }
      if (this.posed?.ids.has(c.id)) {
        m.yaw = this.posed.yaw;
        moving = this.posed.walk;
        if (moving) m.phase += dt * 1.3 / STRIDE * Math.PI * 2; // 1.3 m/s in place
      }
      m.amp += ((moving ? 1 : 0) - m.amp) * Math.min(1, dt * 6);

      _sphere.center.set(x, y + 0.9, z);
      const visible = !c.hidden && _frustum.intersectsSphere(_sphere);
      const nearShown = visible && !far;
      if (nearShown !== w.shown && w.kit) {
        w.shown = nearShown;
        for (let j = 0; j < w.inst.length; j++) w.kit.mesh.setVisibleAt(w.inst[j], nearShown);
      }
      if (!visible) continue;
      shown++;

      // Pose: angles in radians, negative pitch = swing forward.
      const t = now + this.phaseOffset[i];
      const s = Math.sin(m.phase) * m.amp;
      const female = look.choices.sex === 'f';
      const run = m.run * m.amp;
      const legAmp = (female ? 0.3 : 0.4) + 0.45 * run;
      let legL = -legAmp * s, legR = legAmp * s;
      const armAmp = 0.3 + 0.55 * run;
      let armL = armAmp * s, armR = -armAmp * s;
      let headPitch = 0, headYaw = 0, lean = -0.22 * run;
      let bob = (0.03 + 0.05 * run) * (1 - Math.abs(Math.sin(m.phase))) * m.amp;
      if (c.stepBob) bob += c.stepBob;
      const still = 1 - m.amp;
      if (still > 0.01) {
        const breathe = Math.sin(t * 2.2) * 0.03;
        const wp = _pose;
        wp.armL = breathe; wp.armR = -breathe; wp.headPitch = 0; wp.headYaw = Math.sin(t * 0.37) * 0.35; wp.lean = 0;
        const anim = c.activityAnim ?? (c.state === 'WORKING' || c.state === 'PATROLLING' ? 'work' : 'idle');
        if (anim === 'work') this.workAnim[i]?.(t, wp);
        armL = armL * m.amp + wp.armL * still;
        armR = armR * m.amp + wp.armR * still;
        headPitch = wp.headPitch * still;
        headYaw = wp.headYaw * still;
        lean = lean * m.amp + wp.lean * still;
        legL *= m.amp;
        legR *= m.amp;
        bob += Math.sin(t * 2.2) * 0.004 * still;
      }

      // Lying in bed / sitting at a table (indoors, M6): only while standing still.
      const pose = m.amp < 0.05 ? c.pose : undefined;
      let rise = 0, pitch = 0;
      if (pose === 'lie') {
        // Tipped onto the back about the feet: the head goes away from the facing.
        pitch = -Math.PI / 2;
        legL = legR = armL = armR = headPitch = headYaw = lean = 0;
        bob = LIE_BACK;
      } else if (pose === 'sit') {
        // Thighs forward (the legs are one piece: they stick out under the table), hips on
        // the seat, forearms toward the table.
        legL = legR = -1.45;
        armL = -0.45 + armL * 0.3; armR = -0.4 + armR * 0.3;
        lean = 0.04;
        rise = SEAT_H - arch.pivots[4][0] * look.height;
      }
      _e.set(pitch, m.yaw, pose ? 0 : s * 0.03, 'YXZ');
      _q.setFromEuler(_e);
      _p.set(x, y + bob + rise, z);
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

      if (far) {
        if (this.blobs) {
          _blob.makeTranslation(x, y + 0.03, z);
          this.blobs.setMatrixAt(nBlobs++, _blob);
        }
        for (let p = 0; p < PARTS.length; p++) {
          const bi = w.far[p];
          if (bi < 0) continue;
          const b = farBatches[bi];
          const n = b.count++;
          b.mats.set(_parts[p].elements, n * 16);
          b.cits[n] = i;
          b.masks[n * 2] = w.mask[p * 2];
          b.masks[n * 2 + 1] = w.mask[p * 2 + 1];
          tris += b.tris;
        }
      } else if (w.kit) {
        const mesh = w.kit.mesh;
        const ktris = w.kit.tris;
        for (let j = 0; j < w.inst.length; j++) {
          mesh.setMatrixAt(w.inst[j], _parts[w.part[j]]);
          tris += ktris[w.piece[j]];
        }
      }
    }

    if (far) {
      for (const b of farBatches) {
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
    if (this.blobs) {
      this.blobs.count = nBlobs;
      this.blobs.visible = nBlobs > 0;
      if (nBlobs) {
        this.blobs.instanceMatrix.clearUpdateRanges();
        this.blobs.instanceMatrix.addUpdateRange(0, nBlobs * 16);
        this.blobs.instanceMatrix.needsUpdate = true;
      }
    }
    this.lastTris = tris;
    this.lastShown = shown;
  }
}
