import type { CityPlan, Citizen, Parcel, BellHourInfo, FairEvent, StreetNode } from '../types';
import { Life, type Activity, type LifeWorld, type Service } from './life';
import { SpatialHashGrid } from './spatial-hash';
import { NavGrid } from './nav-grid';
import * as THREE from 'three';
import { BuildingIndex, type Building, type Door, type Slot, type Spot } from './building-anchors';
import { hashId, mulberry32 } from './citizen-crowd';
import { freePoint, roomAt, roomCentre, routeInside } from './interiors';

/**
 * Citizens' day: activity (life.ts: blocks + needs) -> destination -> route on the navigation
 * grid -> door / stair legs. Each agent's needs tick and its planner re-thinks once per real
 * second at most (staggered); an activity runs until its time is up or something more urgent
 * comes (carrying bread or water home always comes first). Service lines (baker's windows,
 * the well) and chats between acquaintances (TALK) live here too; the phases below add
 *   TALK      stopped to chat, facing the other (gossip loop), then back to the route
 *   SERVE     in a service line, or at the window / well being served
 *
 * Movement runs at a fixed STEP (20 Hz) on its own seeded RNG, so a run is reproducible for
 * a given start time; positions handed to the renderer are interpolated between steps.
 *
 * Clock vs walking: at the default 5x speed one real second is one sim minute, so walking at
 * a real 1.35 m/s would make a 300 m commute take four sim hours. Travel is therefore shown
 * sped up (TRAVEL_SCALE x walking pace, scaled with sim speed up to 12.5x) and people leave
 * for a block early by the trip's estimated duration so they arrive about on time. Late
 * starters run. Above 12.5x trips take longer in sim hours (tune and test at 5-12x).
 *
 * Phases per citizen:
 *   IDLE      standing at a point destination (square, wall walk), wanders now and then
 *   ROUTE     waiting for a path (A* is budgeted per frame)
 *   WALK      following waypoints on the grid
 *   SCRIPT    a scripted leg off the grid: through a door, up or down a stair
 *   INSIDE    in a building: simulated, hidden (drawn while the building is cut away)
 *   SPOT      standing at a building's work / sell / guard spot, facing it
 *   QUEUE     waiting in line outside a door
 *
 * Inside (M6): a building with an interior has slots (beds, table seats, workbenches, the
 * hearth). Coming in, a citizen takes the slot their schedule state asks for - their own
 * bed (bedNumber) at night, a bench at work, the hearth or a seat otherwise - walks there
 * on the room grid (interiors.ts; up the ladder for an upper storey) and lies, sits or works
 * there. Leaving, they walk back to the door first. Nobody free to take: stand in the room.
 *
 * Doors (M4): a door opens when someone wants through, stays open while anyone is passing
 * and closes DOOR_HOLD s after the last. People pass one lane at a time (wide portals have
 * two or three), DOOR_GAP apart when following in the same direction; people coming out
 * go first, the ones going in queue outside, QUEUE_STEP apart. Someone inside waiting to
 * come out stays hidden until it is their turn. onDoor reports opening / shutting (sound).
 *
 * Walking (M3) is steered, not replayed: each step a walker's velocity relaxes toward its
 * next waypoint and is pushed by
 *   - everyone near it (a 2 m neighbour grid) by predicted time to collision, power-law
 *     falloff (Karamouzas et al. 2014), with a slight keep-right bias in head-on meetings
 *     so opposing streams form lanes;
 *   - walls closer than 1 m, along the distance field's gradient.
 * The grid stays a hard constraint (slide along walls). A walker that makes no progress for
 * STUCK_ASIDE s asks a standing person in its way to shuffle aside and briefly ignores
 * others; after STUCK_REPLAN s it plans again from where it is.
 * Household members leaving the same place for the same place walk together (the second
 * keeps step at the first one's side). Gaits by urgency: stroll (wandering), slow patrol,
 * brisk apprentices, run when late.
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

// Steering (speeds are the shown, sped-up ones: ~3 m/s walking, ~5.5 m/s running).
const NB = 2;                   // neighbour grid cell, m
const NB_R2 = 16;               // neighbours considered within 4 m
const RELAX = 0.3;              // s to reach the desired velocity
const RADIUS2 = 0.55;           // two body radii, m
const TTC_K = 1.5;              // power-law strength
const TTC_T0 = 1.2;             // s, exponential cutoff
const TTC_MAX = 2.5;            // s, ignore collisions further ahead
const KEEP_RIGHT = 2.5;         // m/s^2 lateral push in head-on meetings
const WALL_K = 5;               // m/s^2 at the wall face
const F_MAX = 30;               // m/s^2 cap on avoidance + wall push
const STUCK_ASIDE = 1.5;        // s without progress: ask a standing blocker to step aside
const STUCK_REPLAN = 3;         // s: plan again from here
const GHOST = 1;                // s ignoring other people after STUCK_ASIDE
const PAIR_JOIN = 20;           // m: a household member this close can walk along
const STROLL = 0.72, PATROL = 0.8, BRISK = 1.08;

// Doors (M4), real seconds.
const DOOR_OPEN = 0.4;          // closed -> open, eased by the renderer
const DOOR_CLOSE = 0.6;
const DOOR_HOLD = 0.5;          // stays open after the last person through
const DOOR_GAP = 0.55;          // s between two people through one lane, same direction
const DOOR_PASS = 0.85;         // open enough to walk through
const QUEUE_STEP = 0.75;        // m between people queueing at a door
const STAIR_STRIDE = 0.55;      // stride on steps, fraction of the walking stride
const INDOOR = 0.6;             // walking pace indoors, fraction of the street pace

const Phase = { IDLE: 0, ROUTE: 1, WALK: 2, SCRIPT: 3, INSIDE: 4, SPOT: 5, QUEUE: 6, TALK: 7, SERVE: 8 } as const;
const PHASE_NAMES = ['IDLE', 'ROUTE', 'WALK', 'SCRIPT', 'INSIDE', 'SPOT', 'QUEUE', 'TALK', 'SERVE'];

// Life (M7).
const TALK_R = 1.8;             // m: acquaintances this close may stop for a chat
const TALK_MIN = 4, TALK_MAX = 9; // real s of a chat
const TALK_GAP = 0.6;           // sim h before the same person chats again
const SERVE_MIN = 2.5;          // sim minutes at a baker's window (water: 2)
const SVC_STEP = 0.8;           // m between people in a service line
// Off-screen (M8)
const VIEW_MARGIN = 30;         // m around the camera's ground rectangle simulated in full
type Phase = (typeof Phase)[keyof typeof Phase];

interface Dest {
  b: Building | null;
  door: Door | null;
  spot: Spot | null;
  /** Point to walk to (door approach, spot, or open ground). */
  x: number; z: number;
  /** Open-ground destinations: wander radius around (cx, cz). */
  wander: number; cx: number; cz: number;
  /** A service to line up at (x, z is a point near the end of its line). */
  svc?: Service;
}

interface Agent {
  c: Citizen;
  rng: () => number;
  pace: number;
  /** What the citizen is doing (life.ts decides); next staggered re-think (clock). */
  act: Activity | null;
  nextThink: number;
  /** Talking: real seconds left, with whom; no new chat before this clock. */
  talkT: number; talkWith: number; nextTalk: number;
  /** Phase to go back to after a chat (IDLE or SPOT stand; anything else re-routes). */
  talkFrom: Phase;
  /** Service (baker's window, well) queued at or being served at. */
  svc: Service | null;
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
  /** Sim clock (hours since start, not wrapped) of the next wander. */
  nextWander: number;
  /** Gait pace factor for this leg (stroll / patrol / brisk). */
  gaitPace: number;
  /** Real seconds without progress; seconds left ignoring others. */
  stuck: number; ghost: number;
  /** Re-plans on this trip; after two the leg may cross blocked cells (no grid route). */
  replans: number; noClip: boolean;
  /** Walking at the side of this agent (-1: alone); how many walk at ours. */
  lead: number; followers: number;
  /** Has walked at the leader's side on this trip. */
  paired: boolean;
  /** Has reached the current activity's place (its arrival effects are done). */
  there: boolean;
  /** Door being walked through now (counted in its users); door being waited at. */
  gate: Door | null; qDoor: Door | null;
  /** Inside: slot held; walk in progress (x, y, z triples) and its next point; walking out. */
  slot: Slot | null;
  inPts: number[] | null; inK: number; inExit: boolean;
}

const _from = new THREE.Vector3();
const _pt = new THREE.Vector3();

