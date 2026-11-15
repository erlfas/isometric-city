import * as THREE from 'three';
import { nightFactor } from './door-leaves';
import { FLUE_STYLE, type FlueStyle } from './building-anchors';

/**
 * Chimney smoke (M7): soft camera-facing puffs rising from the flues of buildings whose
 * hearth burns (sim.hearths: someone awake at home, or a smith / baker at work). One draw
 * call: an instanced quad per live puff, position + (size, alpha, shade) per instance. Only
 * flues inside the view emit; puffs drift with a light, steady wind and fade as they spread.
 * Flue styles (anchor_chimney's style, FLUE_STYLE): a charcoal clamp's vents breathe thick,
 * slow, pale smoke; a bloomery shaft puffs dark smoke with a few sparks (shade < 0: drawn
 * as a hot ember that night does not darken).
 */

const MAX = 1500;
const WIND = new THREE.Vector3(0.32, 0, 0.14);
const DAY = new THREE.Color(0.66, 0.64, 0.61);
const NIGHT = new THREE.Color(0.16, 0.16, 0.19);

interface Style {
  every: number;   // real s between puffs of one flue
  life: number;    // real s a puff lives
  rise: number;    // m/s
  size0: number; grow: number;
  alpha: number;
  shade: number;   // colour multiplier (< 0: spark)
  spark: number;   // chance a puff is a spark instead
}
const STYLES: Record<FlueStyle | 'spark', Style> = {
  chimney: { every: 0.45, life: 5.5, rise: 0.75, size0: 0.45, grow: 1.9, alpha: 0.55, shade: 1, spark: 0 },
  clamp: { every: 1.1, life: 9, rise: 0.32, size0: 0.7, grow: 3.0, alpha: 0.42, shade: 1.18, spark: 0 },
  furnace: { every: 0.3, life: 4.2, rise: 1.1, size0: 0.4, grow: 1.6, alpha: 0.62, shade: 0.42, spark: 0.18 },
  spark: { every: 0, life: 1.3, rise: 1.9, size0: 0.11, grow: -0.06, alpha: 1, shade: -1, spark: 0 },
};
const STYLE_LIST: Style[] = [STYLES.chimney, STYLES.clamp, STYLES.furnace, STYLES.spark];
const STYLE_INDEX: Record<FlueStyle, number> = { chimney: 0, clamp: 1, furnace: 2 };
const SPARK = 3;

export class ChimneySmoke {
  private pos = new Float32Array(MAX * 3);
  private puff = new Float32Array(MAX * 3);
  private age = new Float32Array(MAX);
  private seed = new Float32Array(MAX);
  private kind = new Uint8Array(MAX);
  private n = 0;
  private geo = new THREE.InstancedBufferGeometry();
  private mat: THREE.ShaderMaterial;
  private mesh: THREE.Mesh;
  private iPos: THREE.InstancedBufferAttribute;
  private iPuff: THREE.InstancedBufferAttribute;
  private flues = new Map<THREE.Vector3, number>(); // flue -> seconds until the next puff
  private frustum = new THREE.Frustum();
  private m4 = new THREE.Matrix4();
  private sphere = new THREE.Sphere(new THREE.Vector3(), 3);

  constructor(scene: THREE.Scene) {
    const quad = new THREE.PlaneGeometry(1, 1);
    this.geo.index = quad.index;
    this.geo.setAttribute('position', quad.getAttribute('position'));
    this.geo.setAttribute('uv', quad.getAttribute('uv'));
    this.iPos = new THREE.InstancedBufferAttribute(this.pos, 3).setUsage(THREE.DynamicDrawUsage);
    this.iPuff = new THREE.InstancedBufferAttribute(this.puff, 3).setUsage(THREE.DynamicDrawUsage);
    this.geo.setAttribute('iPos', this.iPos);
    this.geo.setAttribute('iPuff', this.iPuff);
    this.geo.instanceCount = 0;
    this.mat = new THREE.ShaderMaterial({
      uniforms: { uColor: { value: DAY.clone() } },
      vertexShader: `
attribute vec3 iPos; attribute vec3 iPuff;
varying vec2 vUv; varying float vA; varying float vShade;
void main() {
  vUv = uv; vA = iPuff.y; vShade = iPuff.z;
  vec4 mv = viewMatrix * vec4(iPos, 1.0);
  mv.xy += position.xy * iPuff.x;
  gl_Position = projectionMatrix * mv;
}`,
      fragmentShader: `
uniform vec3 uColor;
varying vec2 vUv; varying float vA; varying float vShade;
void main() {
  vec2 d = vUv - 0.5;
  float r = length(d) * 2.0;
  if (vShade < 0.0) {
    // Spark: a hot ember, white-orange core.
    float a = smoothstep(1.0, 0.3, r) * vA;
    if (a < 0.01) discard;
    gl_FragColor = vec4(mix(vec3(1.0, 0.45, 0.1), vec3(1.0, 0.9, 0.6), smoothstep(0.6, 0.0, r)), a);
    return;
  }
  // Lumpy edge: a few lobes so puffs don't read as discs.
  float lobes = 0.85 + 0.15 * sin(atan(d.y, d.x) * 5.0 + vA * 40.0);
  float a = smoothstep(lobes, 0.15, r) * vA;
  if (a < 0.01) discard;
  gl_FragColor = vec4(min(uColor * vShade, vec3(1.0)) * (1.05 - 0.25 * r), a);
}`,
      transparent: true,
      depthWrite: false,
    });
    this.mesh = new THREE.Mesh(this.geo, this.mat);
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = 2;
    scene.add(this.mesh);
  }

