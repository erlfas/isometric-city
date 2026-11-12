/**
 * Soundscape for Lublin 1392: the background music track plus a synthesised, positional
 * town (recipes in sound-recipes.ts; nothing else is loaded).
 *
 * - Music: music/Copper_and_Rye.mp3, looped; ducks while bells ring or the herald blows.
 * - Bells: pre-rendered strikes for the parish church (tenor + treble) and the Dominican
 *   friary, rung per canonical hour by tollHour() (curfew = 9 slow tenor strokes).
 * - Workshops: forges, coopers, carpenters' saws and looms in working hours, from the
 *   parcels of the city plan (soundOf).
 * - Beds and nature: crowd murmur scaled by awake citizens near the view, wind (louder
 *   zoomed out), running water by the riverfront tanneries, birds by day, crickets and
 *   owls at night, the odd dog.
 *
 * Positioning: the listener is the camera's look-at point. Effective distance is
 * hypot(ground distance, zoom / 2), so zooming out pushes every source away; pan is the
 * source's horizontal screen position. The AudioContext only runs after a user gesture
 * and is suspended while muted or the tab is hidden; update() is a no-op then.
 */
import musicUrl from '../../music/Copper_and_Rye.mp3?url';
import type { Citizen, CityPlan, Parcel } from '../types';
import { parcelHash, parcelKind } from './parcel-kind';
import * as R from './sound-recipes';

export interface Listener {
  x: number;
  z: number;
  /** World units visible vertically (renderer.zoom). */
  zoom: number;
  /** Horizontal screen position of a world point: -1 left edge, 1 right edge. */
  pan(x: number, z: number): number;
}

interface Point { x: number; z: number }
type EmitterKind = 'forge' | 'cooper' | 'saw' | 'loom';
interface Emitter extends Point { kind: EmitterKind; next: number; pitch: number }
type BellName = 'tenor' | 'treble' | 'friary';

/** What a parcel sounds like, from the building it is drawn as (parcelKind), so a parcel
 *  drawn as a bakery stays quiet even when its buildingType says forge. */
function soundOf(p: Parcel, index: number): EmitterKind | 'water' | null {
  const craft = p.craft?.id ?? '';
  switch (parcelKind(p, parcelHash(p, index))) {
    case 'tanner': return 'water'; // riverfront tanneries
    case 'smith': return 'forge';
    case 'weaver': return craft === 'tailor' ? null : 'loom';
    case 'logging': return 'saw';
    case 'brick': case 'half_timber': case 'log': case 'district':
      // ordinary houses: the trade worked inside decides
      if (craft === 'cooper' || p.buildingType.includes('cooper')) return 'cooper';
      if (craft === 'carpenter' || craft === 'wheelwright' || p.buildingType === 'artisan_half_timber_workshop') return 'saw';
      return null;
    default: return null;
  }
}
/** Reference distance (m) per kind: full volume within it, falling off beyond (see reach). */
const EMITTER_REF: Record<EmitterKind, number> = { forge: 14, cooper: 9, saw: 7, loom: 7 };
const MAX_ACTIVE_EMITTERS = 5;
const DOOR_RATE = 3;   // door sounds per second, sustained
const DOOR_BURST = 4;
const MUSIC_LEVEL = 0.35;
const KEY_MUTED = 'lublin.audio.muted';
const KEY_MUSIC = 'lublin.audio.music';

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const rand = (lo: number, hi: number) => lo + Math.random() * (hi - lo);
const pick = <T>(a: T[]): T => a[Math.floor(Math.random() * a.length)];

function readFlag(key: string, fallback: boolean): boolean {
  try {
    const v = localStorage.getItem(key);
    return v === null ? fallback : v === '1';
  } catch { return fallback; }
}
function writeFlag(key: string, v: boolean): void {
  try { localStorage.setItem(key, v ? '1' : '0'); } catch { /* storage blocked */ }
}

export class Soundscape {
  public isMuted = readFlag(KEY_MUTED, false);
  public musicOn = readFlag(KEY_MUSIC, true);

