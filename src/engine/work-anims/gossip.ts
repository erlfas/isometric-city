import type { WorkPose } from '../work-anims';

/** Townswoman: chats at the market; the right hand gestures in bursts, the head turns
 *  to her listener and nods; the left hand holds her basket a little forward. */
export default function gossip(t: number, p: WorkPose): void {
  const u = (t / 3.4) % 1;
  // Two quick gestures, then a pause while listening.
  const burst = u < 0.55 ? Math.sin((u / 0.55) * Math.PI * 2) ** 2 : 0;
  p.armR = -0.15 - 0.75 * burst - 0.08 * Math.sin(t * 7) * burst;
  p.armL = -0.12;
  p.headPitch = u < 0.55 ? 0.04 * Math.sin(t * 6) : 0.08 + 0.06 * Math.sin(t * 2.5);
  p.headYaw = 0.35 * Math.sin(t * 0.45) + 0.1 * burst;
  p.lean = 0.03 + 0.02 * burst;
}
