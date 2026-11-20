import type { Citizen } from '../types';
import type { Building, BuildingIndex, Door, Slot, Spot, Stall, Tie } from './building-anchors';
import type { Horse, Horses } from './horses';
import type { SimulationEngine } from './simulation';
import type { Wagon } from './wagon';

/**
 * The stable's crew at work (stable plan M5). The citizens are moved to the stable by
 * generate_city_plan.py (STABLE_CREWS: stablemaster, 4 grooms, postilion, farrier, saddler, hay
 * boy) and drawn with char_groom (char_blacksmith for the farrier, char_tanner for the saddler;
 * kit.trades picks each one's look and loop). Their hours: life.ts stableShift (grooms in a
 * dawn and a late shift, the hay boy all day, the postilion round the wagon runs).
 *
 * Who works where (Simulation.workFits): in the stable's buildings a spot naming a loop
 * (anchor_spot tag in build_assets.py) is taken only by the trades in LOOP_TRADES, and a
 * work slot indoors only by those in PROP_TRADES for its furniture. A stall's slot (brush) is
 * open only while its horse stands in the stall; the farrier's shoe spot only while a horse is
 * tied at his post (and then it is the only place he works). Everyone else is unaffected.
 *
 * Leading (Horses.managed): the horses change place only on a groom's lead. A groom on shift
 * is called (Simulation.summon, state LEADING) to fetch one or two horses: at the stable door
 * (they come out of their stalls), inside the paddock gate (they come when called) or where
 * they stand tied; then to where they go, the horses following his hand on a LEAD m rope
 * (side by side with two). Jobs, by priority: the next wagon run's pair to the pole half an
 * hour before it leaves (TEAM_AHEAD); a pair back from a run to the paddock or the stalls;
 * from SHOE_HOURS one palfrey at a time to the farrier's post for SHOE_MIN minutes and back;
 * the stalled horses out to the paddock from OUT_FROM; the paddock's back in from IN_FROM.
 * Whatever is left when the grooms go home stays where it is till morning.
 * A clock jump puts every horse in its place for the hour (horses.ts) and drops every job.
 *
 * Debug: __lublin.stable.stats() (jobs, per-horse holder and place).
 */

/** Loop -> lower-case trades that may take a spot naming it (stable buildings only). */
const LOOP_TRADES: Record<string, string[]> = {
  muck: ['groom', 'hay boy'],
  forkhay: ['groom', 'hay boy'],
  harness: ['groom', 'postilion'],
  brush: ['groom', 'stablemaster'],
  shoe: ['farrier'],
  watch: ['stablemaster', 'postilion', 'groom'],
};
/** Furniture -> trades that may take its work slot (stable buildings only). */
const PROP_TRADES: Record<string, string[]> = {
  stall: ['groom', 'stablemaster', 'hay boy'],
  workbench: ['saddler', 'stablemaster'],
};

/** Who leads horses (on shift: Citizen.state WORKING). */
const LEADERS = ['Groom', 'Hay Boy'];
const LEAD = 1.6;              // m of rope from the hand to the horse's head
const HEAD = 1.1;              // from the horse's head back to its middle (its place)
const SIDE = 0.85;             // two horses: either side of the line behind him
const OUT_FROM = 5.7, OUT_TO = 18.8;
const IN_FROM = 19.3;
const TEAM_AHEAD = 0.6;        // h before a run its pair is led to the pole
const SHOE_HOURS: [number, number] = [9.5, 15.5];
const SHOE_MIN = 45;           // sim minutes at the farrier's post
const SHOE_EVERY = 2.5;        // h between horses shod
const TRAVEL = 2.2;            // the citizens' shown speed-up (simulation TRAVEL_SCALE)
const GIVE_UP = 240;           // real s: a job not done by then is dropped (a groom stuck)

