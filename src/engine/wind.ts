import * as THREE from 'three';

/**
 * Wind in the trees: a vertex-shader sway on the vegetation materials (`Leaves`, `Bark`).
 *
 * Per vertex, `prepare()` stores how far it may move (attribute `windW`, metres, model space):
 *   x = bend: the whole plant leaning and swaying, grows with (height / model height)^2, so the
 *       trunk base stays put and the crown top moves most;
 *   y = flutter: branch clumps and leaves, grows with distance from the trunk axis and height;
 *   z = how fast the plant swings (reeds whip, pines barely rock).
 * Leaves and bark get the same weights from the same positions, so where a crown sits on a
 * branch both move together. Amplitudes per species: SPECIES below.
 *
 * The shader adds a gust field that rolls across the world along the wind (phase from the
 * instance's world position: neighbours are correlated, not in lockstep), each plant's own
 * swing (frequency and phase hashed from its position), and a fast leaf shimmer.
 * Time is real seconds: the wind keeps blowing while the simulation is paused.
 *
 * Only the colour pass moves: the shadow casters (static-batches.ts) are separate meshes and
 * stay still, so the shadow map is not redrawn for the wind.
 */

interface Species { bend: number; flutter: number; freq: number }

const SPECIES: [RegExp, Species][] = [
  [/^tree_pine/, { bend: 0.16, flutter: 0.05, freq: 0.8 }],
  [/^tree_birch/, { bend: 0.32, flutter: 0.16, freq: 1.1 }],
  [/^tree_willow_weeping/, { bend: 0.24, flutter: 0.2, freq: 0.9 }],
  [/^tree_willow/, { bend: 0.26, flutter: 0.14, freq: 1.0 }],
  [/^tree_alder/, { bend: 0.25, flutter: 0.12, freq: 1.05 }],
  [/^tree_hornbeam/, { bend: 0.2, flutter: 0.1, freq: 1.0 }],
  [/^tree_/, { bend: 0.22, flutter: 0.1, freq: 0.95 }], // oaks, lime, anything new
  [/^bush_/, { bend: 0.1, flutter: 0.08, freq: 1.6 }],
  [/^reed_/, { bend: 0.22, flutter: 0.06, freq: 2.2 }],
  [/^fern_/, { bend: 0.06, flutter: 0.05, freq: 1.8 }],
];

/** Materials that sway (by glTF name); anything else on those models stays still. */
const SWAYING = new Set(['Leaves', 'Bark']);
/** Peak displacement per unit of bend / flutter weight (shader below), for the bounds. */
const PEAK_BEND = 1.7, PEAK_FLUTTER = 1.6;

const VERT_HEAD = /* glsl */ `
attribute vec3 windW;
uniform float uWindTime;
uniform float uWindStrength;
uniform vec2 uWindDir;
`;

const VERT_BODY = /* glsl */ `
{
  #ifdef USE_BATCHING
    mat4 windM = modelMatrix * batchingMatrix;
  #else
    mat4 windM = modelMatrix;
  #endif
  #ifdef USE_INSTANCING
    windM = windM * instanceMatrix;
  #endif
  vec2 wO = windM[3].xz;                       // the plant's foot in the world
  float wH = fract(sin(dot(wO, vec2(12.9898, 78.233))) * 43758.5453);
  vec2 wD = uWindDir, wP = vec2(-wD.y, wD.x);
  float wS = dot(wO, wD), wQ = dot(wO, wP), t = uWindTime;
  // Gusts: long waves travelling downwind (~10 m/s), bent crosswise, plus a shorter ripple.
  float gust = 0.5 + 0.3 * sin(wS * 0.045 - t * 0.45 + 1.2 * sin(wQ * 0.019 + t * 0.05))
             + 0.2 * sin(wS * 0.11 + wQ * 0.04 - t * 1.1);
  gust = clamp(gust, 0.0, 1.0);
  // The plant's own swing: lean downwind with the gust, rock at its own frequency.
  float f = (1.3 + 0.7 * wH) * windW.z;
  float osc = sin(t * f + wH * 6.283), osc2 = sin(t * f * 1.37 + wH * 11.0);
  vec2 bend = wD * (0.8 * gust + osc * (0.2 + 0.45 * gust)) + wP * osc2 * (0.08 + 0.17 * gust);
  vec3 wOff = vec3(bend.x, 0.0, bend.y) * windW.x;
  // Clumps of branches flutter (phase coherent over a metre or so), leaves shimmer.
  float ph = dot(position, vec3(0.73, 0.41, 0.62)) + wH * 20.0;
  float fl = (sin(t * 4.1 * windW.z + ph) + 0.5 * sin(t * 6.7 * windW.z + ph * 1.7)) * (0.3 + 0.7 * gust);
  float sh = sin(t * 19.0 + dot(position, vec3(4.1, 3.3, 5.7))) * (0.15 + 0.25 * gust);
  wOff += (vec3(wD.x, 0.35, wD.y) * fl + vec3(0.3, 1.0, -0.25) * sh) * windW.y;
  wOff *= uWindStrength;
  // World offset back into model space (rotation + uniform scale).
  transformed += transpose(mat3(windM)) * wOff / max(dot(windM[0].xyz, windM[0].xyz), 1e-4);
}
`;

