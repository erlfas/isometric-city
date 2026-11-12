import * as THREE from 'three';
import type { Door } from './building-anchors';
import type { TextureLibrary } from './texture-library';

/**
 * Swinging door leaves for the doors the simulation has open (sim.activeDoors).
 *
 * Buildings are solid shells with the closed leaf baked onto the wall (until M5 hollows
 * them), so an open door is drawn in front of that wall: a dark opening quad over the baked
 * leaf, and a plank leaf hinged on one jamb that swings out by up to SWING. Closed doors draw
 * nothing. After dusk the opening glows warm: firelight from inside.
 *
 * Both are InstancedMeshes sized to the open doors only, rewritten every frame (a few
 * dozen at most), so the static batches stay fixed.
 */

const MAX = 512;
const SWING = THREE.MathUtils.degToRad(100);
const LEAF_T = 0.06;          // leaf thickness, m
const LEAF_OUT = 0.18;        // leaf centre in front of the wall face (clears the baked leaf)
const HOLE_OUT = 0.135;       // dark opening quad: baked leaves stand up to 0.11 m proud
const DARK = new THREE.Color(0x14100c);
const GLOW = new THREE.Color(0xffa04a);

const _m = new THREE.Matrix4();
const _x = new THREE.Vector3();
const _y = new THREE.Vector3(0, 1, 0);
const _z = new THREE.Vector3();
const _p = new THREE.Vector3();
const _s = new THREE.Vector3();
const _q = new THREE.Quaternion();
const _c = new THREE.Color();

/** 0 by day, 1 at night: dusk 19-21 h, dawn 5-6.5 h. */
export function nightFactor(hour: number): number {
  if (hour >= 21 || hour < 5) return 1;
  if (hour >= 19) return (hour - 19) / 2;
  if (hour < 6.5) return 1 - (hour - 5) / 1.5;
  return 0;
}

export class DoorLeaves {
  private leaves: THREE.InstancedMesh;
  private holes: THREE.InstancedMesh;
  private leafMat: THREE.MeshStandardMaterial;
  private textures: TextureLibrary;

  constructor(scene: THREE.Scene, textures: TextureLibrary) {
    this.textures = textures;
    // Unit leaf: hinge edge on the y axis, x 0..1 along the leaf, y 0..1 up.
    const leafGeo = new THREE.BoxGeometry(1, 1, 1).translate(0.5, 0.5, 0);
    this.leafMat = new THREE.MeshStandardMaterial({ color: 0x8a6a4a, roughness: 0.9 });
    this.leaves = new THREE.InstancedMesh(leafGeo, this.leafMat, MAX);
    this.leaves.castShadow = true;
    this.leaves.receiveShadow = true;
    // Unit opening: centred on x, y 0..1 up, facing +z.
    // Vertex shade: firelight is strongest low in the doorway, the lintel side is in shadow.
    const holeGeo = new THREE.PlaneGeometry(1, 1, 1, 2).translate(0, 0.5, 0);
    const pos = holeGeo.attributes.position;
    const shade = new Float32Array(pos.count * 3);
    for (let k = 0; k < pos.count; k++) shade.fill(1 - 0.75 * pos.getY(k), k * 3, k * 3 + 3);
    holeGeo.setAttribute('color', new THREE.BufferAttribute(shade, 3));
    this.holes = new THREE.InstancedMesh(holeGeo, new THREE.MeshBasicMaterial({ color: 0xffffff, vertexColors: true }), MAX);
    this.holes.setColorAt(0, DARK);
    for (const m of [this.leaves, this.holes]) {
      m.count = 0;
      m.frustumCulled = false; // instances span the town; count is small
      m.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      scene.add(m);
    }
  }

  update(doors: readonly Door[], hour: number): void {
    if (!this.leafMat.map) {
      const map = this.textures.getAlbedo('plank_board');
      if (map) {
        // Box UVs run 0..1 per face: one board-width texture tile across the leaf.
        const t = map.clone();
        t.repeat.set(1, 1);
        t.needsUpdate = true;
        this.leafMat.map = t;
        this.leafMat.color.setHex(0xb08c6a);
        this.leafMat.needsUpdate = true;
      }
    }
    _c.copy(DARK).lerp(GLOW, nightFactor(hour) * 0.6);
    let n = 0;
    for (const d of doors) {
      if (d.open <= 0 || n >= MAX) continue;
      const e = d.open * d.open * (3 - 2 * d.open); // smoothstep
      // Wall tangent t = (-nz, nx); hinge on the -t jamb.
      const tx = -d.nz, tz = d.nx;
      // Opening: plane facing out (+z -> normal; x = -t keeps the basis right-handed).
      _z.set(d.nx, 0, d.nz);
      _x.set(-tx, 0, -tz);
      _m.makeBasis(_x, _y, _z);
      _q.setFromRotationMatrix(_m);
      _p.set(d.x + d.nx * HOLE_OUT, d.y, d.z + d.nz * HOLE_OUT);
      _s.set(d.w + 0.12, d.h + 0.03, 1); // covers baked leaves a little wider than the clear width
      _m.compose(_p, _q, _s);
      this.holes.setMatrixAt(n, _m);
      this.holes.setColorAt(n, _c);
      // Leaf: from the hinge along cos(a) t + sin(a) n.
      const a = e * SWING, ca = Math.cos(a), sa = Math.sin(a);
      _x.set(tx * ca + d.nx * sa, 0, tz * ca + d.nz * sa);
      _z.crossVectors(_x, _y);
      _m.makeBasis(_x, _y, _z);
      _q.setFromRotationMatrix(_m);
      const hx = d.x - tx * d.w * 0.5 + d.nx * LEAF_OUT, hz = d.z - tz * d.w * 0.5 + d.nz * LEAF_OUT;
      _p.set(hx, d.y, hz);
      _s.set(d.w, d.h, LEAF_T);
      _m.compose(_p, _q, _s);
      this.leaves.setMatrixAt(n, _m);
      n++;
    }
    this.leaves.count = n;
    this.holes.count = n;
    if (n) {
      this.leaves.instanceMatrix.needsUpdate = true;
      this.holes.instanceMatrix.needsUpdate = true;
      this.holes.instanceColor!.needsUpdate = true;
    }
  }
}