  private ctx: AudioContext | null = null;
  private sfx!: GainNode;
  private ambience!: GainNode;
  private crowdBus!: GainNode;
  private reverbSend!: GainNode;
  private musicBus!: GainNode;
  private musicEl: HTMLAudioElement | null = null;
  private noise!: R.Noise;
  private bells: Promise<Record<BellName, AudioBuffer>> | null = null;
  private beds!: { wind: GainNode; crowd: GainNode; water: GainNode };

  private parish: Point = { x: 130, z: 20 };
  private friary: Point = { x: -60, z: -90 };
  private emitters: Emitter[] = [];
  private active: Emitter[] = [];
  private trees: Point[] = [];
  private water: Point[] = [];
  private homes: Point[] = [];

  private listener: Listener | null = null;
  private crowd = 0;
  private greenery = 0;
  private nextSample = 0;
  private nextSyllable = 0;
  private nextBird = 0;
  private nextCricket = 0;
  private nextOwl = 0;
  private nextDog = 0;

  constructor() {
    const unlock = () => this.init();
    window.addEventListener('pointerdown', unlock);
    window.addEventListener('keydown', unlock);
    document.addEventListener('visibilitychange', () => this.applyRunState());
  }

  /** Sound sources from the city plan. */
  public configure(plan: CityPlan): void {
    for (const l of plan.civicLandmarks) {
      if (l.id === 'parish_fara') this.parish = { x: l.x, z: l.z };
      if (l.id === 'dominican_monastery') this.friary = { x: l.x, z: l.z };
    }
    this.emitters = [];
    this.homes = [];
    this.water = [];
    plan.parcels.forEach((p, i) => {
      const kind = soundOf(p, i);
      if (kind === 'water') this.water.push({ x: p.x, z: p.z });
      else if (kind) this.emitters.push({ kind, x: p.x, z: p.z, next: 0, pitch: Math.random() });
      else if (!p.isShed) this.homes.push({ x: p.x, z: p.z });
    });
    this.trees = (plan.vegetation ?? []).map((v) => ({ x: v.x, z: v.z }));
  }

  /** Create (first call) or resume the audio graph. Must run inside a user gesture. */
  public init(): void {
    if (!this.ctx) {
      try {
        this.build();
      } catch (e) {
        console.warn('[audio] Web Audio unavailable:', e);
        return;
      }
    }
    this.applyRunState();
  }

  public toggleMute(): boolean {
    this.isMuted = !this.isMuted;
    writeFlag(KEY_MUTED, this.isMuted);
    this.init();
    return this.isMuted;
  }

  public toggleMusic(): boolean {
    this.musicOn = !this.musicOn;
    writeFlag(KEY_MUSIC, this.musicOn);
    this.init();
    return this.musicOn;
  }

  /** Per frame. Cheap when idle: heavy work is sampled at 4 Hz. */
  public update(listener: Listener, hour: number, citizens: Citizen[]): void {
    this.listener = listener;
    const ctx = this.ctx;
    if (!ctx || ctx.state !== 'running') return;
    const t = ctx.currentTime;
    if (t >= this.nextSample) {
      this.nextSample = t + 0.25;
      this.sample(listener, hour, citizens, t);
    }
    this.scheduleWorkshops(t, hour);
    this.scheduleCrowd(t);
    this.scheduleNature(t, hour);
  }

  /** Ring the bells for a canonical hour (sim.onBellToll). */
  public tollHour(hour: number): void {
    const ctx = this.ctx;
    if (!ctx || !this.bells || ctx.state !== 'running') return;
    void this.bells.then((b) => {
      const t0 = ctx.currentTime + 0.1;
      const rounds = (n: number, t: number) => {
        for (let i = 0; i < n; i++) {
          this.strike(i % 2 ? b.tenor : b.treble, this.parish, t + i * 1.15 + rand(-0.04, 0.04), rand(0.8, 1));
        }
        return t + n * 1.15;
      };
      const friary = (n: number, t: number, gap = 2.4) => {
        for (let i = 0; i < n; i++) this.strike(b.friary, this.friary, t + i * gap, rand(0.75, 0.95));
        return t + n * gap;
      };
      let end: number;
      if (hour === 21) {
        // curfew: the great bell alone, slow
        for (let i = 0; i < 9; i++) this.strike(b.tenor, this.parish, t0 + i * 3.2, 1);
        end = t0 + 9 * 3.2;
      } else if (hour === 0) {
        end = friary(3, t0, 4);
      } else if (hour === 5) {
        // Angelus: three times three on the tenor, then the peal
        for (let k = 0; k < 3; k++) {
          for (let i = 0; i < 3; i++) this.strike(b.tenor, this.parish, t0 + k * 6.5 + i * 1.6, 0.95);
        }
        end = Math.max(rounds(8, t0 + 20), friary(5, t0 + 21));
      } else {
        const n = hour === 12 ? 16 : 10;
        end = Math.max(rounds(n, t0), friary(Math.ceil(n / 2), t0 + 1.7));
      }
      this.duck(end + 4);
    });
  }

