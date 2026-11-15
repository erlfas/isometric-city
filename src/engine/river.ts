import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import type { River, RiverPoint as PlanRiverPoint } from '../types';
import { riverFrames, type RiverFrame } from './river-course';
// Fish only jump on the ground plane; the water (its course run on past the map by
// extendRiver) fades out at the outer edge of the forest skirt.
import { GROUND_HALF, SKIRT } from './world-edge';

/**
 * The Bystrzyca's water (CityPlan.river): one ribbon mesh with a flowing water shader, leaves
 * and twigs drifting with the current, fish jumping, and ripple rings that drift downstream.
 *
 * Flow: the shader scrolls three noise layers (broad swell, fine ripples, long flow streaks)
 * downstream along the ribbon's v (arc length, m) at the local current, two phases cross-faded
 * every FLOW_PERIOD seconds so the cross-stream shear stays bounded. The current is fastest
 * mid-stream and on the outside of bends, slow at the banks (flowSpeed; the shader's riverSpeed
 * is generated from the same FLOW constants). Everything runs on real time, not sim time.
 *
 * Light: the water is a MeshStandardMaterial (lit by the scene's sun, hemisphere and ambient,
 * receives the sun's shadow) whose colour, normal and alpha come from the shader; a sky
 * reflection (fresnel, from the light preset's sky and background) and sun glitter are added
 * after lighting, the glitter masked by the shadow map. It casts nothing, so it never makes the
 * shadow map redraw.
 *
 * Ripples (addRipple): up to RIPPLES rings in a uniform array, each drifting with flowAt();
 * fish, rises (and later ducks, the watermill) feed it.
 */

/** Mid-stream current on a straight (m/s). */
export const FLOW_BASE = 0.45;
/** The ribbon runs this far past the water's edge onto the painted bank (m), for the soft shore. */
const OVERHANG = 1.2;
const RIPPLES = 16;
const RIPPLE_LIFE = 4.5;
/** Seconds per flow phase (the two phases are half a period apart). */
const FLOW_PERIOD = 7;
const DEBRIS = 64;
const DROPS = 72;
const FISH = 4;
/** Fish jumps and rises per minute per 100 m of river in view (times the debug multiplier). */
const JUMPS_PER_MIN = 1.6;
const RISES_PER_MIN = 2.6;

/** Current profile, shared by flowSpeed() and the shader's riverSpeed() (injected below):
 *  speed at the banks (x mid-stream), bend gain per unit curvature, its cap, and how much of
 *  it goes to the outside of the bend. */
const FLOW = { bank: 0.3, curvGain: 22, bendMax: 0.55, outside: 0.9 };

/** Current speed (m/s) at u (-1..1 across the water, + = left bank) where the course curves by curv. */
export function flowSpeed(u: number, curv: number): number {
  const uc = Math.max(-1, Math.min(1, u));
  const profile = FLOW.bank + (1 - FLOW.bank) * (1 - uc * uc);
  const bend = Math.min(FLOW.bendMax, Math.abs(curv) * FLOW.curvGain);
  const outside = -Math.sign(curv) * uc; // > 0 on the outside of the bend
  return FLOW_BASE * profile * (1 + bend * outside * FLOW.outside);
}
const glf = (v: number) => v.toFixed(4);

/** The light preset fields the water uses (LIGHT_PRESETS in three-renderer.ts). */
export interface RiverLight { sun: number; sunI: number; sky: number; hemiI: number; bg: number }

export interface RiverPoint {
  /** Closest point on the centreline. */
  x: number; z: number;
  /** Segment index and fraction along it. */
  i: number; t: number;
  /** Arc length from the source (m). */
  s: number;
  /** Across the water: -1..1 between the banks (+ = left of the flow); beyond on the banks. */
  u: number;
  /** Distance from the centreline (m). */
  dist: number;
  inWater: boolean;
  /** Downstream unit direction. */
  dx: number; dz: number;
  /** Half the water's width here (m) and the course's curvature (1/m). */
  half: number; curv: number;
}

export interface RiverFlow { vx: number; vz: number; speed: number }

interface Drift { s: number; u: number; rot: number; spin: number; sx: number; sz: number; ph: number }
interface Jump { x: number; z: number; dx: number; dz: number; len: number; h: number; t: number; dur: number; roll: number }
interface Drop { x: number; y: number; z: number; vx: number; vy: number; vz: number; life: number; size: number }

const WATER_PARS = /* glsl */ `
#define RIPPLES ${RIPPLES}
varying vec4 vRiver;
varying vec2 vRN;
varying vec3 vWPos;
uniform float uTime;
uniform vec2 uFlowT;
uniform float uFlowW;
uniform vec4 uRipples[RIPPLES];
uniform vec3 uDeep;
uniform vec3 uShallow;
uniform vec3 uStreak;
uniform vec3 uFoam;
uniform vec3 uSkyHorizon;
uniform vec3 uSkyZenith;
uniform vec3 uSunCol;
uniform float uSkyAmt;
uniform vec3 uViewDir;
uniform vec3 uGlintDir;
uniform vec2 uGround;
uniform float uSpeedMul;
uniform float uShallowSky;
#ifdef RACE
varying float vFade;
#endif

float rHash(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}
vec2 rGrad(vec2 z) { float h = rHash(z) * 6.2831853; return vec2(cos(h), sin(h)); }
// Gradient noise with its derivatives (x = value, yz = d/dp), about -0.7..0.7.
vec3 gnoised(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  vec2 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
  vec2 du = 30.0 * f * f * (f * (f - 2.0) + 1.0);
  vec2 ga = rGrad(i), gb = rGrad(i + vec2(1.0, 0.0)), gc = rGrad(i + vec2(0.0, 1.0)), gd = rGrad(i + vec2(1.0, 1.0));
  float va = dot(ga, f), vb = dot(gb, f - vec2(1.0, 0.0)), vc = dot(gc, f - vec2(0.0, 1.0)), vd = dot(gd, f - vec2(1.0, 1.0));
  return vec3(va + u.x * (vb - va) + u.y * (vc - va) + u.x * u.y * (va - vb - vc + vd),
    ga + u.x * (gb - ga) + u.y * (gc - ga) + u.x * u.y * (ga - gb - gc + gd)
    + du * (u.yx * (va - vb - vc + vd) + vec2(vb, vc) - va));
}
// flowSpeed() in river.ts, same constants (FLOW).
float riverSpeed(float u, float curv) {
  float profile = ${glf(FLOW.bank)} + ${glf(1 - FLOW.bank)} * (1.0 - u * u);
  float bend = min(${glf(FLOW.bendMax)}, abs(curv) * ${glf(FLOW.curvGain)});
  return ${glf(FLOW_BASE)} * profile * (1.0 + bend * (-sign(curv) * u) * ${glf(FLOW.outside)});
}
`;

