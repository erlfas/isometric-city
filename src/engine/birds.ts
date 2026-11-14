import * as THREE from 'three';
import type { CityPlan } from '../types';
import { riverFrames, type RiverFrame } from './river-course';
import { nightFactor } from './door-leaves';

/**
 * Birds over the forest and the Bystrzyca: rooks and jackdaws in flocks, a pair of red kites
 * and a pair of buzzards circling on thermals, swallows skimming the water by day, a grey
 * heron fishing from the shallows and flapping slowly along the river, a barn owl at night.
 *
 * Territory comes from the plan at runtime, so it follows the forest when plan.vegetation is
 * regenerated: trees (type tree_*) are binned into 30 m cells, cells with at least ~30% of
 * the densest cell's trees are woods, and connected woods cells are one wood. Woods near the
 * river score higher: the best one holds the rookery (perches on the crowns of its tallest
 * trees, at model height x scale), the others are the flocks' home ranges. Waypoints are woods
 * cells plus points along the river. Swallows and the heron live on the river course.
 *
 * Day: flocks wander between waypoints and settle in trees now and then. Dusk (GATHER) they
 * wheel over the rookery, from SETTLE they drop into it one by one over SETTLE_SPAN hours;
 * they roost all night and lift off from LIFT. Schedule = sim hour; motion = real time
 * (frozen while the sim is paused). A jump of the clock re-places everyone (reset).
 *
 * Drawing: one InstancedBufferGeometry per kind (a dozen flat triangles: body, keel, tail,
 * two jointed wings; the heron adds legs and neck), wings beaten and folded in the vertex
 * shader. No real shadows (moving casters would force shadow-map redraws): low fliers get a
 * soft blob on the ground instead, one more instanced draw. Flocks far out of view move as a
 * rigid formation without steering.
 *
 * Debug: __lublin.birds.stats(), .focus(group); hash &birds=rookery|rooks|kite|buzzard|
 * heron|swallows|owl[,zoom] puts the camera on that group (installBirdDebug).
 */

// ------------------------------------------------------------------ schedule (sim hours)

const GATHER = 18.6;      // rooks head for the rookery and wheel over it
const SETTLE = 19.1;      // ...and drop into it, one by one, over SETTLE_SPAN
const SETTLE_SPAN = 0.6;
const LIFT = 5.3;         // dawn: they lift off over LIFT_SPAN, wheel, disperse
const LIFT_SPAN = 0.7;
const RAPTOR_UP = 8.6, RAPTOR_DOWN = 17.4;  // thermals: late morning to late afternoon
const SWALLOW_UP = 5.9, SWALLOW_DOWN = 20.2;
const OWL_UP = 21.3, OWL_DOWN = 4.8;

const CELL = 30;
const WIND = { x: 0.32, z: 0.14 }; // as the chimney smoke
const TOWN = { x: 30, z: -40 };    // where swallows go to their eaves at night

const S = { FLY: 0, LAND: 1, PERCH: 2, TAKEOFF: 3, HIDDEN: 4 } as const;
type S = (typeof S)[keyof typeof S];

type Kind = 'corvid' | 'kite' | 'buzzard' | 'swallow' | 'heron' | 'owl';
export type BirdCall = 'rook' | 'jackdaw' | 'kite' | 'buzzard' | 'heron';

interface KindCfg {
  span: number;      // real wingspan, m
  boost: number;     // drawn larger than life by this (before the zoom boost)
  freq: number;      // wing beats per second
  amp: number;       // beat amplitude, rad
  dihedral: number;  // wings held up in a glide, rad
  cruise: number; maxSpeed: number; minSpeed: number; maxAcc: number;
  flapOn: [number, number]; glide: [number, number]; // bout lengths, s
  col: number[]; acc: number[]; tipShade: number;
  floor: number;     // least brightness at night
}

const CFG: Record<Kind, KindCfg> = {
  corvid: { span: 0.9, boost: 1.0, freq: 3.4, amp: 0.62, dihedral: 0.06, cruise: 9, maxSpeed: 14, minSpeed: 5, maxAcc: 8,
    flapOn: [1.2, 3.5], glide: [0.4, 1.4], col: [0.075, 0.075, 0.09], acc: [0.06, 0.06, 0.07], tipShade: 0.8, floor: 0 },
  kite: { span: 1.6, boost: 1.0, freq: 2.2, amp: 0.45, dihedral: 0.1, cruise: 8, maxSpeed: 13, minSpeed: 6, maxAcc: 3.2,
    flapOn: [0.8, 1.6], glide: [12, 30], col: [0.5, 0.27, 0.13], acc: [0.62, 0.33, 0.15], tipShade: 0.3, floor: 0 },
  buzzard: { span: 1.25, boost: 1.05, freq: 2.6, amp: 0.45, dihedral: 0.2, cruise: 7.5, maxSpeed: 12, minSpeed: 5.5, maxAcc: 3.2,
    flapOn: [0.8, 1.8], glide: [10, 25], col: [0.31, 0.22, 0.15], acc: [0.38, 0.28, 0.2], tipShade: 0.5, floor: 0 },
  swallow: { span: 0.33, boost: 1.8, freq: 9, amp: 0.7, dihedral: 0, cruise: 11, maxSpeed: 15, minSpeed: 6, maxAcc: 24,
    flapOn: [0.25, 0.7], glide: [0.3, 0.9], col: [0.1, 0.12, 0.24], acc: [0.1, 0.11, 0.2], tipShade: 0.8, floor: 0 },
  heron: { span: 1.85, boost: 1.0, freq: 1.9, amp: 0.55, dihedral: -0.08, cruise: 6.5, maxSpeed: 9, minSpeed: 3.5, maxAcc: 2.6,
    flapOn: [20, 40], glide: [0.5, 1], col: [0.58, 0.6, 0.63], acc: [0.86, 0.86, 0.84], tipShade: 0.38, floor: 0 },
  owl: { span: 0.9, boost: 1.1, freq: 2.8, amp: 0.55, dihedral: 0.05, cruise: 6, maxSpeed: 9, minSpeed: 3, maxAcc: 5,
    flapOn: [0.6, 1.4], glide: [0.8, 2], col: [0.82, 0.68, 0.46], acc: [0.95, 0.93, 0.88], tipShade: 0.85, floor: 0.6 },
};
const KINDS = Object.keys(CFG) as Kind[];

// ------------------------------------------------------------------ geometry

/** Silhouette in units of the wingspan: body along +z (head), wings along x, flat in y. */
interface Shape {
  sh: number; wr: number; xm: number;                 // shoulder, wrist, outer mid (x)
  lead: [number, number, number]; trail: [number, number, number]; // z at sh, wr, xm
  tip: number;                                        // z of the wing tip (x = 0.5)
  hz: number; bw: number; bz: number; tz0: number; keel: number; // body
  tz1: number; tw: number; fork: number;              // tail end, half width, notch depth
  heron?: boolean;
}

const SHAPES: Record<Kind, Shape> = {
  corvid: { sh: 0.04, wr: 0.22, xm: 0.4, lead: [0.07, 0.08, 0.05], trail: [-0.1, -0.1, -0.08], tip: -0.02,
    hz: 0.24, bw: 0.055, bz: 0.04, tz0: -0.12, keel: 0.045, tz1: -0.3, tw: 0.07, fork: -0.02 },
  kite: { sh: 0.03, wr: 0.2, xm: 0.4, lead: [0.06, 0.07, 0.04], trail: [-0.08, -0.09, -0.07], tip: -0.04,
    hz: 0.16, bw: 0.04, bz: 0.03, tz0: -0.07, keel: 0.035, tz1: -0.27, tw: 0.065, fork: 0.07 },
  buzzard: { sh: 0.04, wr: 0.2, xm: 0.4, lead: [0.08, 0.09, 0.06], trail: [-0.11, -0.12, -0.09], tip: -0.01,
    hz: 0.17, bw: 0.05, bz: 0.03, tz0: -0.08, keel: 0.04, tz1: -0.24, tw: 0.085, fork: -0.015 },
  swallow: { sh: 0.04, wr: 0.15, xm: 0.36, lead: [0.05, 0.06, -0.02], trail: [-0.04, -0.05, -0.11], tip: -0.15,
    hz: 0.17, bw: 0.045, bz: 0.03, tz0: -0.08, keel: 0.04, tz1: -0.37, tw: 0.065, fork: 0.18 },
  heron: { sh: 0.04, wr: 0.2, xm: 0.4, lead: [0.07, 0.08, 0.05], trail: [-0.08, -0.09, -0.08], tip: -0.02,
    hz: 0.12, bw: 0.05, bz: 0.02, tz0: -0.08, keel: 0.045, tz1: -0.14, tw: 0.04, fork: 0, heron: true },
  owl: { sh: 0.05, wr: 0.22, xm: 0.4, lead: [0.08, 0.09, 0.06], trail: [-0.08, -0.09, -0.07], tip: 0,
    hz: 0.15, bw: 0.075, bz: 0.04, tz0: -0.08, keel: 0.05, tz1: -0.17, tw: 0.06, fork: -0.02 },
};
/** Heron: stand pitch (rad), leg lift (span units), leg pivot z, neck pivot z. */
const HERON_STAND = new THREE.Vector4(0.45, 0.3, -0.08, 0.08);