  /** Herald's horn for a fair proclamation (sim.onEventTriggered). */
  public herald(): void {
    const ctx = this.ctx;
    if (!ctx || ctx.state !== 'running') return;
    const t = ctx.currentTime + 0.05;
    const dur = R.heraldHorn(ctx, this.spot(0.35, 0, 0.5), t, 0.5);
    this.duck(t + dur + 1);
  }

  /** A citizen's speech bubble: a murmured phrase from where they stand. */
  public voice(x: number, z: number, female: boolean): void {
    const ctx = this.ctx;
    if (!ctx || ctx.state !== 'running') return;
    const r = this.reach(x, z, 6);
    if (!r) return;
    const pitch = female ? rand(185, 245) : rand(95, 140);
    R.phrase(ctx, this.spot(r.gain * 0.6, r.pan, 0.25), ctx.currentTime + 0.05, pitch, 0.3);
  }

  /** A door opening or shutting (sim.onDoor): only within earshot, a few per second at most
   *  (a whole street's doors open together at the morning commute). */
  public door(x: number, z: number, opening: boolean): void {
    const ctx = this.ctx;
    if (!ctx || ctx.state !== 'running') return;
    const t = ctx.currentTime;
    this.doorTokens = Math.min(DOOR_BURST, this.doorTokens + (t - this.doorT) * DOOR_RATE);
    this.doorT = t;
    if (this.doorTokens < 1) return;
    const r = this.reach(x, z, 5);
    if (!r) return;
    this.doorTokens--;
    const out = this.spot(r.gain * 0.55, r.pan, 0.3);
    const at = t + 0.02 + Math.random() * 0.05;
    if (opening) R.doorOpen(ctx, out, at, this.noise, 0.5);
    else R.doorClose(ctx, out, at, this.noise, 0.5);
  }
  private doorTokens = DOOR_BURST;
  private doorT = 0;

  /** For scripts: node scripts/probe.mjs "pause" "__lublin.audio.debugState()". */
  public debugState() {
    return {
      context: this.ctx?.state ?? 'none',
      muted: this.isMuted,
      music: this.musicOn,
      musicPlaying: !!this.musicEl && !this.musicEl.paused,
      musicTime: this.musicEl?.currentTime ?? 0,
      crowd: +this.crowd.toFixed(2),
      greenery: +this.greenery.toFixed(2),
      activeEmitters: this.active.map((e) => e.kind),
      emitters: this.emitters.length,
    };
  }

  // ---------------------------------------------------------------- graph

