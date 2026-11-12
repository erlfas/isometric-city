import type { WorkPose } from '../work-anims';

/** Potter: both hands low and forward round the clay on the wheel, drawing it up in
 *  slow pulls; the hands work slightly out of step, head bowed over the pot. */
export default function shapeClay(t: number, p: WorkPose): void {
  const s = Math.sin(t * 1.6);
  p.armL = -0.85 + 0.1 * s;
  p.armR = -0.85 + 0.1 * Math.sin(t * 1.6 + 0.9);
  p.headPitch = 0.35;
  p.headYaw = 0.05 * Math.sin(t * 0.4);
  p.lean = 0.16 + 0.03 * s;
}
