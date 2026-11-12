import type { WorkPose } from '../work-anims';

/** Weaver at the loom: the left hand throws the shuttle out and back while the eyes follow
 *  it, and after each pass both hands pull the beater in to pack the weft. */
export default function weave(t: number, p: WorkPose): void {
  const u = (t / 2.4) % 1;
  const throwArm = -0.75 - 0.45 * Math.sin(u * Math.PI * 2) ** 2;  // two passes per cycle
  // Beat after each pass (u = 0.5 and 1.0): a quick pull towards the body.
  const v = (u * 2) % 1;
  const beat = v > 0.8 ? Math.sin(((v - 0.8) / 0.2) * Math.PI) : 0;
  p.armL = throwArm + 0.45 * beat;
  p.armR = -0.95 + 0.5 * beat;
  p.headPitch = 0.05;  // the liripipe hangs down the chest from the head part: more would sink it in
  p.headYaw = 0.25 * Math.sin(u * Math.PI * 2);
  p.lean = 0.1 - 0.06 * beat;
}