  private build(): void {
    const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ctx = new Ctor();
    this.ctx = ctx;
    this.noise = R.makeNoise(ctx);

    const limiter = ctx.createDynamicsCompressor();
    limiter.threshold.value = -8;
    limiter.knee.value = 6;
    limiter.ratio.value = 8;
    limiter.attack.value = 0.003;
    limiter.release.value = 0.25;
    const master = ctx.createGain();
    master.gain.value = 0.85;
    master.connect(limiter).connect(ctx.destination);

    this.sfx = ctx.createGain();
    this.sfx.gain.value = 0.9;
    this.sfx.connect(master);
    this.ambience = ctx.createGain();
    this.ambience.gain.value = 0.7;
    this.ambience.connect(master);

    const reverb = ctx.createConvolver();
    reverb.buffer = R.makeReverbIR(ctx);
    const wet = ctx.createGain();
    wet.gain.value = 0.55;
    this.reverbSend = ctx.createGain();
    this.reverbSend.connect(reverb).connect(wet).connect(master);

    // murmured syllables: muffled by distance and walls
    const crowdLp = ctx.createBiquadFilter();
    crowdLp.type = 'lowpass';
    crowdLp.frequency.value = 2000;
    this.crowdBus = ctx.createGain();
    this.crowdBus.connect(crowdLp).connect(this.ambience);
    const crowdWet = ctx.createGain();
    crowdWet.gain.value = 0.25;
    crowdLp.connect(crowdWet).connect(this.reverbSend);

    this.musicBus = ctx.createGain();
    this.musicBus.gain.value = 0;
    this.musicBus.connect(master);

    this.beds = {
      wind: this.bed(this.noise.brown, [['lowpass', 380, 0.8]], 0.06),
      crowd: this.bed(this.noise.pink, [['bandpass', 550, 0.8], ['lowpass', 1300, 0.7]], 0),
      water: this.bed(this.noise.pink, [['bandpass', 1100, 0.6], ['highpass', 260, 0.7]], 0),
    };
    // gusts: sweep the wind filter slowly
    const windFilter = (this.beds.wind as GainNode & { filter?: BiquadFilterNode }).filter!;
    const lfo = ctx.createOscillator();
    lfo.frequency.value = 0.07;
    const depth = ctx.createGain();
    depth.gain.value = 170;
    lfo.connect(depth).connect(windFilter.frequency);
    lfo.start();

    this.bells = Promise.all([R.renderBell(98, 11), R.renderBell(147, 8), R.renderBell(123.5, 9)])
      .then(([tenor, treble, friary]) => ({ tenor, treble, friary }));
  }

  /** Looping filtered-noise bed into the ambience bus; returns its level gain. */
  private bed(buf: AudioBuffer, filters: [BiquadFilterType, number, number][], level: number): GainNode {
    const ctx = this.ctx!;
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.loop = true;
    let node: AudioNode = src;
    let first: BiquadFilterNode | undefined;
    for (const [type, f, q] of filters) {
      const b = ctx.createBiquadFilter();
      b.type = type;
      b.frequency.value = f;
      b.Q.value = q;
      first ??= b;
      node = node.connect(b);
    }
    const g = ctx.createGain() as GainNode & { filter?: BiquadFilterNode };
    g.gain.value = level;
    g.filter = first;
    node.connect(g).connect(this.ambience);
    src.start(0, Math.random() * buf.duration);
    return g;
  }

  /** Run the context and music only when wanted: unmuted, tab visible, after a gesture. */
  private applyRunState(): void {
    const ctx = this.ctx;
    if (!ctx) return;
    const live = !this.isMuted && document.visibilityState === 'visible';
    if (live) void ctx.resume();
    else void ctx.suspend();
    if (live && this.musicOn) {
      if (!this.musicEl) {
        const el = new Audio(musicUrl);
        el.loop = true;
        el.preload = 'auto';
        ctx.createMediaElementSource(el).connect(this.musicBus);
        this.musicEl = el;
        this.musicBus.gain.setValueAtTime(0, ctx.currentTime);
        this.musicBus.gain.linearRampToValueAtTime(MUSIC_LEVEL, ctx.currentTime + 4);
      }
      this.musicEl.play().catch(() => { /* no gesture yet; the next one retries */ });
    } else {
      this.musicEl?.pause();
    }
  }

  /** Lower the music until context time `until`, then bring it back. */
  private duck(until: number): void {
    const g = this.musicBus.gain;
    const now = this.ctx!.currentTime;
    g.cancelScheduledValues(now);
    g.setValueAtTime(g.value, now);
    g.setTargetAtTime(MUSIC_LEVEL * 0.35, now, 0.6);
    g.setTargetAtTime(MUSIC_LEVEL, until, 1.5);
  }

  /** Distance gain and pan for a world point, or null when too faint to bother. */
  private reach(x: number, z: number, ref: number, floor = 0): { gain: number; pan: number } | null {
    const L = this.listener;
    if (!L) return null;
    const e = Math.hypot(Math.hypot(x - L.x, z - L.z), L.zoom * 0.5);
    const gain = Math.max(floor, Math.min(1, (ref / e) ** 1.6)); // steeper than 1/d: walls, wind
    if (gain < 0.03) return null;
    return { gain, pan: clamp(L.pan(x, z), -1, 1) * 0.75 };
  }