const WATER_MAIN = /* glsl */ `
  float rU = vRiver.x, rV = vRiver.y, rCurv = vRiver.z, rHalf = vRiver.w;
  vec2 rN = normalize(vRN);
  vec2 rT = vec2(rN.y, -rN.x);
  float uM = rU * rHalf;
  float uc = clamp(rU, -1.0, 1.0);
  // Noisy shoreline: metres from the water's edge, wobbling with a still pattern.
  float shoreN = gnoised(vWPos.xz * 0.42).x + 0.5 * gnoised(vWPos.xz * 1.3 + 7.1).x;
  float dShore = (1.0 - abs(rU)) * rHalf + shoreN * min(0.7, rHalf * 0.22);
  float depth = smoothstep(0.0, rHalf * 0.55, dShore);
#ifdef STILL
  // Standing pool: the noise in world space (radial u/v would draw rings round its centre),
  // and a narrower pale rim (a peat hole is deep almost to its edge).
  uM = vWPos.x; rV = vWPos.z;
  depth = smoothstep(0.0, rHalf * 0.3, dShore);
#endif
  float speed = riverSpeed(uc, rCurv) * uSpeedMul;
  float outside = clamp(-sign(rCurv) * uc, 0.0, 1.0) * clamp(abs(rCurv) * 30.0, 0.0, 1.0);
  // Slow sideways wobble so the surface does not slide like a conveyor belt.
  float wob = 0.45 * sin(rV * 0.13 + uTime * 0.31) + 0.25 * sin(rV * 0.37 - uTime * 0.53 + uM * 0.4);

  vec2 g = vec2(0.0);   // height gradient in (across, along)
  float streak = 0.0, foamN = 0.0, sparkle = 0.0;
  for (int k = 0; k < 2; k++) {
    float ph = k == 0 ? uFlowT.x : uFlowT.y;
    float w = k == 0 ? uFlowW : 1.0 - uFlowW;
    vec2 seed = k == 0 ? vec2(0.0) : vec2(17.3, 41.9);
    float along = rV - speed * ph;
    vec3 n1 = gnoised(vec2((uM + wob) * 0.5, along * 0.2) + seed);
    g += w * 0.42 * vec2(n1.y * 0.5, n1.z * 0.2);
    vec3 n2 = gnoised(vec2((uM - wob * 0.6) * 1.6, (rV - speed * 1.18 * ph) * 0.75) + seed * 1.7);
    g += w * 0.09 * vec2(n2.y * 1.6, n2.z * 0.75);
    vec3 n3 = gnoised(vec2((uM + wob * 0.8) * 1.25, along * 0.07) + seed * 0.6);
    streak += w * n3.x;
    g += w * 0.08 * vec2(n3.y * 1.25, n3.z * 0.07);
    vec3 n4 = gnoised(vec2((uM + wob) * 4.2, (rV - speed * 1.1 * ph) * 2.6) + seed * 2.9);
    sparkle += w * n4.x;
    g += w * 0.016 * vec2(n4.y * 4.2, n4.z * 2.6);
    foamN += w * (gnoised(vec2(uM * 2.0, along * 0.8) + seed * 2.3).x
      + 0.5 * gnoised(vec2(uM * 5.0, along * 2.0) + seed).x);
  }
  // Calmer, flatter shallows.
  g *= mix(0.4, 1.0, depth);
  vec2 gW = g.x * rN + g.y * rT;

  // Ripple rings (fish, rises, splashes), drifting with the current on the CPU side.
  float ring = 0.0;
  for (int k = 0; k < RIPPLES; k++) {
    vec4 r = uRipples[k];
    if (r.w <= 0.0) continue;
    vec2 dv = vWPos.xz - r.xy;
    float dist = length(dv) + 1e-4;
    float rad = 0.1 + r.z * 0.55;
    float x = dist - rad;
    float env = exp(-x * x * 9.0) * r.w * exp(-r.z * 0.75) / sqrt(1.0 + 2.0 * rad);
    // trailing wavelets inside the leading crest
    env *= smoothstep(-0.9, -0.1, x) + 0.0;
    gW += (dv / dist) * env * cos(x * 15.0) * 0.45;
    ring += env * max(0.0, sin(x * 15.0)) * 1.6;
  }
  vec3 wN = normalize(vec3(-gW.x, 1.0, -gW.y));

  float st = smoothstep(0.18, 0.5, streak) * (0.3 + 0.7 * depth);
  // Foam: a broken line at the waterline, wider on the outside of bends, and fresh rings.
  float band = 0.22 + outside * 1.0;
  float fEdge = (1.0 - smoothstep(0.0, band, dShore)) * smoothstep(-0.25, 0.05, dShore);
  float foam = fEdge * smoothstep(0.5, 0.9, foamN * 0.5 + 0.5 + outside * 0.25) * 0.85;
#ifdef STILL
  foam = 0.0;
#endif
  foam = clamp(foam + ring * 0.5, 0.0, 1.0);

  vec3 body = mix(uShallow, uDeep, depth);
  body = mix(body, uStreak, st * 0.55);
  body = mix(body, uFoam, foam);
  float alpha = mix(0.5, 0.97, depth) * smoothstep(-0.15, 0.55, dShore);
  alpha = max(alpha, foam * 0.85 * smoothstep(-0.25, 0.0, dShore));
  vec2 gEdge = uGround - abs(vWPos.xz);
  float aGround = smoothstep(0.0, 5.0, min(gEdge.x, gEdge.y));
  alpha *= aGround;
#ifdef RACE
  alpha *= vFade;
#endif
  diffuseColor = vec4(body, alpha);
`;