type JobKind = 'out' | 'in' | 'team' | 'home' | 'shoe' | 'unshoe';
interface Place { x: number; z: number; yaw?: number }
interface Job {
  kind: JobKind;
  horses: Horse[];
  groom: number;
  stage: 'fetch' | 'gather' | 'lead' | 'settle';
  pick: Place;
  to: Place;
  /** Real seconds in this stage / in the job. */
  t: number; age: number;
  /** Fetch from the stable: the door they come out of. */
  door: Door | null;
  /** Settle: where each horse ends up (tied). */
  ends: Place[];
}

const hyp = Math.hypot;
const wrapPi = (a: number) => { while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return a; };
const inWin = (h: number, a: number, b: number) => (a <= b ? h >= a && h < b : h >= a || h < b);

export class StableCrew {
  private sim: SimulationEngine;
  private horses: Horses;
  private wagon: Wagon;
  private site = new Set<Building>();
  /** A stall's work slot -> the horse stall it faces. */
  private slotStall = new Map<Slot, Stall>();
  private shoeSpots = new Set<Spot>();
  private forge: Building | null = null;
  private tie: Tie | null = null;
  private stableDoors: Door[] = [];
  private jobs: Job[] = [];
  /** Horses tied at the pole for the coming run / at the farrier's post (and since when, sim clock h). */
  private atPole = new Set<Horse>();
  private shod: { h: Horse; since: number } | null = null;
  private lastShoe = -1e9;
  private jumps = -1;
  private thinkT = 0;
  private gx: number[] = [];
  private gz: number[] = [];
  private stat = { led: 0, dropped: 0, shod: 0 };
  enabled = true;

  constructor(sim: SimulationEngine, buildings: BuildingIndex, horses: Horses, wagon: Wagon) {
    this.sim = sim;
    this.horses = horses;
    this.wagon = wagon;
    for (const b of buildings.all) if (b.parcelId?.startsWith('p_stable_')) this.site.add(b);
    const stalls = [...this.site].flatMap((b) => b.stalls.filter((s) => s.tag === 'horse'));
    for (const b of this.site) {
      for (const s of b.interior?.slots ?? []) {
        if (s.prop !== 'stall') continue;
        let best: Stall | null = null, bd = 3.5;
        for (const st of stalls) {
          const d = hyp(st.x - s.x, st.z - s.z);
          if (d < bd) { bd = d; best = st; }
        }
        if (best) this.slotStall.set(s, best);
      }
      for (const s of b.spots) if (s.anim === 'shoe') this.shoeSpots.add(s);
      if (b.name === 'farrier_forge') { this.forge = b; this.tie = b.ties[0] ?? null; }
      if (b.name === 'stable_long') this.stableDoors.push(...b.doors);
    }
    if (!this.site.size) return;
    sim.workFits = (c, b, s) => this.fits(c, b, s);
    horses.managed = !!this.stableDoors.length && !!horses.gate(0);
  }

  // ---------------------------------------------------------------- who works where

  private fits(c: Citizen, b: Building, s: Spot | Slot): boolean {
    if (!this.site.has(b)) return true;
    const trade = (c.trade || '').toLowerCase();
    if ('kind' in s) {
      const who = s.prop ? PROP_TRADES[s.prop] : undefined;
      if (who && !who.includes(trade)) return false;
      const st = this.slotStall.get(s);
      return !st || this.horseIn(st);
    }
    const who = s.anim ? LOOP_TRADES[s.anim] : undefined;
    if (who && !who.includes(trade)) return false;
    const tied = !!this.tie && this.tie.taken > 0;
    if (this.shoeSpots.has(s)) return tied;
    // a horse at the post: the farrier works on it, nowhere else
    if (tied && b === this.forge && trade === 'farrier') return false;
    return true;
  }

  private horseIn(st: Stall): boolean {
    return this.horses.horses.some((h) => h.stall === st && h.inStall && !h.held);
  }

  // ---------------------------------------------------------------- leading

