import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

/**
 * Rigid-part rigs drawn as one InstancedMesh per model, shared by the wildlife (wildlife.ts) and
 * the stable's horses (horses.ts).
 *
 * Model format (build_animals.py): one glTF mesh per rigid part (node extras "part"), and scene
 * extras "animal" = JSON {pivots: {part: [x, y, z]}, tags?: {part: bit}}. The loader merges the
 * parts into one geometry with a part id per vertex (aPart) and the material's colour as vertex
 * colour. Per instance the pose is `nChan` floats (instanced vec4 attributes iP0..); the vertex
 * shader swings each part about its pivot by its [pitch, yaw, roll] channels, then about its
 * parents' (RigDef, up to `depth` levels).
 *
 * Options beyond the wildlife's:
 * - tagChan: a part with a tag bit is collapsed (not drawn) unless the instance's channel
 *   `tagChan` has that bit set (tack on a horse: saddle, bridle, collar...).
 * - coat: materials named *_coat and *_points take the instance's two colours (writeCoat);
 *   every other material keeps its own (without the option the instance colour multiplies).
 *   WebGL guarantees only 16 vertex attributes, so a 24-channel coat rig packs: the colour
 *   source rides in aPart (part + 64 * source) and both colours in one vec2 (24-bit each).
 *
 * BlobShadows: soft ellipses on the ground under animals, one instanced draw (moving things do
 * not go into the shadow map).
 */

/** Per part: [pitch channel, yaw channel, roll channel, parent part ('' = none)], -1 = no channel. */
export type RigDef = Record<string, [number, number, number, string]>;

export interface RigOptions {
  /** Program cache key: kinds with the same options share one compiled shader. */
  key: string;
  nPart: number;
  /** Pose channels per instance, a multiple of 4. */
  nChan: number;
  depth?: number;
  tagChan?: number;
  coat?: boolean;
}

export interface RigDraw {
  mesh: THREE.InstancedMesh;
  /** Pose attributes iP0.. (4 channels each). */
  p: THREE.InstancedBufferAttribute[];
  /** Coat and points colours per instance, packed (coat option; writeCoat). */
  coat: THREE.InstancedBufferAttribute | null;
  cap: number;
  parts: string[];
  pivots: THREE.Vector3[];
}

