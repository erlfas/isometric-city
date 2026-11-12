import type { ThreeIsometricRenderer } from './engine/three-renderer';
import type { SimulationEngine } from './engine/simulation';
import type { Soundscape } from './engine/audio';

/**
 * Dev-only camera hooks for screenshots and debugging (installed only under `vite dev`).
 *
 * URL hash, applied on load and on every hash change:
 *   #cam=x,z[,zoom[,quadrant]]        world position; zoom = world units visible vertically
 *                                    (mouse wheel allows 8-90; here anything, e.g. 3.5 for faces)
 *   #model=house_timber_log[,n[,zoom[,quadrant]]]   n-th placed instance of a model (default 0)
 *   append &pause to pause the simulation, &hour=12 to set the sim clock
 *   &lineup=char_tanner[,n[,work|walk]]   stand n citizens of a character model in a row at the
 *                                    view centre (needs &pause); work loop or walk in place.
 *                                    Without cam/model it frames open ground at face zoom.
 *
 * window.__lublin: { renderer, sim, audio, ready, snapTo(x,z,zoom?,q?), find(model), stats() }
 *   audio.debugState(): context state, music, crowd level, audible workshops
 * Read any of it from a script: node scripts/probe.mjs "<hash>" "__lublin.stats()"
 * `ready` turns true after the first frame with the scene populated.
 */
/** x, z, zoom: open paving with no walls between the row and the camera at the default
 *  rotation (checked by screenshot); zoom close enough to judge faces. */
const LINEUP_SPOT = [-15.5, -25.5, 3.5] as const;

export function installDebugHooks(renderer: ThreeIsometricRenderer, sim: SimulationEngine, audio: Soundscape): void {
  const api = {
    renderer,
    sim,
    audio,
    ready: false,
    snapTo: (x: number, z: number, zoom?: number, q?: number) => renderer.snapTo(x, z, zoom, q),
    find: (model: string) => renderer.findInstances(model),
    /** Last frame's draw calls and triangles (incl. shadow pass), the citizens' share of those
     *  triangles for one pass, and citizens per character model. */
    stats: () => {
      const { calls, triangles } = renderer.renderer.info.render;
      const models: Record<string, number> = {};
      for (const c of sim.citizens) {
        const m = renderer.getCitizenArchetype(c);
        models[m] = (models[m] ?? 0) + 1;
      }
      return { calls, triangles, citizenTrianglesPerPass: renderer.citizenTriangles(),
        citizens: sim.citizens.length, models };
    },
  };
  (window as unknown as { __lublin: typeof api }).__lublin = api;

  const num = (s: string | undefined) => (s === undefined || s === '' ? undefined : Number(s));

  const apply = () => {
    const params = new URLSearchParams(location.hash.slice(1));
    const cam = params.get('cam');
    const model = params.get('model');
    if (cam) {
      const [x, z, zoom, q] = cam.split(',');
      renderer.snapTo(Number(x), Number(z), num(zoom), num(q));
    } else if (model) {
      const [name, n, zoom, q] = model.split(',');
      const hits = renderer.findInstances(name);
      const hit = hits[num(n) ?? 0];
      if (hit) renderer.snapTo(hit.x, hit.z, num(zoom) ?? 20, num(q));
      else console.warn(`[debug] no instance ${n ?? 0} of model "${name}" (found ${hits.length})`);
    }
    if (params.has('pause') && !sim.isPaused) sim.togglePause();
    const hour = num(params.get('hour') ?? undefined);
    if (hour !== undefined) sim.simTimeHours = hour;
    const lineup = params.get('lineup');
    if (lineup) {
      if (!cam && !model) renderer.snapTo(LINEUP_SPOT[0], LINEUP_SPOT[1], LINEUP_SPOT[2]);
      const [arch, n, mode] = lineup.split(',');
      const m = mode === 'work' || mode === 'walk' ? mode : 'idle';
      const got = renderer.lineup(sim.citizens, arch, num(n) ?? 8, m);
      if (!got) console.warn(`[debug] lineup: no citizens use "${arch}"`);
    }
  };

  window.addEventListener('hashchange', apply);
  apply();
  requestAnimationFrame(() => requestAnimationFrame(() => { api.ready = true; }));
}
