import type { WorkPose } from '../work-anims';

/** Quarryman: two-handed overhead swing of the pick into the rock face. A slow lift until
 *  the head is above and behind the shoulders, a hard drop with the back bending into it,
 *  then a short lever to break the spall loose. */
export default function pick(t: number, p: WorkPose): void {
  const u = (t / 2.0) % 1;
  let lift: number;                      // 0 = point in the rock, 1 = pick overhead
  if (u < 0.45) lift = Math.sin((u / 0.45) * Math.PI / 2) ** 2;
  else if (u < 0.52) lift = 1;
  else if (u < 0.59) lift = 1 - ((u - 0.52) / 0.07) ** 2;
  else lift = 0.12 * Math.sin(((u - 0.59) / 0.41) * Math.PI) ** 2;   // lever the spall off
  p.armR = -0.9 - 1.9 * lift;            // the point strikes at chest height (the face)
  p.armL = -0.95 - 1.8 * lift;
  p.headPitch = 0.15 - 0.25 * lift;
  p.headYaw = 0;
  p.lean = 0.16 - 0.24 * lift;
}
