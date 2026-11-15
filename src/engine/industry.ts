import * as THREE from 'three';
import type { PlacedModel } from './static-batches';

/**
 * Moving parts of the industry sites outside the walls (quarry & ironworks plan): the quarry's
 * treadwheel cranes (wheel, hoisting rope, hook with its block). Their frames are part of the
 * static model; build_assets.py `anchor_machine` writes where the moving parts go:
 *   machines: [{ kind: 'crane', axle, axis, r, tip, lo, hi }]  (glTF model space)
 *     axle: wheel centre, axis: axle direction, r: wheel radius (tread surface),
 *     tip: jib end (rope top), lo / hi: height the block rests at below / is landed at above.
 * Like the mill wheels these are ordinary scene objects, not in the static batches.
 */

interface RawCrane { kind: 'crane'; axle: number[]; axis: number[]; r: number; tip: number[]; lo: number; hi: number }

export interface Crane {
  wheel: THREE.Object3D;
  rope: THREE.Object3D;
  block: THREE.Object3D;
  /** Wheel orientation with no turn; the turn is about its local X. */
  base: THREE.Quaternion;
  /** World jib tip, block heights (hook at the top of the block's sling). */
  tip: THREE.Vector3;
  lo: number; hi: number;
  r: number;
  /** Hook height now (world). */
  hook: number;
  /** Placement (parcel) the crane belongs to. */
  parcelId?: string;
}

/** Hook above the bottom of the block (crane_block.glb: block bottom 1.75 m below the hook). */
const HOOK_ABOVE = 1.75;
const X = new THREE.Vector3(1, 0, 0);

function machinesOf(t: THREE.Object3D): RawCrane[] {
  let a: unknown = t.userData?.anchors;
  if (typeof a === 'string') {
    try { a = JSON.parse(a); } catch { return []; }
  }
  return ((a as { machines?: RawCrane[] } | null)?.machines ?? []).filter((m) => m.kind === 'crane');
}

export class IndustryMachines {
  readonly cranes: Crane[] = [];

  constructor(scene: THREE.Scene, model: (name: string) => THREE.Object3D | undefined, placed: readonly PlacedModel[]) {
    const wheelT = model('crane_wheel'), ropeT = model('crane_rope'), blockT = model('crane_block');
    if (!wheelT || !ropeT || !blockT) return;
    const pos = new THREE.Vector3(), q = new THREE.Quaternion(), s = new THREE.Vector3();
    for (const pm of placed) {
      const raw = machinesOf(pm.template);
      if (!raw.length) continue;
      pm.matrix.decompose(pos, q, s);
      for (const m of raw) {
        const clone = (t: THREE.Object3D) => {
          const o = t.clone(true);
          o.traverse((c) => { if ((c as THREE.Mesh).isMesh) { c.castShadow = true; c.receiveShadow = true; } });
          scene.add(o);
          return o;
        };
        const axis = new THREE.Vector3().fromArray(m.axis).transformDirection(pm.matrix);
        const base = new THREE.Quaternion().setFromUnitVectors(X, axis);
        const wheel = clone(wheelT);
        wheel.position.fromArray(m.axle).applyMatrix4(pm.matrix);
        wheel.quaternion.copy(base);
        const tip = new THREE.Vector3().fromArray(m.tip).applyMatrix4(pm.matrix);
        const crane: Crane = {
          wheel, rope: clone(ropeT), block: clone(blockT), base, tip,
          lo: m.lo + pos.y, hi: m.hi + pos.y, r: m.r, hook: 0, parcelId: pm.parcelId,
        };
        // Facing: the block's long side across the jib.
        crane.block.quaternion.copy(base);
        this.setHook(crane, crane.lo + HOOK_ABOVE + 0.6);
        this.cranes.push(crane);
      }
    }
  }

  /** Hang the hook at world height y (rope from the jib tip down to it). */
  setHook(c: Crane, y: number): void {
    c.hook = y;
    c.block.position.set(c.tip.x, y, c.tip.z);
    c.rope.position.copy(c.tip);
    c.rope.scale.set(1, Math.max(0.05, c.tip.y - y), 1);
  }
}
