import type { WorkPose } from '../work-anims';

/** Tanner: both hands push the fleshing knife down the hide and back. */
export default function scrape(t: number, p: WorkPose): void {
  const sw = Math.sin(t * 2.6);
  p.armL = p.armR = -1.0 + 0.3 * sw;
  p.headPitch = 0.35;
  p.headYaw = 0;
  p.lean = 0.14 + 0.04 * sw;
}
