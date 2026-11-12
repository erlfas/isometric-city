import type { WorkPose } from '../work-anims';

/** Blacksmith: slow raise of the right arm, fast strike; left hand holds the work. */
export default function hammer(t: number, p: WorkPose): void {
  const u = (t / 1.25) % 1;
  p.armR = u < 0.7 ? -0.45 - 2.0 * Math.sin((u / 0.7) * Math.PI / 2) ** 2
                   : -2.45 + 1.75 * Math.min(1, (u - 0.7) / 0.1);
  p.armL = -0.8;
  p.headPitch = 0.3;
  p.headYaw = 0;
  p.lean = 0.08;
}
