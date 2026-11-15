import type { WorkPose } from '../work-anims';

/** Collier: reaches the long rake out over the clamp, draws turf and dust back over a vent
 *  in a slow pull, pats it down with two short taps. */
export default function rake(t: number, p: WorkPose): void {
  const u = (t / 3.0) % 1;
  let reach: number;                     // 1 = rake out at full reach, 0 = drawn in
  let tap = 0;
  if (u < 0.3) reach = Math.sin((u / 0.3) * Math.PI / 2);
  else if (u < 0.75) reach = 1 - Math.sin(((u - 0.3) / 0.45) * Math.PI / 2);
  else { reach = 0; tap = Math.abs(Math.sin(((u - 0.75) / 0.25) * Math.PI * 2)); }
  p.armR = -0.55 - 0.65 * reach + 0.12 * tap;
  p.armL = -0.75 - 0.55 * reach + 0.1 * tap;
  p.headPitch = 0.35 - 0.1 * reach;
  p.headYaw = 0;
  p.lean = 0.08 + 0.2 * reach;
}
