import type { CityPlan, Citizen, Parcel, BellHourInfo, FairEvent, StreetNode, ScheduleItem } from '../types';
import { SpatialHashGrid } from './spatial-hash';
import { NavGrid } from './nav-grid';
import { BuildingIndex, type Building, type Door, type Spot } from './building-anchors';
import { hashId, mulberry32 } from './citizen-crowd';

/**
 * Citizens' day: schedule -> destination -> route on the navigation grid -> door / stair legs.
 *
 * Movement runs at a fixed STEP (20 Hz) on its own seeded RNG, so a run is reproducible for
 * a given start time; positions handed to the renderer are interpolated between steps.
 *
 * Clock vs walking: at the default 5x speed one real second is one sim minute, so walking at
 * a real 1.35 m/s would make a 300 m commute take four sim hours. Travel is therefore shown
 * sped up (TRAVEL_SCALE x walking pace, scaled with sim speed) and every trip leaves early by
 * its estimated duration so people arrive about on the hour. Late starters run.
 *
 * Phases per citizen:
 *   IDLE      standing at a point destination (square, wall walk), wanders now and then
 *   ROUTE     waiting for a path (A* is budgeted per frame)
 *   WALK      following waypoints on the grid
 *   SCRIPT    a scripted leg off the grid: through a door, up or down a stair
 *   INSIDE    in a building: simulated, hidden
 *   SPOT      standing at a building's work / sell / guard spot, facing it
 */

const STEP = 1 / 20;
const MAX_STEPS = 4;
const WALK = 1.35;              // real walking pace, m/s
const TRAVEL_SCALE = 2.2;       // shown speed-up at 5x sim speed
const RUN = 1.85;               // running pace / walking pace
const DOOR_PACE = 0.55;         // door and stair legs, fraction of walking pace
const ROUTE_BUDGET = 40_000;    // A* expansions per frame
const ROUTE_CACHE = 3000;
const MARKET = { x0: -30, x1: 30, z0: -24, z1: 24 };
const TRAVEL = new Set(['COMMUTING', 'RETURNING']);

const Phase = { IDLE: 0, ROUTE: 1, WALK: 2, SCRIPT: 3, INSIDE: 4, SPOT: 5 } as const;
type Phase = (typeof Phase)[keyof typeof Phase];

interface Dest {
  b: Building | null;
  door: Door | null;
  spot: Spot | null;
  /** Point to walk to (door approach, spot, or open ground). */
  x: number; z: number;
  /** Open-ground destinations: wander radius around (cx, cz). */
  wander: number; cx: number; cz: number;
}

interface Agent {
  c: Citizen;
  rng: () => number;
  pace: number;
  items: ScheduleItem[];
  active: number;
  phase: Phase;
  dest: Dest | null;
  heldSpot: Spot | null;
  inB: Building | null;
  inDoor: Door | null;
  pts: Float32Array | null;
  wp: number;
  /** Scripted leg: x, y, z triples; then either go inside or route on to dest. */
  script: number[];
  sp: number;
  scriptInside: boolean;
  queued: boolean;
  running: boolean;
  /** Left for the active entry before its hour (that hour has not come yet). */
  early: boolean;
  /** Sim clock (hours since start, not wrapped) of the next wander. */
  nextWander: number;
}

export interface NavStats {
  buildMs: number; enclosedCells: number; components: number; grid: string;
  buildings: number; doors: number; offGridDoors: number; spots: number;
  routes: number; cacheHits: number; straight: number; failures: number;
  queue: number; avgExpanded: number; routeMsLastFrame: number;
  phases: Record<string, number>; running: number;
}

export class SimulationEngine {
  public plan: CityPlan;
  public spatialGrid: SpatialHashGrid;
  readonly nav: NavGrid;
  readonly buildings: BuildingIndex;

  // Time & Clock state
  public simTimeHours: number = 9.0; // Starts at 9:00 AM (Terce - Royal Fair Opening)
  public simSpeed: number = 5.0;     // 5x default
  public isPaused: boolean = false;
  public currentBellKey: string = 'terce';
  public currentBellInfo: BellHourInfo;

  // Parcels and Street Graph Lookup
  public parcelMap: Map<string, Parcel> = new Map();
  public streetNodeMap: Map<string, StreetNode> = new Map();
  public citizens: Citizen[] = [];