const WATER_POST = /* glsl */ `
  {
    float sunVis = 1.0;
    #if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 0
      sunVis = getShadow( directionalShadowMap[ 0 ], directionalLightShadows[ 0 ].shadowMapSize,
        directionalLightShadows[ 0 ].shadowIntensity, directionalLightShadows[ 0 ].shadowBias,
        directionalLightShadows[ 0 ].shadowRadius, vDirectionalShadowCoord[ 0 ] );
    #endif
    vec3 V = -uViewDir;
    float NdV = clamp(dot(wN, V), 0.0, 1.0);
    float fres = (0.08 + 0.9 * pow(1.0 - NdV, 3.0)) * uSkyAmt;
    vec3 R = reflect(uViewDir, wN);
    vec3 sky = mix(uSkyHorizon, uSkyZenith, smoothstep(0.35, 0.85, R.y));
    float a = max(diffuseColor.a, 0.2);
    float clear = (1.0 - foam) * aGround;
    // Sky in the surface, more of it where the water is deep and dark.
    outgoingLight += sky * fres * clear * mix(uShallowSky, 1.0, depth) + sky * st * 0.08 * clear;
    // Sun glitter: facets tilted toward the glint direction; a broad sheen around them.
    float gd = max(dot(R, uGlintDir), 0.0);
    float glint = pow(gd, 2200.0) * smoothstep(0.25, 0.55, sparkle);
    float sheen = pow(gd, 10.0);
    outgoingLight += uSunCol * (glint * 2.4 + sheen * 0.05 * depth) * sunVis * clear / a;
    outgoingLight += sky * ring * 0.3 * clear;
    diffuseColor.a = clamp(diffuseColor.a + glint * sunVis * 0.5 * aGround, 0.0, 1.0);
  }
`;

export class RiverWater {
  readonly frames: RiverFrame[];
  /** Arc length at each centreline point (m). */
  readonly cum: Float64Array;
  readonly length: number;
  readonly mesh: THREE.Mesh;
  /** Bounding box of the course (x0, z0, x1, z1), for the in-view test. */
  private bbox = [Infinity, Infinity, -Infinity, -Infinity];

  private uniforms = {
    uTime: { value: 0 },
    uFlowT: { value: new THREE.Vector2() },
    uFlowW: { value: 1 },
    uRipples: { value: Array.from({ length: RIPPLES }, () => new THREE.Vector4()) },
    uDeep: { value: new THREE.Color() },
    uShallow: { value: new THREE.Color() },
    uStreak: { value: new THREE.Color() },
    uFoam: { value: new THREE.Color() },
    uSkyHorizon: { value: new THREE.Color() },
    uSkyZenith: { value: new THREE.Color() },
    uSunCol: { value: new THREE.Color() },
    uSkyAmt: { value: 1 },
    uViewDir: { value: new THREE.Vector3(0, -1, 0) },
    uGlintDir: { value: new THREE.Vector3(0, 1, 0) },
    uGround: { value: new THREE.Vector2(GROUND_HALF[0] + SKIRT, GROUND_HALF[1] + SKIRT) },
    /** How much of the sky the shallows mirror (x the deep water's). */
    uShallowSky: { value: 0.55 },
  };
  /** Ripple rings: centre x, z, age (s), strength (0 = free). */
  private ripples = this.uniforms.uRipples.value;

  private debris: THREE.InstancedMesh;
  private drifts: Drift[] = [];
  private fish: THREE.InstancedMesh;
  private jumps: (Jump | null)[] = new Array(FISH).fill(null);
  private drops: THREE.InstancedMesh;
  private dropState: Drop[] = [];
  private nextJump = 3;
  private nextRise = 1.5;
  private last = -1;
  private view = [0, 0, 0, 0];
  /** Arc-length span of the course in view, and its length in view (m). */
  private sView = [0, 0];
  private lenInView = 0;
  private inView = false;
  /** Debug: multiplies the jump and rise rates (hash &fish=N). */
  public fishRate = 1;
  private stat = { jumps: 0, rises: 0, ripples: 0 };
  private m = new THREE.Matrix4();
  private q = new THREE.Quaternion();
  private e = new THREE.Euler(0, 0, 0, 'YZX');
  private p = new THREE.Vector3();
  private sc = new THREE.Vector3();
  private sunDir = new THREE.Vector3();