function birdGeometry(s: Shape, tipShade: number): { pos: Float32Array; part: Float32Array } {
  const pos: number[] = [], part: number[] = [];
  const tri = (id: number, shade: number, accent: number, ...p: number[][]) => {
    for (const v of p) { pos.push(v[0], v[1], v[2]); part.push(id, shade, accent); }
  };
  // body: flat diamond plus a vertical keel (so a banked or edge-on bird is not a hairline)
  const head = [0, 0, s.hz], rear = [0, 0, s.tz0];
  tri(0, 0.9, 0, head, [s.bw, 0, s.bz], rear);
  tri(0, 0.9, 0, head, rear, [-s.bw, 0, s.bz]);
  tri(0, 0.8, 0, head, [0, s.keel, s.bz], rear);
  tri(0, 0.7, 0, head, rear, [0, -s.keel * 1.2, s.bz]);
  // tail
  const bl = [-s.bw * 0.8, 0, s.tz0 + 0.02], br = [s.bw * 0.8, 0, s.tz0 + 0.02];
  const el = [-s.tw, 0, s.tz1], er = [s.tw, 0, s.tz1], notch = [0, 0, s.tz1 + s.fork];
  tri(3, 0.85, 1, bl, br, notch);
  tri(3, 0.85, 1, bl, notch, el);
  tri(3, 0.85, 1, br, er, notch);
  // wings: inner quad shoulder..wrist, outer quad wrist..mid, tip triangle
  for (const side of [-1, 1]) {
    const P = (x: number, z: number) => [side * x, 0, z];
    const [l0, lw, lm] = s.lead, [t0, tw, tm] = s.trail;
    tri(1, 1, 0, P(s.sh, l0), P(s.wr, lw), P(s.wr, tw));
    tri(1, 1, 0, P(s.sh, l0), P(s.wr, tw), P(s.sh, t0));
    tri(1, (1 + tipShade) / 2, 0, P(s.wr, lw), P(s.xm, lm), P(s.xm, tm));
    tri(1, (1 + tipShade) / 2, 0, P(s.wr, lw), P(s.xm, tm), P(s.wr, tw));
    tri(1, tipShade, 0, P(s.xm, lm), P(0.5, s.tip), P(s.xm, tm));
  }
  if (s.heron) {
    // legs trailing behind (part 4), neck + bill (part 5, pale)
    for (const x of [-0.014, 0.014]) {
      tri(4, 0.5, 0, [x - 0.006, 0, s.tz0], [x + 0.006, 0, s.tz0], [x + 0.004, 0, s.tz0 - 0.33]);
      tri(4, 0.5, 0, [x - 0.006, 0, s.tz0], [x + 0.004, 0, s.tz0 - 0.33], [x - 0.004, 0, s.tz0 - 0.33]);
    }
    const n0 = HERON_STAND.w, n1 = 0.27;
    tri(5, 1, 1, [-0.035, 0.01, n0], [0.035, 0.01, n0], [0.026, 0.012, n1]);
    tri(5, 1, 1, [-0.035, 0.01, n0], [0.026, 0.012, n1], [-0.026, 0.012, n1]);
    // a vertical web too, so the neck reads from the side
    tri(5, 0.9, 1, [0, -0.03, n0], [0, 0.035, n0], [0, 0.03, n1]);
    tri(5, 0.75, 0.4, [-0.016, 0.012, n1], [0.016, 0.012, n1], [0, 0.01, n1 + 0.12]);
  }
  return { pos: new Float32Array(pos), part: new Float32Array(part) };
}

const VERT = /* glsl */`
attribute vec3 aPart;
attribute vec3 iPos;
attribute vec4 iRot;   // yaw, pitch, bank, scale
attribute vec4 iWing;  // phase, flap, fold, stand
attribute float iTint;
uniform vec3 uCol; uniform vec3 uAcc;
uniform vec4 uWing;    // shoulder, wrist, amplitude, dihedral
uniform vec4 uStand;   // stand pitch, leg lift, leg pivot z, neck pivot z
uniform float uLight; uniform float uFloor; uniform float uBoost;
varying vec3 vCol;
vec3 rotX(vec3 v, float a) { float c = cos(a), s = sin(a); return vec3(v.x, v.y * c + v.z * s, -v.y * s + v.z * c); }
void main() {
  vec3 p = position;
  float part = aPart.x, shade = aPart.y;
  float flap = iWing.y, fold = iWing.z, stand = iWing.w;
  if (part > 0.5 && part < 1.5) {
    float side = p.x < 0.0 ? -1.0 : 1.0;
    float ax = abs(p.x), sh = uWing.x, wr = uWing.y;
    // the outer wing lags the inner one: the tip whips through each beat
    float a1 = uWing.w + flap * uWing.z * sin(iWing.x);
    float a2 = a1 + flap * uWing.z * 0.6 * sin(iWing.x - 0.9) - fold * 0.0;
    float r = ax - sh;
    vec2 q = ax <= wr ? r * vec2(cos(a1), sin(a1))
                      : (wr - sh) * vec2(cos(a1), sin(a1)) + (ax - wr) * vec2(cos(a2), sin(a2));
    vec3 w = vec3(side * (sh + q.x), p.y + q.y, p.z);
    vec3 f = vec3(side * (sh * 0.9 + r * 0.16), 0.025 + r * 0.04, p.z - r * 0.55);
    p = mix(w, f, fold);
    shade *= 0.86 + 0.14 * cos(a1 * 1.6);
  } else if (part > 3.5 && part < 4.5) {
    vec3 piv = vec3(0.0, 0.0, uStand.z);
    p = piv + rotX(p - piv, stand * (1.5708 - uStand.x));
  } else if (part > 4.5) {
    vec3 piv = vec3(0.0, 0.0, uStand.w);
    p = piv + rotX(p - piv, stand * (1.35 - uStand.x));
  }
  float S = iRot.w * uBoost;
  p *= S;
  float cb = cos(iRot.z), sb = sin(iRot.z);
  p = vec3(p.x * cb - p.y * sb, p.x * sb + p.y * cb, p.z);
  p = rotX(p, iRot.y + stand * uStand.x);
  float cy = cos(iRot.x), sy = sin(iRot.x);
  p = vec3(p.x * cy + p.z * sy, p.y, -p.x * sy + p.z * cy);
  vec3 wp = iPos + p + vec3(0.0, uStand.y * S * stand, 0.0);
  vCol = mix(uCol, uAcc, aPart.z) * (0.85 + 0.3 * iTint) * shade * max(uLight, uFloor);
  gl_Position = projectionMatrix * viewMatrix * vec4(wp, 1.0);
}`;

const FRAG = /* glsl */`
varying vec3 vCol;
void main() { gl_FragColor = vec4(vCol, 1.0); }`;

const BLOB_VERT = /* glsl */`
attribute vec4 iBlob; // x, z, radius, alpha
varying vec2 vUv; varying float vA;
void main() {
  vUv = position.xz; vA = iBlob.w;
  vec3 wp = vec3(iBlob.x + position.x * iBlob.z, 0.09, iBlob.y + position.z * iBlob.z);
  gl_Position = projectionMatrix * viewMatrix * vec4(wp, 1.0);
}`;
const BLOB_FRAG = /* glsl */`
varying vec2 vUv; varying float vA;
void main() {
  float r = length(vUv * vec2(1.0, 1.6)) * 2.0;
  float a = smoothstep(1.0, 0.2, r) * vA;
  if (a < 0.004) discard;
  gl_FragColor = vec4(0.03, 0.04, 0.03, a);
}`;

