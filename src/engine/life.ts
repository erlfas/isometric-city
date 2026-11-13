import type { Citizen, Parcel } from '../types';

/**
 * Citizen life (M7): what each citizen does next, from the town's anchors and their needs.
 *
 * Anchors are fixed blocks per role, in day hours: guild work hours (prime to vespers with a
 * break at sext), the watch shifts of the guards (day or night), the clergy's hours at their
 * church, and the curfew at compline, when everyone but the watch must be home. A household
 * wakes together at its own time just after matins and sits down to supper together.
 *
 * Needs rise while awake (hunger, thirst, fatigue, social, piety; 0 = fine, 1 = urgent) and
 * fall while the citizen is at the place of an activity that meets them. Outside the blocks a
 * citizen scores what is on offer now and nearby, and does the best of it:
 *   eat at home (with the household at breakfast and supper), eat at the market, buy bread at
 *   a baker's window (queue, pay from the purse, carry it home), fetch water at the well
 *   (queue, carry it home), go to church near the canonical bells, the tavern at a brewer's,
 *   stroll the market, or rest at home. Apprentices run errands during work hours.
 * Inside the home block: rest by the hearth, supper, then bed once tired (or late).
 *
 * The simulation asks decide() again when the activity's time is up and on a staggered
 * re-think every 6-12 sim minutes; decide returns the current activity to keep it.
 */

export type Kind = 'sleep' | 'wake' | 'home' | 'eat_home' | 'work' | 'patrol' | 'errand'
  | 'bread' | 'water' | 'church' | 'tavern' | 'market' | 'eat_out' | 'drop';

export interface Activity {
  kind: Kind;
  /** Shown state; it also picks the slot indoors (SLEEPING bed, EATING / RESTING seat ...). */
  state: string;
  /** Parcel id, landmark id, 'market_square', 'wall:k' (wall checkpoint), 'svc:k' (service). */
  location: string;
  task: string;
  /** Sim clock (hours since start, unwrapped) when to decide again. */
  until: number;
  /** Clock by which to be there (late: run); Infinity = no hurry. */
  due: number;
  /** Part of a fixed block (work, watch, night at home): free choices wait for its end. */
  fixed: boolean;
}

export interface Household {
  home: string;
  members: number[];
  /** Loaves and buckets of water in the house. */
  bread: number; water: number;
  /** Day hours: everyone up (after matins); supper. */
  wake: number; supper: number;
  /** Member out buying bread / fetching water now (-1: nobody). */
  buyer: number; fetcher: number;
}

type Role = 'worker' | 'guard_day' | 'guard_night' | 'clergy' | 'merchant';
interface Block { a: number; b: number; kind: 'work' | 'home' }

export interface Mind {
  hunger: number; thirst: number; fatigue: number; social: number; piety: number;
  role: Role;
  blocks: Block[];
  hh: Household;
  apprentice: boolean;
  /** Patrol: wall checkpoint and direction; gate duty: the gate (location id). */
  beat: number; beatDir: number; gate: string | null;
  carrying: 'bread' | 'water' | null;
  tool: string;
  pietyRate: number;
  lastTick: number;
  /** Day of the last wage (clock / 24). */
  paidDay: number;
  diary: { h: number; state: string; task: string }[];
}

/** A place where one person at a time is served: a baker's window, a side of the well. */
export interface Service {
  kind: 'bread' | 'water';
  /** Where the served person stands, facing (fx, fz); the line runs out along (nx, nz). */
  x: number; z: number; fx: number; fz: number; nx: number; nz: number;
  name: string;
  line: number[];
  user: number;
  /** Real seconds (simulation clock) the current customer is done. */
  doneT: number;
}

/** What decide() needs to know about the world (the simulation provides it). */
export interface LifeWorld {
  hour: number;
  clock: number;
  /** Estimated trip (sim hours) from agent i's position to a location. */
  travel(i: number, location: string): number;
  pos(i: number): [number, number];
  wallet(i: number): number;
}

const WAGE: Record<string, number> = { master: 4, guildmaster: 5, journeyman: 3, apprentice: 1, laborer: 1, guardsman: 2, brother: 1 };
const COMPLINE = 21.25;