  constructor(scene: THREE.Scene, river: River) {
    this.frames = riverFrames(river);
    const f = this.frames, n = f.length;
    this.cum = new Float64Array(n);
    for (let i = 1; i < n; i++) this.cum[i] = this.cum[i - 1] + Math.hypot(f[i].x - f[i - 1].x, f[i].z - f[i - 1].z);
    this.length = this.cum[n - 1];
    for (const p of f) {
      const r = p.w * 0.5 + OVERHANG;
      this.bbox[0] = Math.min(this.bbox[0], p.x - r); this.bbox[1] = Math.min(this.bbox[1], p.z - r);
      this.bbox[2] = Math.max(this.bbox[2], p.x + r); this.bbox[3] = Math.max(this.bbox[3], p.z + r);
    }

    this.mesh = new THREE.Mesh(this.buildRibbon(), this.buildMaterial());
    this.mesh.name = 'river_water';
    this.mesh.receiveShadow = true;
    this.mesh.castShadow = false;
    this.mesh.frustumCulled = true;
    this.mesh.renderOrder = 1;
    scene.add(this.mesh);

    // Leaves, foam flecks and twigs (one draw call).
    const leaf = new THREE.BufferGeometry();
    leaf.setAttribute('position', new THREE.Float32BufferAttribute([1, 0, 0, 0, 0, 0.45, -1, 0, 0, 0, 0, -0.45], 3));
    leaf.setAttribute('normal', new THREE.Float32BufferAttribute([0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0], 3));
    leaf.setIndex([0, 2, 1, 0, 3, 2]);
    this.debris = new THREE.InstancedMesh(leaf, new THREE.MeshStandardMaterial({ roughness: 0.85, side: THREE.DoubleSide }), DEBRIS);
    this.debris.name = 'river_debris';
    this.debris.frustumCulled = false;
    this.debris.renderOrder = 2;
    const palette = ['#c8902c', '#a65a22', '#d9b24a', '#7f8a2e', '#8c4a1e', '#e8e4d6', '#efece0', '#5c4630'];
    const col = new THREE.Color();
    for (let k = 0; k < DEBRIS; k++) {
      const kind = k % palette.length;
      const foam = kind === 5 || kind === 6, twig = kind === 7;
      const s = foam ? 0.1 + Math.random() * 0.08 : 0.14 + Math.random() * 0.08;
      this.drifts.push({
        s: Math.random() * this.length, u: (Math.random() * 2 - 1) * 0.75, rot: Math.random() * 6.28,
        spin: (Math.random() * 2 - 1) * 0.35, sx: twig ? 0.4 : s, sz: twig ? 0.06 : foam ? s : s * 0.9,
        ph: Math.random() * 6.28,
      });
      this.debris.setColorAt(k, col.set(palette[kind]));
    }
    scene.add(this.debris);

    // Fish: a silvery body with a tail fin, along +x; a big chub or asp (~0.55 m), so a leap
    // reads at the usual zooms. A little emissive: the flank flashes in any light.
    const body = new THREE.SphereGeometry(1, 10, 6).scale(0.27, 0.07, 0.05).toNonIndexed();
    const tail = new THREE.BufferGeometry();
    tail.setAttribute('position', new THREE.Float32BufferAttribute([-0.22, 0, 0, -0.4, 0.1, 0, -0.4, -0.1, 0], 3));
    tail.setAttribute('normal', new THREE.Float32BufferAttribute([0, 0, 1, 0, 0, 1, 0, 0, 1], 3));
    tail.setAttribute('uv', new THREE.Float32BufferAttribute([0, 0, 1, 0, 0, 1], 2));
    const fishGeo = mergeGeometries([body, tail])!;
    this.fish = new THREE.InstancedMesh(fishGeo, new THREE.MeshStandardMaterial({
      color: 0xd8e0e2, roughness: 0.25, metalness: 0.1, emissive: 0x8a969a, emissiveIntensity: 0.35, side: THREE.DoubleSide }), FISH);
    this.fish.name = 'river_fish';
    this.fish.frustumCulled = false;
    this.fish.count = 0;
    scene.add(this.fish);

    // Splash droplets.
    this.drops = new THREE.InstancedMesh(new THREE.OctahedronGeometry(1, 0),
      new THREE.MeshStandardMaterial({ color: 0xf2f6f6, roughness: 0.4, emissive: 0x9fb0b4, emissiveIntensity: 0.45 }), DROPS);
    this.drops.name = 'river_spray';
    this.drops.frustumCulled = false;
    this.drops.count = 0;
    for (let k = 0; k < DROPS; k++) this.dropState.push({ x: 0, y: 0, z: 0, vx: 0, vy: 0, vz: 0, life: 0, size: 0 });
    scene.add(this.drops);
  }

  /** The water ribbon along `f` (arc lengths `cum`); `fade` (race): alpha 0..1 per point. */
  private buildRibbon(f = this.frames, cum: ArrayLike<number> = this.cum, overhang = OVERHANG, y = 0.03,
    fade?: number[]): THREE.BufferGeometry {
    const n = f.length, C = 10; // columns across
    const pos: number[] = [], nor: number[] = [], river: number[] = [], rn: number[] = [], idx: number[] = [], fd: number[] = [];
    for (let i = 0; i < n; i++) {
      const p = f[i], half = p.w * 0.5, R = half + overhang;
      for (let j = 0; j <= C; j++) {
        // denser near the edges, where the shore detail is
        const a = (j / C) * 2 - 1, o = Math.sign(a) * Math.pow(Math.abs(a), 0.8) * R;
        pos.push(p.x + p.nx * o, y, p.z + p.nz * o);
        nor.push(0, 1, 0);
        river.push(o / half, cum[i], p.curv, half);
        rn.push(p.nx, p.nz);
        if (fade) fd.push(fade[i]);
      }
    }
    for (let i = 0; i + 1 < n; i++) {
      for (let j = 0; j < C; j++) {
        const a = i * (C + 1) + j, b = a + 1, c = a + C + 1, d = c + 1;
        idx.push(a, b, c, b, d, c);
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
    g.setAttribute('aRiver', new THREE.Float32BufferAttribute(river, 4));
    g.setAttribute('aRN', new THREE.Float32BufferAttribute(rn, 2));
    if (fade) g.setAttribute('aFade', new THREE.Float32BufferAttribute(fd, 1));
    g.setIndex(idx);
    g.computeBoundingSphere();
    g.computeBoundingBox();
    return g;
  }

  /** The water material; a race's (speedMul > 1) runs faster and fades in and out along aFade;
   *  still water (speedMul 0, the bog pools) has no aFade. */
  private buildMaterial(speedMul = 1): THREE.Material {
    const race = speedMul > 1, still = speedMul === 0;
    const mat = new THREE.MeshStandardMaterial({ roughness: 0.35, metalness: 0, transparent: true, depthWrite: false });
    mat.name = race ? 'RaceWater' : still ? 'PoolWater' : 'RiverWater';
    if (race) mat.defines = { RACE: '' };
    if (still) mat.defines = { STILL: '' };
    mat.customProgramCacheKey = () => (race ? 'race-water-v1' : still ? 'pool-water-v1' : 'river-water-v1');
    const speed = { value: speedMul };
    mat.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, this.uniforms, { uSpeedMul: speed });
      shader.vertexShader = 'attribute vec4 aRiver;\nattribute vec2 aRN;\nvarying vec4 vRiver;\nvarying vec2 vRN;\nvarying vec3 vWPos;\n'
        + (race ? 'attribute float aFade;\nvarying float vFade;\n' : '')
        + shader.vertexShader.replace('#include <begin_vertex>',
          '#include <begin_vertex>\n  vRiver = aRiver; vRN = aRN; vWPos = (modelMatrix * vec4(transformed, 1.0)).xyz;'
          + (race ? ' vFade = aFade;' : ''));
      shader.fragmentShader = WATER_PARS + shader.fragmentShader
        .replace('#include <color_fragment>', WATER_MAIN)
        .replace('#include <normal_fragment_maps>', 'normal = normalize((viewMatrix * vec4(wN, 0.0)).xyz);')
        .replace('#include <opaque_fragment>', WATER_POST + '#include <opaque_fragment>');
    };
    return mat;
  }

