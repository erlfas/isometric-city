import * as THREE from 'three';
import type { CityPlan, River, RiverCrossing, RiverMill, VegetationElement } from '../types';
import type { Tint } from './static-batches';

/**
 * The Bystrzyca's banks beyond the water itself (river.ts): per-tree colour variation for
 * the woods, the footpaths painted into the ground splat, and the watermill's turning wheel
 * with its race and white water. Data from the plan (generate_city_plan.py stage 4:
 * vegetation, paths, river.crossings, river.mills).
 */

/** Wheel axle in the watermill's model space (glTF axes): build_assets.py MILL_WHEEL_X / _Z. */
const WHEEL_AXLE = new THREE.Vector3(4.9, 1.7, 0);
const WHEEL_R = 2.4;
/** Turning speed (rad/s): rim ~1 m/s, about the race's current. One turn in ~15 s. */
const WHEEL_OMEGA = 0.42;
const RACE_Y = 0.045;          // above the river surface (0.03), so the mouth does not z-fight
const FOAM = 56;
const DROPS = 48;

function hashId(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}

/**
 * Per-plant colour multiplier: crowns vary in lightness and between a yellower and a bluer
 * green (sun-lit edge trees vs shaded ones), bark and stones in lightness only. The species
 * colour itself is in the vertex colours; this multiplies it.
 */
export function vegetationTint(v: VegetationElement): Tint {
  const h = hashId(v.id);
  const r = (k: number) => (((h >>> (k * 5)) & 31) / 31) * 2 - 1; // [-1, 1]
  const light = 1 + r(0) * 0.11;
  const warm = r(1) * 0.07;
  const leaves = new THREE.Color(light * (1 + warm), light * (1 + warm * 0.35), light * (1 - warm * 1.2));
  const wood = new THREE.Color().setScalar(1 + r(2) * 0.1);
  return (mat) => {
    const name = mat.name || '';
    if (name.startsWith('Leaves')) return { material: mat, tint: leaves };
    if (name.startsWith('Bark') || name.startsWith('RiverStone')) return { material: mat, tint: wood };
    return null;
  };
}

/** Low plants in their hundreds whose shadows are lost in the trees' (no shadow casters:
 *  ~90k shadow-map triangles less in a forest view). */
export const SHADOWLESS = new Set(['fern_clump', 'reed_clump']);

type XZ = { x: number; z: number };

/** Each crossing's deck as a walkable strip for the nav grid (NavGrid openings): the middle
 *  of the deck between the handrails, run half a metre onto the banks at both ends. */
export function bridgeOpenings(river: River | undefined): XZ[][] {
  return (river?.crossings ?? []).map((c) => {
    const a = (c.angle * Math.PI) / 180, ux = Math.cos(a), uz = Math.sin(a);
    const h = c.length * 0.5 + 0.6, w = c.width * 0.5 - 0.35;
    return [[-h, -w], [h, -w], [h, w], [-h, w]].map(([s, t]) => ({ x: c.x + ux * s - uz * t, z: c.z + uz * s + ux * t }));
  });
}

/** Mill races as quads (nav obstacles: nobody walks through the race), widened by `extra`. */
export function raceQuads(river: River | undefined, extra = 0.3): XZ[][] {
  const quads: XZ[][] = [];
  for (const m of river?.mills ?? []) {
    const r = m.race;
    const side = (i: number, s: number): XZ => {
      const a = r[Math.max(0, i - 1)], b = r[Math.min(r.length - 1, i + 1)];
      const l = Math.hypot(b.x - a.x, b.z - a.z) || 1;
      const o = s * (r[i].width * 0.5 + extra);
      return { x: r[i].x - ((b.z - a.z) / l) * o, z: r[i].z + ((b.x - a.x) / l) * o };
    };
    for (let i = 0; i + 1 < r.length; i++) quads.push([side(i, 1), side(i + 1, 1), side(i + 1, -1), side(i, -1)]);
  }
  return quads;
}

/** Height of the walking surface at (x, z) if it is on a bridge deck, else null. */
export function deckHeight(crossings: readonly RiverCrossing[], x: number, z: number): number | null {
  for (const c of crossings) {
    const a = (c.angle * Math.PI) / 180, dx = x - c.x, dz = z - c.z;
    const s = dx * Math.cos(a) + dz * Math.sin(a), t = -dx * Math.sin(a) + dz * Math.cos(a);
    const h = c.length * 0.5;
    if (Math.abs(s) > h || Math.abs(t) > c.width * 0.5 + 0.3) continue;
    const u = s / h;
    return c.deckEnd + (c.deckMid - c.deckEnd) * (1 - u * u);
  }
  return null;
}