// ------------------------------------------------------------------ state

interface Tree { x: number; z: number; top: number; r: number }
interface Cell { x: number; z: number; trees: Tree[] }
interface Wood { x: number; z: number; trees: Tree[]; cells: Cell[]; score: number }
interface Perch { x: number; y: number; z: number; yaw: number }
interface Way { x: number; z: number; cell: Cell | null }

interface Bird {
  kind: Kind; cfg: KindCfg;
  x: number; y: number; z: number; vx: number; vy: number; vz: number;
  yaw: number; pitch: number; bank: number;
  phase: number; flap: number; fold: number; stand: number;
  flapping: boolean; bout: number;
  tint: number; size: number; seed: number; stagger: number;
  state: S; t: number; delay: number;
  perch: Perch | null; roost: Perch | null; atRoost: boolean;
  o: Float32Array; // formation offset: freq/phase pairs for x, z, y
  cx: number; cy: number; cz: number; // own target (non-flock kinds)
  jackdaw: boolean;
}

interface Flock {
  birds: Bird[]; home: Wood;
  ax: number; ay: number; az: number; heading: number; vx: number; vy: number; vz: number;
  way: Way; wayY: number; mode: 'day' | 'gather'; sitting: boolean; sitT: number; sitAt: Cell | null;
  spread: number; callT: number; near: boolean;
}

interface Pair {
  birds: Bird[]; kind: 'kite' | 'buzzard'; cx: number; cz: number; alt: number; top: number;
  gliding: boolean; callT: number;
}

interface SwallowGroup { birds: Bird[]; idx: number; dir: number }

interface KindDraw {
  geo: THREE.InstancedBufferGeometry; mesh: THREE.Mesh; mat: THREE.ShaderMaterial;
  iPos: THREE.InstancedBufferAttribute; iRot: THREE.InstancedBufferAttribute;
  iWing: THREE.InstancedBufferAttribute; iTint: THREE.InstancedBufferAttribute;
}

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const wrapPi = (a: number) => { while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return a; };
/** Hours from a to b going forward round the clock. */
const since = (h: number, a: number) => ((h - a) % 24 + 24) % 24;

