import * as THREE from 'three';
import type { PlacedPart, StaticBatches } from './static-batches';

/**
 * Cutaway view: look into a building, and see through the ones in the way.
 *
 * A building being cut away is hidden in the static batches and drawn instead as a
 * temporary copy (one Mesh per part) whose materials take three extra inputs:
 *   cutY  everything above it (roof, upper storeys, wall tops) fades out by a screen-door
 *         dither (4x4 Bayer discard) as `fade` goes 0 -> 1, so there is no alpha sorting
 *   fill  a warm light around a point inside (hearth / window light), below cutY only
 *   back faces become the interior: the models are closed shells, so the inside of a wall
 *         is the back face of the outer one. Downward faces seen from above (a storey box's
 *         underside) are drawn as a plank floor, pulled a few cm toward the camera so they
 *         win over a plinth top in the same plane.
 * The copy's shadow is drawn uncut (the shadow pass ignores the shader changes), so the
 * roof keeps the interior in shade. An occluder (a building between the camera and the
 * person you watch) uses the same copy with cutY far below ground: the whole building
 * dithers to `fade`.
 *
 * The building being looked into (`furnish`) also gets its furniture, plank floors and
 * ladders from `furniture` (interiors.ts), drawn with the same shader, so they fade with it.
 *
 * Fades run over FADE_S; a copy is dropped and the batch instance shown again once its
 * fade is back at 0.
 */

const FADE_S = 0.4;
const FLOOR_BIAS = 2e-5;      // depth units: ~3 cm with the camera's 1500 m depth range
const WALL_IN = new THREE.Color(0xcdbf9f);  // limewashed inner wall (sRGB)
const FLOOR = new THREE.Color(0x7a5a3c);    // boards
const FILL = new THREE.Color(0xffa860);
const FILL_R = 7;             // m
const OFF = -1e4;             // cutY / fill height for "no cut" / "no fill"
const WHITE = new THREE.Color(1, 1, 1);

export interface CutTarget {
  /** Fade everything above this world height... */
  cutY: number;
  /** ...to this much (0 none, 1 gone). */
  fade: number;
  /** Warm light inside, if any. */
  fill?: THREE.Vector3;
  /** Draw the furniture too (the building being looked into, not one merely in the way). */
  furnish?: boolean;
}

interface View {
  group: THREE.Group;
  materials: THREE.Material[];
  made: Map<string, THREE.Material>;
  u: { uCutY: { value: number }; uFade: { value: number }; uFill: { value: THREE.Vector3 }; uFillI: { value: number } };
  fade: number;
  target: number;
  fillI: number;
  fillTarget: number;
  furnished: boolean;
}

/** Furniture, floors and ladders of a placement (interiors.ts), drawn with its cutaway. */
export type FurnitureOf = (placement: number) => readonly PlacedPart[];

