import type { WorkPose } from '../work-anims';

/** Farrier shoeing: bent low over a hoof held between his knees, rasps it level (right arm
 *  back and forth), then taps the nails home in short quick blows; straightens his back. */
export default function shoe(t: number, p: WorkPose): void {
  const u = (t / 10) % 1;
  p.lean = 0.75;
  p.headPitch = 0.55;
  p.headYaw = 0;
  p.armL = -0.55;
  p.legL = -0.18;
  p.legR = 0.12;
  p.bob = -0.06;
  if (u < 0.45) {                        // rasping
    p.armR = -0.75 + 0.3 * Math.sin(t * 6.5);
  } else if (u < 0.85) {                 // nailing: lift and tap
    const v = ((t * 2.4) % 1);
    p.armR = v < 0.7 ? -0.8 - 0.55 * Math.sin((v / 0.7) * Math.PI / 2) : -1.35 + 0.55 * Math.min(1, (v - 0.7) / 0.1);
  } else {                               // straighten up, rub the back
    const k = Math.sin(((u - 0.85) / 0.15) * Math.PI);
    p.lean = 0.75 - 0.8 * k;
    p.headPitch = 0.55 - 0.7 * k;
    p.legL = -0.18 * (1 - k);
    p.legR = 0.12 * (1 - k);
    p.bob = -0.06 * (1 - k);
    p.armR = -0.2 + 0.6 * k;
    p.armL = -0.55 + 0.9 * k;
  }
}