  /** Per frame after the horses' update: hour = sim clock, dt = real seconds. */
  update(hour: number, dt: number): void {
    if (!this.horses.managed) return;
    if (this.jumps !== this.horses.jumps || !this.enabled) {
      // a clock jump: every horse is in its place for the hour; start over
      this.jumps = this.horses.jumps;
      this.dropAll();
      if (!this.enabled) return;
    }
    // the wagon took (or never took) its pair
    for (const h of this.atPole) if (h.holder !== 'tied') this.atPole.delete(h);
    if (this.atPole.size && !this.wagon.running && !this.wagon.nextRun(hour, TEAM_AHEAD + 0.1)) this.atPole.clear();
    if (this.shod && this.shod.h.holder !== 'tied') this.endShoe();

    for (let k = this.jobs.length - 1; k >= 0; k--) this.step(this.jobs[k], dt, hour);
    this.thinkT -= dt;
    if (this.thinkT <= 0) {
      this.thinkT = 0.5;
      this.plan(hour);
    }
  }

  /** Start the most pressing job a free groom can do. */
  private plan(hour: number): void {
    const busy = new Set<Horse>(this.jobs.flatMap((j) => j.horses));
    const free = (h: Horse) => !busy.has(h);
    const H = this.horses.horses;
    const byName = (n: string) => H.find((h) => h.name === n);
    const next = this.wagon.nextRun(hour, TEAM_AHEAD + 0.6);
    const team = next ? next.names.map(byName).filter((h): h is Horse => !!h) : [];
    const soon = !!next && (((next.dep - hour) % 24) + 24) % 24 < TEAM_AHEAD;

    // 1. the coming run's pair to the pole
    if (soon && team.length === 2 && team.every((h) => free(h) && !this.atPole.has(h) && h.holder !== 'wagon')) {
      const places = this.wagon.teamPlaces();
      if (places.length === 2 && this.start('team', team, hour, places)) return;
    }
    // 2. a pair back from a run (tied where the wagon stopped)
    const back = H.filter((h) => free(h) && h.holder === 'tied' && !this.atPole.has(h) && this.shod?.h !== h);
    if (back.length && this.start('home', back.slice(0, 2), hour)) return;
    // 3. the shod horse back to the paddock
    if (this.shod && free(this.shod.h) && this.sim.simClock - this.shod.since > SHOE_MIN / 60) {
      if (this.start('unshoe', [this.shod.h], hour)) return;
    }
    const keep = (h: Horse) => team.includes(h);   // the next pair: left for the pole job
    // 4. out to the paddock (two nearest stalls at a time)
    if (inWin(hour, OUT_FROM, OUT_TO)) {
      const out = H.filter((h) => free(h) && h.inStall && !h.held && !keep(h));
      if (out.length && this.start('out', this.pairNear(out, (h) => h.stall!), hour)) return;
    }
    // 5. a palfrey to the farrier now and then
    if (this.tie && !this.shod && inWin(hour, SHOE_HOURS[0], SHOE_HOURS[1]) && this.sim.simClock - this.lastShoe > SHOE_EVERY
        && !this.jobs.some((j) => j.kind === 'shoe')) {
      const cand = H.filter((h) => free(h) && h.kind === 'horse' && this.horses.loose(h));
      if (cand.length && this.start('shoe', [cand[Math.floor(Math.random() * cand.length)]], hour)) return;
    }
    // 6. back in for the night
    if (hour >= IN_FROM || hour < OUT_FROM - 1) {
      const inn = H.filter((h) => free(h) && this.horses.loose(h) && h.stall);
      const g = this.horses.gate(3.5)!;
      if (inn.length) this.start('in', this.pairNear(inn, () => g), hour);
    }
  }

  /** Up to two horses: the first of the list's nearest to `at`, and its nearest neighbour. */
  private pairNear(list: Horse[], at: (h: Horse) => { x: number; z: number }): Horse[] {
    const p = at(list[0]);
    list.sort((a, b) => hyp(at(a).x - p.x, at(a).z - p.z) - hyp(at(b).x - p.x, at(b).z - p.z));
    return list.slice(0, 2);
  }

