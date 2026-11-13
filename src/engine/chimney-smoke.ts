import * as THREE from 'three';
import { nightFactor } from './door-leaves';

/**
 * Chimney smoke (M7): soft camera-facing puffs rising from the flues of buildings whose
 * hearth burns (sim.hearths: someone awake at home, or a smith / baker at work). One draw
 * call: an instanced quad per live puff, position + (size, alpha) per instance. Only flues
 * inside the view emit; puffs drift with a light, steady wind and fade as they spread.
 */

const MAX = 1500;
const EVERY = 0.45;    // real s between puffs of one flue
const LIFE = 5.5;      // real s a puff lives
const RISE = 0.75;     // m/s
const WIND = new THREE.Vector3(0.32, 0, 0.14);
const DAY = new THREE.Color(0.66, 0.64, 0.61);
const NIGHT = new THREE.Color(0.16, 0.16, 0.19);

export class ChimneySmoke {
  private pos = new Float32Array(MAX * 3);
  private puff = new Float32Array(MAX * 2);
  private age = new Float32Array(MAX);
  private seed = new Float32Array(MAX);
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
    this.iPuff = new THREE.InstancedBufferAttribute(this.puff, 2).setUsage(THREE.DynamicDrawUsage);
    this.geo.setAttribute('iPos', this.iPos);
    this.geo.setAttribute('iPuff', this.iPuff);
    this.geo.instanceCount = 0;
    this.mat = new THREE.ShaderMaterial({
      uniforms: { uColor: { value: DAY.clone() } },
      vertexShader: `
attribute vec3 iPos; attribute vec2 iPuff;
varying vec2 vUv; varying float vA;
void main() {
  vUv = uv; vA = iPuff.y;
  vec4 mv = viewMatrix * vec4(iPos, 1.0);
  mv.xy += position.xy * iPuff.x;
  gl_Position = projectionMatrix * mv;
}`,
      fragmentShader: `
uniform vec3 uColor;
varying vec2 vUv; varying float vA;
void main() {
  vec2 d = vUv - 0.5;
  float r = length(d) * 2.0;
  // Lumpy edge: a few lobes so puffs don't read as discs.
  float lobes = 0.85 + 0.15 * sin(atan(d.y, d.x) * 5.0 + vA * 40.0);
  float a = smoothstep(lobes, 0.15, r) * vA;
  if (a < 0.01) discard;
  gl_FragColor = vec4(uColor * (1.05 - 0.25 * r), a);
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
      if (!this.flues.has(f)) this.flues.set(f, Math.random() * EVERY);
    }
    for (const f of this.flues.keys()) if (!keep.has(f)) this.flues.delete(f);
  }

  get burning(): number { return this.flues.size; }

  update(dt: number, camera: THREE.Camera, hour: number): void {
    this.mat.uniforms.uColor.value.copy(DAY).lerp(NIGHT, nightFactor(hour));
    this.m4.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    this.frustum.setFromProjectionMatrix(this.m4);
    // New puffs from flues in view.
    for (const [f, t] of this.flues) {
      let left = t - dt;
      if (left <= 0) {
        left += EVERY * (0.7 + Math.random() * 0.6);
        this.sphere.center.set(f.x, f.y + 2, f.z);
        if (this.n < MAX && this.frustum.intersectsSphere(this.sphere)) {
          const k = this.n++;
          this.pos[k * 3] = f.x + (Math.random() - 0.5) * 0.15;
          this.pos[k * 3 + 1] = f.y + 0.1;
          this.pos[k * 3 + 2] = f.z + (Math.random() - 0.5) * 0.15;
          this.age[k] = 0;
          this.seed[k] = Math.random();
        }
      }
      this.flues.set(f, left);
    }
    // Age, rise, drift, grow, fade; dead puffs swap with the last.
    for (let k = 0; k < this.n; k++) {
      const a = (this.age[k] += dt);
      if (a >= LIFE) {
        const last = --this.n;
        this.pos.copyWithin(k * 3, last * 3, last * 3 + 3);
        this.age[k] = this.age[last];
        this.seed[k] = this.seed[last];
        k--;
        continue;
      }
      const u = a / LIFE;
      const slow = 1 - u * 0.6; // rising slows as it cools
      this.pos[k * 3] += WIND.x * dt * (0.4 + u);
      this.pos[k * 3 + 1] += RISE * slow * dt;
      this.pos[k * 3 + 2] += WIND.z * dt * (0.4 + u);
      this.puff[k * 2] = 0.45 + 1.9 * Math.sqrt(u) + this.seed[k] * 0.3;
      this.puff[k * 2 + 1] = Math.min(1, a / 0.4) * (1 - u) * (1 - u) * 0.55 + this.seed[k] * 0.001;
    }
    this.geo.instanceCount = this.n;
    if (this.n) {
      this.iPos.needsUpdate = true;
      this.iPuff.needsUpdate = true;
      this.iPos.addUpdateRange(0, this.n * 3);
      this.iPuff.addUpdateRange(0, this.n * 2);
    }
  }
}
