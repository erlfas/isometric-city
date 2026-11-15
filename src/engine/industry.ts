import * as THREE from 'three';
import type { PlacedModel } from './static-batches';
import type { Citizen } from '../types';
import { animPhase } from './citizen-crowd';

/**
 * Moving parts of the industry sites outside the walls (quarry & ironworks plan): the quarry's
 * treadwheel cranes (wheel, hoisting rope, hook with its block). Their frames are part of the
 * static model; build_assets.py `anchor_machine` writes where the moving parts go:
 *   machines: [{ kind: 'crane', axle, axis, r, tip, lo, hi }]  (glTF model space)
 *     axle: wheel centre, axis: axle direction, r: wheel radius (tread surface),
 *     tip: jib end (rope top), lo / hi: height the block rests at below / is landed at above.
 *   machines: [{ kind: 'bellows', p, face }]: a bloomery's foot bellows (two bloomery_bellows.glb bags).
 * Like the mill wheels these are ordinary scene objects, not in the static batches. They move
 * only while worked (update): a crane hoists while a walker treads its wheel, the bags pump in
 * the beat of the treader's `bellows` loop. The cranes' shadows redraw in steps (shadowDue).
 */

interface RawCrane { kind: 'crane'; axle: number[]; axis: number[]; r: number; tip: number[]; lo: number; hi: number }
/** A bloomery's pair of foot bellows: p = middle of the pair on the ground, face = toward the
 *  furnace (glTF ground-plane direction). */
interface RawBellows { kind: 'bellows'; p: number[]; face: number[] }
type RawMachine = RawCrane | RawBellows;

export interface Bellows {
  /** The two bags (bloomery_bellows.glb, nozzles along its +Z; [0] the treader's left one,
   *  mirrored), squashed in height as each is trodden. */
  bags: [THREE.Object3D, THREE.Object3D];
  /** Middle of the pair (world). */
  at: THREE.Vector3;
  parcelId?: string;
}

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
  /** Wheel turn (rad) and hoist direction (+1 up, -1 down, 0 resting at an end). */
  angle: number;
  dir: number;
  /** Real seconds left of the rest at an end (hooking on / landing the block). */
  rest: number;
  /** A walker is in the wheel now. */
  trodden: boolean;
}

/** Hook above the bottom of the block (crane_block.glb: block bottom 1.75 m below the hook). */
const HOOK_ABOVE = 1.75;
const X = new THREE.Vector3(1, 0, 0);

function machinesOf(t: THREE.Object3D): RawMachine[] {
  let a: unknown = t.userData?.anchors;
  if (typeof a === 'string') {
    try { a = JSON.parse(a); } catch { return []; }
  }
  return (a as { machines?: RawMachine[] } | null)?.machines ?? [];
}

export class IndustryMachines {
  readonly cranes: Crane[] = [];
  readonly bellows: Bellows[] = [];