  /** A free groom on shift, nearest to (x, z); -1 if none. */
  private groomFor(x: number, z: number): number {
    const taken = new Set(this.jobs.map((j) => j.groom));
    let best = -1, bd = Infinity;
    this.sim.citizens.forEach((c, i) => {
      if (!LEADERS.includes(c.trade) || taken.has(i) || c.state !== 'WORKING') return;
      const ph = this.sim.phaseOf(i);
      if (ph !== 'SPOT' && ph !== 'IDLE' && ph !== 'WALK' && ph !== 'INSIDE') return;
      const [cx, cz] = this.sim.posOf(i);
      const d = hyp(cx - x, cz - z);
      if (d < bd) { bd = d; best = i; }
    });
    return best;
  }

  private start(kind: JobKind, horses: Horse[], hour: number, ends: Place[] = []): boolean {
    const gateIn = this.horses.gate(3.5)!;
    const h0 = horses[0];
    // where he fetches them
    let pick: Place, door: Door | null = null;
    if (h0.inStall && h0.stall) {
      door = this.doorFor(h0.stall);
      pick = { x: door.ax, z: door.az };
    } else if (h0.held) {
      pick = this.beside(h0);
    } else pick = { x: gateIn.x, z: gateIn.z };
    // where they go
    let to: Place;
    const night = !inWin(hour, OUT_FROM, IN_FROM);
    if (kind === 'team') to = this.besideAll(ends);
    else if (kind === 'shoe' && this.tie) {
      ends = [{ x: this.tie.ax, z: this.tie.az, yaw: this.tie.yaw }];
      to = this.besideAll(ends);
    } else if (kind === 'in' || (kind === 'home' && night)) {
      const d = this.doorFor(h0.stall!);
      to = { x: d.ax, z: d.az };
    } else to = { x: gateIn.x, z: gateIn.z };

    const g = this.groomFor(pick.x, pick.z);
    if (g < 0) return false;
    if (!this.sim.summon(g, pick.x, pick.z, this.sim.simClock + 1, this.task(kind, horses), 'LEADING')) return false;
    const job: Job = { kind, horses, groom: g, stage: 'fetch', pick, to, t: 0, age: 0, door, ends };
    this.jobs.push(job);
    // the paddock's horses come to the gate when he calls
    if (!h0.inStall && !h0.held) horses.forEach((h, k) => this.horses.call(h, gateIn.x + (k - 0.5) * 2.2, gateIn.z));
    return true;
  }

  private task(kind: JobKind, horses: Horse[]): string {
    const names = horses.map((h) => h.name).join(' and ');
    switch (kind) {
      case 'out': return `Leading ${names} out to the paddock`;
      case 'in': return `Leading ${names} in for the night`;
      case 'team': return `Bringing ${names} to the wagon`;
      case 'home': return `Leading ${names} back from the wagon`;
      case 'shoe': return `Leading ${names} to the farrier`;
      default: return `Fetching ${names} from the farrier`;
    }
  }

  private doorFor(st: Stall): Door {
    let best = this.stableDoors[0], bd = Infinity;
    for (const d of this.stableDoors) {
      const v = hyp(d.x - st.x, d.z - st.z);
      if (v < bd) { bd = v; best = d; }
    }
    return best;
  }

  /** Where a groom stands to take (or leave) a horse: beside its head. */
  private beside(h: { x: number; z: number; yaw: number }): Place {
    const ux = Math.sin(h.yaw), uz = Math.cos(h.yaw);
    return { x: h.x + ux * 1.4 - uz * 0.9, z: h.z + uz * 1.4 + ux * 0.9 };
  }

  private besideAll(ends: Place[]): Place {
    const x = ends.reduce((s, e) => s + e.x, 0) / ends.length, z = ends.reduce((s, e) => s + e.z, 0) / ends.length;
    const yaw = ends[0].yaw ?? 0;
    return { x: x + Math.sin(yaw) * 2.2, z: z + Math.cos(yaw) * 2.2 };
  }

