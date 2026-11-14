import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import type { CityPlan, Citizen } from '../types';
import { riverFrames, type RiverFrame } from './river-course';
import { flowSpeed, type RiverWater } from './river';
import { nightFactor } from './door-leaves';

/**
 * Wildlife on the Bystrzyca: red deer that come out of the woods to drink at dawn and dusk,
 * and mallards on the water by day.
 *
 * Deer: a few herds (stag, hinds, a fawn), each with a cover spot in the woods, a forest-edge
 * spot and a drinking place on the bank, chosen at runtime from plan.vegetation and the river
 * (so they follow the forest when it is regenerated): a bank point with open ground behind it,
 * away from paths, bridges, the mill and houses, and a dense patch of trees 15-70 m back on the
 * same side. In the dawn and dusk windows (sim hour) a herd walks to the edge, stops and looks,
 * walks to the bank, drinks (heads down, muzzle ripples, looking up now and then), grazes, and
 * returns to cover, where it lies up. A citizen within FLIGHT m sends the herd bounding back.
 *
 * Ducks: mallard pairs and a duck with a line of ducklings, each group on its own stretch:
 * paddling upstream against the current, drifting back, dabbling tail-up, preening, a wing
 * stretch now and then; at night they sit on the bank. A V-wake decal follows each duck on the
 * water (own instanced draw, so the river's 16 ripple rings are kept for dabbles and muzzles).
 *
 * Drawing: models from build_animals.py (one mesh per rigid part, pivots in the GLB). Each
 * animal is one geometry with a part id per vertex; one InstancedMesh per animal kind, and
 * the vertex shader swings the parts about their pivots from 16 pose channels per instance
 * (part hierarchy in RIGS). No shadow-map shadows (moving casters would redraw the map): a soft
 * blob under each animal on land. Motion runs on real time (also while the sim is paused, like
 * the water); the schedule on sim hours. Out of view (+ margin) nothing is drawn or posed.
 *
 * Debug: __lublin.wildlife (.stats(), .force(state, herd), .focus(name)); hash
 * `deer=drink|graze|emerge|flee|rest[,herd[,zoom]]`, `ducks=family|pair[,zoom]`,
 * `wild=lineup[,pose]` (installWildlifeDebug).
 */

// ------------------------------------------------------------------ tuning

const DAWN: [number, number] = [5.2, 8.0];
const DUSK: [number, number] = [18.2, 21.0];
const DUCK_DAY: [number, number] = [5.6, 20.4];
/** A citizen this close (m) startles a herd that is out; half of it one lying up in cover. */
const FLIGHT = 25;
const WALK = 0.85, BOUND = 6.5;
const DUCK_BOOST = 1.35; // ducks drawn larger than life (a mallard is 0.6 m)
const VIEW_MARGIN = 12;

// ------------------------------------------------------------------ rigs

type Kind = 'deer_stag' | 'deer_hind' | 'deer_fawn' | 'duck_drake' | 'duck_hen' | 'duck_ling';
const KINDS: Kind[] = ['deer_stag', 'deer_hind', 'deer_fawn', 'duck_drake', 'duck_hen', 'duck_ling'];

/** Pose channels (16 per instance). Deer: */
const NECK = 0, NECK_YAW = 1, HEAD = 2, HEAD_YAW = 3, LEG_U = 4, LEG_L = 8, EAR_L = 12, EAR_R = 13, TAIL = 14;
/** Ducks: head pitch/yaw, wing lift (roll). */
const D_HEAD = 0, D_HEAD_YAW = 1, WING_L = 2, WING_R = 3;

/** Per part: [pitch channel, yaw channel, roll channel, parent part] (-1 = none). Legs F/B L/R. */
const DEER_RIG: Record<string, [number, number, number, string]> = {
  body: [-1, -1, -1, ''], neck: [NECK, NECK_YAW, -1, ''], head: [HEAD, HEAD_YAW, -1, 'neck'],
  ear_L: [EAR_L, -1, -1, 'head'], ear_R: [EAR_R, -1, -1, 'head'],
  legU_FL: [LEG_U, -1, -1, ''], legU_FR: [LEG_U + 1, -1, -1, ''], legU_BL: [LEG_U + 2, -1, -1, ''], legU_BR: [LEG_U + 3, -1, -1, ''],
  legL_FL: [LEG_L, -1, -1, 'legU_FL'], legL_FR: [LEG_L + 1, -1, -1, 'legU_FR'],
  legL_BL: [LEG_L + 2, -1, -1, 'legU_BL'], legL_BR: [LEG_L + 3, -1, -1, 'legU_BR'],
  tail: [TAIL, -1, -1, ''],
};
const DUCK_RIG: Record<string, [number, number, number, string]> = {
  body: [-1, -1, -1, ''], head: [D_HEAD, D_HEAD_YAW, -1, ''], wing_L: [-1, -1, WING_L, ''], wing_R: [-1, -1, WING_R, ''],
};

const VERT_PARS = /* glsl */`
#define NPART 14
attribute float aPart;
attribute vec4 iP0; attribute vec4 iP1; attribute vec4 iP2; attribute vec4 iP3;
uniform vec3 uPiv[NPART];
uniform vec4 uCfg[NPART];
vec3 wRX(vec3 v, float a) { float c = cos(a), s = sin(a); return vec3(v.x, v.y * c - v.z * s, v.y * s + v.z * c); }
vec3 wRY(vec3 v, float a) { float c = cos(a), s = sin(a); return vec3(v.x * c + v.z * s, v.y, -v.x * s + v.z * c); }
vec3 wRZ(vec3 v, float a) { float c = cos(a), s = sin(a); return vec3(v.x * c - v.y * s, v.x * s + v.y * c, v.z); }
float wChan(float fi) {
  int i = int(fi + 0.5);
  vec4 q = i < 4 ? iP0 : i < 8 ? iP1 : i < 12 ? iP2 : iP3;
  int j = i - (i / 4) * 4;
  return j == 0 ? q.x : j == 1 ? q.y : j == 2 ? q.z : q.w;
}
void wPose(inout vec3 p, inout vec3 n) {
  int k = int(aPart + 0.5);
  for (int lv = 0; lv < 4; lv++) {
    if (k < 0) break;
    vec4 c = uCfg[k];
    vec3 o = uPiv[k];
    float a = c.x >= 0.0 ? wChan(c.x) : 0.0;
    float b = c.y >= 0.0 ? wChan(c.y) : 0.0;
    float r = c.z >= 0.0 ? wChan(c.z) : 0.0;
    p = wRY(wRX(wRZ(p - o, r), a), b) + o;
    n = wRY(wRX(wRZ(n, r), a), b);
    k = int(c.w + (c.w < 0.0 ? -0.5 : 0.5));
  }
}
`;

const BLOB_VERT = /* glsl */`
attribute vec4 iBlob;  // x, z, radius, alpha
attribute vec2 iDir;   // heading (cos, sin) in x-z
varying vec2 vUv; varying float vA;
void main() {
  vUv = position.xz; vA = iBlob.w;
  vec2 q = vec2(position.x * 0.62, position.z * 1.0) * iBlob.z * 2.0;
  vec2 w = vec2(q.x * iDir.y + q.y * iDir.x, -q.x * iDir.x + q.y * iDir.y);
  vec3 wp = vec3(iBlob.x + w.x, 0.04, iBlob.y + w.y);
  gl_Position = projectionMatrix * viewMatrix * vec4(wp, 1.0);
}`;
const BLOB_FRAG = /* glsl */`
varying vec2 vUv; varying float vA;
void main() {
  float r = length(vUv) * 2.0;
  float a = smoothstep(1.0, 0.15, r) * vA;
  if (a < 0.004) discard;
  gl_FragColor = vec4(0.04, 0.05, 0.03, a);
}`;

/** Wake decal: quad in duck space, x across, z = metres behind the duck (scaled). */
const WAKE_VERT = /* glsl */`
attribute vec4 iWake;  // x, z, strength, size
attribute vec2 iDir;   // heading (cos, sin): forward = (sin, cos) as yaw
varying vec2 vUv; varying float vA;
void main() {
  vec2 q = vec2(position.x, position.z) * iWake.w;
  vUv = vec2(position.x, position.z);
  vA = iWake.z;
  // duck forward f = (iDir.y, iDir.x) as (x, z); right r = (iDir.x, -iDir.y); behind = -f
  vec2 f = vec2(iDir.y, iDir.x), rr = vec2(iDir.x, -iDir.y);
  vec2 w = rr * q.x - f * q.y;
  gl_Position = projectionMatrix * viewMatrix * vec4(iWake.x + w.x, 0.045, iWake.y + w.y, 1.0);
}`;
const WAKE_FRAG = /* glsl */`
uniform float uTime; uniform vec3 uCol;
varying vec2 vUv; varying float vA;
void main() {
  float b = vUv.y, a = abs(vUv.x);
  float arm = 0.1 + max(b, 0.0) * 0.36;
  float d = a - arm;
  float wav = 0.55 + 0.45 * sin(b * 16.0 - uTime * 5.0 - a * 4.0);
  float env = smoothstep(-0.12, 0.25, b) * exp(-max(b, 0.0) * 0.75);
  // bright crest on the arm, a darker trough just outside it (reads on pale and dark water)
  float crest = exp(-d * d * 90.0) * env * wav;
  float trough = exp(-(d - 0.09) * (d - 0.09) * 140.0) * env * 0.8;
  // the little bow wave and the ring of disturbed water round the body
  float r = length(vec2(vUv.x * 1.3, vUv.y + 0.02));
  float r1 = (r - 0.16) * 14.0, r2 = (r - 0.24) * 16.0;
  crest += exp(-r1 * r1) * 0.55;
  trough += exp(-r2 * r2) * 0.3;
  float lb = crest * vA, ld = trough * vA;
  float al = lb + ld;
  if (al < 0.006) discard;
  vec3 col = (uCol * lb + vec3(0.08, 0.12, 0.14) * ld) / al;
  gl_FragColor = vec4(col, min(0.65, al * 0.6));
}`;

