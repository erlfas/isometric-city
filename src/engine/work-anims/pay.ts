import type { WorkPose } from '../work-anims';

/** At a baker's window: counts coins out of the purse, holds them out, takes the loaves. */
export default function pay(t: number, p: WorkPose): void {
  const u = (t / 3.6) % 1;
  if (u < 0.45) {
    // Head down over the purse, both hands together at the belt, fingers busy.
    p.armL = -0.45 + 0.04 * Math.sin(t * 9);
    p.armR = -0.5 + 0.05 * Math.sin(t * 11);
    p.headPitch = 0.4;
  } else {
    // Hand out over the counter and back, the other arm ready for the bread.
    const g = (u - 0.45) / 0.55;
    const e = Math.sin(g * Math.PI);
    p.armR = -0.5 - 0.75 * e;
    p.armL = -0.35 - 0.3 * e;
    p.headPitch = 0.1;
  }
  p.headYaw = 0;
  p.lean = 0.05;
}