  constructor(scene: THREE.Scene, model: (name: string) => THREE.Object3D | undefined, placed: readonly PlacedModel[]) {
    const wheelT = model('crane_wheel'), ropeT = model('crane_rope'), blockT = model('crane_block');
    const bellowsT = model('bloomery_bellows');
    const pos = new THREE.Vector3(), q = new THREE.Quaternion(), s = new THREE.Vector3();
    const clone = (t: THREE.Object3D) => {
      const o = t.clone(true);
      o.traverse((c) => { if ((c as THREE.Mesh).isMesh) { c.castShadow = true; c.receiveShadow = true; } });
      scene.add(o);
      return o;
    };
    for (const pm of placed) {
      const raw = machinesOf(pm.template);
      if (!raw.length) continue;
      pm.matrix.decompose(pos, q, s);
      for (const m of raw) {
        if (m.kind === 'bellows') {
          if (!bellowsT) continue;
          const at = new THREE.Vector3().fromArray(m.p).applyMatrix4(pm.matrix);
          const f = new THREE.Vector3(m.face[0], 0, m.face[1]).transformDirection(pm.matrix);
          const yaw = Math.atan2(f.x, f.z);        // model's +Z (nozzles) toward the furnace
          // The treader faces the furnace too: his left is the model's +X.
          const side = new THREE.Vector3(Math.cos(yaw), 0, -Math.sin(yaw)).multiplyScalar(BELLOWS_DX);
          const bags = [-1, 1].map((sx) => {
            const o = clone(bellowsT);
            o.traverse((c) => { c.castShadow = false; });   // low and pumping: no shadow redraws
            o.position.copy(at).addScaledVector(side, -sx);
            o.rotation.y = yaw;
            o.scale.x = -sx;                                 // the left (+X) bag is the model; right mirrored
            return o;
          }) as [THREE.Object3D, THREE.Object3D];
          this.bellows.push({ bags, at, parcelId: pm.parcelId });
          continue;
        }
        if (m.kind !== 'crane' || !wheelT || !ropeT || !blockT) continue;
        const axis = new THREE.Vector3().fromArray(m.axis).transformDirection(pm.matrix);
        const base = new THREE.Quaternion().setFromUnitVectors(X, axis);
        const wheel = clone(wheelT);
        wheel.position.fromArray(m.axle).applyMatrix4(pm.matrix);
        wheel.quaternion.copy(base);
        const tip = new THREE.Vector3().fromArray(m.tip).applyMatrix4(pm.matrix);
        const crane: Crane = {
          wheel, rope: clone(ropeT), block: clone(blockT), base, tip,
          lo: m.lo + pos.y, hi: m.hi + pos.y, r: m.r, hook: 0, parcelId: pm.parcelId,
          angle: 0, dir: 1, rest: 0, trodden: false,
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

  /** Who works the machines: citizens of these trades (picked once, the list never changes). */
  private crew: Citizen[] | null = null;
  private last = performance.now();
  private shadowAt = 0;
  private moved = 0;

  /**
   * Cranes hoist while a walker treads their wheel (a citizen at the wheel playing `tread`):
   * up from the bench to the landing, a rest, back down, a rest. The wheel turns with the
   * hook (rope wound on the axle). Bellows bags are pressed in the beat of the treader's
   * `bellows` loop (same clock: real time + the citizen's crowd phase). Real time, like the
   * mill wheels; paused sim = idle walkers, so nothing turns.
   */
  update(citizens: readonly Citizen[]): void {
    const now = performance.now();
    const dt = Math.min(0.1, (now - this.last) / 1000);
    this.last = now;
    if (!this.crew) this.crew = citizens.filter((c) => /quarry|smelt/i.test(c.trade ?? ''));
    const t = now / 1000;
    for (const c of this.cranes) {
      c.trodden = this.worker(c.wheel.position, 'tread', CRANE_REACH) !== null;
      if (!c.trodden) continue;
      if (c.rest > 0) { c.rest -= dt; continue; }
      const lo = c.lo + HOOK_ABOVE, hi = c.hi + HOOK_ABOVE;
      let y = c.hook + c.dir * HOIST * dt;
      if (y >= hi || y <= lo) {
        y = Math.min(hi, Math.max(lo, y));
        c.dir = -c.dir;
        c.rest = REST * (0.7 + Math.random() * 0.6);
      }
      const dy = y - c.hook;
      this.setHook(c, y);
      c.angle += dy / AXLE_R;
      c.wheel.quaternion.copy(c.base).multiply(_q.setFromAxisAngle(X, c.angle));
      this.moved += Math.abs(dy / AXLE_R);
    }
    for (const b of this.bellows) {
      const w = this.worker(b.at, 'bellows', 1.6);
      // bellows.ts: the left foot is up while sin > 0, so the right bag is pressed then.
      const s = w ? Math.sin(((t + animPhase(w.id)) / 1.2) * Math.PI * 2) : 0;
      b.bags[0].scale.y = 1 - BAG_SQUASH * Math.max(0, -s);
      b.bags[1].scale.y = 1 - BAG_SQUASH * Math.max(0, s);
    }
  }

  /** A crew member working at `p` (within r m) with the given loop, or null. */
  private worker(p: THREE.Vector3, anim: string, r: number): Citizen | null {
    for (const c of this.crew ?? []) {
      if (c.activityAnim !== anim || c.state !== 'WORKING' || c.isMoving) continue;
      const dx = (c.currentX ?? 0) - p.x, dz = (c.currentZ ?? 0) - p.z;
      if (dx * dx + dz * dz < r * r) return c;
    }
    return null;
  }

  /** World points of the moving shadow casters (crane wheels and blocks). */
  get casters(): THREE.Vector3[] { return this.cranes.map((c) => c.wheel.position); }

  /** True once per SHADOW_STEP of wheel turning since the last redraw (as the mill wheels). */
  shadowDue(): boolean {
    if (Math.abs(this.moved - this.shadowAt) < SHADOW_STEP) return false;
    this.shadowAt = this.moved;
    return true;
  }
}

/** Hook speed (m/s) and the axle the rope winds on: wheel turn = hook travel / AXLE_R. */
const HOIST = 0.14;
const AXLE_R = 0.35;
/** Real seconds the block rests at the bench (slinging) and the landing (unhooking). */
const REST = 9;
/** A walker this near the wheel's axle (ground plane) treads it. */
const CRANE_REACH = 3;
const BELLOWS_DX = 0.36;     // build_assets.py BELLOWS_DX
const BAG_SQUASH = 0.45;     // a trodden bag's height lost
const SHADOW_STEP = 0.12;    // rad of wheel turn between shadow redraws (~3 a second while hoisting)
const _q = new THREE.Quaternion();