const VERT_HEAD = /* glsl */ `
varying vec3 vCutW;
varying vec3 vCutN;
`;
const VERT_BODY = /* glsl */ `
vCutW = (modelMatrix * vec4(transformed, 1.0)).xyz;
vCutN = normalize(mat3(modelMatrix) * normal);
`;
const FRAG_HEAD = /* glsl */ `
uniform float uCutY;
uniform float uFade;
uniform vec3 uFill;
uniform float uFillI;
varying vec3 vCutW;
varying vec3 vCutN;
float cutBayer(vec2 p) {
  const float m[16] = float[16](0., 8., 2., 10., 12., 4., 14., 6., 3., 11., 1., 9., 15., 7., 13., 5.);
  ivec2 q = ivec2(mod(p, 4.0));
  return (m[q.x + q.y * 4] + 0.5) / 16.0;
}
`;
const FRAG_CLIP = /* glsl */ `
if (vCutW.y > uCutY && cutBayer(gl_FragCoord.xy) < uFade) discard;
bool cutFloor = false;
`;
const FRAG_COLOR = (wall: THREE.Color, floor: THREE.Color) => /* glsl */ `
if (!gl_FrontFacing) {
  float l = clamp(dot(diffuseColor.rgb, vec3(0.3, 0.59, 0.11)) * 2.0, 0.0, 1.0);
  cutFloor = vCutN.y < -0.7;
  diffuseColor.rgb = (cutFloor ? vec3(${floor.r}, ${floor.g}, ${floor.b}) : vec3(${wall.r}, ${wall.g}, ${wall.b}))
    * (0.85 + 0.3 * l);
}
`;
const FRAG_FILL = (fill: THREE.Color) => /* glsl */ `
// Inside faces: under a roof in life, so no sun (the faded roof's shadow misses most of a
// narrow interior at the sun's 45 degrees).
if (!gl_FrontFacing) outgoingLight -= reflectedLight.directDiffuse * uFade;
if (uFillI > 0.0 && vCutW.y < uCutY + 0.2) {
  float a = clamp(1.0 - distance(vCutW, uFill) / ${FILL_R.toFixed(1)}, 0.0, 1.0);
  outgoingLight += diffuseColor.rgb * vec3(${fill.r}, ${fill.g}, ${fill.b}) * (a * a * uFillI);
}
gl_FragDepth = gl_FragCoord.z - (cutFloor ? ${FLOOR_BIAS.toExponential()} : 0.0);
`;

// Linear colours for the shader constants (materials work in linear space).
const wallLin = WALL_IN.clone(), floorLin = FLOOR.clone(), fillLin = FILL.clone();
const COLOR_CODE = FRAG_COLOR(wallLin, floorLin);
const FILL_CODE = FRAG_FILL(fillLin);

export class Cutaway {
  private views = new Map<number, View>();
  private warm: THREE.Material[] = [];
  private scene: THREE.Scene;
  private statics: StaticBatches;
  /** Set by the renderer once the furniture model is loaded. */
  furniture: FurnitureOf | null = null;

  constructor(scene: THREE.Scene, statics: StaticBatches) {
    this.scene = scene;
    this.statics = statics;
  }

  /**
   * Compile the cutaway shader variant of every batch material (and of `extra` parts, the
   * furniture) now; call once the batches are built. Otherwise the first cutaway stalls a
   * frame for ~140 ms. The warm-up materials are kept: disposing them would release the
   * programs again.
   */
  prewarm(renderer: THREE.WebGLRenderer, camera: THREE.Camera, extra: readonly PlacedPart[] = []): Promise<void> {
    const tmp = new THREE.Scene();
    const seen = new Set<THREE.Material>();
    const u: View['u'] = { uCutY: { value: OFF }, uFade: { value: 0 }, uFill: { value: new THREE.Vector3() }, uFillI: { value: 0 } };
    const lists: (readonly PlacedPart[])[] = [extra];
    for (let i = 0; i < this.statics.placements.length; i++) lists.push(this.statics.partsOfPlacement(i));
    for (const list of lists) {
      for (const p of list) {
        if (seen.has(p.material)) continue;
        seen.add(p.material);
        const m = this.material(p.material, WHITE, u);
        if (m === p.material) continue;
        const mesh = new THREE.Mesh(p.geometry, m);
        mesh.castShadow = p.cast;
        mesh.receiveShadow = p.receive;
        tmp.add(mesh);
        this.warm.push(m);
      }
    }
    return renderer.compileAsync(tmp, camera, this.scene).then(() => undefined);
  }

  /** Placements cut away now (including ones fading back). */
  get active(): number[] {
    return [...this.views.keys()];
  }