  /** Input node for one positioned sound: gain -> pan -> sfx, with a reverb send. */
  private spot(gain: number, pan: number, wet: number, bus: AudioNode = this.sfx): AudioNode {
    const ctx = this.ctx!;
    const g = ctx.createGain();
    g.gain.value = gain;
    const p = ctx.createStereoPanner();
    p.pan.value = pan;
    g.connect(p).connect(bus);
    if (wet > 0) {
      const s = ctx.createGain();
      s.gain.value = wet;
      p.connect(s).connect(this.reverbSend);
    }
    return g;
  }

  private strike(buf: AudioBuffer, at: Point, t: number, vel: number): void {
    // bells carry across the whole town: never quieter than the floor
    const r = this.reach(at.x, at.z, 90, 0.18) ?? { gain: 0.18, pan: 0 };
    const src = this.ctx!.createBufferSource();
    src.buffer = buf;
    src.playbackRate.value = rand(0.997, 1.003);
    src.connect(this.spot(r.gain * vel, r.pan, 0.7));
    src.start(t);
  }

  // ---------------------------------------------------------------- scheduling

  private sample(L: Listener, hour: number, citizens: Citizen[], t: number): void {
    // crowd: awake citizens around the view centre
    const radius = Math.max(14, L.zoom * 0.55);
    let n = 0;
    for (const c of citizens) {
      if (c.state === 'SLEEPING') continue;
      if (Math.abs((c.currentX ?? 0) - L.x) < radius && Math.abs((c.currentZ ?? 0) - L.z) < radius) n++;
    }
    this.crowd = Math.min(1, n / 45) * Math.min(1, 40 / L.zoom);

    let trees = 0;
    const tr = Math.max(25, L.zoom * 0.6);
    for (const p of this.trees) if (Math.abs(p.x - L.x) < tr && Math.abs(p.z - L.z) < tr) trees++;
    this.greenery = Math.min(1, trees / 20);

    let water = 0;
    for (const p of this.water) {
      water = Math.max(water, Math.min(1, 25 / Math.hypot(Math.hypot(p.x - L.x, p.z - L.z), L.zoom * 0.5)));
    }

    const zoomedOut = clamp((L.zoom - 15) / 60, 0, 1);
    const night = hour >= 21 || hour < 5;
    const set = (g: GainNode, v: number) => g.gain.setTargetAtTime(v, t, 0.5);
    set(this.beds.wind, 0.05 + 0.12 * zoomedOut + (night ? 0.04 : 0));
    set(this.beds.crowd, this.crowd * 0.28);
    set(this.beds.water, water > 0.08 ? water * 0.35 : 0);

    // workshops: the nearest few audible ones
    this.active = this.emitters
      .map((e) => ({ e, r: this.reach(e.x, e.z, EMITTER_REF[e.kind]) }))
      .filter((h) => h.r !== null)
      .sort((a, b) => b.r!.gain - a.r!.gain)
      .slice(0, MAX_ACTIVE_EMITTERS)
      .map((h) => h.e);
  }

  private scheduleWorkshops(t: number, hour: number): void {
    const working = hour >= 7 && hour < 18.5;
    const rate = hour >= 12 && hour < 13 ? 0.4 : 1; // the midday meal
    for (const e of this.active) {
      if (t < e.next) continue;
      if (!working || Math.random() > rate) {
        e.next = t + rand(3, 6);
        continue;
      }
      const r = this.reach(e.x, e.z, EMITTER_REF[e.kind]);
      if (!r) { e.next = t + 1; continue; }
      const at = t + 0.05;
      const dur = this.playEmitter(e, at, this.spot(r.gain, r.pan, 0.3));
      e.next = at + dur;
    }
  }