function mulberry32(seed: number): () => number {
  return () => {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Crown height and radius of a placed tree model (m at scale 1). */
export function treeSizes(models: Map<string, THREE.Object3D>): (type: string) => { h: number; r: number } {
  const cache = new Map<string, { h: number; r: number }>();
  const box = new THREE.Box3();
  return (type) => {
    let s = cache.get(type);
    if (!s) {
      const m = models.get(type) ?? models.get('tree_oak');
      if (m) {
        box.setFromObject(m);
        s = { h: box.max.y, r: Math.max(1, Math.min(box.max.x - box.min.x, box.max.z - box.min.z) / 2) };
      } else s = { h: 11, r: 3.5 };
      cache.set(type, s);
    }
    return s;
  };
}

export class Birds {
  public onCall: ((kind: BirdCall, x: number, z: number) => void) | null = null;

  private rnd = mulberry32(1392);
  private trees: Tree[] = [];
  private woods: Wood[] = [];
  private ways: Way[] = [];
  private frames: RiverFrame[] = [];
  private rookery: Wood | null = null;
  private flocks: Flock[] = [];
  private pairs: Pair[] = [];
  private swallows: SwallowGroup[] = [];
  private heron: Bird | null = null;
  private heronSpots: Perch[] = [];
  private owl: Bird | null = null;
  private all: Bird[] = [];
  private draws = new Map<Kind, KindDraw>();
  private byKind = new Map<Kind, Bird[]>();
  private blobGeo = new THREE.InstancedBufferGeometry();
  private blobMesh: THREE.Mesh;
  private blobAttr: THREE.InstancedBufferAttribute;
  private uLight = { value: 1 };
  private uBoost = { value: 1.3 };
  private time = 0;
  private lastHour = NaN;
  private view = [0, 0, 0, 0];
  private sun = { x: 0, z: 0 };
  private updateMs = 0;
  private _dir = new THREE.Vector3();

  constructor(scene: THREE.Scene, plan: CityPlan, size: (type: string) => { h: number; r: number }) {
    this.territory(plan, size);
    this.populate();
    for (const k of KINDS) {
      const list = this.all.filter((b) => b.kind === k);
      this.byKind.set(k, list);
      if (list.length) this.draws.set(k, this.makeDraw(scene, k, list.length));
    }
    const quad = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
    this.blobGeo.index = quad.index;
    this.blobGeo.setAttribute('position', quad.getAttribute('position'));
    this.blobAttr = new THREE.InstancedBufferAttribute(new Float32Array(Math.max(1, this.all.length) * 4), 4)
      .setUsage(THREE.DynamicDrawUsage);
    this.blobGeo.setAttribute('iBlob', this.blobAttr);
    this.blobGeo.instanceCount = 0;
    this.blobMesh = new THREE.Mesh(this.blobGeo, new THREE.ShaderMaterial({
      vertexShader: BLOB_VERT, fragmentShader: BLOB_FRAG, transparent: true, depthWrite: false,
    }));
    this.blobMesh.frustumCulled = false;
    this.blobMesh.renderOrder = 1;
    this.blobMesh.visible = false;
    scene.add(this.blobMesh);
  }

  // ---------------------------------------------------------------- territory

  private territory(plan: CityPlan, size: (type: string) => { h: number; r: number }): void {
    for (const v of plan.vegetation ?? []) {
      if (!v.type.startsWith('tree')) continue;
      const s = size(v.type), k = v.scale ?? 1;
      this.trees.push({ x: v.x, z: v.z, top: s.h * k, r: s.r * k });
    }
    if (plan.river && plan.river.points.length > 1) this.frames = riverFrames(plan.river);

    const cells = new Map<string, Cell & { i: number; j: number }>();
    for (const t of this.trees) {
      const i = Math.floor(t.x / CELL), j = Math.floor(t.z / CELL), key = `${i},${j}`;
      let c = cells.get(key);
      if (!c) cells.set(key, c = { x: 0, z: 0, trees: [], i, j });
      c.trees.push(t);
    }
    let max = 0;
    for (const c of cells.values()) {
      max = Math.max(max, c.trees.length);
      c.x = c.trees.reduce((s, t) => s + t.x, 0) / c.trees.length;
      c.z = c.trees.reduce((s, t) => s + t.z, 0) / c.trees.length;
    }
    const thr = Math.max(2, Math.ceil(max * 0.3));
    const dense = [...cells.values()].filter((c) => c.trees.length >= thr);
    const seen = new Set<string>();
    const riverDist = (x: number, z: number) => {
      let d = Infinity;
      for (let i = 0; i < this.frames.length; i += 4) d = Math.min(d, Math.hypot(this.frames[i].x - x, this.frames[i].z - z));
      return d;
    };
    for (const c0 of dense) {
      const k0 = `${c0.i},${c0.j}`;
      if (seen.has(k0)) continue;
      seen.add(k0);
      const wood: Wood = { x: 0, z: 0, trees: [], cells: [], score: 0 };
      const stack = [c0];
      while (stack.length) {
        const c = stack.pop()!;
        wood.cells.push(c);
        wood.trees.push(...c.trees);
        for (let di = -1; di <= 1; di++) for (let dj = -1; dj <= 1; dj++) {
          const k = `${c.i + di},${c.j + dj}`, n = cells.get(k);
          if (n && !seen.has(k) && n.trees.length >= thr) { seen.add(k); stack.push(n); }
        }
      }
      wood.x = wood.trees.reduce((s, t) => s + t.x, 0) / wood.trees.length;
      wood.z = wood.trees.reduce((s, t) => s + t.z, 0) / wood.trees.length;
      // the forest round the river is where the birds live; the town's own trees less so
      wood.score = wood.trees.length / (1 + (this.frames.length ? riverDist(wood.x, wood.z) : 0) / 120)
        * (Math.hypot(wood.x, wood.z) < 120 ? 0.4 : 1);
      this.woods.push(wood);
    }
    this.woods.sort((a, b) => b.score - a.score);
    for (const w of this.woods) for (const c of w.cells) this.ways.push({ x: c.x, z: c.z, cell: c });
    for (let i = 0; i < this.frames.length; i += 10) this.ways.push({ x: this.frames[i].x, z: this.frames[i].z, cell: null });
    this.rookery = this.woods[0] ?? null;

    // heron spots: in the shallows, every ~30 m along either bank
    for (let i = 6; i < this.frames.length - 6; i += 10) {
      const f = this.frames[i], side = this.rnd() < 0.5 ? -1 : 1, o = side * (f.w / 2 - 0.7);
      const flow = Math.atan2(f.nz, -f.nx);
      this.heronSpots.push({ x: f.x + f.nx * o, y: 0, z: f.z + f.nz * o, yaw: flow + (this.rnd() < 0.5 ? 0 : Math.PI) + (this.rnd() - 0.5) * 0.8 });
    }
  }

  /** n perches on the crowns of the given trees (tallest and nearest to (x, z) first). */
  private perchesOn(trees: Tree[], x: number, z: number, n: number, perTree = 4): Perch[] {
    const pick = [...trees].sort((a, b) => (Math.hypot(a.x - x, a.z - z) - a.top * 3) - (Math.hypot(b.x - x, b.z - z) - b.top * 3))
      .slice(0, Math.max(1, Math.ceil(n / perTree)));
    const out: Perch[] = [];
    for (let k = 0; k < n; k++) {
      const t = pick[k % pick.length];
      // on the outside of the crown (lumpy clumps: a bit above the dome), not in the leaves
      const a = this.rnd() * Math.PI * 2, u = 0.08 + 0.32 * Math.sqrt(this.rnd());
      out.push({ x: t.x + Math.sin(a) * t.r * u, y: t.top * (1 - 0.15 * u * u) + 0.15, z: t.z + Math.cos(a) * t.r * u,
        yaw: this.rnd() * Math.PI * 2 });
    }
    return out;
  }

  private bird(kind: Kind): Bird {
    const r = this.rnd;
    const o = new Float32Array(6);
    for (let i = 0; i < 6; i += 2) { o[i] = 0.12 + r() * 0.3; o[i + 1] = r() * Math.PI * 2; }
    const b: Bird = {
      kind, cfg: CFG[kind], x: 0, y: 20, z: 0, vx: 0, vy: 0, vz: 1, yaw: 0, pitch: 0, bank: 0,
      phase: r() * Math.PI * 2, flap: 1, fold: 0, stand: 0, flapping: true, bout: r() * 2,
      tint: r() * 0.25, size: 0.9 + r() * 0.2, seed: r(), stagger: r(), state: S.FLY, t: 0, delay: 0,
      perch: null, roost: null, atRoost: false, o, cx: 0, cy: 0, cz: 0, jackdaw: false,
    };
    this.all.push(b);
    return b;
  }

  private populate(): void {
    const r = this.rnd;
    // rooks and jackdaws: more and bigger flocks the more forest there is
    if (this.rookery) {
      const nFlocks = clamp(Math.round(this.trees.length / 300) + 2, 2, 5);
      const homes = this.woods.slice(0, Math.max(1, Math.min(this.woods.length, nFlocks + 2)));
      for (let k = 0; k < nFlocks; k++) {
        const n = 8 + Math.floor(r() * 15);
        const home = homes[k % homes.length];
        const birds: Bird[] = [];
        for (let i = 0; i < n; i++) {
          const b = this.bird('corvid');
          if (r() < 0.3) { b.jackdaw = true; b.size *= 0.78; b.tint = 0.6 + r() * 0.3; }
          birds.push(b);
        }
        this.flocks.push({ birds, home, ax: home.x, ay: 22, az: home.z, heading: r() * 6.28, vx: 0, vy: 0, vz: 0,
          way: { x: home.x, z: home.z, cell: null }, wayY: 22, mode: 'day', sitting: false, sitT: 0, sitAt: null,
          spread: 4 + n * 0.32, callT: r() * 5, near: false });
      }
      const corvids = this.flocks.flatMap((f) => f.birds);
      const roosts = this.perchesOn(this.rookery.trees, this.rookery.x, this.rookery.z, corvids.length, 5);
      corvids.forEach((b, i) => { b.roost = roosts[i]; });
    }
    // a pair of kites and a pair of buzzards on thermals over the woods
    if (this.ways.length) {
      for (const kind of ['kite', 'buzzard'] as const) {
        const w = this.ways[Math.floor(r() * this.ways.length)];
        const pair: Pair = { birds: [this.bird(kind), this.bird(kind)], kind, cx: w.x, cz: w.z, alt: 45, top: 70 + r() * 15,
          gliding: false, callT: 5 + r() * 20 };
        const tall = this.woods.length ? this.perchesOn(this.woods[Math.floor(r() * this.woods.length)].trees, w.x, w.z, 2, 1) : [];
        pair.birds.forEach((b, i) => { b.roost = tall[i] ?? null; b.cx = 18 + i * 7 + r() * 4; b.cy = i * 6; });
        this.pairs.push(pair);
      }
    }
    if (this.frames.length > 20) {
      // swallows over two stretches of the river
      for (let g = 0; g < 2; g++) {
        const birds: Bird[] = [];
        const n = 7 + Math.floor(r() * 5);
        for (let i = 0; i < n; i++) birds.push(this.bird('swallow'));
        this.swallows.push({ birds, idx: this.frames.length * (0.3 + 0.4 * g + r() * 0.15), dir: r() < 0.5 ? -1 : 1 });
      }
      this.heron = this.bird('heron');
    }
    if (this.trees.length) this.owl = this.bird('owl');
  }

  private makeDraw(scene: THREE.Scene, kind: Kind, n: number): KindDraw {
    const cfg = CFG[kind], shape = SHAPES[kind];
    const { pos, part } = birdGeometry(shape, cfg.tipShade);
    const geo = new THREE.InstancedBufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('aPart', new THREE.BufferAttribute(part, 3));
    const attr = (size: number) => new THREE.InstancedBufferAttribute(new Float32Array(n * size), size).setUsage(THREE.DynamicDrawUsage);
    const iPos = attr(3), iRot = attr(4), iWing = attr(4), iTint = attr(1);
    geo.setAttribute('iPos', iPos);
    geo.setAttribute('iRot', iRot);
    geo.setAttribute('iWing', iWing);
    geo.setAttribute('iTint', iTint);
    geo.instanceCount = 0;
    const mat = new THREE.ShaderMaterial({
      uniforms: {
        uCol: { value: new THREE.Color(...cfg.col) }, uAcc: { value: new THREE.Color(...cfg.acc) },
        uWing: { value: new THREE.Vector4(shape.sh, shape.wr, cfg.amp, cfg.dihedral) },
        uStand: { value: HERON_STAND }, uLight: this.uLight, uFloor: { value: cfg.floor }, uBoost: this.uBoost,
      },
      vertexShader: VERT, fragmentShader: FRAG, side: THREE.DoubleSide,
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.frustumCulled = false;
    mesh.visible = false;
    mesh.name = `birds_${kind}`;
    scene.add(mesh);
    return { geo, mesh, mat, iPos, iRot, iWing, iTint };
  }

  // ---------------------------------------------------------------- schedule

  /** Should this rook be in the rookery now (each drops in / lifts off at its own moment)? */
  private roosting(b: Bird, h: number): boolean {
    const ev = since(h, SETTLE), night = since(LIFT, SETTLE);
    if (ev < night) return ev >= b.stagger * SETTLE_SPAN;
    return since(h, LIFT) < b.stagger * LIFT_SPAN;
  }
  private gathering(h: number): boolean { return since(h, GATHER) < since(LIFT + LIFT_SPAN + 0.08, GATHER); }
  private raptorDown(b: Bird, h: number): boolean {
    return h < RAPTOR_UP + b.stagger * 0.6 || h >= RAPTOR_DOWN + b.stagger * 0.6;
  }
  private swallowAway(b: Bird, h: number): boolean {
    return h < SWALLOW_UP + b.stagger * 0.5 || h >= SWALLOW_DOWN + b.stagger * 0.4;
  }
  private owlOut(h: number): boolean { return h >= OWL_UP || h < OWL_DOWN; }

  // ---------------------------------------------------------------- placement on a clock jump

  private reset(h: number): void {
    const r = this.rnd;
    for (const f of this.flocks) {
      f.mode = this.gathering(h) ? 'gather' : 'day';
      f.sitting = false;
      const R = this.rookery!;
      if (f.mode === 'gather') { const a = r() * 6.28; f.ax = R.x + Math.sin(a) * 30; f.az = R.z + Math.cos(a) * 30; f.ay = 26; f.heading = a + Math.PI / 2; }
      else { const w = this.homeWay(f); f.ax = w.x + (r() - 0.5) * 60; f.az = w.z + (r() - 0.5) * 60; f.ay = 18 + r() * 12; f.heading = r() * 6.28; this.newWay(f); }
      f.vx = Math.sin(f.heading) * 8.5; f.vz = Math.cos(f.heading) * 8.5; f.vy = 0;
      for (const b of f.birds) {
        if (f.mode === 'gather' && this.roosting(b, h) && b.roost) this.sit(b, b.roost, true);
        else this.flyAt(b, f.ax + this.offX(b, f), f.ay + this.offY(b), f.az + this.offZ(b, f), f.vx, f.vz);
      }
    }
    for (const p of this.pairs) {
      const w = this.ways[Math.floor(r() * this.ways.length)];
      p.cx = w.x; p.cz = w.z; p.alt = 40 + r() * 25; p.gliding = false;
      for (const b of p.birds) {
        if (this.raptorDown(b, h) && b.roost) this.sit(b, b.roost, true);
        else { const a = r() * 6.28; this.flyAt(b, p.cx + Math.sin(a) * b.cx, p.alt + b.cy, p.cz + Math.cos(a) * b.cx, Math.cos(a) * 8, -Math.sin(a) * 8); }
      }
    }
    for (const g of this.swallows) {
      for (const b of g.birds) {
        if (this.swallowAway(b, h)) { b.state = S.HIDDEN; continue; }
        const f = this.frames[clamp(Math.round(g.idx + (r() - 0.5) * 24), 0, this.frames.length - 1)];
        this.flyAt(b, f.x + (r() - 0.5) * f.w * 0.6, 1 + r() * 2, f.z + (r() - 0.5) * f.w * 0.6, (r() - 0.5) * 20, (r() - 0.5) * 20);
        this.swallowTarget(b, g);
      }
    }
    if (this.heron && this.heronSpots.length) {
      const s = this.heronSpots[Math.floor(r() * this.heronSpots.length)];
      this.sit(this.heron, s, false);
      this.heron.stand = 1;
      this.heron.t = 30 + r() * 120;
    }
    if (this.owl) {
      if (this.owlOut(h)) { this.owlPerch(this.owl, true); } else this.owl.state = S.HIDDEN;
    }
  }

  private offX(b: Bird, f: Flock) { const o = b.o, t = this.time; return f.spread * (0.65 * Math.sin(o[0] * t + o[1]) + 0.35 * Math.sin(o[0] * 2.3 * t + o[3])); }
  private offZ(b: Bird, f: Flock) { const o = b.o, t = this.time; return f.spread * (0.65 * Math.sin(o[2] * t + o[3]) + 0.35 * Math.sin(o[2] * 1.9 * t + o[1])); }
  private offY(b: Bird) { const o = b.o; return 3.5 * Math.sin(o[4] * this.time + o[5]); }

  private flyAt(b: Bird, x: number, y: number, z: number, vx: number, vz: number): void {
    b.x = x; b.y = y; b.z = z; b.vx = vx; b.vy = 0; b.vz = vz;
    b.yaw = Math.atan2(vx, vz); b.pitch = 0; b.bank = 0;
    b.state = S.FLY; b.fold = 0; b.stand = 0; b.perch = null; b.atRoost = false;
  }

  private sit(b: Bird, p: Perch, roost: boolean): void {
    b.x = p.x; b.y = p.y; b.z = p.z; b.vx = b.vy = b.vz = 0;
    b.yaw = p.yaw; b.pitch = 0; b.bank = 0; b.flap = 0; b.fold = 1;
    b.state = S.PERCH; b.perch = p; b.atRoost = roost; b.delay = this.rnd() * 1.8;
  }

  private land(b: Bird, p: Perch, roost: boolean): void {
    b.state = S.LAND; b.perch = p; b.atRoost = roost;
  }

  private takeoff(b: Bird): void {
    b.state = S.TAKEOFF; b.t = 0.9; b.perch = null; b.atRoost = false;
    b.vx = Math.sin(b.yaw) * 2.5; b.vz = Math.cos(b.yaw) * 2.5; b.vy = 3;
    b.flap = 1; b.flapping = true; b.bout = 1.5;
  }

  private homeWay(f: Flock): Way {
    return { x: f.home.x, z: f.home.z, cell: f.home.cells[0] ?? null };
  }

  private newWay(f: Flock): void {
    const r = this.rnd;
    const near = this.ways.filter((w) => Math.hypot(w.x - f.home.x, w.z - f.home.z) < 230
      && Math.hypot(w.x - f.ax, w.z - f.az) > 60);
    const list = near.length ? near : this.ways;
    // woods cells twice as likely as river points
    let w = list[Math.floor(r() * list.length)];
    if (!w.cell && r() < 0.5) w = list[Math.floor(r() * list.length)];
    f.way = w;
    f.wayY = 15 + r() * 18;
  }

  // ---------------------------------------------------------------- per frame

  update(dt: number, hour: number, camera: THREE.Camera, view: readonly number[], zoom: number): void {
    const t0 = performance.now();
    if (!(Math.abs(wrapPi(((hour - this.lastHour) / 24) * Math.PI * 2)) < 0.06)) this.reset(hour); // > ~0.23 h jump
    this.lastHour = hour;
    this.time += dt;
    this.uLight.value = 1 - 0.68 * nightFactor(hour);
    this.uBoost.value = clamp(zoom / 45, 1.3, 4.5);
    const M = 90; // margin round the view: altitude shifts a bird up the screen (~1.4 m per m)
    this.view[0] = view[0] - M; this.view[1] = view[1] - M; this.view[2] = view[2] + M; this.view[3] = view[3] + M;
    const d = camera.getWorldDirection(this._dir);
    const fl = Math.hypot(d.x, d.z) || 1, fx = d.x / fl, fz = d.z / fl;
    const c15 = Math.cos(0.2618), s15 = Math.sin(0.2618);
    this.sun.x = fz * c15 + fx * s15; this.sun.z = -fx * c15 + fz * s15;

    if (dt > 0) {
      for (const f of this.flocks) this.updateFlock(f, dt, hour);
      for (const p of this.pairs) this.updatePair(p, dt, hour);
      for (const g of this.swallows) this.updateSwallows(g, dt, hour);
      if (this.heron) this.updateHeron(this.heron, dt);
      if (this.owl) this.updateOwl(this.owl, dt, hour);
    }
    this.write();
    this.updateMs = this.updateMs * 0.95 + (performance.now() - t0) * 0.05;
  }

  private inView(x: number, z: number, m = 0): boolean {
    const v = this.view;
    return x > v[0] - m && x < v[2] + m && z > v[1] - m && z < v[3] + m;
  }

  private updateFlock(f: Flock, dt: number, h: number): void {
    const r = this.rnd;
    const R = this.rookery!;
    const mode = this.gathering(h) ? 'gather' : 'day';
    if (mode !== f.mode) {
      f.mode = mode; f.sitting = false;
      if (mode === 'day') this.newWay(f);
    }
    // where the formation goes
    let speed = 8.5;
    if (f.mode === 'gather') {
      const rad = 26 + f.spread;
      this.circleAnchor(f, R.x, R.z, rad, 24 + (f.birds.length % 5) * 1.5, speed, dt);
    } else if (f.sitting) {
      const c = f.sitAt!;
      this.circleAnchor(f, c.x, c.z, 25, 20, 7, dt);
      f.sitT -= dt;
      if (f.sitT <= 0) { f.sitting = false; this.newWay(f); }
    } else {
      const dist = Math.hypot(f.way.x - f.ax, f.way.z - f.az);
      if (dist < 25) {
        if (f.way.cell && r() < 0.35) { // drop into the trees for a while
          f.sitting = true; f.sitAt = f.way.cell; f.sitT = 30 + r() * 50;
          const ps = this.perchesOn(f.way.cell.trees, f.way.cell.x, f.way.cell.z, f.birds.length, 4);
          f.birds.forEach((b, i) => { b.perch = ps[i]; });
        } else this.newWay(f);
      }
      if (!f.sitting) this.steerAnchor(f, f.way.x, f.wayY, f.way.z, speed, dt);
    }
    // birds
    let cx = 0, cz = 0;
    for (const b of f.birds) { cx += b.x; cz += b.z; }
    cx /= f.birds.length; cz /= f.birds.length;
    const near = this.inView(cx, cz, 40) || this.inView(f.ax, f.az, 40);
    f.near = near;
    let active = 0;
    for (const b of f.birds) {
      // what this bird should be doing
      if (f.mode === 'gather') {
        const want = this.roosting(b, h) && !!b.roost;
        if (want && (b.state === S.FLY || b.state === S.TAKEOFF)) this.land(b, b.roost!, true);
        else if (want && b.state === S.PERCH && !b.atRoost) this.takeoff(b);
        else if (!want && (b.state === S.PERCH || b.state === S.LAND) && !(b.state === S.PERCH && b.atRoost && b.delay > 0)) {
          if (b.state === S.LAND) b.state = S.FLY; else this.takeoff(b);
        } else if (!want && b.state === S.PERCH) b.delay -= dt;
      } else if (f.sitting) {
        if ((b.state === S.FLY || b.state === S.TAKEOFF) && b.perch && !b.atRoost && f.sitT > 8) this.land(b, b.perch, false);
      } else if (b.state === S.PERCH) {
        b.delay -= dt;
        if (b.delay <= 0) this.takeoff(b);
      } else if (b.state === S.LAND) b.state = S.FLY;

      if (b.state !== S.PERCH) active++;
      const tx = f.ax + f.vx * 0.6 + this.offX(b, f), ty = f.ay + this.offY(b), tz = f.az + f.vz * 0.6 + this.offZ(b, f);
      if (!near) { this.rigid(b, tx, ty, tz, f.vx, f.vy, f.vz, dt); continue; }
      if (b.state === S.FLY || b.state === S.TAKEOFF) {
        let dvx = f.vx + (tx - b.x) * 0.9, dvy = f.vy + (ty - b.y) * 0.9, dvz = f.vz + (tz - b.z) * 0.9;
        // separation from flock mates (scaled with how large they are drawn)
        const sep = 1.5 * b.cfg.span * b.cfg.boost * this.uBoost.value;
        let sx = 0, sy = 0, sz = 0;
        for (const o of f.birds) {
          if (o === b || o.state === S.PERCH) continue;
          const ex = b.x - o.x, ey = b.y - o.y, ez = b.z - o.z, e2 = ex * ex + ey * ey + ez * ez;
          if (e2 < sep * sep && e2 > 1e-6) { const e = Math.sqrt(e2), k = (sep - e) / e; sx += ex * k; sy += ey * k; sz += ez * k; }
        }
        dvx += sx * 3; dvy += sy * 3; dvz += sz * 3;
        this.steer(b, dvx, dvy, dvz, 2.4, dt);
      } else if (b.state === S.LAND) this.approach(b, dt);
      else this.perched(b, dt);
    }
    // voices: a few caws on the wing by day, a racket over the rookery at dusk and dawn
    f.callT -= dt;
    if (f.callT <= 0) {
      const evening = since(h, GATHER) < 1.6 || since(h, LIFT) < LIFT_SPAN + 0.2;
      const rate = active > 0 ? (f.mode === 'gather' ? 1.4 : f.sitting ? 0.35 : 0.3) * Math.min(1, active / 6)
        : (f.mode === 'gather' && evening ? 0.5 : 0);
      f.callT = rate > 0 ? -Math.log(1 - r()) / rate : 2;
      if (rate > 0 && near && this.onCall) {
        const b = f.birds[Math.floor(r() * f.birds.length)];
        this.onCall(b.jackdaw ? 'jackdaw' : 'rook', b.x, b.z);
      }
    }
  }

  private steerAnchor(f: Flock, tx: number, ty: number, tz: number, speed: number, dt: number): void {
    const want = Math.atan2(tx - f.ax, tz - f.az);
    f.heading += clamp(wrapPi(want - f.heading), -0.55 * dt, 0.55 * dt);
    f.vx = Math.sin(f.heading) * speed; f.vz = Math.cos(f.heading) * speed;
    f.vy = clamp((ty - f.ay) * 0.25, -1.5, 1.5);
    f.ax += f.vx * dt; f.ay += f.vy * dt; f.az += f.vz * dt;
  }

  private circleAnchor(f: Flock, cx: number, cz: number, rad: number, y: number, speed: number, dt: number): void {
    const a = Math.atan2(f.ax - cx, f.az - cz) + 0.6;
    this.steerAnchor(f, cx + Math.sin(a) * rad, y, cz + Math.cos(a) * rad, speed, dt);
  }

  /** Out of view: hold formation exactly, no steering; landings and take-offs are instant. */
  private rigid(b: Bird, x: number, y: number, z: number, vx: number, vy: number, vz: number, dt: number): void {
    if (b.state === S.LAND) { this.sit(b, b.perch!, b.atRoost); return; }
    if (b.state === S.PERCH) return;
    b.state = S.FLY;
    b.x = x; b.y = y; b.z = z; b.vx = vx; b.vy = vy; b.vz = vz;
    b.yaw = Math.atan2(vx, vz); b.fold = 0; b.stand = 0;
    b.phase += b.cfg.freq * 6.283 * dt;
  }

  /** Accelerate towards a desired velocity; bank into the turn, pitch with the climb, beat or glide. */
  private steer(b: Bird, dvx: number, dvy: number, dvz: number, gain: number, dt: number, forceFlap = false): void {
    const c = b.cfg;
    const dl = Math.hypot(dvx, dvy, dvz);
    if (dl > c.maxSpeed) { const k = c.maxSpeed / dl; dvx *= k; dvy *= k; dvz *= k; }
    let ax = (dvx - b.vx) * gain, ay = (dvy - b.vy) * gain, az = (dvz - b.vz) * gain;
    const al = Math.hypot(ax, ay, az);
    if (al > c.maxAcc) { const k = c.maxAcc / al; ax *= k; ay *= k; az *= k; }
    b.vx += ax * dt; b.vy += ay * dt; b.vz += az * dt;
    const hs = Math.hypot(b.vx, b.vz);
    if (b.state === S.FLY && hs < c.minSpeed) {
      const k = c.minSpeed / Math.max(hs, 0.01);
      if (hs < 0.01) { b.vx = Math.sin(b.yaw) * c.minSpeed; b.vz = Math.cos(b.yaw) * c.minSpeed; } else { b.vx *= k; b.vz *= k; }
    }
    b.x += b.vx * dt; b.y += b.vy * dt; b.z += b.vz * dt;
    if (b.y < 0.35) { b.y = 0.35; b.vy = Math.max(0, b.vy); }
    const sp = Math.hypot(b.vx, b.vz);
    if (sp > 0.3) b.yaw = Math.atan2(b.vx, b.vz);
    // lateral acceleration: right = (-cos yaw, 0, sin yaw); bank right = +
    const right = -ax * Math.cos(b.yaw) + az * Math.sin(b.yaw);
    const bankT = clamp(Math.atan(right / 9.8) * 1.4, -1.0, 1.0);
    b.bank += (bankT - b.bank) * Math.min(1, dt * 4);
    const pitchT = clamp(Math.atan2(b.vy, Math.max(sp, 0.5)) * 0.8, -0.5, 0.5);
    b.pitch += (pitchT - b.pitch) * Math.min(1, dt * 3);
    // flapping bouts and glides; always beat when climbing hard or slow
    b.bout -= dt;
    if (b.bout <= 0) {
      b.flapping = !b.flapping;
      const [lo, hi] = b.flapping ? c.flapOn : c.glide;
      b.bout = lo + this.rnd() * (hi - lo);
    }
    const want = forceFlap || b.flapping || b.vy > 1.2 || sp < c.cruise * 0.75 ? 1 : 0;
    b.flap += (want - b.flap) * Math.min(1, dt * 5);
    b.fold += (0 - b.fold) * Math.min(1, dt * 6);
    b.stand += (0 - b.stand) * Math.min(1, dt * 4);
    b.phase += c.freq * 6.283 * dt * (0.4 + 0.6 * b.flap);
    if (b.state === S.TAKEOFF) { b.t -= dt; if (b.t <= 0) b.state = S.FLY; }
  }

  /** Fly in to the perch: slow down, flare with quick beats, settle. */
  private approach(b: Bird, dt: number): void {
    const p = b.perch!;
    const ex = p.x - b.x, ey = p.y - b.y, ez = p.z - b.z;
    const dist = Math.hypot(ex, ey, ez);
    if (dist < 2.2) {
      const k = Math.min(1, dt * 2.5);
      b.x += ex * k; b.y += ey * k; b.z += ez * k;
      b.vx = ex * 2.5; b.vy = ey * 2.5; b.vz = ez * 2.5;
      b.flap += (1 - b.flap) * Math.min(1, dt * 6);
      b.phase += b.cfg.freq * 1.4 * 6.283 * dt;
      b.pitch += (0.45 - b.pitch) * Math.min(1, dt * 4);
      b.bank *= 1 - Math.min(1, dt * 4);
      if (b.kind === 'heron') b.stand += (1 - b.stand) * Math.min(1, dt * 3);
      if (dist < 0.12) this.sit(b, p, b.atRoost);
      return;
    }
    const sp = Math.min(b.cfg.cruise, 0.6 + dist * 0.7);
    this.steer(b, (ex / dist) * sp, (ey / dist) * sp, (ez / dist) * sp, 3, dt, dist < 6);
  }

  private perched(b: Bird, dt: number): void {
    b.fold += (1 - b.fold) * Math.min(1, dt * 3);
    b.flap += (0 - b.flap) * Math.min(1, dt * 5);
    b.pitch += (0 - b.pitch) * Math.min(1, dt * 3);
    b.bank = 0;
    // now and then a wing flick or a shuffle
    if (this.rnd() < dt * 0.05) { b.fold = 0.45; b.flap = 0.7; b.yaw += (this.rnd() - 0.5) * 1.2; }
    b.phase += b.cfg.freq * 6.283 * dt;
  }

  private updatePair(p: Pair, dt: number, h: number): void {
    const r = this.rnd;
    p.cx += WIND.x * dt * 1.4; p.cz += WIND.z * dt * 1.4; // the thermal drifts downwind
    let spread = 0;
    for (const b of p.birds) spread = Math.max(spread, Math.hypot(b.x - p.cx, b.z - p.cz));
    if (!p.gliding) {
      p.alt = Math.min(p.top, p.alt + 0.45 * dt);
      if (p.alt >= p.top && r() < dt * 0.02) {
        // top of the thermal: glide off to the next one
        const far = this.ways.filter((w) => { const d = Math.hypot(w.x - p.cx, w.z - p.cz); return d > 120 && d < 320; });
        const w = (far.length ? far : this.ways)[Math.floor(r() * (far.length || this.ways.length))];
        p.cx = w.x; p.cz = w.z; p.gliding = true;
      }
    } else {
      p.alt = Math.max(30, p.alt - 0.9 * dt);
      if (spread < 45) p.gliding = false;
    }
    for (const b of p.birds) {
      const down = this.raptorDown(b, h) && !!b.roost;
      if (down && b.state !== S.PERCH && b.state !== S.LAND) this.land(b, b.roost!, true);
      if (!down && b.state === S.PERCH) this.takeoff(b);
      if (!down && b.state === S.LAND) b.state = S.FLY;
      if (b.state === S.PERCH) { this.perched(b, dt); continue; }
      if (b.state === S.LAND) {
        // spiral down: approach() from a long way out is a straight glide
        this.approach(b, dt); continue;
      }
      let tx: number, tz: number;
      const ty = p.alt + b.cy;
      if (p.gliding && Math.hypot(p.cx - b.x, p.cz - b.z) > b.cx * 1.5) { tx = p.cx; tz = p.cz; }
      else {
        const a = Math.atan2(b.x - p.cx, b.z - p.cz) + 0.55;
        tx = p.cx + Math.sin(a) * b.cx; tz = p.cz + Math.cos(a) * b.cx;
      }
      const ex = tx - b.x, ez = tz - b.z, e = Math.hypot(ex, ez) || 1;
      const sp = p.gliding ? b.cfg.cruise * 1.35 : b.cfg.cruise;
      this.steer(b, (ex / e) * sp, clamp((ty - b.y) * 0.4, -2, 1.2), (ez / e) * sp, 1.5, dt);
      if (!p.gliding) b.flap *= 1 - Math.min(1, dt * 3); // soaring: wings held still
    }
    p.callT -= dt;
    if (p.callT <= 0) {
      p.callT = 14 + r() * 30;
      const b = p.birds[Math.floor(r() * 2)];
      if (b.state !== S.PERCH && this.onCall && this.inView(b.x, b.z)) this.onCall(p.kind, b.x, b.z);
    }
  }

  private swallowTarget(b: Bird, g: SwallowGroup): void {
    const r = this.rnd, n = this.frames.length;
    const f = this.frames[clamp(Math.round(g.idx + (r() - 0.5) * 30), 0, n - 1)];
    const lat = (r() - 0.5) * f.w * 0.8;
    b.cx = f.x + f.nx * lat; b.cz = f.z + f.nz * lat;
    const u = r();
    b.cy = u < 0.12 ? 0.15 : u > 0.92 ? 5 + r() * 4 : 0.6 + r() * 2.4; // a sip, a climb, skimming
    b.t = 1 + r() * 2.5;
  }

  private updateSwallows(g: SwallowGroup, dt: number, h: number): void {
    const n = this.frames.length;
    g.idx += g.dir * dt * 0.35;
    if (g.idx < 15 || g.idx > n - 15 || this.rnd() < dt * 0.01) g.dir = -g.dir;
    g.idx = clamp(g.idx, 10, n - 10);
    for (const b of g.birds) {
      const away = this.swallowAway(b, h);
      if (b.state === S.HIDDEN) {
        if (away) continue;
        this.flyAt(b, TOWN.x, 16, TOWN.z, 0, -8); // out from the eaves in town
        this.swallowTarget(b, g);
      }
      let tx = b.cx, ty = b.cy, tz = b.cz;
      if (away) {
        tx = TOWN.x; ty = 16; tz = TOWN.z;
        if (Math.hypot(b.x - TOWN.x, b.z - TOWN.z) < 25) { b.state = S.HIDDEN; continue; }
      } else {
        b.t -= dt;
        if (b.t <= 0 || Math.hypot(tx - b.x, tz - b.z) < 3) this.swallowTarget(b, g);
      }
      const ex = tx - b.x, ez = tz - b.z, e = Math.hypot(ex, ez) || 1;
      this.steer(b, (ex / e) * b.cfg.cruise, clamp((ty - b.y) * 1.5, -3, 3), (ez / e) * b.cfg.cruise, 3.5, dt);
    }
  }

  private updateHeron(b: Bird, dt: number): void {
    if (b.state === S.PERCH) {
      b.stand = 1; b.fold += (1 - b.fold) * Math.min(1, dt * 2); b.flap *= 1 - Math.min(1, dt * 4);
      b.t -= dt;
      if (b.t <= 0 && this.heronSpots.length > 2) {
        // off along the river to another spot 60-250 m away
        const cand = this.heronSpots.filter((s) => { const d = Math.hypot(s.x - b.x, s.z - b.z); return d > 60 && d < 250; });
        if (!cand.length) { b.t = 60; return; }
        const s = cand[Math.floor(this.rnd() * cand.length)];
        this.takeoff(b);
        b.vy = 1.6; b.perch = s; b.cx = s.x; b.cz = s.z;
        if (this.onCall && this.inView(b.x, b.z)) this.onCall('heron', b.x, b.z);
      }
      return;
    }
    if (b.state === S.LAND) {
      this.approach(b, dt);
      if ((b.state as S) === S.PERCH) b.t = 70 + this.rnd() * 150; // approach() may have landed it
      return;
    }
    const ex = b.cx - b.x, ez = b.cz - b.z, e = Math.hypot(ex, ez) || 1;
    if (e < 28 && b.state === S.FLY) { this.land(b, { x: b.cx, y: 0, z: b.cz, yaw: Math.atan2(ex, ez) }, false); return; }
    const sp = b.cfg.cruise;
    this.steer(b, (ex / e) * sp, clamp((8 - b.y) * 0.5, -1.5, 1.5), (ez / e) * sp, 1.2, dt, true);
  }

  private owlPerch(b: Bird, snap: boolean): void {
    const r = this.rnd;
    let t: Tree | undefined;
    if (b.state !== S.HIDDEN && !snap) {
      const near = this.trees.filter((q) => { const d = Math.hypot(q.x - b.x, q.z - b.z); return d > 20 && d < 90; });
      t = near[Math.floor(r() * near.length)];
    }
    if (!t) {
      // somewhere in the woods by the view if possible
      const vis = this.trees.filter((q) => this.inView(q.x, q.z, -60));
      const list = vis.length ? vis : this.trees;
      t = list[Math.floor(r() * list.length)];
    }
    const p = { x: t.x + (r() - 0.5) * t.r * 0.5, y: t.top * 0.95, z: t.z + (r() - 0.5) * t.r * 0.5, yaw: r() * 6.28 };
    if (snap) this.sit(b, p, false); else this.land(b, p, false);
    b.t = 40 + r() * 80;
  }

  private updateOwl(b: Bird, dt: number, h: number): void {
    const out = this.owlOut(h);
    if (!out) {
      if (b.state === S.PERCH || b.state === S.HIDDEN) { b.state = S.HIDDEN; return; }
    } else if (b.state === S.HIDDEN) { this.owlPerch(b, true); return; }
    if (b.state === S.PERCH) {
      this.perched(b, dt);
      b.t -= dt;
      if (b.t <= 0 || !out) { this.owlPerch(b, false); this.takeoff(b); b.state = S.LAND; b.flapping = true; }
      return;
    }
    if (b.state === S.LAND || b.state === S.TAKEOFF) {
      if (b.state === S.TAKEOFF) b.state = S.LAND;
      this.approach(b, dt);
    }
  }

  // ---------------------------------------------------------------- GPU upload

  private write(): void {
    let nb = 0;
    const blob = this.blobAttr.array as Float32Array;
    const boost = this.uBoost.value;
    for (const [kind, d] of this.draws) {
      const list = this.byKind.get(kind)!;
      const P = d.iPos.array as Float32Array, Rr = d.iRot.array as Float32Array;
      const W = d.iWing.array as Float32Array, T = d.iTint.array as Float32Array;
      let n = 0;
      for (const b of list) {
        if (b.state === S.HIDDEN || !this.inView(b.x, b.z)) continue;
        P[n * 3] = b.x; P[n * 3 + 1] = b.y; P[n * 3 + 2] = b.z;
        const sc = b.cfg.span * b.cfg.boost * b.size;
        Rr[n * 4] = b.yaw; Rr[n * 4 + 1] = b.pitch; Rr[n * 4 + 2] = b.bank; Rr[n * 4 + 3] = sc;
        W[n * 4] = b.phase; W[n * 4 + 1] = b.flap; W[n * 4 + 2] = b.fold; W[n * 4 + 3] = b.stand;
        T[n] = b.tint;
        n++;
        // a soft blob below the low fliers (and the heron standing)
        const hgt = b.y + (b.kind === 'heron' ? HERON_STAND.y * sc * boost * b.stand : 0);
        if (b.state !== S.PERCH && hgt < 16 || b.kind === 'heron') {
          const fade = 1 - hgt / 16;
          blob[nb * 4] = b.x - this.sun.x * hgt;
          blob[nb * 4 + 1] = b.z - this.sun.z * hgt;
          blob[nb * 4 + 2] = sc * boost * (0.55 + hgt * 0.03);
          blob[nb * 4 + 3] = 0.3 * fade * fade * this.uLight.value;
          nb++;
        }
      }
      d.geo.instanceCount = n;
      d.mesh.visible = n > 0;
      if (n) {
        for (const a of [d.iPos, d.iRot, d.iWing, d.iTint]) { a.needsUpdate = true; a.clearUpdateRanges(); a.addUpdateRange(0, n * a.itemSize); }
      }
    }
    this.blobGeo.instanceCount = nb;
    this.blobMesh.visible = nb > 0;
    if (nb) { this.blobAttr.needsUpdate = true; this.blobAttr.clearUpdateRanges(); this.blobAttr.addUpdateRange(0, nb * 4); }
  }

  // ---------------------------------------------------------------- debug

  /** Where a group is: rookery (its trees), rooks (first flock), kite, buzzard, heron, swallows, owl. */
  focus(name: string): { x: number; z: number; y: number } | null {
    const at = (b: Bird | undefined) => (b ? { x: b.x, y: b.y, z: b.z } : null);
    switch (name) {
      case 'rookery': return this.rookery ? { x: this.rookery.x, z: this.rookery.z, y: 12 } : null;
      case 'rooks': { const f = this.flocks[0]; return f ? { x: f.ax, z: f.az, y: f.ay } : null; }
      case 'kite': case 'buzzard': return at(this.pairs.find((p) => p.kind === name)?.birds[0]);
      case 'heron': return at(this.heron ?? undefined);
      case 'swallows': { const g = this.swallows[0]; if (!g) return null; const f = this.frames[Math.round(g.idx)]; return { x: f.x, z: f.z, y: 2 }; }
      case 'owl': return at(this.owl ?? undefined);
    }
    return null;
  }

  stats() {
    const kinds: Record<string, { total: number; drawn: number; flying: number; perched: number; hidden: number }> = {};
    for (const [k, list] of this.byKind) {
      if (!list.length) continue;
      kinds[k] = { total: list.length, drawn: this.draws.get(k)?.geo.instanceCount ?? 0,
        flying: list.filter((b) => b.state === S.FLY || b.state === S.TAKEOFF || b.state === S.LAND).length,
        perched: list.filter((b) => b.state === S.PERCH).length, hidden: list.filter((b) => b.state === S.HIDDEN).length };
    }
    return {
      birds: this.all.length, kinds,
      drawCalls: [...this.draws.values()].filter((d) => d.mesh.visible).length + (this.blobMesh.visible ? 1 : 0),
      updateMs: +this.updateMs.toFixed(3),
      flocks: this.flocks.map((f) => ({ n: f.birds.length, mode: f.mode, sitting: f.sitting, near: f.near,
        x: Math.round(f.ax), z: Math.round(f.az) })),
      territory: { trees: this.trees.length, woods: this.woods.length, ways: this.ways.length,
        rookery: this.rookery ? { x: Math.round(this.rookery.x), z: Math.round(this.rookery.z), trees: this.rookery.trees.length } : null,
        heronSpots: this.heronSpots.length },
    };
  }
}

/** __lublin.birds and the &birds=<group>[,zoom] hash (dev only). */
export function installBirdDebug(birds: Birds, camera: THREE.Camera,
  snapTo: (x: number, z: number, zoom?: number) => void): void {
  const w = window as unknown as { __lublin?: Record<string, unknown> };
  if (w.__lublin) w.__lublin.birds = birds;
  const apply = () => {
    const v = new URLSearchParams(location.hash.slice(1)).get('birds');
    if (!v) return;
    const [name, zoom] = v.split(',');
    // after the first update (reset), so flocks are placed for the hash's hour
    requestAnimationFrame(() => requestAnimationFrame(() => {
      const p = birds.focus(name);
      // the camera centre is on the ground: slide back along the view (1.41 m per m up)
      const d = camera.getWorldDirection(new THREE.Vector3()), l = Math.hypot(d.x, d.z) || 1;
      if (p) snapTo(p.x + (d.x / l) * p.y * 1.414, p.z + (d.z / l) * p.y * 1.414, zoom ? Number(zoom) : 40);
      else console.warn(`[birds] no group "${name}"`);
    }));
  };
  window.addEventListener('hashchange', apply);
  apply();
}
