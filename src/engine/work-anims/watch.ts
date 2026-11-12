import type { WorkPose } from '../work-anims';

/** Guard on watch: weapon grounded just ahead of the right foot, left arm easy at the
 *  side; the head sweeps slowly to one side, dwells, sweeps back, with a rare glance down. */
export default function watch(t: number, p: WorkPose): void {
  const sweep = Math.sin((t / 11) * Math.PI * 2);
  p.headYaw = 0.6 * Math.max(-1, Math.min(1, 1.7 * sweep));       // holds at each side
  p.headPitch = 0.12 * Math.max(0, Math.sin((t / 17) * Math.PI * 2)) ** 4;
  p.armR = -0.1 + Math.sin(t * 1.1) * 0.01;
  p.armL = 0.04 + Math.sin(t * 2.2) * 0.02;
  p.lean = -0.02;
}