const wrap = (h: number) => ((h % 24) + 24) % 24;
/** Is day hour h in [a, b) (wrapping over midnight)? */
const inWin = (h: number, a: number, b: number) => (a <= b ? h >= a && h < b : h >= a || h < b);
/** Hours from day hour h until day hour t (0..24). */
const until = (h: number, t: number) => wrap(t - h);
const clamp01 = (v: number) => Math.max(0, Math.min(1, v));

interface Place { id: string; x: number; z: number; name: string }

export class Life {
  readonly minds: Mind[] = [];
  readonly households: Household[] = [];
  readonly services: Service[];
  private bakers: number[][] = []; // per household: bread service indices, nearest first
  private churches: Place[] = [];
  private taverns: Place[] = [];
  private workshops: Place[] = [];
  private checkpoints: { x: number; z: number }[] = [];

  constructor(
    citizens: Citizen[], households: Map<string, number[]>, parcels: Map<string, Parcel>,
    services: Service[], places: { churches: Place[]; taverns: Place[]; workshops: Place[]; checkpoints: { x: number; z: number }[] },
    rngs: (() => number)[],
  ) {
    this.services = services;
    this.churches = places.churches;
    this.taverns = places.taverns;
    this.workshops = places.workshops;
    this.checkpoints = places.checkpoints;
    const byHome = new Map<string, Household>();
    for (const [home, members] of households) {
      const r = rngs[members[0]];
      const hh: Household = { home, members, bread: 0, water: 0, wake: 5 - 0.2 + r() * 0.55,
        supper: 19.2 + r() * 0.6, buyer: -1, fetcher: -1 };
      byHome.set(home, hh);
      this.households.push(hh);
      const p = parcels.get(home);
      const hx = p?.x ?? 0, hz = p?.z ?? 0;
      const order = services.map((_s, k) => k).filter((k) => services[k].kind === 'bread')
        .sort((a, b) => Math.hypot(services[a].x - hx, services[a].z - hz) - Math.hypot(services[b].x - hx, services[b].z - hz));
      this.bakers.push(order.slice(0, 2));
    }
    for (let i = 0; i < citizens.length; i++) {
      const c = citizens[i], r = rngs[i];
      const hh = byHome.get(c.homeParcelId)!;
      const role: Role = c.guildRank === 'guardsman' ? (r() < 0.5 ? 'guard_day' : 'guard_night')
        : c.guildRank === 'brother' ? 'clergy' : c.guildRank === 'foreign_merchant' ? 'merchant' : 'worker';
      const ws = 6.9 + r() * 0.35, le = 13 + r() * 0.3, we = 17.9 + r() * 0.2;
      const blocks: Block[] =
        role === 'worker' ? [{ a: ws, b: 12, kind: 'work' }, { a: le, b: we, kind: 'work' }, { a: COMPLINE, b: hh.wake, kind: 'home' }]
        : role === 'guard_day' ? [{ a: 6, b: 12.25, kind: 'work' }, { a: 12.9, b: 18.5, kind: 'work' }, { a: 21.5, b: 5.5, kind: 'home' }]
        : role === 'guard_night' ? [{ a: 18, b: 6.5, kind: 'work' }, { a: 7.5, b: 14.5, kind: 'home' }]
        : role === 'clergy' ? [{ a: 5.5, b: 12, kind: 'work' }, { a: 13, b: 20.5, kind: 'work' }, { a: 21, b: 4.9, kind: 'home' }]
        : [{ a: 8.5, b: 12.5, kind: 'work' }, { a: 13.5, b: 18, kind: 'work' }, { a: 21.5, b: 6.5, kind: 'home' }];
      const guard = role === 'guard_day' || role === 'guard_night';
      const gate = guard && r() < 0.4 ? (r() < 0.5 ? 'gate_grodzka' : 'gate_krakow') : null;
      this.minds.push({
        hunger: 0, thirst: 0, fatigue: 0, social: 0, piety: 0, role, blocks, hh,
        apprentice: c.guildRank === 'apprentice', beat: Math.floor(r() * Math.max(1, this.checkpoints.length)),
        beatDir: r() < 0.5 ? 1 : -1, gate, carrying: null, tool: c.carriedItem,
        pietyRate: 0.008 + r() * 0.025, lastTick: 0, paidDay: -1, diary: [],
      });
    }
  }

