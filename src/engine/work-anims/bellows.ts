import type { WorkPose } from '../work-anims';

/** Smelter at the foot bellows: stands on the pair and treads them in turn, shifting his
 *  weight from one to the other, arms out for balance. The bags pump in
 *  industry.ts (M6) on the same 1.2 s beat. */
export default function bellows(t: number, p: WorkPose): void {
  const ph = (t / 1.2) * Math.PI * 2;
  const s = Math.sin(ph);
  // The lifted foot rises (hip forward), the other presses its bag flat.
  p.legL = -0.45 * Math.max(0, s);
  p.legR = -0.45 * Math.max(0, -s);
  p.bob = 0.05 * Math.abs(s);
  p.armL = -0.55 + 0.1 * s;              // arms out for balance, tongs held low
  p.armR = -0.45 - 0.1 * s;
  p.headPitch = 0.1;
  p.headYaw = 0.15 * Math.sin(t * 0.3);  // a glance at the furnace now and then
  p.lean = 0.05;
}
