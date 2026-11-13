import type { WorkPose } from '../work-anims';

/** At the well: pulls the rope up hand over hand, leaning over the curb, then lifts the
 *  bucket clear and pours it into their own. */
export default function draw_water(t: number, p: WorkPose): void {
  const u = (t / 4.2) % 1;
  if (u < 0.7) {
    // Hand over hand: the arms alternate reaching up and pulling down.
    const s = Math.sin((u / 0.7) * Math.PI * 6);
    p.armL = -1.0 - 0.45 * s;
    p.armR = -1.0 + 0.45 * s;
    p.headPitch = 0.3;
    p.lean = 0.16 + 0.03 * Math.abs(s);
  } else {
    // Lift and tip: both arms forward, easing back down.
    const g = (u - 0.7) / 0.3;
    const e = Math.sin(g * Math.PI);
    p.armL = -0.6 - 0.5 * e;
    p.armR = -0.6 - 0.5 * e;
    p.headPitch = 0.4;
    p.lean = 0.1;
  }
  p.headYaw = 0;
}
