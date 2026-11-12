/**
 * Work loops for kit citizens standing at work (state WORKING). One file per loop in
 * ./work-anims/<name>.ts with a default export; a kit picks one by name with
 * kit.anim = {"work": "<name>"} in characters/char_<trade>.py. Unknown names stand idle.
 */

/** Angles in radians about each part's pivot (X axis); negative pitch swings forward/up.
 *  Arms pivot at the shoulder, the head at the neck, lean tilts the upper body at the hips. */
export interface WorkPose {
  armL: number;
  armR: number;
  headPitch: number;
  headYaw: number;
  lean: number;
}

/** t: seconds, already offset per citizen. pose arrives holding the idle values
 *  (breathing arms, slow look-around); overwrite what the loop drives. */
export type WorkAnim = (t: number, pose: WorkPose) => void;

const modules = import.meta.glob<{ default: WorkAnim }>('./work-anims/*.ts', { eager: true });

export const WORK_ANIMS: Record<string, WorkAnim> = {};
for (const [path, mod] of Object.entries(modules)) {
  WORK_ANIMS[path.slice(path.lastIndexOf('/') + 1, -3)] = mod.default;
}
