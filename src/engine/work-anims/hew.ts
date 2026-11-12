import type { WorkPose } from '../work-anims';

/** Carpenter: two-handed broadaxe/adze strokes down a beam in front of the feet.
 *  Slow lift to head height, quick drop, a short rest on the cut. */
export default function hew(t: number, p: WorkPose): void {
  const u = (t / 1.6) % 1;
  let lift: number;                      // 0 = blade on the beam, 1 = top of the swing
  if (u < 0.6) lift = Math.sin((u / 0.6) * Math.PI / 2) ** 2;
  else if (u < 0.72) lift = 1 - (u - 0.6) / 0.12;
  else lift = 0;
  p.armR = -0.35 - 1.55 * lift;
  p.armL = -0.5 - 1.2 * lift;            // lower hand trails on the haft
  p.headPitch = 0.4 - 0.15 * lift;
  p.headYaw = 0;
  p.lean = 0.18 - 0.1 * lift;
}