  private step(j: Job, dt: number, hour: number): void {
    j.t += dt; j.age += dt;
    const g = j.groom, sim = this.sim;
    // the wagon took a horse, the groom was taken away (carried), or it is taking too long
    if (j.horses.some((h) => h.holder === 'wagon') || sim.isCarried(g) || j.age > GIVE_UP) {
      this.drop(j, true);
      return;
    }
    const c = sim.citizens[g];
    const [sx, sz] = sim.posOf(g);
    const gx = c.currentX ?? sx, gz = c.currentZ ?? sz;
    const there = (p: Place, r = 2.5) => sim.waiting(g) && hyp(gx - p.x, gz - p.z) < r;
    switch (j.stage) {
      case 'fetch': {
        if (!there(j.pick, 3)) return;
        if (j.door) {                                    // in through the door for them
          j.stage = 'gather'; j.t = 0;
          return;
        }
        // loose ones: wait for them to come (or go up to them after a while)
        const near = j.horses.every((h) => h.held || hyp(h.x - gx, h.z - gz) < 4.5);
        if (!near && j.t < 25) return;
        this.takeAll(j);
        break;
      }
      case 'gather': {
        if (j.t < 4) return;
        // out of the stalls through the door, behind him
        const d = j.door!;
        j.horses.forEach((h, k) => {
          this.horses.take(h);
          this.horses.drive(h, d.ix - d.nz * (k - 0.5) * 0.9, d.iz + d.nx * (k - 0.5) * 0.9, Math.atan2(d.nx, d.nz), 0, TRAVEL);
        });
        this.lead(j);
        break;
      }
      case 'lead': {
        this.follow(j, gx, gz, dt);
        if (!there(j.to)) return;
        if (j.horses.some((h) => hyp(h.x - gx, h.z - gz) > LEAD + HEAD + SIDE + 1.2)) return;
        this.arrive(j, hour);
        break;
      }
      case 'settle': {
        // into their places, a few steps
        let done = true;
        j.horses.forEach((h, k) => {
          const e = j.ends[k];
          const dx = e.x - h.x, dz = e.z - h.z, d = hyp(dx, dz);
          if (d > 0.05) {
            done = false;
            const s = Math.min(d, 1.4 * TRAVEL * dt);
            const yaw = d > 0.4 ? Math.atan2(dx, dz) : (e.yaw ?? h.yaw);
            this.horses.drive(h, h.x + (dx / d) * s, h.z + (dz / d) * s, this.turn(h.yaw, yaw, dt), s / Math.max(dt, 1e-3), TRAVEL);
          } else this.horses.drive(h, e.x, e.z, this.turn(h.yaw, e.yaw ?? h.yaw, dt), 0, TRAVEL);
          if (e.yaw !== undefined && Math.abs(wrapPi(e.yaw - h.yaw)) > 0.05) done = false;
        });
        if (!done && j.t < 8) return;
        j.horses.forEach((h, k) => {
          const e = j.ends[k];
          this.horses.drive(h, e.x, e.z, e.yaw ?? h.yaw, 0, TRAVEL);
          this.horses.tie(h);
        });
        if (j.kind === 'team') j.horses.forEach((h) => this.atPole.add(h));
        else if (j.kind === 'shoe') this.startShoe(j.horses[0]);
        this.finish(j);
        break;
      }
    }
  }

  private takeAll(j: Job): void {
    for (const h of j.horses) {
      if (j.kind === 'unshoe' && this.shod?.h === h) this.endShoe();
      this.horses.take(h);
    }
    this.atPole.forEach((h) => { if (j.horses.includes(h)) this.atPole.delete(h); });
    this.lead(j);
  }

  private lead(j: Job): void {
    const g = j.groom;
    this.sim.unsummon(g);
    this.sim.summon(g, j.to.x, j.to.z, this.sim.simClock + 1, this.task(j.kind, j.horses), 'LEADING');
    j.stage = 'lead'; j.t = 0;
    this.stat.led += j.horses.length;
  }