  /** Flues burning now (call when the set changes, e.g. twice a second). */
  setFlues(flues: Iterable<THREE.Vector3>): void {
    const keep = new Set<THREE.Vector3>();
    for (const f of flues) {
      keep.add(f);
      if (!this.flues.has(f)) this.flues.set(f, Math.random() * this.styleOf(f).every);
    }
    for (const f of this.flues.keys()) if (!keep.has(f)) this.flues.delete(f);
  }

  get burning(): number { return this.flues.size; }
  /** Live puffs (the MAX budget). */
  get puffs(): number { return this.n; }

  private styleOf(f: THREE.Vector3): Style { return STYLES[FLUE_STYLE.get(f) ?? 'chimney']; }

  update(dt: number, camera: THREE.Camera, hour: number): void {
    this.mat.uniforms.uColor.value.copy(DAY).lerp(NIGHT, nightFactor(hour));
    this.m4.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    this.frustum.setFromProjectionMatrix(this.m4);
    // New puffs from flues in view.
    for (const [f, t] of this.flues) {
      let left = t - dt;
      if (left <= 0) {
        const fs = FLUE_STYLE.get(f) ?? 'chimney';
        const st = STYLES[fs];
        left += st.every * (0.7 + Math.random() * 0.6);
        this.sphere.center.set(f.x, f.y + 2, f.z);
        if (this.n < MAX && this.frustum.intersectsSphere(this.sphere)) {
          const k = this.n++;
          const spread = fs === 'clamp' ? 0.3 : 0.15;
          this.pos[k * 3] = f.x + (Math.random() - 0.5) * spread;
          this.pos[k * 3 + 1] = f.y + 0.1;
          this.pos[k * 3 + 2] = f.z + (Math.random() - 0.5) * spread;
          this.age[k] = 0;
          this.seed[k] = Math.random();
          this.kind[k] = Math.random() < st.spark ? SPARK : STYLE_INDEX[fs];
        }
      }
      this.flues.set(f, left);
    }
    // Age, rise, drift, grow, fade; dead puffs swap with the last.
    for (let k = 0; k < this.n; k++) {
      const st = STYLE_LIST[this.kind[k]];
      const a = (this.age[k] += dt);
      if (a >= st.life) {
        const last = --this.n;
        this.pos.copyWithin(k * 3, last * 3, last * 3 + 3);
        this.age[k] = this.age[last];
        this.seed[k] = this.seed[last];
        this.kind[k] = this.kind[last];
        k--;
        continue;
      }
      const u = a / st.life;
      const slow = 1 - u * 0.6; // rising slows as it cools
      const spark = this.kind[k] === SPARK;
      const jitter = spark ? (this.seed[k] - 0.5) * 1.2 : 0;
      this.pos[k * 3] += (WIND.x * (0.4 + u) + jitter) * dt;
      this.pos[k * 3 + 1] += st.rise * slow * dt;
      this.pos[k * 3 + 2] += (WIND.z * (0.4 + u) - jitter * 0.6) * dt;
      this.puff[k * 3] = st.size0 + st.grow * Math.sqrt(u) + this.seed[k] * (spark ? 0.04 : 0.3);
      this.puff[k * 3 + 1] = spark
        ? (1 - u) * (0.6 + 0.4 * Math.sin(a * 30 + this.seed[k] * 9))
        : Math.min(1, a / 0.4) * (1 - u) * (1 - u) * st.alpha + this.seed[k] * 0.001;
      this.puff[k * 3 + 2] = st.shade;
    }
    this.geo.instanceCount = this.n;
    if (this.n) {
      this.iPos.needsUpdate = true;
      this.iPuff.needsUpdate = true;
      this.iPos.addUpdateRange(0, this.n * 3);
      this.iPuff.addUpdateRange(0, this.n * 3);
    }
  }
}