/** Footpaths, the mill track and forest rides as trodden dirt in the ground splat (blue). */
export function paintPaths(ctx: CanvasRenderingContext2D, plan: CityPlan): void {
  const paths = plan.paths ?? [];
  const mills = plan.river?.mills ?? [];
  if (!paths.length && !mills.length) return;
  ctx.save();
  // world (x -350..350, z -275..275) -> canvas 2048 x 2048
  ctx.setTransform(2048 / 700, 0, 0, 2048 / 550, (350 * 2048) / 700, (275 * 2048) / 550);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  const stroke = (pts: { x: number; z: number }[], width: number, style: string, blurPx: number, op: GlobalCompositeOperation) => {
    ctx.globalCompositeOperation = op;
    ctx.filter = blurPx > 0 ? `blur(${blurPx}px)` : 'none';
    ctx.strokeStyle = style;
    ctx.lineWidth = width;
    ctx.beginPath();
    pts.forEach((p, k) => (k ? ctx.lineTo(p.x, p.z) : ctx.moveTo(p.x, p.z)));
    ctx.stroke();
  };
  for (const p of paths) {
    // Worn verge (grass thinning out), then the trodden middle; rides are grassier.
    const core = p.kind === 'ride' ? 'rgb(0,0,120)' : 'rgb(0,0,215)';
    stroke(p.points, p.width + 1.6, 'rgb(0,0,70)', 4, 'lighter');
    stroke(p.points, p.width, core, 2, 'lighter');
  }
  // The mill race's banks: wet dark earth.
  for (const m of mills) stroke(m.race, 3.6, 'rgba(0,40,190,0.95)', 3, 'source-over');
  ctx.restore();
}

interface Wheel {
  obj: THREE.Object3D;
  base: THREE.Quaternion;
  /** Axle centre (world), the flow direction along the race (unit, x-z) and the race mouth. */
  at: THREE.Vector3;
  fx: number; fz: number;
  mouth: THREE.Vector3;
  spin: number;
}

interface Bit { x: number; y: number; z: number; vx: number; vy: number; vz: number; age: number; life: number; s: number }

/**
 * The watermills' wheels (one moving object each, not in the static batches), the water in
 * their races and the white water where the paddles strike it. `ripple` (river.addRipple)
 * rings the river where the race falls back in.
 */
export class MillWheels {
  readonly wheels: Wheel[] = [];
  private foam: THREE.InstancedMesh;
  private drops: THREE.InstancedMesh;
  private foamBits: Bit[] = [];
  private dropBits: Bit[] = [];
  private raceTex: THREE.CanvasTexture | null = null;
  private last = performance.now();
  private nextFoam = 0;
  private nextRipple = 0;
  private m = new THREE.Matrix4();
  private q = new THREE.Quaternion();
  private v = new THREE.Vector3();
  private s = new THREE.Vector3();
  private c = new THREE.Color();
  private water = new THREE.Color(0x5d7f7c);
  private white = new THREE.Color(0xf4f7f2);
  ripple: ((x: number, z: number, strength: number) => void) | null = null;