  // Active Selected Entity
  public selectedCitizen: Citizen | null = null;
  public selectedParcel: Parcel | null = null;

  // Events & Notifications
  public activeEvents: FairEvent[] = [];
  public onBellToll: ((bellName: string, hour: number) => void) | null = null;
  public onEventTriggered: ((event: FairEvent) => void) | null = null;

  private lastTriggeredBellHour: number = 9;
  private lastTriggeredEvents: Set<string> = new Set();

  private agents: Agent[] = [];
  // Sim-step positions (current and previous step) for interpolation.
  private px: Float32Array; private pz: Float32Array; private py: Float32Array;
  private ox: Float32Array; private oz: Float32Array; private oy: Float32Array;
  private acc = 0;
  private clock = 0; // sim hours since start, unwrapped
  private evalCursor = 0;
  private queue: number[] = [];
  private cache = new Map<string, Float32Array>();
  private marketSpots: Spot[] = [];
  private offGridDoors = 0;
  private stat = { routes: 0, cacheHits: 0, straight: 0, failures: 0, expanded: 0, routeMs: 0 };

  constructor(plan: CityPlan, spatialGrid: SpatialHashGrid, nav: NavGrid, buildings: BuildingIndex) {
    this.plan = plan;
    this.spatialGrid = spatialGrid;
    this.nav = nav;
    this.buildings = buildings;
    this.currentBellInfo = plan.bellHours['terce'];

    for (const p of plan.parcels) this.parcelMap.set(p.id, p);
    for (const node of plan.streetNetwork.nodes) this.streetNodeMap.set(node.id, node);
    this.spatialGrid.indexParcels(plan.parcels);
    // Doors whose approach lies off the walkable area (a front facing a walled gap) are
    // approached from the nearest reachable cell; the door leg then walks the rest.
    for (const b of buildings.all) for (const d of b.doors) {
      if (nav.isFree(d.ax, d.az)) continue;
      const c = nav.nearestFree(d.ax, d.az, 14);
      if (c >= 0) { d.ax = nav.cx(c); d.az = nav.cz(c); }
      this.offGridDoors++;
    }
    for (const name of ['szmatruz', 'town_hall']) {
      for (const b of buildings.byModel.get(name) ?? []) this.marketSpots.push(...b.spots);
    }

    this.citizens = plan.citizens;
    const n = this.citizens.length;
    this.px = new Float32Array(n); this.pz = new Float32Array(n); this.py = new Float32Array(n);
    this.ox = new Float32Array(n); this.oz = new Float32Array(n); this.oy = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const c = this.citizens[i];
      const rng = mulberry32(hashId(c.id) ^ 0x5eed);
      this.agents.push({
        c, rng, pace: 0.88 + rng() * 0.24,
        items: [...c.schedule].sort((a, b) => a.hour - b.hour),
        active: 0, phase: Phase.IDLE, dest: null, heldSpot: null, inB: null, inDoor: null,
        pts: null, wp: 0, script: [], sp: 0, scriptInside: false, queued: false, running: false, early: false, nextWander: 0,
      });
      c.animFrame = rng() * 10;
    }
    this.seatEveryone();
  }

  public setSpeed(speed: number): void {
    this.simSpeed = speed;
    if (speed > 0) this.isPaused = false;
  }

  public togglePause(): boolean {
    this.isPaused = !this.isPaused;
    return this.isPaused;
  }

  /** Jump the clock: everyone is put straight where their schedule says (no walking). */
  public setTime(hour: number): void {
    this.simTimeHours = ((hour % 24) + 24) % 24;
    this.seatEveryone();
    this.checkBellHour();
  }

  /** Sim hours that pass per real second. */
  private get hoursPerSec(): number { return (1.0 / 60.0) * (this.simSpeed / 5.0); }
  /** Shown walking speed (m per real second) for pace 1. */
  private get walkSpeed(): number { return WALK * TRAVEL_SCALE * Math.min(2.5, Math.max(0.5, this.simSpeed / 5)); }

  public update(dt: number): void {
    if (this.isPaused) return;
    const dh = dt * this.hoursPerSec;
    this.simTimeHours = (this.simTimeHours + dh) % 24.0;
    this.clock += dh;
    this.checkBellHour();
    this.checkSystemicEvents();

    this.acc += dt;
    let steps = 0;
    while (this.acc >= STEP && steps < MAX_STEPS) {
      this.ox.set(this.px); this.oz.set(this.pz); this.oy.set(this.py);
      this.step(STEP);
      this.acc -= STEP;
      steps++;
    }
    if (steps === MAX_STEPS) this.acc = Math.min(this.acc, STEP);
    this.processRoutes();

    const a = this.acc / STEP;
    for (let i = 0; i < this.agents.length; i++) {
      const c = this.agents[i].c;
      c.currentX = this.ox[i] + (this.px[i] - this.ox[i]) * a;
      c.currentZ = this.oz[i] + (this.pz[i] - this.oz[i]) * a;
      c.y = this.oy[i] + (this.py[i] - this.oy[i]) * a;
    }
  }

  // ---------------------------------------------------------------- schedule

  /** Item whose hour came last before now (wrapping over midnight). */
  private itemAt(ag: Agent, hour: number): number {
    let best = 0, bestAge = Infinity;
    for (let k = 0; k < ag.items.length; k++) {
      const age = (((hour - ag.items[k].hour) % 24) + 24) % 24;
      if (age < bestAge) { bestAge = age; best = k; }
    }
    return best;
  }

  private seatEveryone(): void {
    this.queue.length = 0;
    for (const b of this.buildings.all) for (const s of b.spots) s.taken = 0;
    for (let i = 0; i < this.agents.length; i++) {
      const ag = this.agents[i];
      ag.queued = false;
      ag.heldSpot = null;
      ag.early = false;
      ag.inB = null;
      ag.inDoor = null;
      ag.active = this.itemAt(ag, this.simTimeHours);
      const item = ag.items[ag.active];
      ag.c.state = item.state;
      ag.c.currentTask = item.task;
      const d = this.destFor(ag, item, null);
      ag.dest = d;
      if (d.spot) {
        this.place(i, d.spot.x, d.spot.y, d.spot.z);
        this.arriveSpot(ag, d.spot);
      } else if (d.door && d.b) {
        this.goInside(i, d.b, d.door);
      } else {
        this.place(i, d.x, 0, d.z);
        this.setPhase(ag, Phase.IDLE);
        ag.nextWander = this.clock + ag.rng() * 0.4;
      }
    }
  }

  /** Leave for the next item once its estimated trip time before the hour has come. */
  private evaluate(i: number): void {
    const ag = this.agents[i];
    const n = ag.items.length;
    const cur = ag.items[ag.active];
    const nextK = (ag.active + 1) % n;
    const next = ag.items[nextK];
    const gap = ((((next.hour - cur.hour) % 24) + 24) % 24) || 24;
    let since = (((this.simTimeHours - cur.hour) % 24) + 24) % 24;
    // Left early for `cur` and its hour has not come yet: the clock reads "almost a day since".
    if (ag.early) {
      if (since > gap) since = 0;
      else ag.early = false;
    }
    // Travel entries (COMMUTING, RETURNING) start on the hour; others are arrived at by it.
    const lead = TRAVEL.has(next.state) ? 0 : Math.min(gap * 0.8, this.leadHours(i, next));
    if (since < gap - lead) return;
    ag.active = nextK;
    ag.early = since < gap;
    this.begin(i, next);
  }

  /** Hour the current trip should end by: a travel entry's following entry, else its own. */
  private deadline(ag: Agent): number {
    const item = ag.items[ag.active];
    if (!TRAVEL.has(item.state)) return item.hour;
    return ag.items[(ag.active + 1) % ag.items.length].hour;
  }

  /** Estimated trip (sim hours) from where the citizen is to an item's place. */
  private leadHours(i: number, item: ScheduleItem): number {
    const ag = this.agents[i];
    const b = this.buildings.resolve(item.location);
    if (b && ag.inB === b) return 0;
    let tx: number, tz: number;
    if (b) { tx = b.x; tz = b.z; }
    else if (item.location === 'market_square') { tx = 0; tz = 0; }
    else return 0.15;
    const metres = Math.hypot(tx - this.px[i], tz - this.pz[i]) * 1.35 + 6;
    return (metres / (this.walkSpeed * ag.pace)) * this.hoursPerSec + 0.05;
  }

  private begin(i: number, item: ScheduleItem): void {
    const ag = this.agents[i];
    ag.c.state = item.state;
    ag.c.currentTask = item.task;
    if (ag.heldSpot) { ag.heldSpot.taken--; ag.heldSpot = null; }
    const d = this.destFor(ag, item, ag.inB);
    ag.dest = d;
    // Same building as now and going indoors again: stay put.
    if (ag.phase === Phase.INSIDE && d.door && d.b === ag.inB) return;
    ag.running = false;
    ag.c.faceYaw = undefined;
    ag.c.activityAnim = undefined;
    if (ag.phase === Phase.INSIDE && ag.inB && ag.inDoor) this.leave(i);
    else this.requestRoute(i);
  }

  private destFor(ag: Agent, item: ScheduleItem, from: Building | null): Dest {
    const loc = item.location;
    const working = item.state === 'WORKING' || item.state === 'PATROLLING';
    const point = (x: number, z: number, wander: number): Dest => {
      const cell = this.nav.nearestFree(x, z, 8);
      const px = cell >= 0 ? this.nav.cx(cell) : x, pz = cell >= 0 ? this.nav.cz(cell) : z;
      return { b: null, door: null, spot: null, x: px, z: pz, wander, cx: px, cz: pz };
    };
    const takeSpot = (spots: Spot[], tags: string[]): Spot | null => {
      const free = spots.filter((s) => tags.includes(s.tag) && s.taken === 0);
      if (!free.length) return null;
      const s = free[Math.floor(ag.rng() * free.length)];
      s.taken++;
      ag.heldSpot = s;
      return s;
    };

    if (loc === 'market_square') {
      const s = ag.rng() < 0.35 ? takeSpot(this.marketSpots, ['stand', 'sell']) : null;
      if (s) return { b: null, door: null, spot: s, x: s.x, z: s.z, wander: 0, cx: s.x, cz: s.z };
      const r = ag.rng, m = MARKET;
      return point(m.x0 + r() * (m.x1 - m.x0), m.z0 + r() * (m.z1 - m.z0), 12);
    }
    if (loc === 'curtain_wall') {
      const per = this.plan.defense.perimeterPoints;
      const p = per[Math.floor(ag.rng() * per.length)];
      // Inner side of the wall: step toward the town centre.
      const l = Math.hypot(p.x, p.z) || 1;
      return point(p.x - (p.x / l) * 9, p.z - (p.z / l) * 9, 14);
    }
    const b = this.buildings.resolve(loc);
    if (b) {
      if (working && b.spots.length) {
        // Visible work for about two in three workers when the building has free spots.
        const s = ag.rng() < 0.67 || !b.doors.length ? takeSpot(b.spots, ['work', 'guard', 'sell']) : null;
        if (s) return { b, door: null, spot: s, x: s.x, z: s.z, wander: 0, cx: s.x, cz: s.z };
      }
      if (b.doors.length) {
        const door = from === b && ag.inDoor ? ag.inDoor : b.doors[Math.floor(ag.rng() * b.doors.length)];
        return { b, door, spot: null, x: door.ax, z: door.az, wander: 0, cx: door.ax, cz: door.az };
      }
      const s = takeSpot(b.spots, ['stand', 'work', 'guard', 'sell']);
      if (s) return { b, door: null, spot: s, x: s.x, z: s.z, wander: 0, cx: s.x, cz: s.z };
      return point(b.x, b.z, 6);
    }
    const node = this.streetNodeMap.get(loc);
    if (node) return point(node.x, node.z, 8);
    return point((ag.rng() - 0.5) * 20, (ag.rng() - 0.5) * 20, 8);
  }

  // ---------------------------------------------------------------- legs

  private place(i: number, x: number, y: number, z: number): void {
    this.px[i] = this.ox[i] = x;
    this.pz[i] = this.oz[i] = z;
    this.py[i] = this.oy[i] = y;
    const c = this.agents[i].c;
    c.currentX = x; c.currentZ = z; c.y = y;
    c.targetX = x; c.targetZ = z;
    c.vx = 0; c.vz = 0;
  }

  private setPhase(ag: Agent, p: Phase): void {
    ag.phase = p;
    const c = ag.c;
    c.hidden = p === Phase.INSIDE;
    c.isMoving = p === Phase.WALK || p === Phase.SCRIPT;
    c.gait = ag.running && c.isMoving ? 1 : 0;
    c.strideScale = Math.sqrt(this.walkSpeed / WALK);
    if (!c.isMoving) { c.vx = 0; c.vz = 0; }
  }

  private goInside(i: number, b: Building, door: Door): void {
    const ag = this.agents[i];
    ag.inB = b;
    ag.inDoor = door;
    const j = (ag.rng() - 0.5) * Math.min(1.5, door.w);
    this.place(i, door.ix - door.nz * j, door.y, door.iz + door.nx * j);
    this.setPhase(ag, Phase.INSIDE);
  }

  private arriveSpot(ag: Agent, s: Spot): void {
    ag.c.faceYaw = s.yaw;
    ag.c.activityAnim = s.tag === 'stand' ? 'idle' : 'work';
    this.setPhase(ag, Phase.SPOT);
  }

  /** Walk out through the door (and down the stair), then route on. */
  private leave(i: number): void {
    const ag = this.agents[i];
    const d = ag.inDoor!;
    const s: number[] = [d.x, d.y, d.z];
    if (d.stair) for (let k = d.stair.length - 1; k >= 0; k--) s.push(d.stair[k].x, d.stair[k].y, d.stair[k].z);
    else s.push(d.ax, this.groundAt(d.ax, d.az), d.az);
    ag.inB = null;
    ag.inDoor = null;
    this.startScript(i, s, false);
  }

  private enter(i: number, d: Door): void {
    const s: number[] = [];
    if (d.stair) for (const p of d.stair) s.push(p.x, p.y, p.z);
    s.push(d.x, d.y, d.z, d.ix, d.y, d.iz);
    this.startScript(i, s, true);
  }

  private startScript(i: number, pts: number[], inside: boolean): void {
    const ag = this.agents[i];
    ag.script = pts;
    ag.sp = 0;
    ag.scriptInside = inside;
    this.setPhase(ag, Phase.SCRIPT);
  }

  private requestRoute(i: number): void {
    const ag = this.agents[i];
    this.setPhase(ag, Phase.ROUTE);
    if (!ag.queued) { ag.queued = true; this.queue.push(i); }
  }

  private processRoutes(): void {
    const t0 = performance.now();
    let budget = ROUTE_BUDGET;
    while (budget > 0 && this.queue.length) {
      const i = this.queue.shift()!;
      const ag = this.agents[i];
      ag.queued = false;
      if (ag.phase !== Phase.ROUTE || !ag.dest) continue;
      budget -= this.computeRoute(i) + 200;
    }
    this.stat.routeMs = performance.now() - t0;
  }

  /** Fills ag.pts and starts walking. Returns A* expansions spent. */
  private computeRoute(i: number): number {
    const ag = this.agents[i];
    const d = ag.dest!;
    const x = this.px[i], z = this.pz[i];
    let pts: Float32Array;
    let spent = 0;
    if (this.nav.lineFree(x, z, d.x, d.z, 1) || Math.hypot(d.x - x, d.z - z) < 1.5) {
      pts = new Float32Array([x, z, d.x, d.z]);
      this.stat.straight++;
    } else {
      const a = this.nav.nearestFree(x, z, 6), b = this.nav.nearestFree(d.x, d.z, 6);
      const key = a < 0 || b < 0 ? '' : `${Math.floor((a % this.nav.w) / 8)},${Math.floor(a / this.nav.w / 8)}|${b}`;
      let core = key ? this.cache.get(key) : undefined;
      if (core) {
        this.cache.delete(key); this.cache.set(key, core);
        this.stat.cacheHits++;
      } else if (key) {
        const r = this.nav.route(a, b);
        if (r) {
          spent = r.expanded;
          core = r.pts;
          this.cache.set(key, core);
          if (this.cache.size > ROUTE_CACHE) this.cache.delete(this.cache.keys().next().value!);
          this.stat.routes++;
          this.stat.expanded += r.expanded;
        }
      }
      if (core) {
        const out = [x, z];
        // Skip leading waypoints already behind us (cached routes start up to 4 m away).
        let k = 0;
        if (core.length > 4 && this.nav.lineFree(x, z, core[2], core[3], 1)) k = 2;
        for (; k < core.length; k++) out.push(core[k]);
        out.push(d.x, d.z);
        pts = new Float32Array(out);
      } else {
        pts = new Float32Array([x, z, d.x, d.z]);
        this.stat.failures++;
      }
    }
    ag.pts = pts;
    ag.wp = 1;
    // Late (or simply in a hurry): run.
    let len = 0;
    for (let k = 2; k < pts.length; k += 2) len += Math.hypot(pts[k] - pts[k - 2], pts[k + 1] - pts[k - 1]);
    const hoursLeft = (((this.deadline(ag) - this.simTimeHours) % 24) + 24) % 24;
    // Past the hour (wrapped to almost a day): late, hurry.
    const realLeft = hoursLeft > 12 ? 0 : hoursLeft / this.hoursPerSec;
    const need = len / Math.max(realLeft, 1);
    ag.running = len > 15 && (need > this.walkSpeed * ag.pace * 1.15 || ag.rng() < 0.05);
    this.setPhase(ag, Phase.WALK);
    return spent;
  }

  // ---------------------------------------------------------------- stepping

  private step(dt: number): void {
    // Re-check a twentieth of the schedules each step: everyone once per real second.
    const n = this.agents.length;
    const chunk = Math.ceil(n / 20);
    for (let k = 0; k < chunk; k++) {
      this.evaluate(this.evalCursor);
      this.evalCursor = (this.evalCursor + 1) % n;
    }
    const walk = this.walkSpeed;
    for (let i = 0; i < n; i++) {
      const ag = this.agents[i];
      const c = ag.c;
      switch (ag.phase) {
        case Phase.WALK: {
          const v = walk * ag.pace * (ag.running ? RUN : 1);
          this.walkStep(i, ag, v * dt);
          break;
        }
        case Phase.SCRIPT:
          this.scriptStep(i, ag, walk * ag.pace * DOOR_PACE * dt);
          break;
        case Phase.IDLE:
          if (ag.dest && ag.dest.wander > 0 && this.clock >= ag.nextWander) this.wander(i, ag);
          break;
        default:
          break;
      }
      if (c.isMoving) {
        c.vx = (this.px[i] - this.ox[i]) / dt;
        c.vz = (this.pz[i] - this.oz[i]) / dt;
        c.animFrame = ((c.animFrame ?? 0) + dt * 8.0) % 8;
      }
    }
  }

  private walkStep(i: number, ag: Agent, dist: number): void {
    const pts = ag.pts!;
    let x = this.px[i], z = this.pz[i];
    while (dist > 0 && ag.wp * 2 < pts.length) {
      const tx = pts[ag.wp * 2], tz = pts[ag.wp * 2 + 1];
      const dx = tx - x, dz = tz - z;
      const l = Math.hypot(dx, dz);
      if (l <= dist) { x = tx; z = tz; dist -= l; ag.wp++; continue; }
      x += (dx / l) * dist; z += (dz / l) * dist;
      dist = 0;
    }
    this.px[i] = x; this.pz[i] = z;
    const gy = this.groundAt(x, z);
    this.py[i] += (gy - this.py[i]) * 0.25;
    if (ag.wp * 2 < pts.length) {
      ag.c.targetX = pts[ag.wp * 2]; ag.c.targetZ = pts[ag.wp * 2 + 1];
      return;
    }
    // Arrived.
    ag.pts = null;
    const d = ag.dest!;
    if (d.door && d.b) this.enter(i, d.door);
    else if (d.spot) {
      this.py[i] = d.spot.y;
      this.arriveSpot(ag, d.spot);
    } else {
      this.setPhase(ag, Phase.IDLE);
      ag.c.activityAnim = 'idle';
      ag.nextWander = this.clock + 0.1 + ag.rng() * 0.5;
    }
  }

  private scriptStep(i: number, ag: Agent, dist: number): void {
    const s = ag.script;
    let x = this.px[i], y = this.py[i], z = this.pz[i];
    while (dist > 0 && ag.sp * 3 < s.length) {
      const tx = s[ag.sp * 3], ty = s[ag.sp * 3 + 1], tz = s[ag.sp * 3 + 2];
      const l = Math.hypot(tx - x, tz - z, (ty - y) * 1.5);
      if (l <= dist) { x = tx; y = ty; z = tz; dist -= l; ag.sp++; continue; }
      const f = dist / l;
      x += (tx - x) * f; y += (ty - y) * f; z += (tz - z) * f;
      dist = 0;
    }
    this.px[i] = x; this.py[i] = y; this.pz[i] = z;
    if (ag.sp * 3 < s.length) {
      ag.c.targetX = s[ag.sp * 3]; ag.c.targetZ = s[ag.sp * 3 + 2];
      return;
    }
    const d = ag.dest;
    if (ag.scriptInside && d?.b && d.door) {
      this.goInside(i, d.b, d.door);
      this.oy[i] = this.py[i];
    } else this.requestRoute(i);
  }

  private wander(i: number, ag: Agent): void {
    const d = ag.dest!;
    ag.nextWander = this.clock + 0.15 + ag.rng() * 0.6;
    const a = ag.rng() * Math.PI * 2, r = Math.sqrt(ag.rng()) * d.wander;
    const tx = d.cx + Math.cos(a) * r, tz = d.cz + Math.sin(a) * r;
    if (!this.nav.isFree(tx, tz) || this.nav.clearance(tx, tz) < 1) return;
    if (!this.nav.lineFree(this.px[i], this.pz[i], tx, tz, 1)) return;
    ag.pts = new Float32Array([this.px[i], this.pz[i], tx, tz]);
    ag.wp = 1;
    ag.running = false;
    this.setPhase(ag, Phase.WALK);
    // Wandering keeps the same destination (centre and radius); only the stop changes.
    ag.dest = { ...d, x: tx, z: tz };
  }

  /** Feet height on open ground: the parcel's raised yard, else the street. */
  private groundAt(x: number, z: number): number {
    const p = this.spatialGrid.findParcelAt(x, z);
    return p ? p.elevation * 0.3 : 0;
  }

  // ---------------------------------------------------------------- stats

  public navStats(): NavStats {
    const names = ['IDLE', 'ROUTE', 'WALK', 'SCRIPT', 'INSIDE', 'SPOT'];
    const phases: Record<string, number> = {};
    let running = 0;
    for (const ag of this.agents) {
      phases[names[ag.phase]] = (phases[names[ag.phase]] ?? 0) + 1;
      if (ag.running && ag.phase === Phase.WALK) running++;
    }
    let doors = 0, spots = 0;
    for (const b of this.buildings.all) { doors += b.doors.length; spots += b.spots.length; }
    const s = this.stat;
    return {
      buildMs: Math.round(this.nav.buildMs), enclosedCells: this.nav.enclosedCells, components: this.nav.components,
      grid: `${this.nav.w}x${this.nav.h}`,
      buildings: this.buildings.all.length, doors, offGridDoors: this.offGridDoors, spots,
      routes: s.routes, cacheHits: s.cacheHits, straight: s.straight, failures: s.failures,
      queue: this.queue.length, avgExpanded: s.routes ? Math.round(s.expanded / s.routes) : 0,
      routeMsLastFrame: Math.round(s.routeMs * 100) / 100, phases, running,
    };
  }

  // ---------------------------------------------------------------- bells & events

  private checkBellHour(): void {
    const hour = Math.floor(this.simTimeHours);
    if (hour !== this.lastTriggeredBellHour) {
      this.lastTriggeredBellHour = hour;
      for (const [key, info] of Object.entries(this.plan.bellHours)) {
        if (info.hour === hour) {
          this.currentBellKey = key;
          this.currentBellInfo = info;
          if (this.onBellToll) this.onBellToll(info.name, info.hour);
          break;
        }
      }
    }
  }

  private checkSystemicEvents(): void {
    const hour = Math.floor(this.simTimeHours);
    for (let i = 0; i < this.plan.fairEvents.length; i++) {
      const ev = this.plan.fairEvents[i];
      if (ev.triggerHour === hour && !this.lastTriggeredEvents.has(ev.id)) {
        this.lastTriggeredEvents.add(ev.id);
        this.activeEvents.unshift(ev);
        if (this.activeEvents.length > 5) this.activeEvents.pop();
        if (this.onEventTriggered) this.onEventTriggered(ev);
      } else if (ev.triggerHour !== hour && this.lastTriggeredEvents.has(ev.id)) {
        this.lastTriggeredEvents.delete(ev.id); // reset for the next day
      }
    }
  }

  public tollCivicBellManually(): void {
    if (this.onBellToll) this.onBellToll(this.currentBellInfo.name, Math.floor(this.simTimeHours));
  }
}
