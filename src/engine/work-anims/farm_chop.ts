import type { WorkPose } from '../work-anims';

/** Farmer: two-handed lift of the hoe (scythe, flail) out in front, a fast chop into
 *  the soil, a short pull back. */
export default function farmChop(t: number, p: WorkPose): void {
  const u = (t / 1.5) % 1;
  const lift = u < 0.55 ? Math.sin((u / 0.55) * Math.PI / 2) ** 2
             : u < 0.68 ? 1 - (u - 0.55) / 0.13
             : 0.06 * Math.sin(((u - 0.68) / 0.32) * Math.PI);
  p.armR = -0.08 - 0.95 * lift;
  p.armL = -0.25 - 0.85 * lift;
  p.headPitch = 0.3;
  p.headYaw = 0;
  p.lean = 0.12 - 0.06 * lift;
}
