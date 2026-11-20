import type { WorkPose } from '../work-anims';

/** Forking hay: a forkful taken from the pile low ahead, heaved up overhead into the rack (or
 *  the loft hatch), shaken off, the fork brought down again. */
export default function forkhay(t: number, p: WorkPose): void {
  const u = (t / 3.6) % 1;
  if (u < 0.25) {                        // into the pile
    const g = Math.sin((u / 0.25) * Math.PI / 2);
    p.armR = -0.2 - 0.15 * g;
    p.armL = -0.5 - 0.1 * g;
    p.lean = 0.12 + 0.3 * g;
    p.headPitch = 0.4;
  } else if (u < 0.55) {                 // heave it up
    const k = Math.sin(((u - 0.25) / 0.3) * Math.PI / 2);
    p.armR = -0.35 - 1.75 * k;
    p.armL = -0.6 - 1.6 * k;
    p.lean = 0.42 - 0.55 * k;
    p.headPitch = 0.4 - 0.75 * k;
  } else if (u < 0.7) {                  // shake it off into the rack
    const k = (u - 0.55) / 0.15;
    p.armR = -2.1 + 0.12 * Math.sin(k * Math.PI * 4);
    p.armL = -2.2 + 0.1 * Math.sin(k * Math.PI * 4);
    p.lean = -0.13;
    p.headPitch = -0.35;
  } else {                               // fork down
    const k = (u - 0.7) / 0.3;
    p.armR = -2.1 + 1.9 * k;
    p.armL = -2.2 + 1.7 * k;
    p.lean = -0.13 + 0.25 * k;
    p.headPitch = -0.35 + 0.75 * k;
  }
  p.headYaw = 0;
}