  /** Needs and stores as they would plausibly be at this hour (start, or a clock jump). */
  seed(i: number, hour: number, clock: number, r: () => number): void {
    const m = this.minds[i];
    const hh = m.hh;
    if (hh.members[0] === i) {
      hh.bread = Math.floor(r() * 4); hh.water = r() * 2; hh.buyer = -1; hh.fetcher = -1;
    }
    const sleeping = this.blockAt(m, hour)?.kind === 'home' && !inWin(hour, COMPLINE, 23);
    const awake = sleeping ? 0 : until(this.wakeHour(m), hour);
    m.fatigue = sleeping ? 0.15 : clamp01(awake / 16.5 + r() * 0.1);
    m.hunger = clamp01(0.15 + r() * 0.4);
    m.thirst = clamp01(0.1 + r() * 0.35);
    m.social = clamp01(0.2 + r() * 0.5);
    m.piety = clamp01(r() * 0.9);
    m.carrying = null;
    m.lastTick = clock;
    m.paidDay = Math.round((clock - hour) / 24) - (hour > 16 ? 0 : 1);
    m.diary.length = 0;
  }

  /** Day hour this citizen gets up. */
  private wakeHour(m: Mind): number {
    if (m.role === 'guard_night') return 14.5;
    const home = m.blocks.find((b) => b.kind === 'home');
    return home ? home.b : m.hh.wake;
  }

  /** Kind of block citizen i is in, or starts within `within` hours (null: free time). */
  blockSoon(i: number, h: number, within: number): 'work' | 'home' | null {
    const m = this.minds[i];
    const b = this.blockAt(m, h);
    if (b) return b.kind;
    const [nb, t] = this.nextBlock(m, h);
    return t <= within ? nb.kind : null;
  }

  checkpoint(k: number): { x: number; z: number } {
    return this.checkpoints[k] ?? { x: 0, z: 0 };
  }

  private blockAt(m: Mind, h: number): Block | null {
    for (const b of m.blocks) if (inWin(h, b.a, b.b)) return b;
    return null;
  }

  /** The next block to start after hour h, and hours until it. */
  private nextBlock(m: Mind, h: number): [Block, number] {
    let best = m.blocks[0], bt = 99;
    for (const b of m.blocks) {
      const t = until(h, b.a) || 24;
      if (t < bt) { bt = t; best = b; }
    }
    return [best, bt];
  }

  /**
   * Needs over the sim hours since the last tick. `here`: at the place of the current
   * activity (inside it, at its spot, or standing at its point), so it is doing it.
   */
  tick(i: number, clock: number, hour: number, act: Activity | null, here: boolean, c: Citizen): void {
    const m = this.minds[i];
    const dh = Math.min(1, clock - m.lastTick);
    m.lastTick = clock;
    if (dh <= 0) return;
    const asleep = here && act?.kind === 'sleep';
    m.hunger = clamp01(m.hunger + dh * (asleep ? 0.02 : 0.075));
    m.thirst = clamp01(m.thirst + dh * (asleep ? 0.02 : 0.09));
    m.fatigue = clamp01(m.fatigue + dh * (asleep ? -1 / 7 : 1 / 16.5));
    m.social = clamp01(m.social + dh * (asleep ? 0 : 0.08));
    m.piety = clamp01(m.piety + dh * m.pietyRate);
    if (!here || !act) return;
    const hh = m.hh;
    switch (act.kind) {
      case 'eat_home':
        m.hunger = clamp01(m.hunger - dh * 2.4);
        if (hh.water > 0) { m.thirst = clamp01(m.thirst - dh * 2); hh.water = Math.max(0, hh.water - dh * 0.3); }
        break;
      case 'eat_out':
        m.hunger = clamp01(m.hunger - dh * 2.4);
        m.thirst = clamp01(m.thirst - dh * 1.5);
        m.social = clamp01(m.social - dh * 0.4);
        break;
      case 'home': case 'wake':
        if (hh.water > 0 && m.thirst > 0.2) { m.thirst = clamp01(m.thirst - dh * 1.5); hh.water = Math.max(0, hh.water - dh * 0.2); }
        m.social = clamp01(m.social - dh * 0.15);
        break;
      case 'tavern':
        m.thirst = clamp01(m.thirst - dh * 2.5);
        m.social = clamp01(m.social - dh * 0.9);
        m.hunger = clamp01(m.hunger - dh * 0.6);
        break;
      case 'market': m.social = clamp01(m.social - dh * 0.5); break;
      case 'church': m.piety = clamp01(m.piety - dh * 2.2); m.social = clamp01(m.social - dh * 0.2); break;
      // Small beer and company at the bench.
      case 'work': case 'patrol':
        m.social = clamp01(m.social - dh * 0.06);
        m.thirst = clamp01(m.thirst - dh * 0.05);
        break;
      default: break;
    }
    // Wages at the end of the working day.
    const day = Math.round((clock - hour) / 24);
    if (act.kind === 'work' && m.paidDay !== day && hour > 16) {
      m.paidDay = day;
      c.walletGroschen += WAGE[c.guildRank] ?? 0;
    }
  }