  /** `mills`: each mill's placed matrix (as the parcel was put) and its plan entry. */
  constructor(scene: THREE.Scene, template: THREE.Object3D | undefined, mills: { matrix: THREE.Matrix4; mill: RiverMill }[]) {
    const foamGeo = new THREE.CircleGeometry(1, 10).rotateX(-Math.PI / 2);
    this.foam = new THREE.InstancedMesh(foamGeo, new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.85, depthWrite: false }), FOAM);
    this.drops = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 0), new THREE.MeshBasicMaterial({ color: 0xeef4f2 }), DROPS);
    for (const im of [this.foam, this.drops]) {
      im.count = 0;
      im.frustumCulled = false;
      im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      scene.add(im);
    }
    this.foam.setColorAt(0, this.white); // allocates instanceColor
    this.foam.renderOrder = 2;
    for (const { matrix, mill } of mills) {
      if (mill.race.length > 1) scene.add(this.raceMesh(mill));
      if (!template) continue;
      const obj = template.clone(true);
      obj.traverse((o) => { if ((o as THREE.Mesh).isMesh) { o.castShadow = true; o.receiveShadow = true; } });
      const at = WHEEL_AXLE.clone().applyMatrix4(matrix);
      const base = new THREE.Quaternion();
      matrix.decompose(this.v, base, this.s);
      obj.position.copy(at);
      obj.quaternion.copy(base);
      scene.add(obj);
      const r = mill.race;
      const a = r[0], b = r[r.length - 1];
      const fl = Math.hypot(b.x - a.x, b.z - a.z) || 1;
      const fx = (b.x - a.x) / fl, fz = (b.z - a.z) / fl;
      // Turn so that the paddles at the bottom move with the current: the bottom's velocity
      // for a positive turn about the local X axle is local -Z.
      const vel = new THREE.Vector3(0, 0, -1).applyQuaternion(base);
      const spin = vel.x * fx + vel.z * fz >= 0 ? 1 : -1;
      this.wheels.push({ obj, base, at, fx, fz, mouth: new THREE.Vector3(b.x, 0, b.z), spin });
    }
  }

  /** A ribbon of slow brown-green water down the race, fading in and out at the river. */
  private raceMesh(mill: RiverMill): THREE.Mesh {
    const r = mill.race;
    const pos: number[] = [], uv: number[] = [], col: number[] = [], idx: number[] = [];
    let along = 0;
    for (let i = 0; i < r.length; i++) {
      const a = r[Math.max(0, i - 1)], b = r[Math.min(r.length - 1, i + 1)];
      const l = Math.hypot(b.x - a.x, b.z - a.z) || 1;
      const nx = -(b.z - a.z) / l, nz = (b.x - a.x) / l;
      if (i) along += Math.hypot(r[i].x - r[i - 1].x, r[i].z - r[i - 1].z);
      const half = r[i].width * 0.5;
      const alpha = Math.min(1, i / 2.5, (r.length - 1 - i) / 2.5);
      for (const s of [-1, 1]) {
        pos.push(r[i].x + nx * half * s, RACE_Y, r[i].z + nz * half * s);
        uv.push(s * 0.5 + 0.5, along / 3);
        col.push(1, 1, 1, alpha);
      }
      if (i) { const k = i * 2; idx.push(k - 2, k - 1, k, k - 1, k + 1, k); } // counter-clockwise from above
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    g.setAttribute('color', new THREE.Float32BufferAttribute(col, 4));
    g.setIndex(idx);
    const normals = new Float32Array(pos.length);
    for (let k = 1; k < normals.length; k += 3) normals[k] = 1; // flat water: straight up
    g.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
    this.raceTex ??= this.streaks();
    const mat = new THREE.MeshStandardMaterial({
      color: 0x4f6f6a, roughness: 0.18, metalness: 0.0, map: this.raceTex, vertexColors: true,
      transparent: true, depthWrite: false,
    });
    const mesh = new THREE.Mesh(g, mat);
    mesh.receiveShadow = true;
    mesh.name = 'mill_race';
    mesh.renderOrder = 1;
    return mesh;
  }

  /** Light streaks of the current (repeats along the race; scrolled in update). */
  private streaks(): THREE.CanvasTexture {
    const cv = document.createElement('canvas');
    cv.width = 32; cv.height = 128;
    const g = cv.getContext('2d')!;
    g.fillStyle = '#bfbfbf';
    g.fillRect(0, 0, 32, 128);
    for (let k = 0; k < 26; k++) {
      const x = 3 + Math.random() * 26, y = Math.random() * 128, len = 10 + Math.random() * 30;
      g.fillStyle = `rgba(255,255,255,${0.25 + Math.random() * 0.4})`;
      g.fillRect(x, y, 1 + Math.random() * 1.5, len);
      g.fillRect(x, y - 128, 1 + Math.random() * 1.5, len);
    }
    const t = new THREE.CanvasTexture(cv);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
  }

  /** Turn (rad) between shadow redraws: ~7 a second (the renderer asks shadowDue()). */
  static readonly SHADOW_STEP = 0.06;
  private angle = 0;
  private shadowAngle = -1;

  /** True once per SHADOW_STEP of turning: time to redraw the wheels' shadows. */
  shadowDue(): boolean {
    if (Math.abs(this.angle - this.shadowAngle) < MillWheels.SHADOW_STEP) return false;
    this.shadowAngle = this.angle;
    return true;
  }

  /** Turn the wheels and animate the white water (real time, like the river). */
  update(): void {
    const now = performance.now();
    const dt = Math.min(0.1, (now - this.last) / 1000);
    this.last = now;
    const t = now / 1000;
    this.angle = WHEEL_OMEGA * t;
    if (this.raceTex) this.raceTex.offset.y = -t * 0.32; // 3 m per repeat: ~1 m/s
    for (const w of this.wheels) {
      this.q.setFromAxisAngle(_X, w.spin * WHEEL_OMEGA * t);
      w.obj.quaternion.copy(w.base).multiply(this.q);
    }
    this.nextFoam -= dt;
    while (this.nextFoam < 0 && this.wheels.length) {
      this.nextFoam += 0.045;
      for (const w of this.wheels) this.spawn(w);
    }
    this.nextRipple -= dt;
    if (this.nextRipple < 0) {
      this.nextRipple = 0.7 + Math.random() * 0.6;
      for (const w of this.wheels) this.ripple?.(w.mouth.x + (Math.random() - 0.5) * 1.5, w.mouth.z + (Math.random() - 0.5) * 1.5, 0.55);
    }
    this.step(this.foamBits, this.foam, dt, true);
    this.step(this.dropBits, this.drops, dt, false);
  }

  private spawn(w: Wheel): void {
    // Where the paddles strike the water: just upstream of the axle; foam rides off downstream.
    const side = (Math.random() - 0.5) * 1.5;
    const ax = -w.fz, az = w.fx; // across the race
    const off = (Math.random() - 0.3) * 2.0;
    if (this.foamBits.length < FOAM) {
      this.foamBits.push({
        x: w.at.x + w.fx * off + ax * side, y: RACE_Y + 0.02, z: w.at.z + w.fz * off + az * side,
        vx: w.fx * (0.9 + Math.random() * 0.5), vy: 0, vz: w.fz * (0.9 + Math.random() * 0.5),
        age: 0, life: 1.2 + Math.random() * 1.4, s: 0.18 + Math.random() * 0.22,
      });
    }
    if (this.dropBits.length < DROPS && Math.random() < 0.7) {
      // Water shed by a paddle rising out on the downstream side, thrown up and on.
      const up = 0.4 + Math.random() * 1.2;
      const k = Math.sqrt(Math.max(0, WHEEL_R * WHEEL_R - (w.at.y - up) * (w.at.y - up)));
      this.dropBits.push({
        x: w.at.x + w.fx * k + ax * side, y: up, z: w.at.z + w.fz * k + az * side,
        vx: w.fx * (0.6 + Math.random() * 0.8), vy: 0.6 + Math.random() * 1.0, vz: w.fz * (0.6 + Math.random() * 0.8),
        age: 0, life: 2, s: 0.035 + Math.random() * 0.03,
      });
    }
  }

  private step(bits: Bit[], im: THREE.InstancedMesh, dt: number, foam: boolean): void {
    let n = 0;
    for (let i = 0; i < bits.length; i++) {
      const b = bits[i];
      b.age += dt;
      b.x += b.vx * dt; b.z += b.vz * dt;
      if (foam) {
        b.vx *= 1 - 0.4 * dt; b.vz *= 1 - 0.4 * dt;
      } else {
        b.vy -= 9.8 * dt; b.y += b.vy * dt;
        if (b.y < RACE_Y) b.age = b.life;
      }
      if (b.age >= b.life) continue;
      bits[n++] = b;
      const k = b.age / b.life;
      const sc = foam ? b.s * (0.6 + k * 1.6) : b.s;
      this.v.set(b.x, b.y, b.z);
      this.s.set(sc, sc, sc);
      this.m.compose(this.v, _Q0, this.s);
      im.setMatrixAt(n - 1, this.m);
      if (foam) im.setColorAt(n - 1, this.c.copy(this.white).lerp(this.water, k * k));
    }
    bits.length = n;
    im.count = n;
    im.instanceMatrix.needsUpdate = true;
    if (foam && im.instanceColor) im.instanceColor.needsUpdate = true;
  }
}

const _X = new THREE.Vector3(1, 0, 0);
const _Q0 = new THREE.Quaternion();