  /** Play one work pattern; returns the time until the next one may start. */
  private playEmitter(e: Emitter, t: number, out: AudioNode): number {
    const ctx = this.ctx!;
    const nz = this.noise;
    switch (e.kind) {
      case 'forge': {
        const f0 = 1100 + e.pitch * 600;
        const blows = 2 + Math.floor(Math.random() * 5);
        for (let i = 0; i < blows; i++) {
          const at = t + i * rand(0.4, 0.46);
          R.anvil(ctx, out, at, nz, f0 * rand(0.98, 1.02), rand(0.8, 1));
          if (i < blows - 1) R.anvil(ctx, out, at + 0.2, nz, f0 * 1.06, 0.25); // tap on the anvil between blows
        }
        return blows * 0.45 + rand(1.5, 5);
      }
      case 'cooper': {
        const f = 150 + e.pitch * 70;
        const n = 3 + Math.floor(Math.random() * 5);
        for (let i = 0; i < n; i++) R.knock(ctx, out, t + i * rand(0.26, 0.32), nz, f * rand(0.95, 1.05), rand(0.7, 1));
        return n * 0.3 + rand(2, 6);
      }
      case 'saw': {
        const n = 5 + Math.floor(Math.random() * 6);
        const stroke = rand(0.3, 0.36);
        for (let i = 0; i < n; i++) R.sawStroke(ctx, out, t + i * stroke, nz, stroke * 0.95, i % 2 === 0);
        return n * stroke + rand(3, 8);
      }
      case 'loom': {
        const n = 2 + Math.floor(Math.random() * 4);
        for (let i = 0; i < n; i++) R.loomCycle(ctx, out, t + i * 1.1, nz);
        return n * 1.1 + rand(1, 3);
      }
    }
  }

  private scheduleCrowd(t: number): void {
    const perSecond = this.crowd * 16;
    if (perSecond < 0.3) { this.nextSyllable = t + 0.5; return; }
    if (this.nextSyllable < t) this.nextSyllable = t;
    while (this.nextSyllable < t + 0.15) {
      const female = Math.random() < 0.45;
      const pitch = female ? rand(180, 250) : rand(95, 145);
      const out = this.spot(rand(0.5, 1), rand(-0.8, 0.8), 0, this.crowdBus);
      R.syllable(this.ctx!, out, this.nextSyllable, pitch, rand(0.08, 0.2), 0.2);
      this.nextSyllable += -Math.log(1 - Math.random()) / perSecond;
    }
  }

  private scheduleNature(t: number, hour: number): void {
    const ctx = this.ctx!;
    const L = this.listener!;
    const near = Math.min(1, 30 / L.zoom); // nature detail fades when zoomed out
    const day = hour >= 4.5 && hour < 20;
    const dawn = hour >= 4.5 && hour < 8;
    const night = hour >= 20.5 || hour < 4.5;
    const green = 0.25 + this.greenery * 0.75;

    if (day && t >= this.nextBird) {
      R.birdCall(ctx, this.spot(rand(0.05, 0.12) * green * near, rand(-0.9, 0.9), 0.3), t + 0.05, 0.6);
      const perSecond = (0.12 + this.greenery * 0.5) * (dawn ? 3 : 1);
      this.nextBird = t + -Math.log(1 - Math.random()) / perSecond;
    }
    if (night && t >= this.nextCricket) {
      const f = pick([4200, 4450, 4700]);
      R.cricket(ctx, this.spot(0.08 * green * near, rand(-0.9, 0.9), 0.1), t + 0.02, f, 0.5);
      this.nextCricket = t + rand(0.25, 0.7) / green;
    }
    if (hour >= 22 || hour < 4) {
      if (this.nextOwl === 0) this.nextOwl = t + rand(10, 30);
      if (t >= this.nextOwl) {
        R.owl(ctx, this.spot(0.12 * green * near, rand(-0.7, 0.7), 0.5), t + 0.05, this.noise, 0.5);
        this.nextOwl = t + rand(25, 70);
      }
    }
    if (t >= this.nextDog) {
      if (this.nextDog > 0 && this.homes.length) {
        const h = pick(this.homes);
        const r = this.reach(h.x, h.z, 20);
        if (r) R.bark(ctx, this.spot(r.gain * 0.5, r.pan, 0.5), t + 0.05, this.noise, 0.4);
      }
      // homes picked town-wide, so most picks are out of earshot: this is a rare sound
      this.nextDog = t + rand(3, 7) * (night ? 1.5 : 1);
    }
  }
}