// ------------------------------------------------------------------ state

interface Animal {
  kind: Kind;
  x: number; z: number; y: number; yaw: number; pitch: number; roll: number;
  scale: number; tint: THREE.Color;
  ch: Float32Array;   // pose channels now
  vis: boolean;
  blob: number;       // blob shadow radius (0 = none)
  wake: number;       // wake strength (0 = none)
  seed: number;
}

type DeerAct = 'stand' | 'walk' | 'graze' | 'drink' | 'alert' | 'bound' | 'lie';
interface Deer extends Animal {
  herd: Herd; role: 'stag' | 'hind' | 'fawn'; mother: Deer | null; idx: number;
  tx: number; tz: number; tyaw: number | null; v: number; phase: number; gait: number;
  act: DeerAct; actT: number; bout: number; head: number; lie: number;
  look: number; lookT: number; earT: [number, number]; tailT: number; dipT: number;
  slot: { x: number; z: number; yaw: number }; rest: { x: number; z: number };
  arrived: boolean;
}

type HerdState = 'rest' | 'emerge' | 'edge' | 'bank' | 'drink' | 'graze' | 'return' | 'flee';
interface Spot {
  bank: { x: number; z: number; nx: number; nz: number; i: number; side: number };
  edge: { x: number; z: number }; cover: { x: number; z: number }; score: number;
}
interface Herd {
  deer: Deer[]; spot: Spot; state: HerdState; t: number; restT: number; scare: number;
  start: number; win: number; threat: { x: number; z: number } | null; out: number;
}

type DuckAct = 'paddle' | 'drift' | 'dabble' | 'preen' | 'flap' | 'follow' | 'rest' | 'land';
interface Duck extends Animal {
  group: DuckGroup; lead: Duck | null; gap: number; side: number;
  s: number; u: number; tu: number; vx: number; vz: number;
  act: DuckAct; actT: number; dab: number; dabT: number; flap: number; bob: number;
  hint: number; rest: { x: number; z: number; yaw: number }; onBank: number; rippleT: number;
}
interface DuckGroup { ducks: Duck[]; leader: Duck; s0: number; s1: number; restS: number; restSide: number; name: string; night: boolean }

interface Draw {
  mesh: THREE.InstancedMesh; p: THREE.InstancedBufferAttribute[]; cap: number; list: Animal[];
}

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

export class Wildlife {
  public herds: Herd[] = [];
  public groups: DuckGroup[] = [];
  /** Debug: hold the herds in this state (deer=drink), null = live. */
  public hold: HerdState | null = null;
  /** Debug lineup (wild=lineup): all six kinds in a row at this point, in this pose. */
  public lineup: { x: number; z: number; pose: string } | null = null;
  /** Debug (wild=off, for perf.mjs before/after): nothing updated or drawn. */
  public enabled = true;

  private rnd = mulberry32(1392 * 7);
  private frames: RiverFrame[] = [];
  private cum: Float64Array = new Float64Array(0);
  private river: RiverWater | null;
  private deer: Deer[] = [];
  private ducks: Duck[] = [];
  private draws = new Map<Kind, Draw>();
  private blobGeo = new THREE.InstancedBufferGeometry();
  private blobMesh: THREE.Mesh;
  private blobAttr: THREE.InstancedBufferAttribute;
  private blobDir: THREE.InstancedBufferAttribute;
  private wakeGeo = new THREE.InstancedBufferGeometry();
  private wakeMesh: THREE.Mesh;
  private wakeAttr: THREE.InstancedBufferAttribute;
  private wakeDir: THREE.InstancedBufferAttribute;
  private uTime = { value: 0 };
  private lastHour = NaN;
  private last = -1;
  private scareT = 0;
  private rippleBudget = 0;
  private view = [0, 0, 0, 0];
  private updateMs = 0;
  private trees: { x: number; z: number }[] = [];
  private m4 = new THREE.Matrix4();
  private q = new THREE.Quaternion();
  private e = new THREE.Euler(0, 0, 0, 'YXZ');
  private p = new THREE.Vector3();
  private sc = new THREE.Vector3();
  private stat = { scares: 0, drinks: 0 };
  private loaded = false;

  private scene: THREE.Scene;

  constructor(scene: THREE.Scene, plan: CityPlan, river: RiverWater | null) {
    this.scene = scene;
    this.river = river;
    if (plan.river && plan.river.points.length > 1) {
      this.frames = riverFrames(plan.river);
      const f = this.frames;
      this.cum = new Float64Array(f.length);
      for (let i = 1; i < f.length; i++) this.cum[i] = this.cum[i - 1] + Math.hypot(f[i].x - f[i - 1].x, f[i].z - f[i - 1].z);
      this.placeHerds(plan);
      this.placeDucks(plan);
    }
    const quad = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
    const n = Math.max(1, this.deer.length + this.ducks.length);
    this.blobGeo.index = quad.index;
    this.blobGeo.setAttribute('position', quad.getAttribute('position'));
    this.blobAttr = new THREE.InstancedBufferAttribute(new Float32Array(n * 4), 4).setUsage(THREE.DynamicDrawUsage);
    this.blobDir = new THREE.InstancedBufferAttribute(new Float32Array(n * 2), 2).setUsage(THREE.DynamicDrawUsage);
    this.blobGeo.setAttribute('iBlob', this.blobAttr);
    this.blobGeo.setAttribute('iDir', this.blobDir);
    this.blobGeo.instanceCount = 0;
    this.blobMesh = new THREE.Mesh(this.blobGeo, new THREE.ShaderMaterial({
      vertexShader: BLOB_VERT, fragmentShader: BLOB_FRAG, transparent: true, depthWrite: false,
    }));
    this.blobMesh.frustumCulled = false;
    this.blobMesh.renderOrder = 1;
    this.blobMesh.visible = false;
    this.blobMesh.name = 'wildlife_blobs';
    scene.add(this.blobMesh);

    // Wake: quad x -1.3..1.3 across, z -0.4..3.6 behind (duck sizes).
    const wq = new THREE.PlaneGeometry(2.6, 4, 1, 1).rotateX(-Math.PI / 2).translate(0, 0, 1.6);
    this.wakeGeo.index = wq.index;
    this.wakeGeo.setAttribute('position', wq.getAttribute('position'));
    const nd = Math.max(1, this.ducks.length);
    this.wakeAttr = new THREE.InstancedBufferAttribute(new Float32Array(nd * 4), 4).setUsage(THREE.DynamicDrawUsage);
    this.wakeDir = new THREE.InstancedBufferAttribute(new Float32Array(nd * 2), 2).setUsage(THREE.DynamicDrawUsage);
    this.wakeGeo.setAttribute('iWake', this.wakeAttr);
    this.wakeGeo.setAttribute('iDir', this.wakeDir);
    this.wakeGeo.instanceCount = 0;
    this.wakeMesh = new THREE.Mesh(this.wakeGeo, new THREE.ShaderMaterial({
      vertexShader: WAKE_VERT, fragmentShader: WAKE_FRAG, transparent: true, depthWrite: false, side: THREE.DoubleSide,
      uniforms: { uTime: this.uTime, uCol: { value: new THREE.Color(0xdde6e6) } },
    }));
    this.wakeMesh.frustumCulled = false;
    this.wakeMesh.renderOrder = 2;
    this.wakeMesh.visible = false;
    this.wakeMesh.name = 'wildlife_wakes';
    scene.add(this.wakeMesh);
    void this.load();
  }

  // ---------------------------------------------------------------- models

  private async load(): Promise<void> {
    const loader = new GLTFLoader();
    await Promise.all(KINDS.map(async (kind) => {
      const list = [...this.deer, ...this.ducks].filter((a) => a.kind === kind);
      if (!list.length) return;
      try {
        const gltf = await loader.loadAsync(`/models/animal_${kind}.glb`);
        this.draws.set(kind, this.makeDraw(kind, gltf, list));
      } catch (e) {
        console.warn(`[wildlife] animal_${kind}.glb`, e);
      }
    }));
    this.loaded = true;
  }

