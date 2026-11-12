import type { ThreeIsometricRenderer } from './engine/three-renderer';
import type { SimulationEngine } from './engine/simulation';

/**
 * Dev-only camera hooks for screenshots and debugging (installed only under `vite dev`).
 *
 * URL hash, applied on load and on every hash change:
 *   #cam=x,z[,zoom[,quadrant]]        world position; zoom = world units visible (8-90); quadrant 0-3
 *   #model=house_timber_log[,n[,zoom[,quadrant]]]   n-th placed instance of a model (default 0)
 *   append &pause to pause the simulation, &hour=12 to set the sim clock
 *
 * window.__lublin: { renderer, sim, ready, snapTo(x,z,zoom?,q?), find(model) }
 * `ready` turns true after the first frame with the scene populated.
 */
export function installDebugHooks(renderer: ThreeIsometricRenderer, sim: SimulationEngine): void {
  const api = {
    renderer,
    sim,
    ready: false,
    snapTo: (x: number, z: number, zoom?: number, q?: number) => renderer.snapTo(x, z, zoom, q),
    find: (model: string) => renderer.findInstances(model),
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
  };

  window.addEventListener('hashchange', apply);
  apply();
  requestAnimationFrame(() => requestAnimationFrame(() => { api.ready = true; }));
}
