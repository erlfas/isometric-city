import type { WorkPose } from '../work-anims';

/** Friar: slow lift of the hoe in the right hand, quick chop to the ground, a short
 *  pull back; the left hand holds its basket or book a little forward. */
export default function till(t: number, p: WorkPose): void {
  const u = (t / 1.6) % 1;
  if (u < 0.55) p.armR = -0.05 - 0.75 * Math.sin((u / 0.55) * Math.PI / 2) ** 2;
  else if (u < 0.65) p.armR = -0.8 + 0.75 * ((u - 0.55) / 0.1);
  else p.armR = -0.05 + 0.1 * Math.sin(((u - 0.65) / 0.35) * Math.PI);
  p.armL = -0.3;
  p.headPitch = 0.35;
  p.headYaw = 0;
  p.lean = 0.06;
}
