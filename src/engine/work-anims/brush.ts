import type { WorkPose } from '../work-anims';

/** Groom at a horse: the curry comb in the left hand works in circles along the coat, the
 *  right hand (the fork grounded) rests; now and then the comb is knocked clean on a heel. */
export default function brush(t: number, p: WorkPose): void {
  const cyc = (t / 9) % 1;
  p.armR = -0.12 + 0.02 * Math.sin(t * 0.6);
  if (cyc < 0.85) {
    const a = t * 5.2;
    p.armL = -1.15 + 0.22 * Math.sin(a) - 0.12 * Math.sin(cyc * Math.PI * 6);
    p.lean = 0.1 + 0.04 * Math.cos(a);
    p.headPitch = 0.12 + 0.05 * Math.sin(cyc * Math.PI * 6);
    p.headYaw = 0.1 * Math.sin(t * 0.4);
  } else {                               // knock the comb on a heel
    const k = (cyc - 0.85) / 0.15;
    p.armL = -0.5 - 0.25 * Math.abs(Math.sin(k * Math.PI * 4));
    p.lean = 0.25;
    p.headPitch = 0.5;
    p.headYaw = 0;
  }
}