  /**
   * A mill race (upstream first) as the same water, running ~2.4x the river's current toward
   * the wheel and fading in and out where it leaves and rejoins the river.
   */
  raceWater(race: PlanRiverPoint[]): THREE.Mesh | null {
    if (race.length < 2) return null;
    // Resample to ~1 m, so the frames (and the flow's curvature) are smooth.
    const pts: PlanRiverPoint[] = [];
    for (let i = 0; i + 1 < race.length; i++) {
      const a = race[i], b = race[i + 1], k = Math.max(1, Math.round(Math.hypot(b.x - a.x, b.z - a.z)));
      for (let j = 0; j < k; j++) pts.push({ x: a.x + (b.x - a.x) * j / k, z: a.z + (b.z - a.z) * j / k, width: a.width + (b.width - a.width) * j / k });
    }
    pts.push(race[race.length - 1]);
    const f = riverFrames({ name: 'race', flow: '', lengthM: 0, points: pts });
    const cum: number[] = [0];
    for (let i = 1; i < f.length; i++) cum.push(cum[i - 1] + Math.hypot(f[i].x - f[i - 1].x, f[i].z - f[i - 1].z));
    const L = cum[cum.length - 1];
    const fade = cum.map((s) => Math.min(1, s / 3, (L - s) / 3));
    const mesh = new THREE.Mesh(this.buildRibbon(f, cum, 0.35, 0.045, fade), this.buildMaterial(2.4));
    mesh.name = 'mill_race';
    mesh.receiveShadow = true;
    mesh.renderOrder = 1;
    return mesh;
  }

  /**
   * Standing pools (the ironworks bog, plan.grounds kind 'pool') as the river's water, still:
   * one fan per ring, shore at the ring (pushed out `grow` m under the painted mud's edge),
   * deepest at its centre. One mesh for all of them.
   */
  poolWater(rings: { x: number; z: number }[][], grow = 0.6): THREE.Mesh | null {
    const pos: number[] = [], nor: number[] = [], river: number[] = [], rn: number[] = [], idx: number[] = [];
    for (const raw of rings) {
      if (raw.length < 3) continue;
      // Round the plan's few-cornered rings (Chaikin, 3 passes), else the shallows show the corners.
      let ring = raw;
      for (let pass = 0; pass < 3; pass++) {
        const out: { x: number; z: number }[] = [];
        for (let k = 0; k < ring.length; k++) {
          const a = ring[k], b = ring[(k + 1) % ring.length];
          out.push({ x: a.x * 0.75 + b.x * 0.25, z: a.z * 0.75 + b.z * 0.25 }, { x: a.x * 0.25 + b.x * 0.75, z: a.z * 0.25 + b.z * 0.75 });
        }
        ring = out;
      }
      const n = ring.length;
      const cx = ring.reduce((s, q) => s + q.x, 0) / n, cz = ring.reduce((s, q) => s + q.z, 0) / n;
      // Half-width: the centre's distance to the nearest edge (the shallows' scale).
      let half = Infinity;
      for (let k = 0; k < n; k++) {
        const a = ring[k], b = ring[(k + 1) % n];
        const ex = b.x - a.x, ez = b.z - a.z, L2 = ex * ex + ez * ez || 1;
        const t = Math.max(0, Math.min(1, ((cx - a.x) * ex + (cz - a.z) * ez) / L2));
        half = Math.min(half, Math.hypot(cx - a.x - ex * t, cz - a.z - ez * t));
      }
      half = Math.max(0.8, half + grow);
      const base = pos.length / 3;
      const vert = (x: number, z: number, u: number) => {
        pos.push(x, 0.03, z); nor.push(0, 1, 0); river.push(u, x + z, 0, half); rn.push(1, 0);
      };
      vert(cx, cz, 0);
      for (const q of ring) {           // mid ring, then the shore
        vert(cx + (q.x - cx) * 0.5, cz + (q.z - cz) * 0.5, 0.5);
      }
      for (const q of ring) {
        const dx = q.x - cx, dz = q.z - cz, d = Math.hypot(dx, dz) || 1;
        vert(q.x + (dx / d) * grow, q.z + (dz / d) * grow, 1);
      }
      for (let k = 0; k < n; k++) {
        const k1 = (k + 1) % n, m0 = base + 1 + k, m1 = base + 1 + k1, s0 = m0 + n, s1 = m1 + n;
        idx.push(base, m1, m0, m0, m1, s1, m0, s1, s0);
      }
    }
    if (!idx.length) return null;
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
    g.setAttribute('aRiver', new THREE.Float32BufferAttribute(river, 4));
    g.setAttribute('aRN', new THREE.Float32BufferAttribute(rn, 2));
    g.setIndex(idx);
    g.computeBoundingSphere();
    g.computeBoundingBox();
    const mat = this.buildMaterial(0);
    mat.side = THREE.DoubleSide;        // rings come in either winding
    const mesh = new THREE.Mesh(g, mat);
    mesh.name = 'bog_pools';
    mesh.receiveShadow = true;
    mesh.renderOrder = 1;
    return mesh;
  }

