import { LINEUP_ROW, LINEUP_ROW_GAP, LINEUP_STEP, type ThreeIsometricRenderer } from './engine/three-renderer';
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
 *   &lineup=char_tanner[,n[,work|walk]]   stand n citizens of a character model in rows of 6 at
 *                                    the view centre (needs &pause); work loop or walk in place.
 *                                    Without cam/model it frames open ground, zoomed to fit all n.
 *   &door=house_baker[,n[,k[,zoom]]]  camera on the k-th door of the n-th placed building of a
 *                                    model, from the side it faces; the door is held open
 *   &follow=walk[,zoom]             camera follows the first visible walking citizen (polls
 *                                    until one walks); or follow=<index|id>[,zoom]; follow=inside
 *                                    picks someone indoors (the cutaway opens their building)
 *   &cutaway=<parcelId | model[,n[,zoom[,quadrant]]]>   look into a building (roof faded,
 *                                    people inside shown), camera on it unless cam/model given
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
     *  triangles for one pass, citizens per character model, and placed instances per
     *  building model (0 = loaded but never placed: check before relying on a model). */
    stats: () => {
      const { calls, triangles } = renderer.renderer.info.render;
      const models: Record<string, number> = {};
      for (const c of sim.citizens) {
        const m = renderer.getCitizenArchetype(c);
        models[m] = (models[m] ?? 0) + 1;
      }
      return { calls, triangles, citizenTrianglesPerPass: renderer.citizenTriangles(),
        crowd: renderer.crowdStats(), citizens: sim.citizens.length, models, placed: renderer.placedCounts(),
        nav: sim.navStats() };
    },
    /** Navigation only: grid build, routes (computed / cached / straight / failed), phases. */
    nav: () => sim.navStats(),
    /** One citizen's runtime state (index or id). */
    citizen: (k: number | string) => {
      const c = typeof k === 'number' ? sim.citizens[k] : sim.citizens.find((x) => x.id === k);
      if (!c) return null;
      const { id, name, trade, state, currentTask, currentX, currentZ, y, hidden, isMoving, gait, activityAnim } = c;
      return { id, name, trade, state, currentTask, currentX, currentZ, y, hidden, isMoving, gait, activityAnim };
    },
  };
  (window as unknown as { __lublin: typeof api }).__lublin = api;

  const num = (s: string | undefined) => (s === undefined || s === '' ? undefined : Number(s));
  /** Camera quadrant that looks at a wall with outward normal (nx, nz) most squarely. */
  const facing = (nx: number, nz: number) => {
    let q = 0, best = -2;
    for (let i = 0; i < 4; i++) {
      const yaw = (i * Math.PI) / 2 + Math.PI / 4;
      const dot = nx * Math.sin(yaw) + nz * Math.cos(yaw);
      if (dot > best) { best = dot; q = i; }
    }
    return q;
  };

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
    if (hour !== undefined) sim.setTime(hour);
    const door = params.get('door');
    if (door) {
      // n-th building of a model, k-th door: camera on the side the door faces, held open.
      const [name, n, k, zoom] = door.split(',');
      const b = sim.buildings.byModel.get(name)?.[num(n) ?? 0];
      const d = b?.doors[num(k) ?? 0];
      if (d) {
        const q = facing(d.nx, d.nz);
        // Centre the screen on the doorway's middle: the ground point behind it on the
        // camera ray (pitch 35.26 deg: 1.414 m back per metre up).
        const yaw = (q * Math.PI) / 2 + Math.PI / 4;
        const back = (d.y + d.h * 0.5) * 1.414;
        renderer.snapTo(d.x - Math.sin(yaw) * back, d.z - Math.cos(yaw) * back, num(zoom) ?? 9, q);
        sim.pinDoor(d, true);
      } else console.warn(`[debug] no door ${k ?? 0} on building ${n ?? 0} of "${name}"`);
    }
    const cut = params.get('cutaway');
    renderer.peek = null;
    if (cut) {
      // A parcel id, or model[,n]: look into that building (camera on it unless cam/model set).
      const [name, n, zoom, q] = cut.split(',');
      const b = sim.buildings.byParcel.get(name) ?? sim.buildings.byModel.get(name)?.[num(n) ?? 0];
      if (b) {
        renderer.peek = b;
        const d = b.doors[0];
        if (!cam && !model) renderer.snapTo(b.x, b.z, num(zoom) ?? 22, num(q) ?? (d ? facing(d.nx, d.nz) : undefined));
      } else console.warn(`[debug] cutaway: no building "${cut}"`);
    }
    const follow = params.get('follow');
    if (follow) {
      // A citizen index / id, or "walk" = the first visible citizen walking (waits for one).
      const [who, zoom] = follow.split(',');
      const pick = () => (who === 'walk'
        ? sim.citizens.find((c) => c.isMoving && !c.hidden)
        : who === 'inside' ? sim.citizens.find((c) => c.hidden && sim.insideOf(c))
        : /^\d+$/.test(who) ? sim.citizens[Number(who)] : sim.citizens.find((c) => c.id === who));
      let tries = 0;
      const t = setInterval(() => {
        const c = pick();
        if (c || ++tries > 120) clearInterval(t);
        if (!c) return;
        renderer.snapTo(c.currentX ?? 0, c.currentZ ?? 0, num(zoom) ?? 16);
        renderer.followingCitizen = c;
      }, 250);
    }
    const lineup = params.get('lineup');
    if (lineup) {
      if (!cam && !model) renderer.snapTo(LINEUP_SPOT[0], LINEUP_SPOT[1], LINEUP_SPOT[2]);
      const [arch, n, mode] = lineup.split(',');
      const m = mode === 'work' || mode === 'walk' ? mode : 'idle';
      const got = renderer.lineup(sim.citizens, arch, num(n) ?? 8, m);
      if (!got) console.warn(`[debug] lineup: no citizens use "${arch}"`);
      else if (!cam && !model) {
        // Zoom out until the whole block fits: the widest row across, and each row behind
        // the first rises LINEUP_ROW_GAP * sin(35°) on screen.
        const aspect = innerWidth / innerHeight || 16 / 9;
        const cols = Math.min(got, LINEUP_ROW), rows = Math.ceil(got / LINEUP_ROW);
        const zoom = Math.max(LINEUP_SPOT[2], ((cols - 1) * LINEUP_STEP + 1.2) / aspect,
          LINEUP_SPOT[2] + (rows - 1) * LINEUP_ROW_GAP * 0.6);
        renderer.snapTo(LINEUP_SPOT[0], LINEUP_SPOT[1], zoom);
      }
    }
  };

  window.addEventListener('hashchange', apply);
  apply();
  requestAnimationFrame(() => requestAnimationFrame(() => { api.ready = true; }));
}
