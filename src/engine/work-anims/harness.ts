import type { WorkPose } from '../work-anims';

/** At the harness pegs: lifts a collar and hames down at head height, works the buckles and
 *  straps at the chest, hangs it back; between, a long look over the leather. */
export default function harness(t: number, p: WorkPose): void {
  const u = (t / 7) % 1;
  if (u < 0.2) {                         // reach up to the pegs
    const k = Math.sin((u / 0.2) * Math.PI / 2);
    p.armL = p.armR = -0.4 - 1.5 * k;
    p.lean = -0.05 * k;
    p.headPitch = -0.3 * k;
  } else if (u < 0.75) {                 // the buckles at the chest, hands working by turns
    const k = Math.min(1, (u - 0.2) / 0.08);
    p.armR = -1.9 + 0.75 * k + 0.12 * Math.sin(t * 4.5);
    p.armL = -1.9 + 0.85 * k + 0.1 * Math.sin(t * 4.5 + 2);
    p.lean = 0.06;
    p.headPitch = 0.35 * k;
  } else if (u < 0.88) {                 // hang it back
    const k = Math.sin(((u - 0.75) / 0.13) * Math.PI);
    p.armL = p.armR = -1.1 - 0.8 * k;
    p.lean = 0;
    p.headPitch = 0.35 - 0.6 * k;
  } else {                               // arms down, looking it over
    const k = (u - 0.88) / 0.12;
    p.armL = p.armR = -1.1 + 0.9 * Math.min(1, k * 2);
    p.lean = 0;
    p.headPitch = -0.1;
  }
  p.headYaw = 0.15 * Math.sin(t * 0.5);
}