  private makeDraw(kind: Kind, gltf: { scene: THREE.Object3D }, list: Animal[]): Draw {
    const meta = JSON.parse((gltf.scene.userData as { animal?: string }).animal ?? '{"pivots":{}}') as { pivots: Record<string, number[]> };
    const rig = kind.startsWith('deer') ? DEER_RIG : DUCK_RIG;
    const names = Object.keys(rig);
    const geos: THREE.BufferGeometry[] = [];
    gltf.scene.updateMatrixWorld(true);
    gltf.scene.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh) return;
      let part: string | undefined;
      for (let p: THREE.Object3D | null = o; p && !part; p = p.parent) part = (p.userData as { part?: string }).part;
      const k = names.indexOf(part ?? 'body');
      const g = mesh.geometry.clone().applyMatrix4(mesh.matrixWorld);
      const mat = mesh.material as THREE.MeshStandardMaterial;
      const n = g.getAttribute('position').count;
      const col = new Float32Array(n * 3), id = new Float32Array(n);
      for (let v = 0; v < n; v++) { col[v * 3] = mat.color.r; col[v * 3 + 1] = mat.color.g; col[v * 3 + 2] = mat.color.b; id[v] = Math.max(0, k); }
      for (const a of Object.keys(g.attributes)) if (a !== 'position' && a !== 'normal') g.deleteAttribute(a);
      g.setAttribute('color', new THREE.BufferAttribute(col, 3));
      g.setAttribute('aPart', new THREE.BufferAttribute(id, 1));
      geos.push(g.index ? g.toNonIndexed() : g);
    });
    const geo = mergeGeometries(geos)!;
    const piv = names.map((nm) => new THREE.Vector3(...((meta.pivots[nm] ?? [0, 0, 0]) as [number, number, number])));
    const cfg = names.map((nm) => {
      const [a, b, r, par] = rig[nm];
      return new THREE.Vector4(a, b, r, par ? names.indexOf(par) : -1);
    });
    while (piv.length < 14) { piv.push(new THREE.Vector3()); cfg.push(new THREE.Vector4(-1, -1, -1, -1)); }
    const cap = list.length;
    const p: THREE.InstancedBufferAttribute[] = [];
    for (let k = 0; k < 4; k++) {
      const at = new THREE.InstancedBufferAttribute(new Float32Array(cap * 4), 4).setUsage(THREE.DynamicDrawUsage);
      geo.setAttribute(`iP${k}`, at);
      p.push(at);
    }
    const mat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.9, metalness: 0 });
    mat.onBeforeCompile = (sh) => {
      sh.uniforms.uPiv = { value: piv };
      sh.uniforms.uCfg = { value: cfg };
      sh.vertexShader = VERT_PARS + sh.vertexShader
        .replace('#include <beginnormal_vertex>', 'vec3 objectNormal = vec3(normal);\nvec3 wP = position;\nwPose(wP, objectNormal);')
        .replace('#include <begin_vertex>', 'vec3 transformed = wP;');
    };
    mat.customProgramCacheKey = () => `wildlife_${kind}`;
    const mesh = new THREE.InstancedMesh(geo, mat, cap);
    mesh.name = `wildlife_${kind}`;
    mesh.frustumCulled = false;
    mesh.castShadow = false;
    mesh.receiveShadow = true;
    mesh.count = 0;
    mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    mesh.setColorAt(0, new THREE.Color(1, 1, 1));
    this.scene.add(mesh);
    return { mesh, p, cap, list };
  }

  // ---------------------------------------------------------------- river helpers

  /** Closest centreline point near segment `hint` (searches hint +- span). */
  private project(x: number, z: number, hint = -1, span = 8): { i: number; t: number; s: number; u: number; half: number; dx: number; dz: number; nx: number; nz: number; curv: number; cx: number; cz: number } {
    const f = this.frames;
    let i0 = 0, i1 = f.length - 2;
    if (hint >= 0) { i0 = Math.max(0, hint - span); i1 = Math.min(f.length - 2, hint + span); }
    let best = Infinity, bi = i0, bt = 0;
    for (let i = i0; i <= i1; i++) {
      const ax = f[i].x, az = f[i].z, ex = f[i + 1].x - ax, ez = f[i + 1].z - az;
      const l2 = ex * ex + ez * ez || 1;
      const t = clamp(((x - ax) * ex + (z - az) * ez) / l2, 0, 1);
      const px = ax + ex * t - x, pz = az + ez * t - z, d2 = px * px + pz * pz;
      if (d2 < best) { best = d2; bi = i; bt = t; }
    }
    const a = f[bi], b = f[bi + 1];
    const cx = a.x + (b.x - a.x) * bt, cz = a.z + (b.z - a.z) * bt;
    let nx = a.nx + (b.nx - a.nx) * bt, nz = a.nz + (b.nz - a.nz) * bt;
    const nl = Math.hypot(nx, nz) || 1; nx /= nl; nz /= nl;
    const half = (a.w + (b.w - a.w) * bt) * 0.5;
    return { i: bi, t: bt, s: this.cum[bi] + (this.cum[bi + 1] - this.cum[bi]) * bt, u: ((x - cx) * nx + (z - cz) * nz) / half,
      half, dx: nz, dz: -nx, nx, nz, curv: a.curv + (b.curv - a.curv) * bt, cx, cz };
  }

  private at(s: number, u: number): { x: number; z: number; i: number; half: number; dx: number; dz: number; nx: number; nz: number; curv: number } {
    const cum = this.cum;
    let lo = 0, hi = cum.length - 1;
    s = clamp(s, 0, cum[hi]);
    while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (cum[mid] <= s) lo = mid; else hi = mid; }
    const t = (s - cum[lo]) / (cum[lo + 1] - cum[lo] || 1);
    const a = this.frames[lo], b = this.frames[lo + 1] ?? a;
    let nx = a.nx + (b.nx - a.nx) * t, nz = a.nz + (b.nz - a.nz) * t;
    const nl = Math.hypot(nx, nz) || 1; nx /= nl; nz /= nl;
    const half = (a.w + (b.w - a.w) * t) * 0.5;
    return { x: a.x + (b.x - a.x) * t + nx * u * half, z: a.z + (b.z - a.z) * t + nz * u * half, i: lo, half,
      dx: nz, dz: -nx, nx, nz, curv: a.curv + (b.curv - a.curv) * t };
  }

  // ---------------------------------------------------------------- deer: places

  private placeHerds(plan: CityPlan): void {
    const CELL = 6;
    const dens = new Map<number, number>();
    const key = (i: number, j: number) => (i + 2000) * 4096 + (j + 2000);
    const reeds: { x: number; z: number }[] = [];
    for (const v of plan.vegetation ?? []) {
      const tree = v.type.startsWith('tree'), bush = v.type.startsWith('bush');
      if (v.type.startsWith('reed')) reeds.push(v);
      if (!tree && !bush) continue;
      if (tree) this.trees.push({ x: v.x, z: v.z });
      const k = key(Math.floor(v.x / CELL), Math.floor(v.z / CELL));
      dens.set(k, (dens.get(k) ?? 0) + (tree ? 1 : 0.5));
    }
    const density = (x: number, z: number) => {
      const i = Math.floor(x / CELL), j = Math.floor(z / CELL);
      let s = 0;
      for (let di = -1; di <= 1; di++) for (let dj = -1; dj <= 1; dj++) s += dens.get(key(i + di, j + dj)) ?? 0;
      return s; // trees in an 18 m square
    };
    const treeNear = (x: number, z: number, r: number) => this.trees.some((t) => (t.x - x) ** 2 + (t.z - z) ** 2 < r * r);
    const avoid: { x: number; z: number; r: number }[] = [];
    for (const c of plan.river?.crossings ?? []) avoid.push({ x: c.x, z: c.z, r: 30 + c.length / 2 });
    for (const m of plan.river?.mills ?? []) {
      avoid.push({ x: m.wheel.x, z: m.wheel.z, r: 45 });
      for (const p of m.race ?? []) avoid.push({ x: p.x, z: p.z, r: 14 });
    }
    for (const p of plan.parcels ?? []) avoid.push({ x: p.x, z: p.z, r: 38 });
    for (const path of plan.paths ?? []) for (const p of path.points) avoid.push({ x: p.x, z: p.z, r: 11 });
    const blocked = (x: number, z: number) => avoid.some((a) => (a.x - x) ** 2 + (a.z - z) ** 2 < a.r * a.r);

    // Strict first (clear bank, a meadow before the trees); relaxed passes if the banks are wooded.
    const f = this.frames;
    const chosen: Spot[] = [];
    const LEVELS = [{ tree: 3, reed: 2.2, meadow: 6, curv: 0.03, open: 2.5 }, { tree: 2, reed: 1.3, meadow: 3, curv: 0.05, open: 3.5 },
      { tree: 1.3, reed: 0.8, meadow: 0, curv: 0.08, open: 5 }];
    for (const lv of LEVELS) {
      if (chosen.length >= 3) break;
      const cands: Spot[] = [];
      for (let i = 4; i < f.length - 4; i += 2) {
        const fr = f[i];
        if (Math.abs(fr.curv) > lv.curv) continue;
        for (const side of [-1, 1]) {
          const o = side * (fr.w / 2 + 1.0);
          const bx = fr.x + fr.nx * o, bz = fr.z + fr.nz * o;
          if (Math.abs(bx) > 335 || Math.abs(bz) > 262) continue;
          if (blocked(bx, bz) || treeNear(bx, bz, lv.tree)) continue;
          if (reeds.some((r) => (r.x - bx) ** 2 + (r.z - bz) ** 2 < lv.reed * lv.reed)) continue;
          // open sky over the drinking place, so the herd can be seen there
          let over = 0;
          for (const t of this.trees) if ((t.x - bx) ** 2 + (t.z - bz) ** 2 < 100) over++;
          // cover: the densest trees 15-70 m back from the bank on this side
          let best: Spot | null = null;
          for (let ang = -0.9; ang <= 0.9001; ang += 0.3) {
            const c = Math.cos(ang), s = Math.sin(ang);
            const dx = (fr.nx * c - fr.nz * s) * side, dz = (fr.nz * c + fr.nx * s) * side;
            for (let d = 15; d <= 70; d += 5) {
              const cx = bx + dx * d, cz = bz + dz * d;
              const dn = density(cx, cz);
              if (dn < 6) continue;
              const pr = this.project(cx, cz, i, 30);
              if (Math.sign(pr.u) !== side || Math.abs(pr.u) < 2.5) continue;
              // the forest edge: walking out from the cover, the last point still among trees
              let ex = cx, ez = cz;
              for (let e = d; e >= 0; e -= 2) {
                const px = bx + dx * e, pz = bz + dz * e;
                if (density(px, pz) < lv.open) break;
                ex = px; ez = pz;
              }
              if (blocked(cx, cz)) continue;
              const meadow = Math.hypot(ex - bx, ez - bz);
              if (meadow < lv.meadow) continue;
              const score = dn * 0.25 - Math.abs(meadow - 18) * 0.25 - Math.abs(d - 35) * 0.05 - Math.abs(ang) * 1.5
                + Math.min(Math.hypot(bx - 20, bz + 20), 250) / 40 - over * 0.8;
              if (!best || score > best.score) {
                best = { bank: { x: bx, z: bz, nx: -fr.nx * side, nz: -fr.nz * side, i, side },
                  edge: { x: ex, z: ez }, cover: { x: cx, z: cz }, score };
              }
              break;
            }
          }
          if (best) cands.push(best);
        }
      }
      cands.sort((a, b) => b.score - a.score);
      for (const c of cands) {
        if (chosen.length >= 3) break;
        if (chosen.some((o) => Math.hypot(o.bank.x - c.bank.x, o.bank.z - c.bank.z) < 60)) continue;
        chosen.push(c);
      }
    }
    if (!chosen.length) {
      // No forest (yet): drink on the far bank of the course's middle, cover 40 m back.
      const i = Math.floor(f.length * 0.35), fr = f[i], side = -1, o = side * (fr.w / 2 + 1.0);
      const bx = fr.x + fr.nx * o, bz = fr.z + fr.nz * o;
      chosen.push({ bank: { x: bx, z: bz, nx: -fr.nx * side, nz: -fr.nz * side, i, side },
        edge: { x: bx + fr.nx * side * 25, z: bz + fr.nz * side * 25 }, cover: { x: bx + fr.nx * side * 40, z: bz + fr.nz * side * 40 }, score: 0 });
    }

    const comp: ('stag' | 'hind' | 'fawn')[][] = [['stag', 'hind', 'hind', 'fawn'], ['hind', 'hind', 'fawn'], ['stag', 'hind', 'hind', 'hind', 'fawn']];
    chosen.forEach((spot, h) => {
      const herd: Herd = { deer: [], spot, state: 'rest', t: 0, restT: 0, scare: 0, start: 0, win: -1, threat: null, out: 0 };
      const roles = comp[h % comp.length];
      roles.forEach((role, k) => {
        const kind: Kind = role === 'stag' ? 'deer_stag' : role === 'hind' ? 'deer_hind' : 'deer_fawn';
        const d: Deer = {
          kind, x: 0, z: 0, y: 0, yaw: 0, pitch: 0, roll: 0, scale: 0.95 + this.rnd() * 0.1,
          tint: new THREE.Color().setScalar(0.92 + this.rnd() * 0.16), ch: new Float32Array(16), vis: false, blob: 0, wake: 0,
          seed: this.rnd() * 100, herd, role, mother: null, idx: k,
          tx: 0, tz: 0, tyaw: null, v: 0, phase: this.rnd() * 6.28, gait: 0, act: 'lie', actT: 0, bout: 0, head: 0, lie: 1,
          look: 0, lookT: 0, earT: [this.rnd() * 4, this.rnd() * 4], tailT: this.rnd() * 6, dipT: 0,
          slot: { x: 0, z: 0, yaw: 0 }, rest: { x: 0, z: 0 }, arrived: false,
        };
        herd.deer.push(d);
      });
      const fawn = herd.deer.find((d) => d.role === 'fawn');
      if (fawn) fawn.mother = herd.deer.find((d) => d.role === 'hind') ?? null;
      this.layoutHerd(herd);
      for (const d of herd.deer) { d.x = d.rest.x; d.z = d.rest.z; d.yaw = this.rnd() * 6.28; }
      this.herds.push(herd);
      this.deer.push(...herd.deer);
    });
  }

  /** Bank slots side by side along the water (fawn next to its mother) and resting places in cover. */
  private layoutHerd(herd: Herd): void {
    const sp = herd.spot, n = herd.deer.length;
    const base = this.project(sp.bank.x, sp.bank.z, sp.bank.i, 6);
    const order = [...herd.deer].sort((a, b) => (a.role === 'stag' ? -1 : 0) - (b.role === 'stag' ? -1 : 0));
    const fawn = order.find((d) => d.role === 'fawn');
    if (fawn && fawn.mother) { order.splice(order.indexOf(fawn), 1); order.splice(order.indexOf(fawn.mother) + 1, 0, fawn); }
    order.forEach((d, k) => {
      const ds = (k - (n - 1) / 2) * 1.9 + (this.rnd() - 0.5) * 0.5;
      const sc = d.role === 'fawn' ? 0.6 : d.role === 'hind' ? 0.88 : 1;
      const back = 0.5 * sc * d.scale + (d.role === 'stag' ? 0.5 : 0) + this.rnd() * 0.3;
      const p = this.at(base.s + ds, sp.bank.side * (1 + back / base.half));
      const toWater = Math.atan2(-p.nx * sp.bank.side, -p.nz * sp.bank.side);
      d.slot = { x: p.x, z: p.z, yaw: toWater + (this.rnd() - 0.5) * 0.6 };
      const a = this.rnd() * 6.28, r = 1.5 + this.rnd() * 4;
      d.rest = { x: sp.cover.x + Math.cos(a) * r, z: sp.cover.z + Math.sin(a) * r };
    });
  }

  // ---------------------------------------------------------------- ducks: places

  private placeDucks(plan: CityPlan): void {
    const L = this.cum[this.cum.length - 1];
    // Ducks keep clear of the mill wheel; a footbridge they may paddle under (people there feed them).
    const bad: { s: number; r: number }[] = [];
    for (const c of plan.river?.crossings ?? []) bad.push({ s: this.project(c.x, c.z).s, r: 4 });
    for (const m of plan.river?.mills ?? []) bad.push({ s: this.project(m.wheel.x, m.wheel.z).s, r: 30 });
    const inGround = (s: number) => { const p = this.at(s, 0); return Math.abs(p.x) < 330 && Math.abs(p.z) < 255; };
    const free = (s: number) => bad.every((b) => Math.abs(b.s - s) > 35 + b.r) && inGround(s - 35) && inGround(s + 35);
    // Four stretches clear of the mill, under open sky (few trees over and beside the water,
    // so they can be seen), apart from each other.
    const cands: { s: number; score: number }[] = [];
    for (let s = 40; s < L - 40; s += 10) {
      if (!free(s)) continue;
      let cover = 0;
      for (let ds = -30; ds <= 30; ds += 10) {
        const p = this.at(s + ds, 0), r = p.half + 14;
        for (const t of this.trees) if ((t.x - p.x) ** 2 + (t.z - p.z) ** 2 < r * r) cover++;
      }
      cands.push({ s, score: -cover + this.rnd() * 2 });
    }
    cands.sort((a, b) => b.score - a.score);
    const stretches: number[] = [];
    for (const c of cands) {
      if (stretches.every((s) => Math.abs(s - c.s) > 90)) stretches.push(c.s);
      if (stretches.length === 4) break;
    }
    for (let k = stretches.length; k < 4; k++) stretches.push(L * (0.14 + k * 0.23));
    const defs: { name: string; kinds: Kind[] }[] = [
      { name: 'family', kinds: ['duck_hen', 'duck_ling', 'duck_ling', 'duck_ling', 'duck_ling', 'duck_ling', 'duck_ling'] },
      { name: 'pair', kinds: ['duck_drake', 'duck_hen'] },
      { name: 'pair2', kinds: ['duck_hen', 'duck_drake'] },
      { name: 'trio', kinds: ['duck_drake', 'duck_hen', 'duck_drake'] },
    ];
    defs.forEach((def, gi) => {
      const c = stretches[gi];
      const g: DuckGroup = { ducks: [], leader: null as unknown as Duck, s0: c - 35, s1: c + 35, restS: c + (this.rnd() - 0.5) * 30,
        restSide: this.rnd() < 0.5 ? -1 : 1, name: def.name, night: false };
      def.kinds.forEach((kind, k) => {
        const ling = kind === 'duck_ling';
        const d: Duck = {
          kind, x: 0, z: 0, y: 0.03, yaw: 0, pitch: 0, roll: 0, scale: DUCK_BOOST * (ling ? 0.9 + this.rnd() * 0.2 : 0.95 + this.rnd() * 0.1),
          tint: new THREE.Color().setScalar(0.94 + this.rnd() * 0.12), ch: new Float32Array(16), vis: false, blob: 0, wake: 0,
          seed: this.rnd() * 100, group: g, lead: k === 0 ? null : (def.name === 'family' ? g.ducks[k - 1] : g.ducks[0]),
          gap: ling ? 0.42 + this.rnd() * 0.12 : 0.9 + this.rnd() * 0.4, side: k % 2 ? 1 : -1,
          s: c - k * 0.6, u: 0, tu: 0, vx: 0, vz: 0, act: k === 0 ? 'paddle' : 'follow', actT: 5 + this.rnd() * 10,
          dab: 0, dabT: 3 + this.rnd() * 10, flap: 0, bob: this.rnd() * 6.28, hint: -1,
          rest: { x: 0, z: 0, yaw: 0 }, onBank: 0, rippleT: this.rnd() * 3,
        };
        g.ducks.push(d);
      });
      g.leader = g.ducks[0];
      this.layoutRest(g);
      this.groups.push(g);
      this.ducks.push(...g.ducks);
    });
    for (const g of this.groups) this.resetGroup(g, false);
  }

  private layoutRest(g: DuckGroup): void {
    g.ducks.forEach((d, k) => {
      const ds = (k - g.ducks.length / 2) * 0.55 + (this.rnd() - 0.5) * 0.3;
      const p = this.at(g.restS + ds, 0);
      const u = g.restSide * (1 + (0.7 + this.rnd() * 0.8) / p.half);
      const q = this.at(g.restS + ds, u);
      d.rest = { x: q.x, z: q.z, yaw: this.rnd() * 6.28 };
    });
  }

  private resetGroup(g: DuckGroup, night: boolean): void {
    g.night = night;
    for (const [k, d] of g.ducks.entries()) {
      if (night) {
        d.act = 'rest'; d.onBank = 1; d.x = d.rest.x; d.z = d.rest.z; d.yaw = d.rest.yaw;
      } else {
        d.act = k === 0 ? 'paddle' : 'follow'; d.onBank = 0;
        d.s = (g.s0 + g.s1) / 2 + k * d.gap; d.u = k === 0 ? (this.rnd() - 0.5) * 0.6 : g.ducks[0].u + (k % 2 ? 0.03 : -0.03); d.tu = d.u;
        const p = this.at(d.s, d.u); d.x = p.x; d.z = p.z; d.hint = p.i;
        d.yaw = Math.atan2(-p.dx, -p.dz);
      }
      d.vx = d.vz = 0;
    }
  }

  // ---------------------------------------------------------------- update

  /** Per frame: hour = sim clock, view = the camera's ground rectangle (renderer.groundView). */
  update(hour: number, citizens: readonly Citizen[], view: number[]): void {
    const t0 = performance.now();
    const now = t0 * 0.001;
    const dt = this.last < 0 ? 0 : Math.min(0.1, now - this.last);
    this.last = now;
    this.uTime.value = now % 1000;
    for (let k = 0; k < 4; k++) this.view[k] = view[k];
    if (!this.enabled) {
      for (const d of this.draws.values()) d.mesh.visible = false;
      this.blobMesh.visible = this.wakeMesh.visible = false;
      return;
    }
    if (!this.frames.length) return;

    // A jump of the clock (hash, time controls) re-places everyone for the new hour.
    const jump = Number.isNaN(this.lastHour) || Math.abs(wrapPi((hour - this.lastHour) / 24 * 2 * Math.PI)) > 0.35 * 2 * Math.PI / 24;
    this.lastHour = hour;
    if (jump) {
      for (const h of this.herds) this.toRest(h, true);
      for (const g of this.groups) this.resetGroup(g, !inWin(hour, DUCK_DAY));
    }
    this.rippleBudget = Math.min(2, this.rippleBudget + dt / 0.8);

    this.scareT -= dt;
    const look = this.scareT <= 0;
    if (look) this.scareT = 0.4;
    if (this.lineup) this.poseLineup(dt);
    else {
      for (const h of this.herds) this.updateHerd(h, dt, hour, look ? citizens : null);
      for (const d of this.deer) this.updateDeer(d, dt);
      for (const g of this.groups) this.updateGroup(g, dt, hour);
    }
    if (this.loaded) this.pack(hour);
    this.updateMs = this.updateMs * 0.9 + (performance.now() - t0) * 0.1;
  }

  private window(hour: number): [number, number] | null {
    return inWin(hour, DAWN) ? DAWN : inWin(hour, DUSK) ? DUSK : null;
  }

  private toRest(h: Herd, place: boolean): void {
    h.state = 'rest'; h.t = 0; h.restT = 0;
    for (const d of h.deer) {
      if (place) { d.x = d.rest.x; d.z = d.rest.z; d.lie = 1; d.act = 'lie'; d.v = 0; }
      d.tx = d.rest.x; d.tz = d.rest.z; d.tyaw = null; d.arrived = place;
    }
  }

  private setHerd(h: Herd, s: HerdState): void {
    h.state = s; h.t = 0;
    const sp = h.spot;
    for (const d of h.deer) {
      d.arrived = false; d.tyaw = null;
      if (s === 'emerge' || s === 'edge') {
        // in file toward the edge, the leader first
        const a = d.idx * 1.3;
        const ex = sp.edge.x - sp.bank.nx * a + sp.bank.nz * (d.idx % 2 ? 1.2 : -1.2) * Math.min(1, d.idx);
        const ez = sp.edge.z - sp.bank.nz * a - sp.bank.nx * (d.idx % 2 ? 1.2 : -1.2) * Math.min(1, d.idx);
        d.tx = ex; d.tz = ez;
        d.actT = d.idx * 1.6 + this.rnd(); // stagger
      } else if (s === 'bank' || s === 'drink') {
        d.tx = d.slot.x; d.tz = d.slot.z; d.tyaw = d.slot.yaw; d.actT = d.idx * 0.8 + this.rnd() * 0.8;
      } else if (s === 'graze') {
        this.grazeTarget(d);
      } else if (s === 'return' || s === 'flee' || s === 'rest') {
        d.tx = d.rest.x; d.tz = d.rest.z; d.actT = s === 'flee' ? this.rnd() * 0.3 : d.idx * 0.7;
      }
      if (s === 'drink' && this.hold) { d.x = d.slot.x; d.z = d.slot.z; d.yaw = d.slot.yaw; d.lie = 0; d.v = 0; d.arrived = true; d.act = 'drink'; d.bout = 4 + this.rnd() * 5; }
      if (s === 'graze' && this.hold) { d.x = d.tx; d.z = d.tz; d.lie = 0; }
      if (s === 'flee') d.act = 'bound';
    }
  }

  private grazeTarget(d: Deer): void {
    const sp = d.herd.spot;
    const f = 0.25 + this.rnd() * 0.6;
    const lat = (this.rnd() - 0.5) * 14;
    let x = sp.bank.x + (sp.edge.x - sp.bank.x) * f + sp.bank.nz * lat;
    let z = sp.bank.z + (sp.edge.z - sp.bank.z) * f - sp.bank.nx * lat;
    const pr = this.project(x, z, sp.bank.i, 12);
    if (Math.abs(pr.u) < 1 + 2.5 / pr.half || Math.sign(pr.u) !== sp.bank.side) {
      x = sp.bank.x - sp.bank.nx * 4; z = sp.bank.z - sp.bank.nz * 4;
    }
    d.tx = x; d.tz = z; d.tyaw = null;
  }

  private updateHerd(h: Herd, dt: number, hour: number, citizens: readonly Citizen[] | null): void {
    h.t += dt;
    h.scare -= dt;
    const win = this.window(hour);
    if (this.hold) {
      if (h.state !== this.hold) {
        if (this.hold === 'rest') this.toRest(h, true);
        else this.setHerd(h, this.hold);
      }
      if (this.hold === 'flee' && h.deer.every((d) => d.arrived)) { this.toRest(h, true); this.setHerd(h, 'flee'); for (const d of h.deer) { d.x = d.slot.x; d.z = d.slot.z; } }
      return;
    }
    // Startle: someone close by.
    if (citizens && h.state !== 'flee') {
      let cx = 0, cz = 0;
      for (const d of h.deer) { cx += d.x; cz += d.z; }
      cx /= h.deer.length; cz /= h.deer.length;
      const r = h.state === 'rest' ? FLIGHT * 0.5 : FLIGHT;
      let best = r * r, who: Citizen | null = null;
      for (const c of citizens) {
        if (c.hidden) continue;
        const dx = (c.currentX ?? 0) - cx, dz = (c.currentZ ?? 0) - cz, d2 = dx * dx + dz * dz;
        if (d2 < best) { best = d2; who = c; }
      }
      if (who) {
        h.threat = { x: who.currentX ?? 0, z: who.currentZ ?? 0 };
        if (h.state === 'rest') { h.scare = Math.max(h.scare, 60); for (const d of h.deer) { d.look = 1; d.lookT = 6; } }
        else { this.setHerd(h, 'flee'); h.scare = 120; this.stat.scares++; }
        return;
      }
    }
    switch (h.state) {
      case 'rest': {
        h.restT += dt;
        if (win && h.win !== win[0]) { h.win = win[0]; h.start = h.restT + 2 + this.herds.indexOf(h) * 9 + this.rnd() * 6; }
        const left = win ? win[1] - hour : 0;
        // Out when the window opens (staggered per herd), again after a long rest if there is time.
        if (win && h.scare <= 0 && left > 0.6 && (h.restT > h.start || h.restT > 70)) { h.restT = 0; h.start = 1e9; this.setHerd(h, 'emerge'); }
        break;
      }
      case 'emerge':
        if (h.deer.every((d) => d.arrived)) this.setHerd(h, 'edge');
        break;
      case 'edge': // stand at the edge of the trees, heads up, looking out
        if (h.t > 5 + (h.deer.length % 3)) this.setHerd(h, 'bank');
        break;
      case 'bank':
        if (h.deer.every((d) => d.arrived)) { this.setHerd(h, 'drink'); this.stat.drinks++; h.out = 30 + this.rnd() * 20; }
        break;
      case 'drink':
        if (h.t > h.out || (win && win[1] - hour < 0.2) || !win) { this.setHerd(h, 'graze'); h.out = 35 + this.rnd() * 30; }
        break;
      case 'graze':
        if (h.t > h.out || !win || win[1] - hour < 0.12) this.setHerd(h, 'return');
        break;
      case 'return': case 'flee':
        if (h.deer.every((d) => d.arrived)) { this.toRest(h, false); if (h.threat) h.threat = null; }
        break;
    }
  }

  private updateDeer(d: Deer, dt: number): void {
    const h = d.herd, st = h.state;
    d.actT -= dt;
    let speed = 0, target = false;
    const dx = d.tx - d.x, dz = d.tz - d.z, dist = Math.hypot(dx, dz);
    const sc = d.role === 'fawn' ? 0.6 : d.role === 'hind' ? 0.88 : 1;

    // What to do now.
    if (st === 'rest') {
      if (!d.arrived && dist > 0.6) { target = true; speed = WALK * 0.8; d.act = 'walk'; }
      else { d.arrived = true; d.act = d.look > 0.5 ? 'alert' : 'lie'; }
    } else if (st === 'flee') {
      if (d.actT > 0) { d.act = 'alert'; }
      else if (!d.arrived && dist > 1.2) { target = true; speed = BOUND * (d.role === 'fawn' ? 0.92 : 1); d.act = 'bound'; }
      else { d.arrived = true; d.act = 'alert'; }
    } else if (st === 'drink') {
      d.arrived = true;
      d.bout -= dt;
      if (d.bout <= 0) {
        // drink bouts (heads down) and looking up; the stag keeps watch more
        const drinking = d.act === 'drink';
        d.act = drinking ? 'alert' : 'drink';
        d.bout = drinking ? (d.role === 'stag' ? 4 : 2) + this.rnd() * 3 : 5 + this.rnd() * 7;
        if (!drinking) d.dipT = 0.9;
        if (drinking) { d.look = 1; d.lookT = 0; }
      }
      if (d.act === 'drink') {
        d.dipT -= dt;
        if (d.dipT <= 0) { d.dipT = 3 + this.rnd() * 3; this.muzzleRipple(d); }
      }
      d.tyaw = d.slot.yaw;
    } else if (st === 'graze') {
      if (dist > 0.4 && d.actT <= 0) { target = true; speed = 0.35; d.act = 'walk'; }
      else {
        d.act = d.look > 0.5 ? 'alert' : 'graze';
        if (dist <= 0.4) { d.arrived = true; if (d.actT <= -8 - this.rnd() * 10) { this.grazeTarget(d); d.actT = 0; } }
        if (this.rnd() < dt * 0.06) { d.look = 1; d.lookT = 0; }
      }
    } else if (st === 'edge') {
      d.act = 'alert'; d.arrived = true;
      d.tyaw = Math.atan2(h.spot.bank.x - d.x, h.spot.bank.z - d.z);
    } else { // emerge, bank, return
      if (d.actT > 0) { d.act = st === 'return' ? 'graze' : st === 'bank' ? 'alert' : 'stand'; }
      else if (dist > 0.35) {
        target = true; speed = WALK * (st === 'bank' ? 0.8 : 1);
        // cautious: stop and look now and then on the way out
        if (st === 'bank' && this.rnd() < dt * 0.12) { d.actT = 1.2 + this.rnd() * 1.5; d.look = 1; d.lookT = 0; }
        d.act = 'walk';
      } else { d.arrived = true; d.act = st === 'bank' ? 'alert' : 'stand'; }
      if (d.arrived && d.tyaw === null && st !== 'bank') d.tyaw = null;
    }
    // A fawn sticks to its mother when the herd is moving.
    if (d.role === 'fawn' && d.mother && (st === 'emerge' || st === 'return' || st === 'graze') && !d.arrived) {
      d.tx = d.mother.x - Math.sin(d.mother.yaw) * 1.1 + Math.cos(d.mother.yaw) * 0.8;
      d.tz = d.mother.z - Math.cos(d.mother.yaw) * 1.1 - Math.sin(d.mother.yaw) * 0.8;
      if (Math.hypot(d.tx - d.x, d.tz - d.z) < 0.5 && d.mother.arrived) d.arrived = true;
    }

    // Move: turn toward the target, walk along the heading.
    if (target) {
      const want = Math.atan2(dx, dz);
      const turn = d.act === 'bound' ? 3.5 : 2.0;
      d.yaw += clamp(wrapPi(want - d.yaw), -turn * dt, turn * dt);
      const facing = Math.cos(wrapPi(want - d.yaw));
      const goal = speed * clamp(facing, 0.15, 1) * (dist < 1.5 && d.act !== 'bound' ? 0.5 + dist / 3 : 1);
      d.v = smooth(d.v, goal, d.act === 'bound' ? 3 : 2.5, dt);
    } else {
      d.v = smooth(d.v, 0, 4, dt);
      if (d.tyaw !== null) d.yaw += clamp(wrapPi(d.tyaw - d.yaw), -1.2 * dt, 1.2 * dt);
    }
    d.x += Math.sin(d.yaw) * d.v * dt;
    d.z += Math.cos(d.yaw) * d.v * dt;
    // herd-mates keep a little apart
    for (const o of h.deer) {
      if (o === d) continue;
      const ox = d.x - o.x, oz = d.z - o.z, l = Math.hypot(ox, oz);
      const min = st === 'drink' ? 0 : 1.1 * sc;
      if (l > 1e-3 && l < min) { d.x += (ox / l) * (min - l) * 0.5 * Math.min(1, dt * 4); d.z += (oz / l) * (min - l) * 0.5 * Math.min(1, dt * 4); }
    }
    // stay on land
    const pr = this.project(d.x, d.z, h.spot.bank.i, 30);
    const minU = 1 + (0.35 * sc) / pr.half;
    if (Math.abs(pr.u) < minU) {
      const side = Math.sign(pr.u) || h.spot.bank.side, push = (minU - Math.abs(pr.u)) * pr.half;
      d.x += pr.nx * side * push; d.z += pr.nz * side * push;
    }
    this.animateDeer(d, dt);
  }

  private muzzleRipple(d: Deer): void {
    if (!this.river || this.rippleBudget < 1 || !this.inView(d.x, d.z)) return;
    this.rippleBudget -= 1;
    const reach = 0.85 * (d.role === 'fawn' ? 0.6 : d.role === 'hind' ? 0.88 : 1) * d.scale;
    this.river.addRipple(d.x + Math.sin(d.yaw) * reach, d.z + Math.cos(d.yaw) * reach, 0.28);
  }

  private inView(x: number, z: number, m = VIEW_MARGIN): boolean {
    const v = this.view;
    return x > v[0] - m && x < v[2] + m && z > v[1] - m && z < v[3] + m;
  }

  /** Procedural pose from the deer's act and speed. */
  private animateDeer(d: Deer, dt: number): void {
    const sc = (d.role === 'fawn' ? 0.6 : d.role === 'hind' ? 0.88 : 1) * d.scale;
    d.vis = this.inView(d.x, d.z);
    d.lie = smooth(d.lie, d.act === 'lie' ? 1 : 0, 1.6, dt);
    const bound = d.act === 'bound' ? 1 : 0;
    d.gait = smooth(d.gait, bound, 5, dt);
    d.look -= dt * 0.12;
    d.lookT -= dt;
    if (!d.vis) { d.phase += dt * 3; return; }
    const ch = d.ch;
    const stride = (1.05 + d.gait * 2.2) * sc;
    d.phase += (d.v / stride) * Math.PI * 2 * dt;
    const ph = d.phase;
    const amp = clamp(d.v / (WALK * 0.8), 0, 1) * (1 - d.gait);
    // walk: lateral sequence (BL, FL, BR, FR a quarter apart)
    const off = [0.25, 0.75, 0, 0.5];
    let bob = 0, pitch = 0;
    for (let k = 0; k < 4; k++) {
      const th = ph + off[k] * Math.PI * 2;
      const front = k < 2;
      const lift = Math.pow(Math.max(0, Math.cos(th)), 1.5);
      let up = -0.34 * Math.sin(th) * amp, lo = (front ? 0.95 : -0.75) * lift * amp;
      // bound: forelegs together, hind legs together, half a stride apart
      const thb = ph + (front ? 0 : Math.PI) + (k % 2) * 0.25;
      const ub = front ? -0.75 * Math.sin(thb) - 0.1 : -0.8 * Math.sin(thb) + 0.15;
      const lb = front ? 1.5 * Math.max(0, Math.cos(thb)) : -1.0 * Math.max(0, Math.cos(thb)) - 0.15;
      up = up * (1 - d.gait) + ub * d.gait;
      lo = lo * (1 - d.gait) + lb * d.gait;
      ch[LEG_U + k] = up; ch[LEG_L + k] = lo;
    }
    bob = 0.02 * Math.cos(2 * ph) * amp * sc + d.gait * 0.32 * sc * Math.max(0, Math.sin(ph + 0.9));
    pitch = d.gait * 0.2 * Math.sin(ph + 0.4);

    // head and neck
    let neck = 0, head = 0, nyaw = 0;
    const lookAround = d.lookT <= 0 ? ((d.lookT = 1.5 + this.rnd() * 3), true) : false;
    if (lookAround) d.head = (this.rnd() - 0.5) * 1.4;
    switch (d.act) {
      case 'drink': neck = 2.15; head = -0.8; pitch += 0.1; for (const k of [0, 1]) ch[LEG_U + k] += -0.22; break;
      case 'graze': neck = 2.2; head = -0.75; for (const k of [0, 1]) ch[LEG_U + k] += -0.15; nyaw = Math.sin(this.uTime.value * 0.7 + d.seed) * 0.25; break;
      case 'alert': neck = -0.22; head = 0.12; nyaw = d.head; break;
      case 'bound': neck = 0.35; head = -0.15; break;
      case 'walk': neck = 0.25 + (d.herd.state === 'bank' ? 0.25 : 0); head = 0.05; nyaw = d.look > 0.5 ? d.head * 0.6 : 0; break;
      case 'lie': neck = 0.15; head = -0.1; nyaw = d.head * 0.5; break;
      default: neck = 0.1; head = 0; nyaw = d.look > 0.3 ? d.head * 0.5 : Math.sin(this.uTime.value * 0.3 + d.seed) * 0.3;
    }
    const hr = d.act === 'alert' || d.act === 'bound' ? 7 : 3;
    ch[NECK] = smooth(ch[NECK], neck, hr, dt);
    ch[HEAD] = smooth(ch[HEAD], head, hr, dt);
    ch[NECK_YAW] = smooth(ch[NECK_YAW], nyaw, 3, dt);
    ch[HEAD_YAW] = ch[NECK_YAW] * 0.4;
    // ears: flick now and then, pricked forward when alert
    for (const k of [0, 1]) {
      d.earT[k] -= dt;
      if (d.earT[k] < -0.18) d.earT[k] = 1.5 + this.rnd() * 5;
      const flick = d.earT[k] < 0 ? Math.sin((-d.earT[k] / 0.18) * Math.PI) * 0.7 : 0;
      ch[EAR_L + k] = (d.act === 'alert' ? -0.25 : 0.05) + flick;
    }
    // tail: flicks, held up (white flash) in flight
    d.tailT -= dt;
    if (d.tailT < -0.3) d.tailT = 2 + this.rnd() * 6;
    const tflick = d.tailT < 0 ? Math.sin((-d.tailT / 0.3) * Math.PI * 2) * 0.35 : 0;
    ch[TAIL] = smooth(ch[TAIL], d.act === 'bound' ? -1.6 : 0, 6, dt) + tflick * (1 - d.gait);

    // lying up: legs folded under, body down
    if (d.lie > 0.01) {
      const l = d.lie;
      const fold = [1.2, 1.2, -1.15, -1.15], low = [0.45, 0.45, 2.3, 2.3];
      for (let k = 0; k < 4; k++) {
        ch[LEG_U + k] = ch[LEG_U + k] * (1 - l) + fold[k] * l;
        ch[LEG_L + k] = ch[LEG_L + k] * (1 - l) + low[k] * l;
      }
      bob = bob * (1 - l) - 0.6 * sc * l;
      ch[NECK] = ch[NECK] * (1 - l * 0.5);
    }
    d.y = bob;
    d.pitch = pitch;
    d.blob = 0.85 * sc;
  }

  // ---------------------------------------------------------------- ducks

  private updateGroup(g: DuckGroup, dt: number, hour: number): void {
    const day = inWin(hour, DUCK_DAY) || this.lineup !== null;
    const lead = g.leader;
    if (!day && !g.night) {
      g.night = true;
      for (const d of g.ducks) d.act = 'land';
    } else if (day && g.night) {
      g.night = false;
      for (const [k, d] of g.ducks.entries()) {
        d.act = k === 0 ? 'drift' : 'follow'; d.actT = 6;
        const pr = this.project(d.x, d.z);
        d.s = pr.s; d.u = clamp(pr.u, -0.85, 0.85); d.tu = d.u * 0.5; d.hint = pr.i; d.onBank = 1;
      }
    }
    for (const d of g.ducks) {
      if (d.act === 'land' || d.act === 'rest') this.duckToBank(d, dt);
      else if (d === lead) this.duckLead(d, dt);
      else this.duckFollow(d, dt);
      this.animateDuck(d, dt);
    }
  }

  private duckLead(d: Duck, dt: number): void {
    const g = d.group;
    d.actT -= dt;
    const here = this.at(d.s, d.u);
    const flow = flowSpeed(d.u, here.curv);
    let paddle = 0; // m/s upstream, through the water
    if (d.actT <= 0) {
      const r = this.rnd();
      if (d.s < g.s0) d.act = 'drift';
      else if (d.s > g.s1) d.act = 'paddle';
      else d.act = r < 0.4 ? 'paddle' : r < 0.6 ? 'drift' : r < 0.8 ? 'dabble' : r < 0.93 ? 'preen' : 'flap';
      d.actT = d.act === 'paddle' ? 12 + this.rnd() * 14 : d.act === 'drift' ? 7 + this.rnd() * 9
        : d.act === 'dabble' ? 6 + this.rnd() * 6 : d.act === 'preen' ? 5 + this.rnd() * 5 : 1.6;
      d.tu = clamp(d.u + (this.rnd() - 0.5) * 0.9, -0.7, 0.7);
      if (d.act === 'dabble') d.dabT = 0.5;
    }
    switch (d.act) {
      case 'paddle': paddle = flow + 0.22; break;
      case 'drift': paddle = flow * 0.25; break;
      default: paddle = flow * 0.75;
    }
    if (d.dab > 0.5 || d.flap > 0.3) paddle = flow * 0.6;
    d.u = smooth(d.u, d.tu, 0.25, dt);
    const ds = (flow - paddle) * dt;
    d.s += ds;
    const p = this.at(d.s, d.u);
    const vx = (p.x - d.x) / Math.max(dt, 1e-4), vz = (p.z - d.z) / Math.max(dt, 1e-4);
    d.x = p.x; d.z = p.z; d.hint = p.i;
    d.vx = dt > 0 ? vx : 0; d.vz = dt > 0 ? vz : 0;
    // face through the water: the duck's own motion relative to the current
    const wx = d.vx - p.dx * flow, wz = d.vz - p.dz * flow, ws = Math.hypot(wx, wz);
    if (ws > 0.06) d.yaw += clamp(wrapPi(Math.atan2(wx, wz) - d.yaw), -1.5 * dt, 1.5 * dt);
    else d.yaw += Math.sin(this.uTime.value * 0.13 + d.seed) * 0.25 * dt; // drifting: a slow turn
    d.wake = clamp(ws / 0.35, 0, 1);
  }

  private duckFollow(d: Duck, dt: number): void {
    const lead = d.lead ?? d.group.leader;
    // target: behind the one followed (a line for ducklings; beside and behind for a mate)
    const ling = d.kind === 'duck_ling';
    const back = d.gap * (ling ? 1 : 0.8), lat = ling ? Math.sin(this.uTime.value * 0.6 + d.seed) * 0.12 : d.side * 0.45;
    const tx = lead.x - Math.sin(lead.yaw) * back + Math.cos(lead.yaw) * lat;
    const tz = lead.z - Math.cos(lead.yaw) * back - Math.sin(lead.yaw) * lat;
    const pr = this.project(d.x, d.z, d.hint, 4);
    d.hint = pr.i;
    const flow = flowSpeed(pr.u, pr.curv);
    const fx = pr.dx * flow, fz = pr.dz * flow;
    const ex = tx - d.x, ez = tz - d.z, dist = Math.hypot(ex, ez);
    const vmax = ling ? 0.6 : 0.5;
    const want = Math.min(vmax, dist * 0.9);
    // own paddling (relative to water) toward the target, plus the current
    const ox = dist > 1e-3 ? (ex / dist) * want : 0, oz = dist > 1e-3 ? (ez / dist) * want : 0;
    const gvx = ox, gvz = oz; // ground velocity wanted; paddle = ground - current
    d.vx = smooth(d.vx, gvx, 2.2, dt); d.vz = smooth(d.vz, gvz, 2.2, dt);
    d.x += d.vx * dt; d.z += d.vz * dt;
    // keep apart from the group
    for (const o of d.group.ducks) {
      if (o === d || o.act === 'rest') continue;
      const qx = d.x - o.x, qz = d.z - o.z, l = Math.hypot(qx, qz), min = ling && o.kind === 'duck_ling' ? 0.3 : 0.55;
      if (l > 1e-4 && l < min) { d.x += (qx / l) * (min - l) * 0.5; d.z += (qz / l) * (min - l) * 0.5; }
    }
    // stay on the water
    const q = this.project(d.x, d.z, d.hint, 4);
    if (Math.abs(q.u) > 0.85) { const k = (Math.abs(q.u) - 0.85) * q.half * Math.sign(q.u); d.x -= q.nx * k; d.z -= q.nz * k; }
    const wx = d.vx - fx, wz = d.vz - fz, ws = Math.hypot(wx, wz);
    if (ws > 0.05) d.yaw += clamp(wrapPi(Math.atan2(wx, wz) - d.yaw), -2.2 * dt, 2.2 * dt);
    d.wake = clamp(ws / 0.35, 0, 1);
    // a mate copies the leader's dabbling and preening now and then
    if (!ling && (lead.act === 'dabble' || lead.act === 'preen') && d.act === 'follow' && this.rnd() < dt * 0.3) { d.act = lead.act; d.actT = 3 + this.rnd() * 3; d.dabT = 0.6; }
    if (ling && this.rnd() < dt * 0.04 && d.act === 'follow') { d.act = 'dabble'; d.actT = 1.5; d.dabT = 0.2; }
    if (d.act !== 'follow') { d.actT -= dt; if (d.actT <= 0) d.act = 'follow'; }
  }

  private duckToBank(d: Duck, dt: number): void {
    const ex = d.rest.x - d.x, ez = d.rest.z - d.z, dist = Math.hypot(ex, ez);
    if (d.act === 'land') {
      if (dist < 0.08) { d.act = 'rest'; d.onBank = 1; }
      else {
        const v = Math.min(dist, 0.45 * dt * 1);
        d.x += (ex / dist) * v; d.z += (ez / dist) * v;
        d.yaw += clamp(wrapPi(Math.atan2(ex, ez) - d.yaw), -2 * dt, 2 * dt);
        const pr = this.project(d.x, d.z, d.hint, 6); d.hint = pr.i;
        d.onBank = smooth(d.onBank, Math.abs(pr.u) > 1 ? 1 : 0, 3, dt);
        d.wake = Math.abs(pr.u) > 1 ? 0 : 0.6;
      }
    } else {
      d.yaw += clamp(wrapPi(d.rest.yaw - d.yaw), -1 * dt, 1 * dt);
      d.wake = 0;
    }
  }

  private animateDuck(d: Duck, dt: number): void {
    d.vis = this.inView(d.x, d.z, 6);
    const ch = d.ch;
    d.bob += dt * (1.7 + (d.seed % 1) * 0.4);
    const resting = d.act === 'rest';
    // dabbling: tail up, head under, two or three dips
    if (d.act === 'dabble') {
      d.dabT -= dt;
      if (d.dabT <= 0) {
        const down = d.dab < 0.5;
        d.dabT = down ? 1.4 + this.rnd() * 1.6 : 0.8 + this.rnd() * 1.2;
        d.dab = down ? 1 : 0;
        if (this.river && d.vis && this.rippleBudget >= 1 && d.kind !== 'duck_ling') {
          this.rippleBudget -= 1;
          this.river.addRipple(d.x + Math.sin(d.yaw) * 0.25, d.z + Math.cos(d.yaw) * 0.25, down ? 0.4 : 0.25);
        }
      }
    } else d.dab = 0;
    const up = smooth(d.pitch, d.dab ? 1.25 : 0, 5, dt);
    d.pitch = up;
    d.flap = d.act === 'flap' ? Math.min(1, d.flap + dt * 4) : Math.max(0, d.flap - dt * 3);
    if (!d.vis) return;
    let hp = 0.05, hy = Math.sin(this.uTime.value * 0.4 + d.seed) * 0.35;
    if (d.act === 'preen') { hy = 2.3 * Math.sign(Math.sin(d.seed)) ; hp = 0.55 + Math.sin(this.uTime.value * 7 + d.seed) * 0.12; }
    if (resting) { hy = 2.6 * (d.seed % 2 > 1 ? 1 : -1); hp = 0.75; }
    if (d.dab) hp = 0.7;
    ch[D_HEAD] = smooth(ch[D_HEAD], hp, 5, dt);
    ch[D_HEAD_YAW] = smooth(ch[D_HEAD_YAW], hy, 4, dt);
    const beat = d.flap > 0 ? Math.sin(this.uTime.value * 26) * 0.5 + 0.9 : 0;
    ch[WING_L] = beat * d.flap * 1.4;
    ch[WING_R] = -beat * d.flap * 1.4;
    d.roll = Math.sin(d.bob * 0.7) * 0.03;
    const sit = resting || d.onBank > 0.5;
    d.y = sit ? 0.035 * d.onBank : 0.03 + Math.sin(d.bob) * 0.008 - d.flap * -0.06;
    if (d.flap > 0) d.pitch = -0.45 * d.flap;
    d.blob = sit ? 0.28 * d.scale : 0;
  }

  // ---------------------------------------------------------------- debug lineup

  /** All six kinds side by side on the ground, in one pose (wild=lineup,<pose>), animated in place. */
  private poseLineup(dt: number): void {
    const l = this.lineup!;
    let k = 0;
    const all: Animal[] = [...this.deer, ...this.ducks];
    for (const a of all) a.vis = false;
    for (const kind of KINDS) {
      const a = all.find((x) => x.kind === kind);
      if (!a) continue;
      a.x = l.x + (k - 2.5) * 2.0; a.z = l.z; a.yaw = Math.PI / 2;
      if ((a as Deer).herd) {
        const d = a as Deer;
        d.act = (l.pose as DeerAct) || 'stand';
        d.v = d.act === 'walk' ? WALK : d.act === 'bound' ? BOUND : 0;
        if (d.act !== 'lie') d.lie = 0;
        this.animateDeer(d, dt);
      } else {
        const d = a as Duck;
        d.act = (l.pose === 'graze' ? 'dabble' : l.pose === 'lie' ? 'rest' : l.pose === 'bound' ? 'flap' : 'follow') as DuckAct;
        d.onBank = 1;
        this.animateDuck(d, dt);
      }
      a.vis = true;
      k++;
    }
  }

  // ---------------------------------------------------------------- draw

  private pack(hour: number): void {
    const night = nightFactor(hour);
    let nb = 0, nw = 0;
    const blob = this.blobAttr.array as Float32Array, bdir = this.blobDir.array as Float32Array;
    const wake = this.wakeAttr.array as Float32Array, wdir = this.wakeDir.array as Float32Array;
    for (const dr of this.draws.values()) {
      let n = 0;
      const arr = dr.p.map((a) => a.array as Float32Array);
      for (const a of dr.list) {
        if (!a.vis) continue;
        this.e.set(a.pitch, a.yaw, a.roll, 'YXZ');
        this.q.setFromEuler(this.e);
        this.p.set(a.x, a.y, a.z);
        this.sc.setScalar(a.scale);
        dr.mesh.setMatrixAt(n, this.m4.compose(this.p, this.q, this.sc));
        dr.mesh.setColorAt(n, a.tint);
        for (let c = 0; c < 16; c++) arr[c >> 2][n * 4 + (c & 3)] = a.ch[c];
        n++;
        if (a.blob > 0 && nb < blob.length / 4) {
          blob[nb * 4] = a.x; blob[nb * 4 + 1] = a.z; blob[nb * 4 + 2] = a.blob; blob[nb * 4 + 3] = 0.42 * (1 - 0.75 * night);
          bdir[nb * 2] = Math.cos(a.yaw); bdir[nb * 2 + 1] = Math.sin(a.yaw);
          nb++;
        }
        if (a.wake > 0.02 && nw < wake.length / 4) {
          const ling = a.kind === 'duck_ling', sz = ling ? 0.38 : 1;
          wake[nw * 4] = a.x; wake[nw * 4 + 1] = a.z; wake[nw * 4 + 2] = a.wake * (ling ? 0.55 : 1) * (1 - 0.7 * night); wake[nw * 4 + 3] = sz * a.scale / DUCK_BOOST;
          wdir[nw * 2] = Math.cos(a.yaw); wdir[nw * 2 + 1] = Math.sin(a.yaw);
          nw++;
        }
      }
      dr.mesh.count = n;
      dr.mesh.visible = n > 0;
      if (n) {
        dr.mesh.instanceMatrix.needsUpdate = true;
        if (dr.mesh.instanceColor) dr.mesh.instanceColor.needsUpdate = true;
        for (const at of dr.p) at.needsUpdate = true;
      }
    }
    this.blobGeo.instanceCount = nb;
    this.blobMesh.visible = nb > 0;
    if (nb) { this.blobAttr.needsUpdate = true; this.blobDir.needsUpdate = true; }
    this.wakeGeo.instanceCount = nw;
    this.wakeMesh.visible = nw > 0;
    if (nw) { this.wakeAttr.needsUpdate = true; this.wakeDir.needsUpdate = true; }
  }

  // ---------------------------------------------------------------- debug

  /** Hold every herd in a state (deer=drink), or null to let them live again. */
  force(state: HerdState | null): void {
    this.hold = state;
    if (state) for (const h of this.herds) { if (state === 'rest') this.toRest(h, true); else this.setHerd(h, state); }
  }

  /** Where a herd's bank spot or a duck group is. */
  focus(name: string, i = 0): { x: number; z: number } | null {
    if (name === 'deer' || name === 'herd') {
      const h = this.herds[i % Math.max(1, this.herds.length)];
      return h ? { x: h.spot.bank.x * 0.85 + h.spot.edge.x * 0.15, z: h.spot.bank.z * 0.85 + h.spot.edge.z * 0.15 } : null;
    }
    const g = this.groups.find((q) => q.name === name) ?? this.groups[i];
    return g ? { x: g.leader.x, z: g.leader.z } : null;
  }

  stats() {
    let drawn = 0, calls = 0;
    for (const d of this.draws.values()) { drawn += d.mesh.count; if (d.mesh.visible) calls++; }
    return {
      deer: this.deer.length, ducks: this.ducks.length, drawn,
      drawCalls: calls + (this.blobMesh.visible ? 1 : 0) + (this.wakeMesh.visible ? 1 : 0),
      updateMs: +this.updateMs.toFixed(3), hold: this.hold, ...this.stat,
      herds: this.herds.map((h) => ({ state: h.state, n: h.deer.length, bank: [Math.round(h.spot.bank.x), Math.round(h.spot.bank.z)],
        edge: [Math.round(h.spot.edge.x), Math.round(h.spot.edge.z)], cover: [Math.round(h.spot.cover.x), Math.round(h.spot.cover.z)],
        acts: h.deer.map((d) => d.act).join(',') })),
      groups: this.groups.map((g) => ({ name: g.name, n: g.ducks.length, x: Math.round(g.leader.x), z: Math.round(g.leader.z),
        act: g.leader.act, night: g.night })),
    };
  }
}