export interface NavStats {
  buildMs: number; enclosedCells: number; components: number; grid: string;
  buildings: number; doors: number; offGridDoors: number; spots: number;
  routes: number; cacheHits: number; straight: number; failures: number;
  queue: number; avgExpanded: number; routeMsLastFrame: number;
  phases: Record<string, number>; running: number;
  /** Walkers now: stuck (> STUCK_ASIDE), pairs walking together; totals since start. */
  stuckNow: number; pairs: number; replans: number; asides: number; stepMs: number;
  /** Walkers now off view, gliding along their routes without avoidance (M8). */
  gliding: number;
  /** Doors now open or moving, people queueing outside / waiting inside; totals since start. */
  doorsOpen: number; queueing: number; waitingInside: number; doorOpenings: number;
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
  /** A door starts opening (true) or has just shut (false). */
  public onDoor: ((door: Door, opening: boolean) => void) | null = null;
  /** Two acquaintances stop to talk (speech bubble, voice). */
  public onTalk: ((a: Citizen, b: Citizen) => void) | null = null;
  /** Needs, households and the activity planner (M7). */
  readonly life: Life;
  /** Doors open or moving (the renderer draws their leaves). */
  readonly activeDoors: Door[] = [];

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
  private stat = { routes: 0, cacheHits: 0, straight: 0, failures: 0, expanded: 0, routeMs: 0,
    replans: 0, asides: 0, stepMs: 0, doorOpenings: 0, talks: 0, served: 0, errands: 0, gliding: 0 };
  // Ground rectangle seen by the camera plus VIEW_MARGIN (M8); everything counts as in view
  // until the renderer reports one.
  private vx0 = -Infinity; private vz0 = -Infinity; private vx1 = Infinity; private vz1 = Infinity;
  private world: LifeWorld;
  private realT = 0; // real seconds of simulated stepping
  // Steering velocity (m/s, shown speed) per agent.
  private vx: Float32Array; private vz: Float32Array;
  // Neighbour grid: linked lists of agents per NB cell, rebuilt every step.
  private nbW: number; private nbH: number;
  private nbHead: Int32Array; private nbNext: Int32Array;
  private nbUsed: number[] = [];
  private household = new Map<string, number[]>();
  private force = { x: 0, z: 0 };

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
    this.vx = new Float32Array(n); this.vz = new Float32Array(n);
    this.nbW = Math.ceil((nav.w * 0.5) / NB) + 1;
    this.nbH = Math.ceil((nav.h * 0.5) / NB) + 1;
    this.nbHead = new Int32Array(this.nbW * this.nbH).fill(-1);
    this.nbNext = new Int32Array(n);
    for (let i = 0; i < n; i++) {
      const c = this.citizens[i];
      const rng = mulberry32(hashId(c.id) ^ 0x5eed);
      this.agents.push({
        c, rng, pace: 0.88 + rng() * 0.24,
        act: null, nextThink: 0, talkT: 0, talkWith: -1, nextTalk: 0, talkFrom: Phase.IDLE, svc: null,
        phase: Phase.IDLE, dest: null, heldSpot: null, inB: null, inDoor: null,
        pts: null, wp: 0, script: [], sp: 0, scriptInside: false, queued: false, running: false, nextWander: 0,
        gaitPace: 1, stuck: 0, ghost: 0, replans: 0, noClip: false, lead: -1, followers: 0, paired: false, there: false,
        gate: null, qDoor: null, slot: null, inPts: null, inK: 0, inExit: false,
      });
      c.animFrame = rng() * 10;
      const h = this.household.get(c.homeParcelId);
      if (h) h.push(i); else this.household.set(c.homeParcelId, [i]);
    }
    this.life = new Life(this.citizens, this.household, this.parcelMap, this.buildServices(), this.lifePlaces(),
      this.agents.map((a) => a.rng));
    const sim = this;
    this.world = {
      get hour() { return sim.simTimeHours; },
      get clock() { return sim.clock; },
      travel: (i, loc) => this.leadHours(i, loc),
      pos: (i) => [this.px[i], this.pz[i]],
      wallet: (i) => this.citizens[i].walletGroschen,
    };
    this.seatEveryone();
  }

  /** Baker's windows (beside the shop door) and the four sides of the town well. */
  private buildServices(): Service[] {
    const out: Service[] = [];
    const free = (x: number, z: number) => this.nav.isFree(x, z) && this.nav.clearance(x, z) >= 0.5;
    for (const b of this.buildings.all) {
      const p = b.parcelId ? this.parcelMap.get(b.parcelId) : undefined;
      if (p?.craft?.id !== 'baker' || !b.doors.length) continue;
      const d = b.doors[0];
      // The window counter: along the front beside the door, or the door itself.
      for (const s of [1.6, -1.6, 0]) {
        const x = d.ax - d.nz * s, z = d.az + d.nx * s;
        if (!free(x, z) || !free(x + d.nx * SVC_STEP, z + d.nz * SVC_STEP)) continue;
        out.push({ kind: 'bread', x, z, fx: -d.nx, fz: -d.nz, nx: d.nx, nz: d.nz,
          name: p.name ?? `the baker on ${p.streetName}`, line: [], user: -1, doneT: 0 });
        break;
      }
    }
    const wx = -14, wz = 10; // three-renderer places town_well here
    for (let k = 0; k < 4; k++) {
      const a = (k * Math.PI) / 2 + Math.PI / 4;
      const nx = Math.sin(a), nz = Math.cos(a);
      for (let r = 1.0; r <= 3; r += 0.25) {
        const x = wx + nx * r, z = wz + nz * r;
        if (!free(x, z)) continue;
        out.push({ kind: 'water', x, z, fx: -nx, fz: -nz, nx, nz, name: 'the town well', line: [], user: -1, doneT: 0 });
        break;
      }
    }
    return out;
  }

  /** Churches, taverns (brewers), workshops (errands) and the wall checkpoints. */
  private lifePlaces() {
    const churches = [];
    for (const [id, name] of [['parish_fara', "St Michael's (Fara)"], ['dominican_monastery', "the Dominicans' St Stanislaus"]]) {
      const b = this.buildings.resolve(id);
      if (b?.doors.length) churches.push({ id, name, x: b.x, z: b.z });
    }
    const taverns = [], workshops = [];
    for (const b of this.buildings.all) {
      const p = b.parcelId ? this.parcelMap.get(b.parcelId) : undefined;
      if (!p?.craft || !b.doors.length) continue;
      const place = { id: p.id, x: b.x, z: b.z, name: p.name ?? `the ${p.craft.id} on ${p.streetName}` };
      workshops.push(place);
      if (p.craft.id === 'brewer') taverns.push(place);
    }
    // Inner side of each tower and gate, in order round the wall.
    const per = [...this.plan.defense.perimeterPoints].sort((a, b) => Math.atan2(a.z, a.x) - Math.atan2(b.z, b.x));
    const checkpoints = [];
    for (const p of per) {
      const l = Math.hypot(p.x, p.z) || 1;
      const c = this.nav.nearestFree(p.x - (p.x / l) * 9, p.z - (p.z / l) * 9, 12);
      if (c >= 0) checkpoints.push({ x: this.nav.cx(c), z: this.nav.cz(c) });
    }
    return { churches, taverns, workshops, checkpoints };
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

  private seatEveryone(): void {
    this.queue.length = 0;
    for (const s of this.life.services) { s.line.length = 0; s.user = -1; }
    // Households' stores and everyone's needs as they would be at this hour; the planner
    // then says where each one is.
    for (let i = 0; i < this.agents.length; i++) {
      const ag = this.agents[i];
      this.life.seed(i, this.simTimeHours, this.clock, ag.rng);
      this.px[i] = this.citizens[i].currentX ?? 0;
      this.pz[i] = this.citizens[i].currentZ ?? 0;
    }
    for (const b of this.buildings.all) {
      for (const s of b.spots) s.taken = 0;
      for (const s of b.interior?.slots ?? []) s.taken = 0;
      for (const d of b.doors) {
        d.open = 0; d.users = 0; d.dir = 0; d.hold = 0; d.active = false;
        d.queue.length = 0; d.exitQ.length = 0;
      }
    }
    this.activeDoors.length = 0;
    for (let i = 0; i < this.agents.length; i++) {
      const ag = this.agents[i];
      ag.queued = false;
      ag.gate = null; ag.qDoor = null;
      ag.heldSpot = null;
      ag.inB = null;
      ag.inDoor = null;
      ag.slot = null; ag.inPts = null; ag.inExit = false;
      ag.svc = null; ag.talkT = 0; ag.talkWith = -1;
      this.clearPose(ag.c);
      ag.c.carriedItem = this.life.minds[i].tool;
      ag.c.carrying = undefined;
      ag.lead = -1; ag.followers = 0;
      ag.stuck = 0; ag.ghost = 0;
      this.vx[i] = 0; this.vz[i] = 0;
      const act = this.life.decide(i, ag.c, null, this.world, ag.rng);
      // Errands and services in progress are not seated: rest at home instead.
      if (act.kind === 'bread' || act.kind === 'water' || act.kind === 'errand') {
        this.life.release(i);
        act.kind = 'home'; act.state = 'RESTING'; act.location = this.life.minds[i].hh.home; act.task = 'At home';
      }
      ag.act = act;
      ag.nextThink = this.clock + ag.rng() * 0.2;
      ag.nextTalk = this.clock + ag.rng() * TALK_GAP;
      ag.c.state = act.state;
      ag.c.currentTask = act.task;
      this.life.note(this.life.minds[i], act, this.simTimeHours);
      const d = this.destFor(ag, act, null);
      ag.dest = d;
      ag.there = true;
      if (d.spot) {
        this.place(i, d.spot.x, d.spot.y, d.spot.z);
        this.arriveSpot(ag, d.spot);
      } else if (d.door && d.b) {
        this.goInside(i, d.b, d.door, true);
      } else {
        this.place(i, d.x, 0, d.z);
        this.setPhase(ag, Phase.IDLE);
        ag.nextWander = this.clock + ag.rng() * 0.4;
      }
    }
  }

  /** Needs over time, then ask the planner whether to keep going or do something else. */
  private evaluate(i: number): void {
    const ag = this.agents[i];
    const life = this.life;
    life.tick(i, this.clock, this.simTimeHours, ag.act, ag.there && ag.phase !== Phase.TALK, ag.c);
    if (ag.phase === Phase.TALK) return;
    if (ag.phase === Phase.IDLE || ag.phase === Phase.WALK) this.maybeTalk(i, ag);
    if ((ag.phase as Phase) === Phase.TALK) return;
    const cur = ag.act;
    // Served and carrying: decide now (take it home).
    const forced = !!life.minds[i].carrying && cur?.kind !== 'drop';
    if (!forced && cur && this.clock < cur.until && this.clock < ag.nextThink) return;
    // Waiting in a line or at the window: keep going while the activity lasts.
    if (!forced && ag.svc && cur && this.clock < cur.until) return;
    ag.nextThink = this.clock + 0.1 + ag.rng() * 0.1;
    const next = life.decide(i, ag.c, cur, this.world, ag.rng);
    if (next === cur) return;
    if (cur && (cur.kind === 'bread' || cur.kind === 'water') && !life.minds[i].carrying) life.release(i);
    if (next.kind === 'errand') this.stat.errands++;
    ag.act = next;
    this.begin(i, next);
  }

  /** Estimated trip (sim hours) from where the citizen is to a location. */
  private leadHours(i: number, loc: string): number {
    const ag = this.agents[i];
    const b = this.buildings.resolve(loc);
    if (b && ag.inB === b) return 0;
    let tx: number, tz: number;
    if (b) { tx = b.x; tz = b.z; }
    else if (loc === 'market_square') { tx = 0; tz = 0; }
    else if (loc.startsWith('svc:')) { const s = this.life.services[+loc.slice(4)]; tx = s.x; tz = s.z; }
    else if (loc.startsWith('wall:')) { const p = this.life.checkpoint(+loc.slice(5)); tx = p.x; tz = p.z; }
    else return 0.15;
    const metres = Math.hypot(tx - this.px[i], tz - this.pz[i]) * 1.35 + 6;
    return (metres / (this.walkSpeed * ag.pace)) * this.hoursPerSec + 0.05;
  }

  private begin(i: number, act: Activity): void {
    const ag = this.agents[i];
    ag.c.state = act.state;
    ag.c.currentTask = act.task;
    this.life.note(this.life.minds[i], act, this.simTimeHours);
    if (ag.heldSpot) { ag.heldSpot.taken--; ag.heldSpot = null; }
    this.releaseDoor(i);
    this.leaveService(i);
    ag.c.activityAnim = undefined;
    const d = this.destFor(ag, act, ag.inB);
    ag.dest = d;
    ag.there = false;
    // Same building as now and going indoors again: stay, moving to the slot for the new state.
    if (ag.phase === Phase.INSIDE && d.door && d.b === ag.inB) {
      this.reached(i);
      if (ag.inB?.interior) this.takeSlot(i, false);
      return;
    }
    this.dropPair(i);
    ag.running = false;
    ag.replans = 0;
    ag.noClip = false;
    this.clearPose(ag.c);
    const fromB = ag.phase === Phase.INSIDE ? ag.inB : null;
    if (ag.phase === Phase.INSIDE && ag.inB && ag.inDoor) this.walkOut(i);
    else this.requestRoute(i);
    this.recruitCompanion(i, act, fromB);
  }

  /**
   * A household member at the same place comes along: to the same block place (work, home)
   * when theirs starts within 45 min, or to a free outing (market, church, tavern, home) when
   * they are only resting or strolling themselves.
   */
  private recruitCompanion(i: number, act: Activity, fromB: Building | null): void {
    const ag = this.agents[i];
    if (ag.lead >= 0 || ag.followers > 0) return;
    const fam = this.household.get(ag.c.homeParcelId);
    if (!fam || fam.length < 2) return;
    const outing = act.kind === 'market' || act.kind === 'church' || act.kind === 'tavern' || act.kind === 'home'
      || act.kind === 'eat_out';
    for (const k of fam) {
      if (k === i) continue;
      const K = this.agents[k];
      if (K.lead >= 0 || K.followers > 0 || K.phase === Phase.TALK || K.svc) continue;
      if (fromB) {
        if (K.phase !== Phase.INSIDE || K.inB !== fromB) continue;
      } else {
        if (K.phase !== Phase.IDLE && K.phase !== Phase.SPOT) continue;
        if (Math.hypot(this.px[k] - this.px[i], this.pz[k] - this.pz[i]) > PAIR_JOIN) continue;
      }
      const ka = K.act;
      if (!ka || ka.location === act.location) continue;
      let next: Activity | null = null;
      if (ka.fixed || ka.kind === 'bread' || ka.kind === 'water' || ka.kind === 'errand' || ka.kind === 'drop') continue;
      const soon = this.life.blockSoon(k, this.simTimeHours, 0.75);
      const same = soon === 'home' ? this.life.minds[k].hh.home : soon === 'work' ? K.c.workParcelId : null;
      if (same === act.location && (act.kind === 'work' || act.kind === 'home' || act.kind === 'sleep')) {
        next = { ...act };
      } else if (outing && (ka.kind === 'home' || ka.kind === 'market')) {
        next = { ...act };
      }
      if (!next) continue;
      K.act = next;
      this.begin(k, next);
      // Stayed inside (already there), or brought someone of its own along.
      if ((K.phase === Phase.INSIDE && !K.inExit) || K.followers > 0) continue;
      K.lead = i;
      ag.followers++;
      // Same stop: share the leader's door, or stand beside its point.
      const d = ag.dest!;
      if (K.heldSpot && !d.spot) { K.heldSpot.taken--; K.heldSpot = null; }
      if (!d.spot) {
        const ox = this.nav.isFree(d.x + 0.8, d.z) ? 0.8 : 0;
        K.dest = { ...d, x: d.x + ox, cx: d.cx + ox };
      }
      return;
    }
  }

  /** Stop walking together (either side). */
  private dropPair(i: number): void {
    const ag = this.agents[i];
    ag.paired = false;
    if (ag.lead >= 0) { this.agents[ag.lead].followers--; ag.lead = -1; }
    if (ag.followers > 0) {
      for (const k of this.household.get(ag.c.homeParcelId) ?? []) {
        const K = this.agents[k];
        if (K.lead !== i) continue;
        K.lead = -1;
        // Its own route is stale once it has walked beside us: plan again from here.
        if (K.paired && K.phase === Phase.WALK) this.requestRoute(k);
        K.paired = false;
      }
      ag.followers = 0;
    }
  }

  private destFor(ag: Agent, item: Activity, from: Building | null): Dest {
    const loc = item.location;
    const working = item.state === 'WORKING' || item.state === 'PATROLLING';
    if (loc.startsWith('svc:')) {
      // Walk to just past the end of the line; join it there.
      const s = this.life.services[+loc.slice(4)];
      const k = s.line.length + 1;
      let x = s.x + s.nx * SVC_STEP * k, z = s.z + s.nz * SVC_STEP * k;
      const cell = this.nav.nearestFree(x, z, 6);
      if (cell >= 0) { x = this.nav.cx(cell); z = this.nav.cz(cell); }
      return { b: null, door: null, spot: null, x, z, wander: 0, cx: x, cz: z, svc: s };
    }
    if (loc.startsWith('wall:')) {
      const p = this.life.checkpoint(+loc.slice(5));
      return { b: null, door: null, spot: null, x: p.x, z: p.z, wander: 3, cx: p.x, cz: p.z };
    }
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

  /** In through the door: to a slot (walking there, or put straight on it when `settle`). */
  private goInside(i: number, b: Building, door: Door, settle = false): void {
    const ag = this.agents[i];
    ag.inB = b;
    ag.inDoor = door;
    ag.inExit = false;
    const j = (ag.rng() - 0.5) * Math.min(1.5, door.w);
    this.place(i, door.ix - door.nz * j, door.y, door.iz + door.nx * j);
    this.setPhase(ag, Phase.INSIDE);
    if (ag.dest?.b === b) this.reached(i);
    if (b.interior) this.takeSlot(i, settle);
  }

  /** The slot the citizen's state asks for in the building they are in, or null (none free). */
  private pickSlot(ag: Agent, b: Building): Slot | null {
    const slots = b.interior!.slots;
    const st = ag.c.state;
    if (st === 'SLEEPING' && b.parcelId === ag.c.homeParcelId) {
      let n = 0;
      for (const s of slots) if (s.kind === 'sleep') n++;
      let k = n ? (((ag.c.bedNumber - 1) % n) + n) % n : -1;
      for (const s of slots) if (s.kind === 'sleep' && k-- === 0 && !s.taken) return s;
    }
    const want: Slot['kind'][] = st === 'SLEEPING' ? ['sleep']
      : st === 'WORKING' || st === 'PATROLLING' ? ['work', 'seat']
      : st === 'WAKING' ? ['hearth', 'seat'] : ['seat', 'hearth'];
    for (const kind of want) {
      let free = 0;
      for (const s of slots) if (s.kind === kind && !s.taken) free++;
      if (!free) continue;
      let k = Math.floor(ag.rng() * free);
      for (const s of slots) if (s.kind === kind && !s.taken && k-- === 0) return s;
    }
    return null;
  }

  /** Take (or change to) the slot for the current state and walk to it; settle = be there now. */
  private takeSlot(i: number, settle: boolean): void {
    const ag = this.agents[i];
    const b = ag.inB!, it = b.interior!;
    const old = ag.slot;
    if (old) old.taken--;
    ag.slot = null;
    const s = this.pickSlot(ag, b);
    if (s) { s.taken++; ag.slot = s; }
    ag.inExit = false;
    if (s && s === old && !ag.inPts) { this.arriveSlot(ag); return; } // already there
    const room = s ? s.room : 0;
    if (!s) freePoint(b, 0, ag.rng(), _pt);
    if (settle) {
      if (s) this.place(i, s.x, s.y, s.z); else this.place(i, _pt.x, _pt.y, _pt.z);
      ag.inPts = null;
      this.arriveSlot(ag);
      return;
    }
    _from.set(this.px[i], this.py[i], this.pz[i]);
    const floorY = roomCentre(it, room, _pt.clone()).y;
    let pts: number[];
    if (s) {
      pts = routeInside(b, _from, roomAt(it, this.py[i]), s.ax, floorY, s.az, room);
      pts.push(s.x, s.y, s.z);
    } else pts = routeInside(b, _from, roomAt(it, this.py[i]), _pt.x, _pt.y, _pt.z, room);
    this.startInside(ag, pts, false);
  }

  /** Leaving: back to the door through the rooms, then out (leave) when there. */
  private walkOut(i: number): void {
    const ag = this.agents[i];
    const b = ag.inB!, d = ag.inDoor!;
    if (ag.slot) { ag.slot.taken--; ag.slot = null; }
    this.clearPose(ag.c);
    if (!b.interior || Math.hypot(this.px[i] - d.ix, this.pz[i] - d.iz) < 0.6) { ag.inPts = null; this.leave(i); return; }
    _from.set(this.px[i], this.py[i], this.pz[i]);
    const it = b.interior;
    const pts = routeInside(b, _from, roomAt(it, this.py[i]), d.ix, roomCentre(it, 0, _pt).y, d.iz, 0);
    this.startInside(ag, pts, true);
  }

  private startInside(ag: Agent, pts: number[], exit: boolean): void {
    ag.inPts = pts;
    ag.inK = 0;
    ag.inExit = exit;
    this.clearPose(ag.c);
    ag.c.isMoving = true;
    ag.c.gait = 0;
  }

  /** Walk on along the inside path; at its end take the slot, or go out. */
  private insideStep(i: number, ag: Agent, dist: number): void {
    const s = ag.inPts!;
    let x = this.px[i], y = this.py[i], z = this.pz[i];
    while (dist > 0 && ag.inK * 3 < s.length) {
      const tx = s[ag.inK * 3], ty = s[ag.inK * 3 + 1], tz = s[ag.inK * 3 + 2];
      const l = Math.hypot(tx - x, tz - z, ty - y);
      if (l <= dist) { x = tx; y = ty; z = tz; dist -= l; ag.inK++; continue; }
      const f = dist / l;
      x += (tx - x) * f; y += (ty - y) * f; z += (tz - z) * f;
      dist = 0;
    }
    this.px[i] = x; this.py[i] = y; this.pz[i] = z;
    if (ag.inK * 3 < s.length) {
      ag.c.targetX = s[ag.inK * 3]; ag.c.targetZ = s[ag.inK * 3 + 2];
      return;
    }
    ag.inPts = null;
    if (ag.inExit) {
      ag.inExit = false;
      ag.c.isMoving = false;
      this.leave(i);
    } else this.arriveSlot(ag);
  }

  private arriveSlot(ag: Agent): void {
    const c = ag.c, s = ag.slot;
    c.isMoving = false;
    c.vx = 0; c.vz = 0;
    c.pose = s && s.pose !== 'stand' ? s.pose : undefined;
    c.faceYaw = s ? s.yaw : undefined;
    c.activityAnim = s?.kind === 'work' ? 'work' : 'idle';
  }

  private clearPose(c: Citizen): void {
    c.pose = undefined;
    c.faceYaw = undefined;
    c.activityAnim = undefined;
  }

  private arriveSpot(ag: Agent, s: Spot): void {
    ag.c.pose = undefined;
    ag.c.faceYaw = s.yaw;
    ag.c.activityAnim = s.tag === 'stand' ? 'idle' : 'work';
    this.setPhase(ag, Phase.SPOT);
  }

  /** Come out through the door when it is our turn (and down the stair), then route on. */
  private leave(i: number): void {
    const ag = this.agents[i];
    const d = ag.inDoor!;
    if (!this.gateFree(d, -1)) { this.wait(i, d, d.exitQ); return; }
    this.takeGate(i, d, -1);
    const s: number[] = [d.x, d.y, d.z];
    if (d.stair) for (let k = d.stair.length - 1; k >= 0; k--) s.push(d.stair[k].x, d.stair[k].y, d.stair[k].z);
    else s.push(d.ax, this.groundAt(d.ax, d.az), d.az);
    ag.inB = null;
    ag.inDoor = null;
    this.place(i, d.x, d.y, d.z);
    this.startScript(i, s, false);
  }

  /** Up the stair and in through the door, or into the queue outside it. */
  private enter(i: number, d: Door, headOfQueue = false): void {
    if ((!headOfQueue && d.queue.length) || !this.gateFree(d, 1)) {
      this.wait(i, d, d.queue);
      this.setPhase(this.agents[i], Phase.QUEUE);
      return;
    }
    this.takeGate(i, d, 1);
    const s: number[] = [];
    if (d.stair) for (const p of d.stair) s.push(p.x, p.y, p.z);
    s.push(d.x, d.y, d.z, d.ix, d.y, d.iz);
    this.startScript(i, s, true);
  }

  // ---------------------------------------------------------------- doors

  /** May someone walk through in direction dir (+1 in, -1 out) now? Coming out goes first. */
  private gateFree(d: Door, dir: number): boolean {
    if (d.open < DOOR_PASS) { this.wake(d); return false; }
    if (dir > 0 && d.exitQ.length) return false;
    if (d.users === 0) return true;
    return d.dir === dir && this.realT - d.gateT >= DOOR_GAP / d.lanes;
  }

  private takeGate(i: number, d: Door, dir: number): void {
    d.users++; d.dir = dir; d.gateT = this.realT;
    this.agents[i].gate = d;
    this.wake(d);
  }

  private wait(i: number, d: Door, line: number[]): void {
    line.push(i);
    this.agents[i].qDoor = d;
    this.wake(d);
  }

  /** The building a citizen is in (hidden there) and the door they came in by, or null. */
  public insideOf(c: Citizen): { b: Building; door: Door } | null {
    const i = this.citizens.indexOf(c);
    const ag = this.agents[i];
    return ag && ag.phase === Phase.INSIDE && ag.inB && ag.inDoor ? { b: ag.inB, door: ag.inDoor } : null;
  }

  /** Everyone inside a building now (the cutaway shows them). */
  public occupants(b: Building, out: Citizen[] = []): Citizen[] {
    for (const ag of this.agents) if (ag.phase === Phase.INSIDE && ag.inB === b) out.push(ag.c);
    return out;
  }

  /** Placement indices of buildings with someone awake inside (lit windows at night). */
  public awakeInside(out: Set<number>): Set<number> {
    out.clear();
    for (const ag of this.agents) {
      if (ag.phase === Phase.INSIDE && ag.inB && ag.c.pose !== 'lie') out.add(ag.inB.index);
    }
    return out;
  }

  /** Debug: hold a door open (or let it shut again). */
  public pinDoor(d: Door, on: boolean): void {
    d.pinned = on;
    this.wake(d);
  }

  private wake(d: Door): void {
    if (d.active) return;
    d.active = true;
    this.activeDoors.push(d);
  }

  /** Let go of a door: through it (gate), or no longer waiting (schedule moved on). */
  private releaseDoor(i: number): void {
    const ag = this.agents[i];
    if (ag.gate) { ag.gate.users = Math.max(0, ag.gate.users - 1); ag.gate = null; }
    const d = ag.qDoor;
    if (d) {
      let k = d.queue.indexOf(i);
      if (k >= 0) d.queue.splice(k, 1);
      k = d.exitQ.indexOf(i);
      if (k >= 0) d.exitQ.splice(k, 1);
      ag.qDoor = null;
    }
  }

  /** Where the k-th person in a door's queue stands: back from the approach, away from it. */
  private queuePoint(d: Door, k: number): [number, number] {
    let ox = d.nx, oz = d.nz;
    if (d.stair && d.stair.length > 1) {
      const a = d.stair[0], b = d.stair[1];
      const l = Math.hypot(a.x - b.x, a.z - b.z) || 1;
      ox = (a.x - b.x) / l; oz = (a.z - b.z) / l;
    }
    const side = (k & 1 ? 1 : -1) * 0.15; // a loose line, not a column
    let x = d.ax + ox * QUEUE_STEP * k - oz * side, z = d.az + oz * QUEUE_STEP * k + ox * side;
    if (k > 0 && !this.nav.isFree(x, z)) {
      // Facing a wall or a street edge: line up along the front instead.
      const s = k & 1 ? 1 : -1;
      x = d.ax - oz * QUEUE_STEP * Math.ceil(k / 2) * s;
      z = d.az + ox * QUEUE_STEP * Math.ceil(k / 2) * s;
    }
    return [x, z];
  }

  /** Shuffle up in the queue toward our place in it. */
  private queueStep(i: number, ag: Agent, dist: number): void {
    const d = ag.qDoor;
    const k = d ? d.queue.indexOf(i) : -1;
    if (!d || k < 0) { this.requestRoute(i); return; }
    const [tx, tz] = this.queuePoint(d, k);
    const x = this.px[i], z = this.pz[i];
    const l = Math.hypot(tx - x, tz - z);
    const c = ag.c;
    if (l < 0.03) {
      c.isMoving = false;
      // Face the door.
      c.faceYaw = Math.atan2(d.x - x, d.z - z);
      return;
    }
    const f = Math.min(1, dist / l);
    this.px[i] = x + (tx - x) * f;
    this.pz[i] = z + (tz - z) * f;
    this.py[i] = this.groundAt(this.px[i], this.pz[i]);
    c.isMoving = true;
    c.gait = 0;
    c.targetX = tx; c.targetZ = tz;
  }

  /** Swing doors, let the next person through, report openings and shuttings. */
  private updateDoors(dt: number): void {
    const list = this.activeDoors;
    for (let k = list.length - 1; k >= 0; k--) {
      const d = list[k];
      const want = d.users > 0 || d.queue.length > 0 || d.exitQ.length > 0 || !!d.pinned;
      if (want) {
        if (d.open === 0) { this.stat.doorOpenings++; this.onDoor?.(d, true); }
        d.open = Math.min(1, d.open + dt / DOOR_OPEN);
        d.hold = DOOR_HOLD;
      } else if (d.hold > 0) {
        d.hold -= dt;
      } else {
        d.open -= dt / DOOR_CLOSE;
        if (d.open <= 0) {
          d.open = 0;
          d.active = false;
          list[k] = list[list.length - 1];
          list.pop();
          this.onDoor?.(d, false);
        }
        continue;
      }
      // One person a step: out first, then the head of the queue.
      if (d.exitQ.length && this.gateFree(d, -1)) {
        const i = d.exitQ.shift()!;
        this.agents[i].qDoor = null;
        this.leave(i);
      } else if (d.queue.length && this.gateFree(d, 1) && d.exitQ.length === 0) {
        const i = d.queue[0];
        const ag = this.agents[i];
        const [qx, qz] = this.queuePoint(d, 0);
        // Not at the front yet (still shuffling up): next step.
        if (Math.hypot(this.px[i] - qx, this.pz[i] - qz) > 0.3) continue;
        d.queue.shift();
        ag.qDoor = null;
        ag.c.faceYaw = undefined;
        this.enter(i, d, true);
      }
    }
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
        ag.noClip = true; // no grid route: the straight line may cross walls
      }
    }
    ag.pts = pts;
    ag.wp = 1;
    ag.stuck = 0;
    // Gait by urgency: slow patrol, brisk apprentices; late (or simply in a hurry): run.
    const c = ag.c;
    ag.gaitPace = c.state === 'PATROLLING' ? PATROL : c.guildRank === 'apprentice' ? BRISK : 1;
    let len = 0;
    for (let k = 2; k < pts.length; k += 2) len += Math.hypot(pts[k] - pts[k - 2], pts[k + 1] - pts[k - 1]);
    // Due somewhere by a time (work, curfew): late means hurry.
    const due = ag.act?.due ?? Infinity;
    const realLeft = isFinite(due) ? Math.max(0, due - this.clock) / this.hoursPerSec : 1e9;
    const need = len / Math.max(realLeft, 1);
    const errand = c.guildRank === 'apprentice' ? 0.15 : 0.05;
    ag.running = len > 15 && (need > this.walkSpeed * ag.pace * ag.gaitPace * 1.15 || ag.rng() < errand);
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
    const t0 = performance.now();
    this.buildNeighbours();
    const walk = this.walkSpeed;
    let gliding = 0;
    for (let i = 0; i < n; i++) {
      const ag = this.agents[i];
      const c = ag.c;
      switch (ag.phase) {
        case Phase.WALK: {
          const speed = walk * ag.pace * ag.gaitPace * (ag.running ? RUN : 1);
          // Off view and walking alone: glide along the route (M8). Followers keep their
          // leader's side through walkStep, without avoidance (steer checks the view).
          if (ag.lead < 0 && this.offView(i)) { this.glide(i, ag, dt, speed); gliding++; }
          else this.walkStep(i, ag, dt, speed);
          break;
        }
        case Phase.SCRIPT:
          this.scriptStep(i, ag, walk * ag.pace * DOOR_PACE * dt);
          this.vx[i] = (this.px[i] - this.ox[i]) / dt;
          this.vz[i] = (this.pz[i] - this.oz[i]) / dt;
          break;
        case Phase.IDLE:
          if (ag.dest && ag.dest.wander > 0 && this.clock >= ag.nextWander) this.wander(i, ag);
          break;
        case Phase.QUEUE:
          this.queueStep(i, ag, walk * ag.pace * STROLL * 0.6 * dt);
          break;
        case Phase.INSIDE:
          if (ag.inPts) this.insideStep(i, ag, walk * ag.pace * INDOOR * dt);
          break;
        case Phase.SERVE:
          this.serviceStep(i, ag, walk * ag.pace * STROLL * 0.6 * dt);
          break;
        case Phase.TALK:
          ag.talkT -= dt;
          if (ag.talkT <= 0) this.endTalk(i, ag);
          break;
        default:
          break;
      }
      if (c.isMoving) {
        c.vx = (this.px[i] - this.ox[i]) / dt;
        c.vz = (this.pz[i] - this.oz[i]) / dt;
        c.animFrame = ((c.animFrame ?? 0) + dt * 8.0) % 8;
      } else {
        this.vx[i] = 0; this.vz[i] = 0;
        if (ag.phase === Phase.QUEUE || ag.phase === Phase.SERVE) { c.vx = 0; c.vz = 0; }
      }
    }
    this.realT += dt;
    this.updateDoors(dt);
    this.updateServices();
    this.stat.stepMs = performance.now() - t0;
    this.stat.gliding = gliding;
  }

  /**
   * The ground rectangle the camera sees (axis-aligned, world x/z). Walkers outside it plus
   * VIEW_MARGIN glide along their routes instead of steering around people and walls.
   */
  public setView(x0: number, z0: number, x1: number, z1: number): void {
    this.vx0 = x0 - VIEW_MARGIN; this.vz0 = z0 - VIEW_MARGIN;
    this.vx1 = x1 + VIEW_MARGIN; this.vz1 = z1 + VIEW_MARGIN;
  }

  private offView(i: number): boolean {
    const x = this.px[i], z = this.pz[i];
    return x < this.vx0 || x > this.vx1 || z < this.vz0 || z > this.vz1;
  }

  /**
   * Off-view walking (M8): position is a function of route distance only - no avoidance, no
   * wall sliding, no stuck handling. Velocity points along the route, so a walker that comes
   * into view carries on under full steering without a jolt.
   */
  private glide(i: number, ag: Agent, dt: number, speed: number): void {
    const pts = ag.pts!;
    if (ag.followers > 0) speed *= 0.9;
    let x = this.px[i], z = this.pz[i], left = speed * dt, hx = 0, hz = 0;
    while (ag.wp * 2 < pts.length) {
      const tx = pts[ag.wp * 2], tz = pts[ag.wp * 2 + 1];
      const d = Math.hypot(tx - x, tz - z);
      if (d <= left) { x = tx; z = tz; left -= d; ag.wp++; continue; }
      hx = (tx - x) / d; hz = (tz - z) / d;
      x += hx * left; z += hz * left;
      break;
    }
    this.px[i] = x; this.pz[i] = z;
    this.py[i] = this.groundAt(x, z);
    ag.stuck = 0;
    if (ag.wp * 2 >= pts.length) { this.arrive(i, ag); return; }
    this.vx[i] = hx * speed; this.vz[i] = hz * speed;
    ag.c.targetX = pts[ag.wp * 2]; ag.c.targetZ = pts[ag.wp * 2 + 1];
  }

  /** Bucket everyone outdoors into NB-metre cells (linked lists in typed arrays). */
  private buildNeighbours(): void {
    const head = this.nbHead, next = this.nbNext;
    for (const k of this.nbUsed) head[k] = -1;
    this.nbUsed.length = 0;
    const x0 = this.nav.minX, z0 = this.nav.minZ;
    for (let i = 0; i < this.agents.length; i++) {
      if (this.agents[i].phase === Phase.INSIDE) continue;
      const gx = Math.floor((this.px[i] - x0) / NB), gz = Math.floor((this.pz[i] - z0) / NB);
      if (gx < 0 || gz < 0 || gx >= this.nbW || gz >= this.nbH) continue;
      const k = gz * this.nbW + gx;
      if (head[k] < 0) this.nbUsed.push(k);
      next[i] = head[k];
      head[k] = i;
    }
  }

  /**
   * Avoidance acceleration for walker i into this.force: time-to-collision power law against
   * everyone within 4 m, keep-right in head-on meetings, overlap push, wall push.
   * Returns the nearest standing person ahead (index, -1 if none) for stuck handling.
   */
  private avoid(i: number, ag: Agent, people: boolean): number {
    const x = this.px[i], z = this.pz[i];
    const vxi = this.vx[i], vzi = this.vz[i];
    const spi = Math.hypot(vxi, vzi);
    let fx = 0, fz = 0;
    let blocker = -1, blockD = 1.44;
    if (people) {
      const gx = Math.floor((x - this.nav.minX) / NB), gz = Math.floor((z - this.nav.minZ) / NB);
      for (let cz = gz - 2; cz <= gz + 2; cz++) {
        if (cz < 0 || cz >= this.nbH) continue;
        for (let cx = gx - 2; cx <= gx + 2; cx++) {
          if (cx < 0 || cx >= this.nbW) continue;
          for (let j = this.nbHead[cz * this.nbW + cx]; j >= 0; j = this.nbNext[j]) {
            if (j === i || j === ag.lead || this.agents[j].lead === i) continue;
            const wx = x - this.px[j], wz = z - this.pz[j];
            const d2 = wx * wx + wz * wz;
            if (d2 > NB_R2) continue;
            const vxj = this.vx[j], vzj = this.vz[j];
            // A standing person close ahead: candidate to step aside.
            if (vxj === 0 && vzj === 0 && d2 < blockD && wx * vxi + wz * vzi < 0) { blocker = j; blockD = d2; }
            const c = d2 - RADIUS2 * RADIUS2;
            if (c < 0) {
              const d = Math.sqrt(d2) || 0.01;
              const push = ((RADIUS2 - d) / RADIUS2) * 12;
              fx += (wx / d) * push; fz += (wz / d) * push;
              continue;
            }
            const rvx = vxi - vxj, rvz = vzi - vzj;
            const a = rvx * rvx + rvz * rvz;
            const b = wx * rvx + wz * rvz;
            if (b >= 0 || a < 1e-6) continue; // moving apart
            const disc = b * b - a * c;
            if (disc <= 0) continue; // passes clear
            const tau = Math.max(0.05, (-b - Math.sqrt(disc)) / a);
            if (tau > TTC_MAX) continue;
            const e = Math.exp(-tau / TTC_T0);
            const mag = Math.min(F_MAX, (TTC_K * e * (2 / tau + 1 / TTC_T0)) / tau);
            // Separation at the moment of contact (length RADIUS2), pointing away from j.
            fx += ((wx + rvx * tau) / RADIUS2) * mag;
            fz += ((wz + rvz * tau) / RADIUS2) * mag;
            const spj = Math.hypot(vxj, vzj);
            if (spi > 0.1 && vxi * vxj + vzi * vzj < -0.3 * spi * spj) {
              // Head-on: both lean to their own right, so opposing streams form lanes.
              fx += (-vzi / spi) * KEEP_RIGHT * e;
              fz += (vxi / spi) * KEEP_RIGHT * e;
            }
          }
        }
      }
    }
    // Walls within 1 m: push down the distance field's slope.
    const cl = this.nav.clearance(x, z);
    if (cl > 0 && cl < 1) {
      const gx = this.nav.clearance(x + 0.5, z) - this.nav.clearance(x - 0.5, z);
      const gz = this.nav.clearance(x, z + 0.5) - this.nav.clearance(x, z - 0.5);
      const gl = Math.hypot(gx, gz);
      if (gl > 0) { fx += (gx / gl) * WALL_K * (1 - cl); fz += (gz / gl) * WALL_K * (1 - cl); }
    }
    const fl = Math.hypot(fx, fz);
    if (fl > F_MAX) { fx *= F_MAX / fl; fz *= F_MAX / fl; }
    this.force.x = fx; this.force.z = fz;
    return blocker;
  }

  private walkStep(i: number, ag: Agent, dt: number, speed: number): void {
    const pts = ag.pts!;
    let x = this.px[i], z = this.pz[i];
    // Walking at a household member's side: steer to a point beside it instead of the route.
    if (ag.lead >= 0) {
      const L = this.agents[ag.lead];
      const lx = this.px[ag.lead], lz = this.pz[ag.lead];
      const far = Math.hypot(lx - x, lz - z) > 12;
      if (L.phase === Phase.WALK && !far) {
        ag.paired = true;
        this.pairStep(i, ag, dt, lx, lz, speed);
        return;
      }
      // Before setting off the leader may still be leaving its door or waiting for a path:
      // walk our own route meanwhile. Once together, any other case (arrived, lost them,
      // re-planning) means finishing alone: our own route is stale by then.
      const coming = L.phase === Phase.ROUTE || L.phase === Phase.SCRIPT || (L.phase === Phase.INSIDE && L.inExit);
      if (far || ag.paired || !coming) {
        this.dropPair(i);
        this.requestRoute(i);
        return;
      }
    }
    if (ag.followers > 0) speed *= 0.9; // wait for company
    // Next waypoint: corners are taken within 0.4 m; the last one exactly.
    let tx = x, tz = z, last = true, dl = 0;
    while (ag.wp * 2 < pts.length) {
      tx = pts[ag.wp * 2]; tz = pts[ag.wp * 2 + 1];
      last = ag.wp * 2 + 2 >= pts.length;
      dl = Math.hypot(tx - x, tz - z);
      if (dl <= (last ? speed * dt : 0.4)) {
        ag.wp++;
        if (last) { x = tx; z = tz; }
        continue;
      }
      break;
    }
    if (ag.wp * 2 >= pts.length) {
      this.px[i] = x; this.pz[i] = z;
      this.arrive(i, ag);
      return;
    }
    // Ease in to the final point; avoidance off for the last metre so it lands exactly.
    const want = last && dl < 1.5 ? Math.max(speed * 0.45, speed * (dl / 1.5)) : speed;
    const near = last && dl < 1;
    this.steer(i, ag, dt, (tx - x) / dl * want, (tz - z) / dl * want, want, !near);
    ag.c.targetX = tx; ag.c.targetZ = tz;
  }

  /** Keep step beside the leader: aim 0.75 m to its right (behind it where that is a wall). */
  private pairStep(i: number, ag: Agent, dt: number, lx: number, lz: number, speed: number): void {
    const lvx = this.vx[ag.lead], lvz = this.vz[ag.lead];
    const ls = Math.hypot(lvx, lvz);
    let tx = lx, tz = lz;
    if (ls > 0.1) {
      const hx = lvx / ls, hz = lvz / ls;
      tx = lx - hz * 0.75; tz = lz + hx * 0.75;
      if (!this.nav.isFree(tx, tz) || this.nav.clearance(tx, tz) < 0.5) { tx = lx - hx * 0.9; tz = lz - hz * 0.9; }
    }
    const x = this.px[i], z = this.pz[i];
    const dx = tx - x, dz = tz - z, d = Math.hypot(dx, dz);
    // Match the leader's velocity, plus a catch-up term toward the slot.
    const catchUp = Math.min(speed * 0.5, d * 2);
    let dvx = lvx + (d > 0.01 ? (dx / d) * catchUp : 0), dvz = lvz + (d > 0.01 ? (dz / d) * catchUp : 0);
    const dvs = Math.hypot(dvx, dvz), cap = speed * 1.35;
    if (dvs > cap) { dvx *= cap / dvs; dvz *= cap / dvs; }
    ag.running = this.agents[ag.lead].running;
    ag.c.gait = ag.running ? 1 : 0;
    this.steer(i, ag, dt, dvx, dvz, Math.max(dvs, 0.3), true);
    ag.c.targetX = tx; ag.c.targetZ = tz;
  }

  /** Relax velocity toward (dvx, dvz) under avoidance, move, slide along walls, track progress. */
  private steer(i: number, ag: Agent, dt: number, dvx: number, dvz: number, want: number, people: boolean): void {
    const x = this.px[i], z = this.pz[i];
    if (ag.ghost > 0) { ag.ghost -= dt; people = false; }
    if (people && this.offView(i)) people = false;
    const blocker = this.avoid(i, ag, people);
    let vx = this.vx[i] + ((dvx - this.vx[i]) / RELAX + this.force.x) * dt;
    let vz = this.vz[i] + ((dvz - this.vz[i]) / RELAX + this.force.z) * dt;
    const vs = Math.hypot(vx, vz), cap = Math.max(want, 0.3) * 1.3;
    if (vs > cap) { vx *= cap / vs; vz *= cap / vs; }
    let nx = x + vx * dt, nz = z + vz * dt;
    // The grid is a hard constraint, except where we stand on a blocked cell already (a door
    // facing a walled gap) or this leg has no grid route.
    if (!ag.noClip && this.nav.isFree(x, z) && !this.nav.isFree(nx, nz)) {
      if (this.nav.isFree(nx, z)) { nz = z; vz = 0; }
      else if (this.nav.isFree(x, nz)) { nx = x; vx = 0; }
      else { nx = x; nz = z; vx = 0; vz = 0; }
    }
    this.vx[i] = vx; this.vz[i] = vz;
    this.px[i] = nx; this.pz[i] = nz;
    const gy = this.groundAt(nx, nz);
    this.py[i] += (gy - this.py[i]) * 0.25;
    // Progress: under a third of the wanted speed counts as stuck.
    const moved = Math.hypot(nx - x, nz - z);
    if (moved < want * dt * 0.33) ag.stuck += dt;
    else ag.stuck = Math.max(0, ag.stuck - dt * 2);
    if (ag.stuck > STUCK_ASIDE && ag.ghost <= 0 && ag.stuck - dt <= STUCK_ASIDE) {
      ag.ghost = GHOST;
      if (blocker >= 0 && this.agents[blocker].phase === Phase.IDLE) this.stepAside(blocker, vx, vz);
    }
    if (ag.stuck > STUCK_REPLAN && ag.lead < 0) {
      ag.stuck = 0;
      ag.replans++;
      this.stat.replans++;
      if (ag.replans >= 2) ag.noClip = true;
      this.requestRoute(i);
    }
  }

  /** A standing person shuffles 0.8 m sideways out of a walker's way. */
  private stepAside(j: number, wvx: number, wvz: number): void {
    const ag = this.agents[j];
    const s = Math.hypot(wvx, wvz) || 1;
    const x = this.px[j], z = this.pz[j];
    for (const side of [1, -1]) {
      const tx = x - (wvz / s) * 0.8 * side, tz = z + (wvx / s) * 0.8 * side;
      if (!this.nav.isFree(tx, tz)) continue;
      ag.pts = new Float32Array([x, z, tx, tz]);
      ag.wp = 1;
      ag.running = false;
      ag.gaitPace = STROLL;
      this.setPhase(ag, Phase.WALK);
      ag.dest = { ...ag.dest!, x: tx, z: tz };
      this.stat.asides++;
      return;
    }
  }

  private arrive(i: number, ag: Agent): void {
    this.vx[i] = 0; this.vz[i] = 0;
    ag.pts = null;
    const d = ag.dest!;
    if (d.svc) this.joinService(i, d.svc);
    else if (d.door && d.b) this.enter(i, d.door);
    else if (d.spot) {
      this.py[i] = d.spot.y;
      this.arriveSpot(ag, d.spot);
      this.reached(i);
    } else {
      this.setPhase(ag, Phase.IDLE);
      ag.c.activityAnim = 'idle';
      ag.nextWander = this.clock + 0.1 + ag.rng() * 0.5;
      this.reached(i);
    }
  }

  /** At the current activity's place: its arrival effects, once. */
  private reached(i: number): void {
    const ag = this.agents[i];
    if (ag.there || !ag.act) return;
    ag.there = true;
    this.life.arrived(i, ag.act, ag.c);
  }

  // ---------------------------------------------------------------- services (M7)

  private joinService(i: number, s: Service): void {
    const ag = this.agents[i];
    s.line.push(i);
    ag.svc = s;
    this.setPhase(ag, Phase.SERVE);
  }

  private leaveService(i: number): void {
    const ag = this.agents[i];
    const s = ag.svc;
    if (!s) return;
    if (s.user === i) s.user = -1;
    const k = s.line.indexOf(i);
    if (k >= 0) s.line.splice(k, 1);
    ag.svc = null;
  }

  /** Where the k-th person in a service line stands (0 = next to be served). */
  private servicePoint(s: Service, k: number): [number, number] {
    const side = (k & 1 ? 1 : -1) * 0.12;
    const x = s.x + s.nx * SVC_STEP * (k + 1) - s.nz * side, z = s.z + s.nz * SVC_STEP * (k + 1) + s.nx * side;
    if (this.nav.isFree(x, z)) return [x, z];
    // Out of room straight back: bend the line along the front.
    const t = k & 1 ? 1 : -1, a = Math.ceil((k + 1) / 2) * SVC_STEP;
    return [s.x + s.nx * SVC_STEP - s.nz * a * t, s.z + s.nz * SVC_STEP + s.nx * a * t];
  }

  /** Shuffle up in the line, or step up to the window / well and be served. */
  private serviceStep(i: number, ag: Agent, dist: number): void {
    const s = ag.svc;
    const c = ag.c;
    if (!s) { this.requestRoute(i); return; }
    let tx: number, tz: number;
    if (s.user === i) { tx = s.x; tz = s.z; }
    else {
      const k = s.line.indexOf(i);
      if (k < 0) { this.requestRoute(i); return; }
      [tx, tz] = this.servicePoint(s, k);
    }
    const x = this.px[i], z = this.pz[i];
    const l = Math.hypot(tx - x, tz - z);
    if (l < 0.03) {
      c.isMoving = false;
      c.faceYaw = s.user === i ? Math.atan2(s.fx, s.fz) : Math.atan2(s.x - x, s.z - z);
      if (s.user === i && !ag.there) {
        ag.there = true;
        c.activityAnim = s.kind === 'water' ? 'draw_water' : 'pay';
        s.doneT = this.realT + ((s.kind === 'water' ? SERVE_MIN * 0.8 : SERVE_MIN) / 60) / this.hoursPerSec;
      }
      return;
    }
    const f = Math.min(1, dist / l);
    this.px[i] = x + (tx - x) * f;
    this.pz[i] = z + (tz - z) * f;
    this.py[i] = this.groundAt(this.px[i], this.pz[i]);
    c.isMoving = true;
    c.gait = 0;
    c.targetX = tx; c.targetZ = tz;
  }

  /** Next customer up; the one served pays, takes the bread or water, and goes. */
  private updateServices(): void {
    for (const s of this.life.services) {
      if (s.user >= 0) {
        const ag = this.agents[s.user];
        if (!ag.there || this.realT < s.doneT) continue;
        const i = s.user;
        s.user = -1;
        ag.svc = null;
        ag.c.activityAnim = undefined;
        ag.c.faceYaw = undefined;
        this.life.served(i, s, ag.c);
        this.stat.served++;
        this.setPhase(ag, Phase.IDLE);
        ag.dest = { b: null, door: null, spot: null, x: this.px[i], z: this.pz[i], wander: 0, cx: this.px[i], cz: this.pz[i] };
        ag.nextThink = 0;
        this.evaluate(i);
      }
      if (s.user < 0 && s.line.length) {
        const i = s.line[0];
        const [qx, qz] = this.servicePoint(s, 0);
        if (Math.hypot(this.px[i] - qx, this.pz[i] - qz) > 0.4 && this.agents[i].phase === Phase.SERVE) continue;
        s.line.shift();
        s.user = i;
        this.agents[i].there = false;
      }
    }
  }

  // ---------------------------------------------------------------- chats (M7)

  /** Same household, workshop or trade, or living near each other. */
  private acquainted(i: number, j: number): boolean {
    const a = this.citizens[i], b = this.citizens[j];
    if (a.homeParcelId === b.homeParcelId || a.workParcelId === b.workParcelId || a.trade === b.trade) return true;
    const pa = this.parcelMap.get(a.homeParcelId), pb = this.parcelMap.get(b.homeParcelId);
    return !!pa && !!pb && Math.hypot(pa.x - pb.x, pa.z - pb.z) < 45;
  }

  /** Free to stop for a chat: not late, not walking with someone, not on a fixed errand. */
  private chatty(ag: Agent, i: number): boolean {
    if (ag.running || ag.lead >= 0 || ag.followers > 0 || ag.svc || this.clock < ag.nextTalk) return false;
    if (ag.phase !== Phase.IDLE && ag.phase !== Phase.WALK) return false;
    const a = ag.act;
    if (!a || (isFinite(a.due) && a.due - this.clock < 0.4) || a.kind === 'drop') return false;
    if (this.life.minds[i].social <= 0.3) return false;
    // Not in a narrow lane or a doorway, where two standing people block the way.
    return this.nav.clearance(this.px[i], this.pz[i]) >= 1.4;
  }

  private maybeTalk(i: number, ag: Agent): void {
    if (!this.chatty(ag, i)) return;
    ag.nextTalk = this.clock + 0.05;
    if (ag.rng() > 0.4) return;
    const x = this.px[i], z = this.pz[i];
    const gx = Math.floor((x - this.nav.minX) / NB), gz = Math.floor((z - this.nav.minZ) / NB);
    for (let cz = gz - 1; cz <= gz + 1; cz++) {
      if (cz < 0 || cz >= this.nbH) continue;
      for (let cx = gx - 1; cx <= gx + 1; cx++) {
        if (cx < 0 || cx >= this.nbW) continue;
        for (let j = this.nbHead[cz * this.nbW + cx]; j >= 0; j = this.nbNext[j]) {
          if (j === i) continue;
          const dx = this.px[j] - x, dz = this.pz[j] - z;
          if (dx * dx + dz * dz > TALK_R * TALK_R) continue;
          const J = this.agents[j];
          if (!this.chatty(J, j) || !this.acquainted(i, j)) continue;
          this.startTalk(i, j);
          return;
        }
      }
    }
  }

  private startTalk(i: number, j: number): void {
    const t = TALK_MIN + this.agents[i].rng() * (TALK_MAX - TALK_MIN);
    for (const [a, b] of [[i, j], [j, i]]) {
      const ag = this.agents[a];
      ag.talkFrom = ag.phase;
      ag.talkT = t;
      ag.talkWith = b;
      ag.nextTalk = this.clock + TALK_GAP;
      this.dropPair(a);
      this.setPhase(ag, Phase.TALK);
      this.vx[a] = 0; this.vz[a] = 0;
      ag.c.faceYaw = Math.atan2(this.px[b] - this.px[a], this.pz[b] - this.pz[a]);
      ag.c.activityAnim = 'gossip';
      this.life.talked(a);
    }
    this.stat.talks++;
    this.onTalk?.(this.citizens[i], this.citizens[j]);
  }

  private endTalk(i: number, ag: Agent): void {
    ag.talkWith = -1;
    ag.c.activityAnim = undefined;
    ag.c.faceYaw = undefined;
    if (ag.talkFrom === Phase.IDLE) {
      this.setPhase(ag, Phase.IDLE);
      ag.nextWander = this.clock + 0.05 + ag.rng() * 0.3;
    } else this.requestRoute(i);
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
    const climbing = Math.abs(y - this.py[i]) > 1e-4;
    this.px[i] = x; this.py[i] = y; this.pz[i] = z;
    if (ag.sp * 3 < s.length) {
      ag.c.targetX = s[ag.sp * 3]; ag.c.targetZ = s[ag.sp * 3 + 2];
      // Short steps on a stair, one per tread.
      ag.c.strideScale = Math.sqrt(this.walkSpeed / WALK) * (climbing ? STAIR_STRIDE : 1);
      return;
    }
    ag.c.strideScale = Math.sqrt(this.walkSpeed / WALK);
    this.releaseDoor(i);
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
    ag.gaitPace = STROLL;
    ag.stuck = 0;
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
    const names = PHASE_NAMES;
    let queueing = 0, waitingInside = 0;
    for (const d of this.activeDoors) { queueing += d.queue.length; waitingInside += d.exitQ.length; }
    const phases: Record<string, number> = {};
    let running = 0, stuckNow = 0, pairs = 0;
    for (const ag of this.agents) {
      phases[names[ag.phase]] = (phases[names[ag.phase]] ?? 0) + 1;
      if (ag.phase !== Phase.WALK) continue;
      if (ag.running) running++;
      if (ag.stuck > STUCK_ASIDE) stuckNow++;
      if (ag.lead >= 0 && ag.paired) pairs++;
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
      stuckNow, pairs, replans: s.replans, asides: s.asides, stepMs: Math.round(s.stepMs * 100) / 100,
      gliding: s.gliding,
      doorsOpen: this.activeDoors.length, queueing, waitingInside, doorOpenings: s.doorOpenings,
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

  /** Life (M7): what people are doing, households' stores, lines, chats, errands. */
  public lifeStats() {
    const acts: Record<string, number> = {};
    for (const ag of this.agents) if (ag.act) acts[ag.act.kind] = (acts[ag.act.kind] ?? 0) + 1;
    const hh = this.life.households;
    const avg = (f: (h: (typeof hh)[number]) => number) => Math.round((hh.reduce((s, h) => s + f(h), 0) / hh.length) * 100) / 100;
    const ms = this.life.minds;
    const need = (k: 'hunger' | 'thirst' | 'fatigue' | 'social' | 'piety') =>
      Math.round((ms.reduce((s, m) => s + m[k], 0) / ms.length) * 100) / 100;
    return {
      hour: Math.round(this.simTimeHours * 100) / 100, acts,
      needs: { hunger: need('hunger'), thirst: need('thirst'), fatigue: need('fatigue'), social: need('social'), piety: need('piety') },
      bread: avg((h) => h.bread), water: avg((h) => h.water), noBread: hh.filter((h) => h.bread <= 0).length,
      noWater: hh.filter((h) => h.water <= 0).length,
      lines: this.life.services.map((s) => s.line.length + (s.user >= 0 ? 1 : 0)),
      talking: this.agents.filter((a) => a.phase === Phase.TALK).length,
      talks: this.stat.talks, served: this.stat.served, errands: this.stat.errands,
      purse: Math.round(this.citizens.reduce((s, c) => s + c.walletGroschen, 0) / this.citizens.length),
    };
  }

  /** Buildings whose hearth burns: someone awake inside, or a smith / baker working at it. */
  public hearths(out: Set<Building>): Set<Building> {
    out.clear();
    const h = this.simTimeHours;
    for (const ag of this.agents) {
      const b = ag.phase === Phase.INSIDE ? ag.inB : ag.phase === Phase.SPOT && ag.act?.kind === 'work' ? ag.dest?.b : null;
      if (!b || !b.chimneys.length || ag.c.pose === 'lie') continue;
      // At home the fire is banked overnight; workshops burn while worked.
      if (ag.act?.kind === 'work' || (h > 4.5 && h < 22.5)) out.add(b);
    }
    return out;
  }

  /** Needs (0 fine .. 1 urgent) and the last activities of one citizen (inspector). */
  public mindOf(c: Citizen) {
    const i = this.citizens.indexOf(c);
    return i >= 0 ? this.life.minds[i] : null;
  }

  public tollCivicBellManually(): void {
    if (this.onBellToll) this.onBellToll(this.currentBellInfo.name, Math.floor(this.simTimeHours));
  }
}