export class Wind {
  /** Overall strength (0 = calm, 1 = a breeze, 2 = a strong wind); set from __lublin.wind. */
  strength = 1;
  /** Direction the wind blows towards, radians from +x towards +z. */
  direction = 0.6;
  /** Slow drift of strength and direction (0 = constant). */
  variation = 1;
  private uniforms = {
    uWindTime: { value: 0 },
    uWindStrength: { value: 1 },
    uWindDir: { value: new THREE.Vector2(1, 0) },
  };
  private patched = new WeakSet<THREE.Material>();

  /** Give a loaded model's vegetation meshes their sway weights and their materials the shader. */
  prepare(name: string, root: THREE.Object3D): void {
    const meshes: THREE.Mesh[] = [];
    root.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.isMesh && !Array.isArray(m.material) && SWAYING.has(m.material.name)) meshes.push(m);
    });
    if (!meshes.length) return;
    const sp = SPECIES.find(([re]) => re.test(name))?.[1];
    // Model height and crown radius from the swaying parts (geometry is in model space).
    let top = 0, rad = 0;
    for (const m of meshes) {
      const p = m.geometry.attributes.position;
      for (let i = 0; i < p.count; i++) {
        top = Math.max(top, p.getY(i));
        rad = Math.max(rad, Math.hypot(p.getX(i), p.getZ(i)));
      }
    }
    const weeping = /weeping/.test(name);
    for (const m of meshes) {
      const g = m.geometry, p = g.attributes.position;
      const w = new Float32Array(p.count * 3);
      const leaves = (m.material as THREE.Material).name === 'Leaves';
      if (sp && top > 0) {
        for (let i = 0; i < p.count; i++) {
          const y = p.getY(i), r = Math.hypot(p.getX(i), p.getZ(i));
          const t = THREE.MathUtils.clamp(y / top, 0, 1);
          // Hanging willow strands move with the crown they hang from, and swing more lower down.
          const tb = weeping && leaves ? Math.max(t, 0.75) : t;
          const out = THREE.MathUtils.smoothstep(r, 0.4, Math.max(0.5, rad * 0.7));
          let fw = Math.min(1, out * 0.8 + t * t * 0.5) * THREE.MathUtils.smoothstep(t, 0, 0.35);
          if (weeping && leaves) fw *= 1 + 1.5 * (1 - t);
          w[i * 3] = sp.bend * tb * tb;
          w[i * 3 + 1] = sp.flutter * fw;
          w[i * 3 + 2] = sp.freq;
        }
      }
      g.setAttribute('windW', new THREE.BufferAttribute(w, 3));
      // Bounds must hold the displaced vertices (batch culling uses the geometry's box).
      if (sp) {
        const reach = PEAK_BEND * sp.bend + PEAK_FLUTTER * sp.flutter * (weeping ? 2.5 : 1);
        g.computeBoundingBox();
        g.boundingBox!.expandByVector(new THREE.Vector3(reach, reach * 0.5, reach));
        g.boundingSphere = null;
        g.computeBoundingSphere();
      }
      this.patch(m.material as THREE.Material);
    }
  }

  private patch(mat: THREE.Material): void {
    if (this.patched.has(mat)) return;
    this.patched.add(mat);
    const u = this.uniforms;
    mat.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, u);
      shader.vertexShader = VERT_HEAD + shader.vertexShader.replace('#include <begin_vertex>',
        `#include <begin_vertex>\n${VERT_BODY}`);
    };
    mat.customProgramCacheKey = () => 'wind-v1';
  }

  /** Advance the wind; `now` in real seconds. */
  update(now: number): void {
    const u = this.uniforms, v = this.variation;
    u.uWindTime.value = now % 100000;
    // Strength breathes over minutes; the direction veers a few degrees either way.
    const s = 1 + v * (0.18 * Math.sin(now * 0.021) + 0.1 * Math.sin(now * 0.057 + 1.3));
    u.uWindStrength.value = Math.max(0, this.strength * s);
    const a = this.direction + v * 0.15 * Math.sin(now * 0.009 + 0.7);
    u.uWindDir.value.set(Math.cos(a), Math.sin(a));
  }
}