  /** Colours for the light preset now in use (called when the preset changes). */
  setLight(p: RiverLight): void {
    const u = this.uniforms, c = new THREE.Color();
    const bg = new THREE.Color(p.bg), sky = new THREE.Color(p.sky);
    const lvl = p.hemiI / 2.35;
    // Water body (lit by the scene): dark green-blue deep, olive-brown shallows over the bed.
    u.uDeep.value.set('#143047');
    u.uShallow.value.set('#4b5a4a');
    u.uStreak.value.set('#5f8494');
    u.uFoam.value.set('#e9ede6');
    // The reflected sky: the background's colour toward the zenith, the warm fill near the horizon.
    // Dawn and dusk keep a cool, bright sky overhead (else the warm light turns the water to mud);
    // at night only the dark blue background and the moon.
    const night = p.sunI < 1.5;
    const low = !night && p.sunI < 3; // dawn, dusk: low warm sun, darker mirror-like water
    const k = night ? Math.max(0.35, lvl) : low ? 1.6 : Math.max(0.8, lvl);
    // Low sun: the warm light would turn a lit body to mauve mud, so the water is mostly a
    // mirror then: a dark slate body under a strong reflection of a pale, cool upper sky that
    // warms toward the horizon. It reads lighter and cooler than the warm banks around it.
    if (low) { u.uDeep.value.set('#0e2436').multiplyScalar(0.55); u.uShallow.value.set('#3a4a2a').multiplyScalar(0.6); u.uStreak.value.set('#4f7484').multiplyScalar(0.55); }
    u.uSkyAmt.value = low ? 2.1 : 1;
    // Low sun: the shallows show more of the warm bed than the cool sky (else they go lavender).
    u.uShallowSky.value = low ? 0.3 : 0.55;
    u.uSkyZenith.value.copy(bg).lerp(c.set(night ? 0x2a3c5c : low ? 0x8fb0cc : 0x7f9fbe), night ? 0.3 : low ? 0.92 : 0.6).multiplyScalar(0.42 * k);
    // (the low sun's peach sky over grey-blue went lavender in the shallows: lean it to straw gold)
    if (low) u.uSkyHorizon.value.set(0xa4b6c0).lerp(c.set(0xe2c48e), 0.38).multiplyScalar(0.42 * k);
    else u.uSkyHorizon.value.copy(bg).lerp(sky, 0.45).multiplyScalar(0.4 * k);
    u.uSunCol.value.set(p.sun).multiplyScalar(p.sunI);
  }