  /**
   * Wanted state per placement index; placements not listed fade back and are dropped.
   * Call every frame, then update(dt).
   */
  set(targets: Map<number, CutTarget>): void {
    for (const [i, t] of targets) {
      let v = this.views.get(i);
      if (!v) this.views.set(i, (v = this.make(i)));
      if (t.furnish && !v.furnished && this.furniture) {
        v.furnished = true;
        this.add(v, this.furniture(i));
      }
      v.target = t.fade;
      v.u.uCutY.value = t.cutY;
      if (t.fill) { v.u.uFill.value.copy(t.fill); v.fillTarget = 1; } else v.fillTarget = 0;
    }
    for (const [i, v] of this.views) if (!targets.has(i)) { v.target = 0; v.fillTarget = 0; }
  }

  update(dt: number): void {
    const step = dt / FADE_S;
    for (const [i, v] of this.views) {
      v.fade += Math.max(-step, Math.min(step, v.target - v.fade));
      v.fillI += Math.max(-step, Math.min(step, v.fillTarget - v.fillI));
      v.u.uFade.value = v.fade;
      v.u.uFillI.value = v.fillI * 0.9;
      if (v.fade <= 0 && v.target <= 0 && v.fillI <= 0) this.drop(i, v);
    }
  }

  private make(i: number): View {
    const u = {
      uCutY: { value: OFF }, uFade: { value: 0 }, uFill: { value: new THREE.Vector3(0, OFF, 0) }, uFillI: { value: 0 },
    };
    const group = new THREE.Group();
    group.matrixAutoUpdate = false;
    const v: View = { group, materials: [], made: new Map(), u, fade: 0, target: 0, fillI: 0, fillTarget: 0, furnished: false };
    this.add(v, this.statics.partsOfPlacement(i));
    this.scene.add(group);
    this.statics.setPlacementVisible(i, false);
    return v;
  }

  /** Draw these parts in a view, with cutaway copies of their materials. */
  private add(v: View, parts: readonly PlacedPart[]): void {
    for (const p of parts) {
      const key = `${p.material.uuid}|${p.tint.getHexString()}`;
      let m = v.made.get(key);
      if (!m) {
        v.made.set(key, (m = this.material(p.material, p.tint, v.u)));
        if (m !== p.material) v.materials.push(m);
      }
      const mesh = new THREE.Mesh(p.geometry, m);
      mesh.matrixAutoUpdate = false;
      mesh.matrix.copy(p.matrix);
      mesh.matrixWorld.copy(p.matrix);
      mesh.castShadow = p.cast;
      mesh.receiveShadow = p.receive;
      v.group.add(mesh);
    }
  }

  private drop(i: number, v: View): void {
    this.scene.remove(v.group);
    for (const m of v.materials) m.dispose();
    this.statics.setPlacementVisible(i, true);
    this.views.delete(i);
  }

  /** A copy of a batch material with the placement's tint and the cutaway shader inputs. */
  private material(base: THREE.Material, tint: THREE.Color, u: View['u']): THREE.Material {
    if (base.transparent) return base; // glass panes etc.: leave as they are
    const m = base.clone();
    const c = (m as THREE.MeshStandardMaterial).color;
    if (c) c.multiply(tint);
    m.side = THREE.DoubleSide;
    m.shadowSide = THREE.FrontSide;
    m.onBeforeCompile = cutShader(u);
    m.customProgramCacheKey = () => `cutaway|${base.customProgramCacheKey()}`;
    return m;
  }
}

function cutShader(u: View['u']) {
  return (shader: THREE.WebGLProgramParametersWithUniforms) => {
    Object.assign(shader.uniforms, u);
    shader.vertexShader = VERT_HEAD + shader.vertexShader.replace('#include <project_vertex>',
      `#include <project_vertex>\n${VERT_BODY}`);
    shader.fragmentShader = FRAG_HEAD + shader.fragmentShader
      .replace('#include <clipping_planes_fragment>', `#include <clipping_planes_fragment>\n${FRAG_CLIP}`)
      .replace('#include <color_fragment>', `#include <color_fragment>\n${COLOR_CODE}`)
      .replace('#include <opaque_fragment>', `${FILL_CODE}\n#include <opaque_fragment>`);
  };
}
