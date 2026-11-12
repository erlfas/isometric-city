import type { WorkPose } from '../work-anims';

/** Stonemason: left hand holds the chisel forward to the stone; right hand lifts the
 *  mallet and taps it down in a quick, steady rhythm. */
export default function chisel(t: number, p: WorkPose): void {
  const u = (t / 0.7) % 1;
  const lift = u < 0.62 ? Math.sin((u / 0.62) * Math.PI / 2) ** 2   // raise
                        : Math.max(0, 1 - (u - 0.62) / 0.08);        // tap
  p.armR = -0.9 - 0.6 * lift;
  const hit = u >= 0.7 && u < 0.78 ? 1 - (u - 0.7) / 0.08 : 0;     // chisel jolts on impact
  p.armL = -0.95 + 0.04 * hit;
  p.headPitch = 0.38;
  p.headYaw = 0;
  p.lean = 0.12;
}
