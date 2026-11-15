import type { WorkPose } from '../work-anims';

/** Smelter charging the shaft: stoops for a basket of charcoal (or roasted ore), heaves
 *  it up to the furnace mouth above his head, tips it in, lowers the empty basket. */
export default function stoke(t: number, p: WorkPose): void {
  const u = (t / 3.4) % 1;
  if (u < 0.25) {                        // stoop and grip
    const g = Math.sin((u / 0.25) * Math.PI / 2);
    p.armL = p.armR = -0.3 - 0.25 * g;
    p.lean = 0.1 + 0.35 * g;
    p.headPitch = 0.4;
  } else if (u < 0.55) {                 // heave up to the mouth
    const k = (u - 0.25) / 0.3;
    p.armL = p.armR = -0.55 - 1.75 * Math.sin(k * Math.PI / 2);
    p.lean = 0.45 - 0.55 * k;
    p.headPitch = 0.4 - 0.65 * k;
  } else if (u < 0.7) {                  // tip it in
    const k = (u - 0.55) / 0.15;
    p.armL = p.armR = -2.3 - 0.25 * Math.sin(k * Math.PI);
    p.lean = -0.1;
    p.headPitch = -0.25;
  } else {                               // lower the empty basket
    const k = (u - 0.7) / 0.3;
    p.armL = p.armR = -2.3 + 2.0 * k;
    p.lean = -0.1 + 0.2 * k;
    p.headPitch = -0.25 + 0.65 * k;
  }
  p.armL -= 0.05;
  p.headYaw = 0;
}
