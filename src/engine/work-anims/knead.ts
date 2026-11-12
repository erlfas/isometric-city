import type { WorkPose } from '../work-anims';

/** Baker: both hands push the dough away and roll it back; the body leans into each push. */
export default function knead(t: number, p: WorkPose): void {
  const u = (t / 1.3) % 1;
  // Quick push (first 40%), slow draw back.
  const push = u < 0.4 ? Math.sin((u / 0.4) * Math.PI / 2) : Math.cos(((u - 0.4) / 0.6) * Math.PI / 2);
  p.armL = -0.8 - 0.35 * push;
  p.armR = -0.8 - 0.3 * push;
  p.headPitch = 0.35;
  p.headYaw = 0;
  p.lean = 0.14 + 0.08 * push;
}
