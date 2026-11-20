import type { WorkPose } from '../work-anims';

/** Groom mucking out: drives the fork in low ahead, lifts the load of dung and straw to the
 *  hip, turns and pitches it to the right (the barrow, the heap), turns back. */
export default function muck(t: number, p: WorkPose): void {
  const u = (t / 3.2) % 1;
  if (u < 0.3) {                         // drive the fork in
    const g = Math.sin((u / 0.3) * Math.PI / 2);
    p.armR = -0.15 - 0.15 * g;
    p.armL = -0.45 - 0.2 * g;
    p.lean = 0.15 + 0.35 * g;
    p.headPitch = 0.5;
    p.headYaw = 0;
  } else if (u < 0.5) {                  // lift the load
    const k = (u - 0.3) / 0.2;
    p.armR = -0.3 - 0.45 * k;
    p.armL = -0.65 - 0.3 * k;
    p.lean = 0.5 - 0.3 * k;
    p.headPitch = 0.5 - 0.2 * k;
    p.headYaw = 0.5 * k;
  } else if (u < 0.65) {                 // pitch it aside
    const k = (u - 0.5) / 0.15;
    p.armR = -0.75 - 0.35 * Math.sin(k * Math.PI);
    p.armL = -0.95 + 0.2 * k;
    p.lean = 0.2;
    p.headPitch = 0.3;
    p.headYaw = 0.5 + 0.3 * k;
  } else {                               // back to the floor
    const k = (u - 0.65) / 0.35;
    p.armR = -0.75 + 0.6 * k;
    p.armL = -0.75 + 0.3 * k;
    p.lean = 0.2 - 0.05 * k;
    p.headPitch = 0.3 + 0.2 * k;
    p.headYaw = 0.8 * (1 - k);
  }
}