  /** Arc length (m) -> segment index and fraction. */
  private locate(s: number): [number, number] {
    const cum = this.cum;
    let lo = 0, hi = cum.length - 1;
    if (s <= 0) return [0, 0];
    if (s >= cum[hi]) return [hi - 1, 1];
    while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (cum[mid] <= s) lo = mid; else hi = mid; }
    return [lo, (s - cum[lo]) / (cum[lo + 1] - cum[lo] || 1)];
  }

  /** Point on the water at arc length s and across-position u (-1..1). */
  pointAt(s: number, u: number, out: { x: number; z: number; curv: number; half: number; dx: number; dz: number }) {
    const [i, t] = this.locate(s);
    const a = this.frames[i], b = this.frames[i + 1] ?? a;
    const nx = a.nx + (b.nx - a.nx) * t, nz = a.nz + (b.nz - a.nz) * t;
    const half = (a.w + (b.w - a.w) * t) * 0.5;
    out.x = a.x + (b.x - a.x) * t + nx * u * half;
    out.z = a.z + (b.z - a.z) * t + nz * u * half;
    out.curv = a.curv + (b.curv - a.curv) * t;
    out.half = half;
    out.dx = nz; out.dz = -nx;
    return out;
  }

  /** Closest point of the course to (x, z), with where (x, z) lies across the water. */
  nearestPoint(x: number, z: number): RiverPoint {
    const f = this.frames;
    let best = Infinity, bi = 0, bt = 0;
    for (let i = 0; i + 1 < f.length; i++) {
      const ax = f[i].x, az = f[i].z, ex = f[i + 1].x - ax, ez = f[i + 1].z - az;
      const l2 = ex * ex + ez * ez || 1;
      const t = Math.max(0, Math.min(1, ((x - ax) * ex + (z - az) * ez) / l2));
      const px = ax + ex * t - x, pz = az + ez * t - z;
      const d2 = px * px + pz * pz;
      if (d2 < best) { best = d2; bi = i; bt = t; }
    }
    const a = f[bi], b = f[bi + 1];
    const cx = a.x + (b.x - a.x) * bt, cz = a.z + (b.z - a.z) * bt;
    const nx = a.nx + (b.nx - a.nx) * bt, nz = a.nz + (b.nz - a.nz) * bt;
    const nl = Math.hypot(nx, nz) || 1;
    const half = (a.w + (b.w - a.w) * bt) * 0.5;
    const u = ((x - cx) * nx + (z - cz) * nz) / nl / half;
    return {
      x: cx, z: cz, i: bi, t: bt, s: this.cum[bi] + (this.cum[bi + 1] - this.cum[bi]) * bt, u,
      dist: Math.sqrt(best), inWater: Math.abs(u) <= 1, dx: nz / nl, dz: -nx / nl, half,
      curv: a.curv + (b.curv - a.curv) * bt,
    };
  }

  /** Surface current at (x, z) (m/s); zero off the water. */
  flowAt(x: number, z: number): RiverFlow {
    const h = this.nearestPoint(x, z);
    if (!h.inWater) return { vx: 0, vz: 0, speed: 0 };
    const speed = flowSpeed(h.u, h.curv);
    return { vx: h.dx * speed, vz: h.dz * speed, speed };
  }

  /** A ring spreading from (x, z) and drifting with the current; strength ~0.3 (rise) .. 1.5 (splash). */
  addRipple(x: number, z: number, strength = 1): void {
    let k = 0, oldest = -1;
    for (let j = 0; j < RIPPLES; j++) {
      const r = this.ripples[j];
      if (r.w <= 0) { k = j; oldest = Infinity; break; }
      if (r.z > oldest) { oldest = r.z; k = j; }
    }
    this.ripples[k].set(x, z, 0, strength);
    this.stat.ripples++;
  }

  /** A fish leaps at (x, z) (default: a calm spot in view). Returns false if none is free. */
  jumpFish(x?: number, z?: number): boolean {
    const k = this.jumps.indexOf(null);
    if (k < 0) return false;
    let at: { x: number; z: number; dx: number; dz: number } | null;
    if (x !== undefined && z !== undefined) {
      const h = this.nearestPoint(x, z);
      at = { x, z, dx: h.dx, dz: h.dz };
    } else at = this.calmSpot();
    if (!at) return false;
    // Mostly upstream (fish face the current), up to ~45 degrees off.
    const turn = (Math.random() * 2 - 1) * 0.8, c = Math.cos(turn), s = Math.sin(turn);
    const dx = -(at.dx * c - at.dz * s), dz = -(at.dx * s + at.dz * c);
    const len = 0.9 + Math.random() * 0.8;
    this.jumps[k] = { x: at.x - dx * len * 0.5, z: at.z - dz * len * 0.5, dx, dz, len,
      h: 0.5 + Math.random() * 0.4, t: 0, dur: 0.85 + Math.random() * 0.3, roll: (Math.random() * 2 - 1) * 0.5 };
    this.addRipple(at.x - dx * len * 0.5, at.z - dz * len * 0.5, 1.1);
    this.splash(at.x - dx * len * 0.5, at.z - dz * len * 0.5, 8, 1.5);
    this.stat.jumps++;
    return true;
  }

  /** A fish rising to a fly: rings only. */
  rise(x?: number, z?: number): void {
    const at = x !== undefined && z !== undefined ? { x, z } : this.calmSpot();
    if (!at) return;
    this.addRipple(at.x, at.z, 0.45 + Math.random() * 0.25);
    this.stat.rises++;
  }

  /** A random calm point of the course in view: low curvature, away from the banks. */
  private calmSpot(): { x: number; z: number; dx: number; dz: number } | null {
    const o = { x: 0, z: 0, curv: 0, half: 0, dx: 0, dz: 0 };
    const [x0, z0, x1, z1] = this.view;
    for (let tries = 0; tries < 12; tries++) {
      const s = this.sView[0] + Math.random() * (this.sView[1] - this.sView[0]);
      this.pointAt(s, (Math.random() * 2 - 1) * 0.55, o);
      if (o.x < x0 + 3 || o.x > x1 - 3 || o.z < z0 + 3 || o.z > z1 - 3) continue;
      if (Math.abs(o.curv) > 0.02 && tries < 8) continue;
      if (Math.abs(o.x) > GROUND_HALF[0] - 4 || Math.abs(o.z) > GROUND_HALF[1] - 4) continue;
      return { x: o.x, z: o.z, dx: o.dx, dz: o.dz };
    }
    return null;
  }

  private splash(x: number, z: number, n: number, power: number): void {
    for (let k = 0, made = 0; k < DROPS && made < n; k++) {
      const d = this.dropState[k];
      if (d.life > 0) continue;
      const a = Math.random() * Math.PI * 2, r = (0.4 + Math.random() * 0.6) * power * 0.6;
      d.x = x; d.y = 0.05; d.z = z;
      d.vx = Math.cos(a) * r; d.vz = Math.sin(a) * r; d.vy = (1.2 + Math.random() * 1.4) * power;
      d.life = 1; d.size = 0.04 + Math.random() * 0.04;
      made++;
    }
  }

  /** Per frame (real time): flow phases, ripples, drifting debris, fish, spray. */
  update(camera: THREE.Camera, view: number[], sun: THREE.DirectionalLight): void {
    const now = performance.now() * 0.001;
    const dt = this.last < 0 ? 0 : Math.min(0.1, now - this.last);
    this.last = now;
    const u = this.uniforms;
    const tt = now % 3600;
    u.uTime.value = tt;
    const ph = (tt / FLOW_PERIOD) % 1;
    u.uFlowT.value.set(ph * FLOW_PERIOD, ((ph + 0.5) % 1) * FLOW_PERIOD);
    u.uFlowW.value = 1 - Math.abs(2 * ph - 1);

    const vd = camera.getWorldDirection(u.uViewDir.value);
    // Glitter direction: the mirror of the view ray, swung a little toward the sun's side, so
    // only facets tilted a few degrees catch it.
    this.sunDir.subVectors(sun.position, sun.target.position).setY(0).normalize();
    u.uGlintDir.value.set(vd.x, -vd.y, vd.z).addScaledVector(this.sunDir, 0.2).normalize();

    // In view? (the course's box against the view's ground rectangle)
    for (let k = 0; k < 4; k++) this.view[k] = view[k];
    const b = this.bbox;
    this.inView = !(b[2] < view[0] || b[0] > view[2] || b[3] < view[1] || b[1] > view[3]);
    this.debris.visible = this.fish.visible = this.drops.visible = this.inView;
    if (!this.inView) return;
    let s0 = Infinity, s1 = -Infinity, inPts = 0;
    for (let i = 0; i < this.frames.length; i++) {
      const f = this.frames[i];
      if (f.x < view[0] - 10 || f.x > view[2] + 10 || f.z < view[1] - 10 || f.z > view[3] + 10) continue;
      if (this.cum[i] < s0) s0 = this.cum[i];
      if (this.cum[i] > s1) s1 = this.cum[i];
      inPts++;
    }
    if (!inPts) { this.inView = this.debris.visible = this.fish.visible = this.drops.visible = false; return; }
    this.sView[0] = Math.max(0, s0 - 6); this.sView[1] = Math.min(this.length, s1 + 6);
    this.lenInView = inPts * (this.length / this.frames.length);

    // Ripples age and drift with the current.
    for (const r of this.ripples) {
      if (r.w <= 0) continue;
      r.z += dt;
      if (r.z > RIPPLE_LIFE) { r.w = 0; continue; }
      const fl = this.flowAt(r.x, r.y);
      r.x += fl.vx * dt; r.y += fl.vz * dt;
    }

    this.updateDebris(dt, now);
    this.updateFish(dt);
  }

  private updateDebris(dt: number, now: number): void {
    const o = { x: 0, z: 0, curv: 0, half: 0, dx: 0, dz: 0 };
    const [sa, sb] = this.sView;
    const e = this.debris.instanceMatrix.array as Float32Array;
    for (let k = 0; k < this.drifts.length; k++) {
      const d = this.drifts[k];
      // Keep the flotsam where it can be seen: out of the stretch in view -> back in upstream.
      if (d.s > sb + 4) { d.s = sa + Math.random() * 6; d.u = (Math.random() * 2 - 1) * 0.75; }
      else if (d.s < sa - 10) { d.s = sa + Math.random() * (sb - sa); d.u = (Math.random() * 2 - 1) * 0.75; }
      this.pointAt(d.s, d.u, o);
      const v = flowSpeed(d.u, o.curv);
      d.s += v * dt;
      d.u = Math.max(-0.85, Math.min(0.85, d.u + Math.sin(now * 0.21 + d.ph) * 0.025 * dt));
      // Turning in the shear (slower water at the banks) plus its own spin.
      d.rot += (d.spin + d.u * 0.15) * dt;
      const yaw = Math.atan2(-o.dz, o.dx) + d.rot, c = Math.cos(yaw), s = Math.sin(yaw);
      const bob = 0.045 + Math.sin(now * 1.7 + d.ph) * 0.006;
      const j = k * 16;
      e[j] = c * d.sx; e[j + 1] = 0; e[j + 2] = -s * d.sx; e[j + 3] = 0;
      e[j + 4] = 0; e[j + 5] = 1; e[j + 6] = 0; e[j + 7] = 0;
      e[j + 8] = s * d.sz; e[j + 9] = 0; e[j + 10] = c * d.sz; e[j + 11] = 0;
      e[j + 12] = o.x; e[j + 13] = bob; e[j + 14] = o.z; e[j + 15] = 1;
    }
    this.debris.instanceMatrix.needsUpdate = true;
  }

  private updateFish(dt: number): void {
    // New jumps and rises: Poisson, by the length of river in view.
    const per100 = Math.max(0.5, Math.min(2.5, this.lenInView / 100)) * this.fishRate;
    this.nextJump -= dt * per100 * JUMPS_PER_MIN / 60;
    if (this.nextJump <= 0) { this.jumpFish(); this.nextJump = -Math.log(1 - Math.random()); }
    this.nextRise -= dt * per100 * RISES_PER_MIN / 60;
    if (this.nextRise <= 0) { this.rise(); this.nextRise = -Math.log(1 - Math.random()); }

    let n = 0;
    for (let k = 0; k < FISH; k++) {
      const j = this.jumps[k];
      if (!j) continue;
      j.t += dt / j.dur;
      if (j.t >= 1) {
        const ex = j.x + j.dx * j.len, ez = j.z + j.dz * j.len;
        this.addRipple(ex, ez, 1.8);
        this.splash(ex, ez, 16, 1.2);
        this.jumps[k] = null;
        continue;
      }
      const t = j.t;
      const y = 4 * j.h * t * (1 - t) - 0.06;
      const slope = (4 * j.h * (1 - 2 * t)) / j.len;
      this.e.set(j.roll * (1 - t), Math.atan2(-j.dz, j.dx), Math.atan(slope) * 0.9, 'YZX');
      this.q.setFromEuler(this.e);
      this.p.set(j.x + j.dx * j.len * t, Math.max(0.0, y), j.z + j.dz * j.len * t);
      // A flick of the tail: the body bends slightly (scale wobble reads as it at this size).
      const s = y < 0 ? 0 : 1;
      this.sc.set(s, s, s * (1 + Math.sin(t * 40) * 0.15));
      this.fish.setMatrixAt(n++, this.m.compose(this.p, this.q, this.sc));
    }
    this.fish.count = n;
    if (n) this.fish.instanceMatrix.needsUpdate = true;

    let m = 0;
    for (const d of this.dropState) {
      if (d.life <= 0) continue;
      d.vy -= 9.8 * dt;
      d.x += d.vx * dt; d.y += d.vy * dt; d.z += d.vz * dt;
      d.life -= dt * 1.6;
      if (d.y < 0.02) d.life = 0;
      if (d.life <= 0) continue;
      this.p.set(d.x, d.y, d.z);
      this.q.identity();
      this.sc.setScalar(d.size);
      this.drops.setMatrixAt(m++, this.m.compose(this.p, this.q, this.sc));
    }
    this.drops.count = m;
    if (m) this.drops.instanceMatrix.needsUpdate = true;
  }

  stats() {
    return {
      inView: this.inView, lengthInView: Math.round(this.lenInView), sView: this.sView.map(Math.round),
      ripplesActive: this.ripples.filter((r) => r.w > 0).length, fishInAir: this.fish.count,
      drops: this.drops.count, debris: this.drifts.length, ...this.stat, fishRate: this.fishRate,
    };
  }
}
