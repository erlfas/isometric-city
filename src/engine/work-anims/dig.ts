import type { WorkPose } from '../work-anims';

/** Ore digger: spade cuts into the bog face (foot on the tread), the spadeful of ore-mud
 *  levered up and swung aside onto the heap. */
export default function dig(t: number, p: WorkPose): void {
  const u = (t / 2.6) % 1;
  if (u < 0.3) {
    // Drive the blade in: arms low, the right foot stamps on the tread.
    const e = Math.sin((u / 0.3) * Math.PI);
    p.armR = -0.35 - 0.1 * e;
    p.armL = -0.55 - 0.1 * e;
    p.legR = -0.35 * e;
    p.bob = 0.06 * e;
    p.lean = 0.3;
    p.headPitch = 0.4;
    p.headYaw = 0;
  } else if (u < 0.7) {
    // Lever and lift the load to waist height.
    const g = Math.sin(((u - 0.3) / 0.4) * Math.PI / 2);
    p.armR = -0.45 - 0.55 * g;
    p.armL = -0.65 - 0.45 * g;
    p.lean = 0.3 - 0.15 * g;
    p.headPitch = 0.35;
    p.headYaw = 0.5 * g;                 // look to the heap
  } else {
    // Toss it aside and bring the spade back.
    const g = (u - 0.7) / 0.3;
    const e = Math.sin(g * Math.PI);
    p.armR = -1.0 + 0.65 * g - 0.2 * e;
    p.armL = -1.1 + 0.55 * g;
    p.lean = 0.15 + 0.15 * g;
    p.headPitch = 0.35;
    p.headYaw = 0.5 * (1 - g);
  }
}