  /** The horses after his hand: LEAD m behind him, two side by side. */
  private follow(j: Job, gx: number, gz: number, dt: number): void {
    // his heading: from where he was a moment ago
    const k0 = j.groom;
    const px = this.gx[k0] ?? gx, pz = this.gz[k0] ?? gz;
    let ux = gx - px, uz = gz - pz;
    const ul = hyp(ux, uz);
    if (ul > 1e-3) { ux /= ul; uz /= ul; } else {
      const h = j.horses[0];
      ux = gx - h.x; uz = gz - h.z;
      const l = hyp(ux, uz) || 1; ux /= l; uz /= l;
    }
    this.gx[k0] = gx; this.gz[k0] = gz;
    const n = j.horses.length;
    j.horses.forEach((h, k) => {
      const side = n === 2 ? (k === 0 ? SIDE : -SIDE) : 0;
      const back = LEAD + HEAD * h.scale;
      const tx = gx - ux * back + uz * side, tz = gz - uz * back - ux * side;
      const dx = tx - h.x, dz = tz - h.z, d = hyp(dx, dz);
      let v = 0, yaw = h.yaw;
      if (d > 0.12) {
        v = Math.min(4.2 * TRAVEL, d * 3);
        const s = Math.min(d, v * dt);
        yaw = this.turn(h.yaw, Math.atan2(dx, dz), dt);
        this.horses.drive(h, h.x + (dx / d) * s, h.z + (dz / d) * s, yaw, v, TRAVEL);
      } else {
        yaw = this.turn(h.yaw, Math.atan2(gx - h.x, gz - h.z), dt * 0.5);
        this.horses.drive(h, h.x, h.z, yaw, 0, TRAVEL);
      }
    });
  }

  private turn(from: number, to: number, dt: number): number {
    return from + Math.max(-3 * dt, Math.min(3 * dt, wrapPi(to - from)));
  }

  private arrive(j: Job, hour: number): void {
    switch (j.kind) {
      case 'out':
      case 'unshoe':
        j.horses.forEach((h) => this.horses.turnOut(h));
        break;
      case 'in':
        j.horses.forEach((h) => this.horses.stable(h));
        break;
      case 'home':
        if (inWin(hour, OUT_FROM, IN_FROM)) j.horses.forEach((h) => this.horses.turnOut(h));
        else j.horses.forEach((h) => this.horses.stable(h));
        break;
      case 'team':
      case 'shoe':
        j.stage = 'settle'; j.t = 0;
        return;
    }
    this.finish(j);
  }

  private startShoe(h: Horse): void {
    this.shod = { h, since: this.sim.simClock };
    this.lastShoe = this.sim.simClock;
    if (this.tie) this.tie.taken++;
    this.stat.shod++;
    // the farrier leaves the anvil for the hoof
    this.sim.citizens.forEach((c, i) => { if (c.trade === 'Farrier' && c.state === 'WORKING') this.sim.replan(i); });
  }

  private endShoe(): void {
    if (this.tie && this.tie.taken > 0) this.tie.taken--;
    this.shod = null;
    this.sim.citizens.forEach((c, i) => { if (c.trade === 'Farrier' && c.state === 'WORKING') this.sim.replan(i); });
  }

  private finish(j: Job): void {
    this.sim.unsummon(j.groom);
    this.jobs.splice(this.jobs.indexOf(j), 1);
  }

  /** Give a job up: the groom back to his day; horses on the rope are tied where they stand. */
  private drop(j: Job, count: boolean): void {
    for (const h of j.horses) if (h.holder === 'lead') this.horses.tie(h);
    this.sim.unsummon(j.groom);
    this.jobs.splice(this.jobs.indexOf(j), 1);
    if (count) this.stat.dropped++;
  }

  private dropAll(): void {
    for (const j of [...this.jobs]) this.sim.unsummon(j.groom);
    this.jobs = [];
    this.atPole.clear();
    if (this.tie) this.tie.taken = 0;
    this.shod = null;
  }

  stats() {
    return {
      managed: this.horses.managed, jobs: this.jobs.map((j) => ({ kind: j.kind, stage: j.stage, groom: j.groom,
        horses: j.horses.map((h) => h.name), age: Math.round(j.age) })),
      ...this.stat, atPole: [...this.atPole].map((h) => h.name), shod: this.shod?.h.name ?? null,
      horses: this.horses.horses.map((h) => `${h.name}:${h.holder ?? (h.inStall ? 'stall' : 'paddock')}`).join(' '),
    };
  }
}