  /** A chat with an acquaintance. */
  talked(i: number): void { this.minds[i].social = clamp01(this.minds[i].social - 0.35); }

  /** Arrived at an activity's place: one-off effects (meal from the stores, pay the tavern). */
  arrived(i: number, act: Activity, c: Citizen): void {
    const m = this.minds[i], hh = m.hh;
    if (act.kind === 'eat_home') hh.bread = Math.max(0, hh.bread - 0.3);
    if ((act.kind === 'tavern' || act.kind === 'eat_out') && c.walletGroschen > 0) c.walletGroschen--;
    if (m.carrying && act.location === hh.home) {
      // A basket of loaves; two buckets on a yoke.
      if (m.carrying === 'bread') hh.bread += 2 + hh.members.length * 0.6; else hh.water += 3;
      m.carrying = null;
      c.carrying = undefined;
      c.carriedItem = m.tool;
    }
  }

  /** Served at a baker's window or the well: pay, take it, carry it home. */
  served(i: number, s: Service, c: Citizen): void {
    const m = this.minds[i];
    if (s.kind === 'bread') { c.walletGroschen = Math.max(0, c.walletGroschen - 2); c.carriedItem = 'Rye loaves'; }
    else c.carriedItem = 'Bucket of well water';
    m.carrying = s.kind;
    c.carrying = s.kind;
    this.release(i);
  }

  /** No longer the household's buyer / fetcher (served, or gave up). */
  release(i: number): void {
    const hh = this.minds[i].hh;
    if (hh.buyer === i) hh.buyer = -1;
    if (hh.fetcher === i) hh.fetcher = -1;
  }

  /**
   * What to do now: the current activity (keep going) or a new one.
   * `cur` may be null (start of the run, or after a clock jump).
   */
  decide(i: number, c: Citizen, cur: Activity | null, w: LifeWorld, r: () => number): Activity {
    const m = this.minds[i];
    const h = w.hour, now = w.clock;
    const block = this.blockAt(m, h);
    const end = (t: number) => now + until(h, t);

    if (block?.kind === 'work') {
      if (cur?.kind === 'errand' && now < cur.until) return cur;
      // Apprentices are sent on errands now and then (checked every re-think, ~8 a sim hour).
      if (m.apprentice && cur?.kind === 'work' && r() < 0.03 && this.workshops.length) {
        const [x, z] = w.pos(i);
        const near = this.workshops.filter((p) => p.id !== c.workParcelId && Math.hypot(p.x - x, p.z - z) < 160);
        if (near.length) {
          const p = near[Math.floor(r() * near.length)];
          return this.act(m, 'errand', 'ERRAND', p.id, `Errand to ${p.name}`, now + 0.25, Infinity, false);
        }
      }
      if (cur && cur.fixed && now < cur.until) return cur;
      return this.duty(i, c, m, cur, w, r, end(block.b), end(block.a));
    }
    if (block?.kind === 'home') {
      const home = m.hh.home;
      const due = cur && cur.location === home ? Infinity : now + w.travel(i, home);
      const asleepNow = cur?.kind === 'sleep';
      const lateNight = !inWin(h, COMPLINE, 22.75);
      if (asleepNow || m.fatigue > 0.6 || lateNight) {
        if (asleepNow && now < cur!.until) return cur!;
        return this.act(m, 'sleep', 'SLEEPING', home, 'Asleep', end(block.b), due, true);
      }
      if (cur && cur.fixed && cur.location === home && now < cur.until) return cur;
      if (m.hunger > 0.45 && m.hh.bread > 0) return this.act(m, 'eat_home', 'EATING', home, 'Supper by the hearth', now + 0.5, due, true);
      return this.act(m, 'home', 'RESTING', home, 'By the hearth', now + 0.3, due, true);
    }

    // Free time. Keep a running activity until its time is up (errands run to the end).
    const [nb, inH] = this.nextBlock(m, h);
    const nbLoc = nb.kind === 'home' ? m.hh.home : this.dutyLocation(c, m);
    const leave = inH - w.travel(i, nbLoc) - 0.05;
    if (leave <= 0) {
      // Time to go: the block's activity, arriving by its start.
      return nb.kind === 'home'
        ? this.act(m, 'home', 'RESTING', m.hh.home, 'Home before curfew', now + inH + 0.1, now + inH, false)
        : this.duty(i, c, m, cur, w, r, now + inH + until(nb.a, nb.b), now + inH);
    }
    // Just got up: stand by the hearth first.
    if (cur?.kind === 'sleep' || (cur === null && Math.abs(h - m.hh.wake) < 0.2 && m.role === 'worker')) {
      return this.act(m, 'wake', 'WAKING', m.hh.home, 'Kindling the hearth', now + Math.min(0.25, leave), Infinity, false);
    }
    if (cur?.fixed) cur = null; // the block is over
    if (m.carrying && cur?.kind !== 'drop') {
      return this.act(m, 'drop', 'RETURNING', m.hh.home, m.carrying === 'bread' ? 'Carrying bread home' : 'Carrying water home',
        now + 0.12, Infinity, false);
    }
    if (cur && now < cur.until && cur.kind !== 'home') return cur;
    if (cur?.kind === 'drop' && now < cur.until) return cur;
    const last = now + leave;
    return this.choose(i, c, m, cur, w, r, last);
  }

