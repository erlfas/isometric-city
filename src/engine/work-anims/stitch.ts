import type { WorkPose } from '../work-anims';

/** Saddler stitching leather in a clam: both needles through the same awl hole, the hands
 *  draw the thread out wide by turns; every few stitches the awl is pushed through. */
export default function stitch(t: number, p: WorkPose): void {
  const u = (t / 2.4) % 1;
  const pull = u < 0.5 ? Math.sin((u / 0.5) * Math.PI) : 0;
  const awl = u >= 0.5 && u < 0.7 ? Math.sin(((u - 0.5) / 0.2) * Math.PI) : 0;
  const side = Math.floor(t / 2.4) % 2;
  p.armR = -1.05 + (side ? 0.45 : 0.1) * pull - 0.2 * awl;
  p.armL = -1.05 + (side ? 0.1 : 0.45) * pull;
  p.lean = 0.16 + 0.04 * awl;
  p.headPitch = 0.45;
  p.headYaw = (side ? -0.15 : 0.15) * pull;
}