function vertexPars(o: RigOptions): string {
  const nv = o.nChan / 4;
  const attrs = Array.from({ length: nv }, (_, k) => `attribute vec4 iP${k};`).join(' ');
  let sel = `iP${nv - 1}`;
  for (let k = nv - 2; k >= 0; k--) sel = `i < ${(k + 1) * 4} ? iP${k} : ${sel}`;
  return /* glsl */`
#define NPART ${o.nPart}
attribute float aPart;
${attrs}
uniform vec3 uPiv[NPART];
uniform vec4 uCfg[NPART];
${o.tagChan !== undefined ? `#define RIG_TAGCH ${o.tagChan}.0\nuniform float uTag[NPART];` : ''}
${o.coat ? `attribute vec2 iCoat;
#define RIG_PART(a) int(mod(a + 0.5, 64.0))
#define RIG_TINT(a) floor((a + 0.5) / 64.0)
vec3 rigUnpack(float f) {
  float r = floor(f / 65536.0), g = floor((f - r * 65536.0) / 256.0), b = f - r * 65536.0 - g * 256.0;
  vec3 c = vec3(r, g, b) / 255.0;
  return c * c;
}` : '#define RIG_PART(a) int(a + 0.5)'}
vec3 wRX(vec3 v, float a) { float c = cos(a), s = sin(a); return vec3(v.x, v.y * c - v.z * s, v.y * s + v.z * c); }
vec3 wRY(vec3 v, float a) { float c = cos(a), s = sin(a); return vec3(v.x * c + v.z * s, v.y, -v.x * s + v.z * c); }
vec3 wRZ(vec3 v, float a) { float c = cos(a), s = sin(a); return vec3(v.x * c - v.y * s, v.x * s + v.y * c, v.z); }
float wChan(float fi) {
  int i = int(fi + 0.5);
  vec4 q = ${sel};
  int j = i - (i / 4) * 4;
  return j == 0 ? q.x : j == 1 ? q.y : j == 2 ? q.z : q.w;
}
void wPose(inout vec3 p, inout vec3 n) {
  int k = RIG_PART(aPart);
#ifdef RIG_TAGCH
  float tg = uTag[k];
  if (tg > 0.5 && mod(floor(wChan(RIG_TAGCH) / tg + 0.001), 2.0) < 0.5) { p = vec3(0.0); return; }
#endif
  for (int lv = 0; lv < ${o.depth ?? 4}; lv++) {
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
}

/** Load a rigid-part model (gltf from GLTFLoader) as an InstancedMesh for up to `cap` instances. */
export function makeRigMesh(gltf: { scene: THREE.Object3D }, rig: RigDef, o: RigOptions, cap: number, name: string): RigDraw {
  const meta = JSON.parse((gltf.scene.userData as { animal?: string }).animal ?? '{"pivots":{}}') as
    { pivots: Record<string, number[]>; tags?: Record<string, number> };
  const names = Object.keys(rig);
  const geos: THREE.BufferGeometry[] = [];
  gltf.scene.updateMatrixWorld(true);
  gltf.scene.traverse((ob) => {
    const mesh = ob as THREE.Mesh;
    if (!mesh.isMesh) return;
    let part: string | undefined;
    for (let p: THREE.Object3D | null = ob; p && !part; p = p.parent) part = (p.userData as { part?: string }).part;
    const k = names.indexOf(part ?? 'body');
    const g = mesh.geometry.clone().applyMatrix4(mesh.matrixWorld);
    const mat = mesh.material as THREE.MeshStandardMaterial;
    const n = g.getAttribute('position').count;
    const col = new Float32Array(n * 3), id = new Float32Array(n);
    // coat option: the colour source rides in aPart (part + 64 * tint), as WebGL has only 16 attributes
    const tint = o.coat ? (mat.name.endsWith('_coat') ? 1 : mat.name.endsWith('_points') ? 2 : 0) : 0;
    for (let v = 0; v < n; v++) { col[v * 3] = mat.color.r; col[v * 3 + 1] = mat.color.g; col[v * 3 + 2] = mat.color.b; id[v] = Math.max(0, k) + 64 * tint; }
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
  const tags = names.map((nm) => meta.tags?.[nm] ?? 0);
  while (piv.length < o.nPart) { piv.push(new THREE.Vector3()); cfg.push(new THREE.Vector4(-1, -1, -1, -1)); tags.push(0); }
  const p: THREE.InstancedBufferAttribute[] = [];
  for (let k = 0; k < o.nChan / 4; k++) {
    const at = new THREE.InstancedBufferAttribute(new Float32Array(cap * 4), 4).setUsage(THREE.DynamicDrawUsage);
    geo.setAttribute(`iP${k}`, at);
    p.push(at);
  }
  let coat: THREE.InstancedBufferAttribute | null = null;
  if (o.coat) {
    coat = new THREE.InstancedBufferAttribute(new Float32Array(cap * 2), 2).setUsage(THREE.DynamicDrawUsage);
    geo.setAttribute('iCoat', coat);
  }
  const mat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.9, metalness: 0 });
  mat.onBeforeCompile = (sh) => {
    sh.uniforms.uPiv = { value: piv };
    sh.uniforms.uCfg = { value: cfg };
    if (o.tagChan !== undefined) sh.uniforms.uTag = { value: tags };
    let vs = vertexPars(o) + sh.vertexShader
      .replace('#include <beginnormal_vertex>', 'vec3 objectNormal = vec3(normal);\nvec3 wP = position;\nwPose(wP, objectNormal);')
      .replace('#include <begin_vertex>', 'vec3 transformed = wP;');
    if (o.coat) {
      vs = vs.replace('#include <color_vertex>',
        '#include <color_vertex>\nfloat rTint = RIG_TINT(aPart);\nvColor.rgb = rTint < 0.5 ? color.rgb : rigUnpack(rTint < 1.5 ? iCoat.x : iCoat.y);');
    }
    sh.vertexShader = vs;
  };
  // Same shader for every model with these options (the rig is in the uniforms): one program,
  // compiled once, not a stall per kind the first time one comes into view.
  mat.customProgramCacheKey = () => o.key;
  const mesh = new THREE.InstancedMesh(geo, mat, cap);
  mesh.name = name;
  mesh.frustumCulled = false;
  mesh.castShadow = false;
  mesh.receiveShadow = true;
  mesh.count = 0;
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  if (!o.coat) mesh.setColorAt(0, new THREE.Color(1, 1, 1));
  return { mesh, p, coat, cap, parts: names, pivots: piv };
}

/** A linear colour as 24-bit sRGB-ish (sqrt) in one float, for iCoat. */
function packColor(c: THREE.Color): number {
  const q = (v: number) => Math.round(Math.sqrt(Math.min(1, Math.max(0, v))) * 255);
  return q(c.r) * 65536 + q(c.g) * 256 + q(c.b);
}

/** Instance n's coat and points colours (coat option). */
export function writeCoat(d: RigDraw, n: number, coat: THREE.Color, points: THREE.Color): void {
  const a = d.coat!.array as Float32Array;
  a[n * 2] = packColor(coat); a[n * 2 + 1] = packColor(points);
}

/** Write instance n's pose channels (ch.length = the rig's nChan). */
export function writePose(d: RigDraw, n: number, ch: ArrayLike<number>): void {
  for (let c = 0; c < ch.length; c++) (d.p[c >> 2].array as Float32Array)[n * 4 + (c & 3)] = ch[c];
}

/** Mark instance data written this frame (count = instances drawn). */
export function commitRig(d: RigDraw, count: number): void {
  d.mesh.count = count;
  d.mesh.visible = count > 0;
  if (!count) return;
  d.mesh.instanceMatrix.needsUpdate = true;
  if (d.mesh.instanceColor) d.mesh.instanceColor.needsUpdate = true;
  for (const at of d.p) at.needsUpdate = true;
  if (d.coat) d.coat.needsUpdate = true;
}

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

/** Soft blob shadows: begin(), add() per animal, end(). Long axis along the heading. */
export class BlobShadows {
  readonly mesh: THREE.Mesh;
  private geo = new THREE.InstancedBufferGeometry();
  private attr: THREE.InstancedBufferAttribute;
  private dir: THREE.InstancedBufferAttribute;
  private n = 0;

  constructor(scene: THREE.Scene, cap: number, name: string) {
    const quad = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
    cap = Math.max(1, cap);
    this.geo.index = quad.index;
    this.geo.setAttribute('position', quad.getAttribute('position'));
    this.attr = new THREE.InstancedBufferAttribute(new Float32Array(cap * 4), 4).setUsage(THREE.DynamicDrawUsage);
    this.dir = new THREE.InstancedBufferAttribute(new Float32Array(cap * 2), 2).setUsage(THREE.DynamicDrawUsage);
    this.geo.setAttribute('iBlob', this.attr);
    this.geo.setAttribute('iDir', this.dir);
    this.geo.instanceCount = 0;
    this.mesh = new THREE.Mesh(this.geo, new THREE.ShaderMaterial({
      vertexShader: BLOB_VERT, fragmentShader: BLOB_FRAG, transparent: true, depthWrite: false,
    }));
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = 1;
    this.mesh.visible = false;
    this.mesh.name = name;
    scene.add(this.mesh);
  }

  begin(): void { this.n = 0; }

  add(x: number, z: number, radius: number, alpha: number, yaw: number): void {
    const b = this.attr.array as Float32Array, d = this.dir.array as Float32Array, n = this.n;
    if (n >= b.length / 4) return;
    b[n * 4] = x; b[n * 4 + 1] = z; b[n * 4 + 2] = radius; b[n * 4 + 3] = alpha;
    d[n * 2] = Math.cos(yaw); d[n * 2 + 1] = Math.sin(yaw);
    this.n++;
  }

  end(): void {
    this.geo.instanceCount = this.n;
    this.mesh.visible = this.n > 0;
    if (this.n) { this.attr.needsUpdate = true; this.dir.needsUpdate = true; }
  }

  hide(): void { this.mesh.visible = false; }
}