  /** The block's work: the workplace, a wall checkpoint, or the gate. */
  private duty(_i: number, c: Citizen, m: Mind, cur: Activity | null, w: LifeWorld, r: () => number, endT: number, due: number): Activity {
    const now = w.clock;
    if (m.role === 'guard_day' || m.role === 'guard_night') {
      if (m.gate) return this.act(m, 'patrol', 'PATROLLING', m.gate, 'Gate watch', endT, due, true);
      // Walk the wall from checkpoint to checkpoint, a while at each.
      const n = this.checkpoints.length;
      if (cur?.kind === 'patrol' && n) m.beat = (m.beat + m.beatDir + n) % n;
      const stay = now + 0.3 + r() * 0.3;
      return this.act(m, 'patrol', 'PATROLLING', `wall:${m.beat}`, 'Walking the wall', Math.min(endT, stay), due, true);
    }
    const loc = this.dutyLocation(c, m);
    const task = c.schedule.find((s) => s.state === 'WORKING')?.task ?? 'At work';
    return this.act(m, 'work', 'WORKING', loc, m.role === 'clergy' ? 'Prayers and offices' : task, endT, due, true);
  }

  private dutyLocation(c: Citizen, m: Mind): string {
    if (m.role === 'guard_day' || m.role === 'guard_night') return m.gate ?? `wall:${m.beat}`;
    return c.workParcelId;
  }

