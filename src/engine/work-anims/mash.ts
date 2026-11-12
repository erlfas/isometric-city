import type { WorkPose } from '../work-anims';

/** Brewer: stirs the mash, the upright paddle tilted into the tun; the hips sway a
 *  quarter-cycle behind the arm so the blade traces a loop. Left hand keeps the tankard. */
export default function mash(t: number, p: WorkPose): void {
  const a = t * 2.0;
  p.armR = -0.55 + 0.18 * Math.sin(a);
  p.armL = -0.2 + 0.05 * Math.sin(a);
  p.headPitch = 0.3;
  p.headYaw = 0.08 * Math.sin(a);
  p.lean = 0.09 + 0.05 * Math.cos(a);
}
