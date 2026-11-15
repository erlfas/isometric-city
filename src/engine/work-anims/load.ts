import type { WorkPose } from '../work-anims';

/** Barrow man at a block pile: bends for a rough stone, lifts it to the chest, turns and
 *  sets it into the barrow at his side. */
export default function load(t: number, p: WorkPose): void {
  const u = (t / 3.0) % 1;
  if (u < 0.3) {                         // bend and grip
    const g = Math.sin((u / 0.3) * Math.PI / 2);
    p.armL = p.armR = -0.2 - 0.4 * g;
    p.lean = 0.1 + 0.45 * g;
    p.headPitch = 0.45;
    p.headYaw = 0;
  } else if (u < 0.55) {                 // lift to the chest
    const k = (u - 0.3) / 0.25;
    p.armL = p.armR = -0.6 - 0.35 * k;
    p.lean = 0.55 - 0.5 * k;
    p.headPitch = 0.45 - 0.2 * k;
    p.headYaw = 0;
  } else if (u < 0.8) {                  // turn and lower into the barrow
    const k = (u - 0.55) / 0.25;
    p.armL = p.armR = -0.95 + 0.4 * k;
    p.lean = 0.05 + 0.3 * k;
    p.headPitch = 0.25 + 0.2 * k;
    p.headYaw = 0.7 * Math.sin(k * Math.PI / 2);
  } else {                               // straighten and turn back
    const k = (u - 0.8) / 0.2;
    p.armL = p.armR = -0.55 + 0.35 * k;
    p.lean = 0.35 - 0.25 * k;
    p.headPitch = 0.45;
    p.headYaw = 0.7 * (1 - k);
  }
  p.armR += 0.04;
}