  /** Score what is on offer in free time; `last` = clock by which to leave for the next block. */
  private choose(i: number, _c: Citizen, m: Mind, cur: Activity | null, w: LifeWorld, r: () => number, last: number): Activity {
    const h = w.hour, now = w.clock, hh = m.hh;
    const [x, z] = w.pos(i);
    const purse = w.wallet(i);
    const cost = (loc: string) => w.travel(i, loc) * 0.9; // ~0.1 per 6 minutes walking
    const opts: { s: number; a: () => Activity }[] = [];
    const add = (s: number, a: () => Activity) => opts.push({ s: s + (r() - 0.5) * 0.15, a });
    const span = (d: number) => Math.min(last, now + d);
    const home = hh.home;

    // Home: rest, more so in the evening and when tired; meals with the household.
    add(0.2 + m.fatigue * 0.5 + (h >= 19.5 ? 0.5 : 0) - cost(home),
      () => this.act(m, 'home', 'RESTING', home, 'At home', span(0.3 + r() * 0.3), Infinity, false));
    if (hh.bread > 0 && m.hunger > 0.3) {
      const meal = Math.abs(h - (hh.wake + 0.35)) < 0.6 || Math.abs(h - hh.supper) < 0.6 ? 0.5 : 0;
      add(m.hunger * 1.3 + meal - cost(home),
        () => this.act(m, 'eat_home', 'EATING', home, meal ? 'Eating with the household' : 'A bite at home', span(0.5), Infinity, false));
    }
    if (purse >= 1 && m.hunger > 0.35 && (inWin(h, 11, 14) || inWin(h, 17, 20))) {
      add(m.hunger * 1.0 - cost('market_square'),
        () => this.act(m, 'eat_out', 'EATING', 'market_square', 'Pie and small beer at the fair', span(0.5), Infinity, false));
    }
    // Errands for the house, one member at a time.
    if (hh.bread < 2 && hh.buyer < 0 && purse >= 2 && inWin(h, 6, 19)) {
      const k = this.bakers[this.households.indexOf(hh)]?.[0];
      if (k !== undefined) {
        add(0.65 + m.hunger * 0.4 + (hh.bread === 0 ? 0.3 : 0) - cost(`svc:${k}`), () => {
          hh.buyer = i;
          return this.act(m, 'bread', 'SHOPPING', `svc:${k}`, `Buying bread at ${this.services[k].name}`, now + 1.5, Infinity, false);
        });
      }
    }
    if (hh.water < 1 && hh.fetcher < 0 && inWin(h, 5, 20.5)) {
      let k = -1, best = 1e9;
      this.services.forEach((s, j) => { if (s.kind === 'water' && s.line.length < best) { best = s.line.length; k = j; } });
      if (k >= 0) {
        add(0.7 + m.thirst * 0.5 + (hh.water <= 0 ? 0.3 : 0) - cost(`svc:${k}`) - best * 0.05, () => {
          hh.fetcher = i;
          return this.act(m, 'water', 'FETCHING', `svc:${k}`, 'Fetching water at the town well', now + 1.5, Infinity, false);
        });
      }
    }
    // Church near the canonical bells.
    // Vespers runs on after the bell: people come from work.
    const bell = [5, 7, 9, 15, 18].find((b) => h > b - 0.7 && h < b + (b === 18 ? 0.8 : 0.15));
    if (bell !== undefined && m.piety > 0.35 && this.churches.length) {
      const ch = this.nearest(this.churches, x, z);
      add(m.piety * 1.4 - cost(ch.id),
        () => this.act(m, 'church', 'PRAYING', ch.id, `Mass at ${ch.name}`, span(Math.max(0.5, bell + 0.6 - h)), Infinity, false));
    }
    // Tavern at a brewer's: thirst and company, for a coin.
    if (purse >= 1 && (inWin(h, 11.5, 14) || inWin(h, 17, COMPLINE)) && this.taverns.length) {
      const near = [...this.taverns].sort((a, b) => Math.hypot(a.x - x, a.z - z) - Math.hypot(b.x - x, b.z - z)).slice(0, 3);
      const t = near[Math.floor(r() * near.length)];
      add(0.1 + m.social * 0.6 + m.thirst * 0.6 - cost(t.id),
        () => this.act(m, 'tavern', 'DRINKING', t.id, `Ale at ${t.name}`, span(0.8 + r() * 0.7), Infinity, false));
    }
    // The fair on the square.
    if (inWin(h, 8, 20.5)) {
      add(0.15 + m.social * 0.7 - cost('market_square'),
        () => this.act(m, 'market', 'SOCIALIZING', 'market_square', 'Strolling the fair', span(0.5 + r() * 0.7), Infinity, false));
    }
    let best = opts[0];
    for (const o of opts) if (o.s > best.s) best = o;
    // Same choice as now (resting at home again): extend it rather than restart it.
    const a = best.a();
    if (cur && cur.kind === a.kind && cur.location === a.location) { cur.until = a.until; return cur; }
    return a;
  }

  private nearest(list: Place[], x: number, z: number): Place {
    let best = list[0], bd = Infinity;
    for (const p of list) { const d = Math.hypot(p.x - x, p.z - z); if (d < bd) { bd = d; best = p; } }
    return best;
  }

  private act(_m: Mind, kind: Kind, state: string, location: string, task: string, until: number, due: number, fixed: boolean): Activity {
    return { kind, state, location, task, until, due, fixed };
  }

  /** Remember a started activity (the inspector shows the last ones). */
  note(m: Mind, a: Activity, hour?: number): void {
    const d = m.diary;
    if (d.length && d[d.length - 1].task === a.task) return;
    d.push({ h: hour ?? -1, state: a.state, task: a.task });
    if (d.length > 10) d.shift();
  }
}