/** __lublin.wildlife and the deer= / ducks= / wild= hashes (dev only). */
export function installWildlifeDebug(w: Wildlife, snapTo: (x: number, z: number, zoom?: number) => void): void {
  const g = window as unknown as { __lublin?: Record<string, unknown> };
  if (g.__lublin) g.__lublin.wildlife = w;
  const apply = () => {
    const params = new URLSearchParams(location.hash.slice(1));
    const deer = params.get('deer'), ducks = params.get('ducks'), wild = params.get('wild');
    requestAnimationFrame(() => requestAnimationFrame(() => {
      if (deer) {
        const [state, herd, zoom] = deer.split(',');
        w.force(state === 'live' ? null : state as HerdState);
        const p = w.focus('deer', Number(herd) || 0);
        if (p) snapTo(p.x, p.z, zoom ? Number(zoom) : 16);
      } else if (w.hold) w.force(null);
      if (ducks) {
        const [name, zoom] = ducks.split(',');
        const p = w.focus(name);
        if (p) snapTo(p.x, p.z, zoom ? Number(zoom) : 10);
      }
      if (wild) {
        const [what, pose] = wild.split(',');
        if (what === 'lineup') {
          const p = w.focus('deer', 0);
          if (p) { w.lineup = { x: p.x, z: p.z, pose: pose ?? 'stand' }; snapTo(p.x, p.z, 9); }
        }
        w.enabled = what !== 'off';
      } else { w.lineup = null; w.enabled = true; }
    }));
  };
  window.addEventListener('hashchange', apply);
  apply();
}
