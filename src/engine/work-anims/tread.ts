import type { WorkPose } from '../work-anims';

/** Treadwheel walker: steady uphill walk in place on the wheel's inner rim, hands on the
 *  spokes ahead at chest height, body leaning into the climb. The wheel itself turns in
 *  industry.ts (M6). */
export default function tread(t: number, p: WorkPose): void {
  const ph = (t / 1.5) * Math.PI * 2;    // one stride pair per 1.5 s (a slow climb)
  const s = Math.sin(ph);
  p.legL = -0.38 * s - 0.12;             // feet reach forward up the rising rim
  p.legR = 0.38 * s - 0.12;
  p.bob = 0.03 * (1 - Math.abs(Math.cos(ph)));
  p.armL = -1.25 + 0.12 * s;             // hand over hand along the spokes
  p.armR = -1.25 - 0.12 * s;
  p.headPitch = -0.05;
  p.headYaw = 0;
  p.lean = 0.2;
}
