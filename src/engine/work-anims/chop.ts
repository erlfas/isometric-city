import type { WorkPose } from '../work-anims';

/** Woodcutter: two-handed overhead axe chop into a log on the block in front.
 *  Slow wind-up until the axe stands above and behind the head, a fast drop with the
 *  body bending into it, a short rest in the cut, then the axe is worked free. */
export default function chop(t: number, p: WorkPose): void {
  const u = (t / 1.7) % 1;
  let lift: number;                      // 0 = blade in the log, 1 = axe over the head
  if (u < 0.5) lift = Math.sin((u / 0.5) * Math.PI / 2) ** 2;
  else if (u < 0.58) lift = 1;
  else if (u < 0.66) lift = 1 - ((u - 0.58) / 0.08) ** 2;
  else lift = 0.04 * Math.sin(((u - 0.66) / 0.34) * Math.PI * 2) ** 2;   // wrench the blade free
  p.armR = -0.6 - 2.1 * lift;            // in the cut the blade rests at knee height
  p.armL = -0.65 - 2.0 * lift;           // lower hand on the haft
  p.headPitch = 0.35 - 0.3 * lift;
  p.headYaw = 0;
  p.lean = 0.2 - 0.26 * lift;            // arch back on the wind-up, bend into the stroke
}
