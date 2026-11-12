import type { WorkPose } from '../work-anims';

/** Merchant: holds the sealed scroll up to read it, now and then gesturing with the free hand. */
export default function reckon(t: number, p: WorkPose): void {
  const u = (t / 7) % 1;
  // Free hand: rests, rises into a gesture with two beats, sinks again.
  const g = u < 0.45 ? 0 : u < 0.55 ? (u - 0.45) / 0.1 : u < 0.85 ? 1 : 1 - (u - 0.85) / 0.15;
  const ease = g * g * (3 - 2 * g);
  p.armR = -1.05 + 0.04 * Math.sin(t * 0.9) + 0.25 * ease;
  p.armL = 0.03 * Math.sin(t * 2.2) - ease * (0.75 + 0.12 * Math.sin(t * 5.5));
  p.headPitch = 0.35 - 0.25 * ease;
  p.headYaw = 0.08 * Math.sin(t * 0.6) * (1 - ease);
  p.lean = 0.04;
}
