/**
 * Synthesised one-shot sounds for the soundscape (src/engine/audio.ts).
 * Each recipe schedules nodes into `out` at context time `t`; nodes stop themselves.
 * Recipes take a BaseAudioContext so they also render offline (bells are pre-rendered).
 */

export interface Noise {
  white: AudioBuffer;
  pink: AudioBuffer;
  brown: AudioBuffer;
}

export function makeNoise(ctx: BaseAudioContext, seconds = 3): Noise {
  const n = Math.floor(ctx.sampleRate * seconds);
  const white = ctx.createBuffer(1, n, ctx.sampleRate);
  const pink = ctx.createBuffer(1, n, ctx.sampleRate);
  const brown = ctx.createBuffer(1, n, ctx.sampleRate);
  const w = white.getChannelData(0), p = pink.getChannelData(0), b = brown.getChannelData(0);
  let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0, last = 0;
  for (let i = 0; i < n; i++) {
    const x = Math.random() * 2 - 1;
    w[i] = x;
    // Paul Kellet's pink filter
    b0 = 0.99886 * b0 + x * 0.0555179; b1 = 0.99332 * b1 + x * 0.0750759;
    b2 = 0.969 * b2 + x * 0.153852; b3 = 0.8665 * b3 + x * 0.3104856;
    b4 = 0.55 * b4 + x * 0.5329522; b5 = -0.7616 * b5 - x * 0.016898;
    p[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + x * 0.5362) * 0.11;
    b6 = x * 0.115926;
    last = (last + 0.02 * x) / 1.02;
    b[i] = last * 3.5;
  }
  return { white, pink, brown };
}

/** Stereo impulse response: diffuse exponential tail with a few early slap-backs off walls. */
export function makeReverbIR(ctx: BaseAudioContext, seconds = 2.6): AudioBuffer {
  const n = Math.floor(ctx.sampleRate * seconds);
  const ir = ctx.createBuffer(2, n, ctx.sampleRate);
  for (let c = 0; c < 2; c++) {
    const d = ir.getChannelData(c);
    let lp = 0;
    for (let i = 0; i < n; i++) {
      const t = i / ctx.sampleRate;
      lp += 0.35 * ((Math.random() * 2 - 1) - lp); // darker tail
      d[i] = lp * Math.pow(1 - t / seconds, 2) * Math.exp(-t * 2.2);
    }
    for (const [ms, g] of [[23, 0.5], [41, 0.35], [67, 0.25], [97, 0.18]]) {
      const k = Math.floor(((ms + c * 7) / 1000) * ctx.sampleRate);
      if (k < n) d[k] += g;
    }
  }
  return ir;
}

function noiseSource(ctx: BaseAudioContext, buf: AudioBuffer, t: number, dur: number): AudioBufferSourceNode {
  const s = ctx.createBufferSource();
  s.buffer = buf;
  s.loop = true;
  s.start(t, Math.random() * (buf.duration - 0.2));
  s.stop(t + dur + 0.05);
  return s;
}

/** Gain node with a fast attack to `peak`, then exponential decay (time to ~-40 dB = `decay`). */
function envGain(ctx: BaseAudioContext, t: number, peak: number, attack: number, decay: number): GainNode {
  const g = ctx.createGain();
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(peak, t + attack);
  g.gain.setTargetAtTime(0, t + attack, decay / 4.6);
  return g;
}

function tone(ctx: BaseAudioContext, out: AudioNode, t: number, type: OscillatorType, f: number,
  peak: number, attack: number, decay: number): OscillatorNode {
  const o = ctx.createOscillator();
  o.type = type;
  o.frequency.setValueAtTime(f, t);
  const g = envGain(ctx, t, peak, attack, decay);
  o.connect(g).connect(out);
  o.start(t);
  o.stop(t + attack + decay + 0.05);
  return o;
}

function filtered(ctx: BaseAudioContext, type: BiquadFilterType, f: number, q: number): BiquadFilterNode {
  const b = ctx.createBiquadFilter();
  b.type = type;
  b.frequency.value = f;
  b.Q.value = q;
  return b;
}

function noiseBurst(ctx: BaseAudioContext, out: AudioNode, t: number, noise: AudioBuffer,
  type: BiquadFilterType, f: number, q: number, peak: number, decay: number, attack = 0.002): void {
  const f1 = filtered(ctx, type, f, q);
  const g = envGain(ctx, t, peak, attack, decay);
  noiseSource(ctx, noise, t, attack + decay).connect(f1).connect(g).connect(out);
}

// ---------------------------------------------------------------- bells

/** Partials of a cast-bronze bell relative to its prime, slightly out of tune like a
 *  14th-century casting: [ratio, amplitude, decay as a fraction of the bell's length]. */
const BELL_PARTIALS: [number, number, number][] = [
  [0.502, 0.55, 1.0],  // hum
  [1.0, 0.45, 0.72],   // prime
  [1.187, 0.42, 0.62], // tierce (minor third: the "bell" colour)
  [1.48, 0.18, 0.45],  // quint
  [2.0, 0.6, 0.5],     // nominal: the strike note
  [2.51, 0.22, 0.3],
  [2.67, 0.2, 0.27],
  [3.03, 0.2, 0.2],
  [4.06, 0.1, 0.13],
  [5.21, 0.06, 0.09],
];

/** Render one strike of a bell. Every partial is a detuned pair, so it beats (the warble). */
export async function renderBell(prime: number, seconds: number, noiseSeconds = 0.5): Promise<AudioBuffer> {
  const sr = 44100;
  const ctx = new OfflineAudioContext(1, Math.floor(sr * seconds), sr);
  const out = ctx.createGain();
  out.connect(ctx.destination);
  for (const [ratio, amp, frac] of BELL_PARTIALS) {
    const f = prime * ratio;
    if (f > 9000) continue;
    const decay = seconds * frac;
    const beat = 0.3 + Math.random() * 1.2;
    for (const d of [-beat / 2, beat / 2]) {
      tone(ctx, out, 0, 'sine', f + d, amp * 0.5, ratio > 2 ? 0.002 : 0.006, decay);
    }
  }
  // clapper strike: a short metallic noise click
  const noise = makeNoise(ctx, noiseSeconds);
  noiseBurst(ctx, out, 0, noise.white, 'bandpass', Math.min(prime * 9, 6000), 1.2, 0.35, 0.07);
  const buf = await ctx.startRendering();
  const d = buf.getChannelData(0);
  let peak = 0;
  for (let i = 0; i < d.length; i++) peak = Math.max(peak, Math.abs(d[i]));
  if (peak > 0) for (let i = 0; i < d.length; i++) d[i] *= 0.9 / peak;
  return buf;
}

// ---------------------------------------------------------------- workshops

/** Hammer on an anvil: inharmonic plate partials plus the thud of the blow. */
export function anvil(ctx: BaseAudioContext, out: AudioNode, t: number, noise: Noise, f0: number, vel: number): void {
  const parts: [number, number, number][] = [[1, 1, 0.9], [2.76, 0.55, 0.5], [5.4, 0.3, 0.25], [8.93, 0.15, 0.12]];
  for (const [r, a, d] of parts) tone(ctx, out, t, 'sine', f0 * r, a * 0.22 * vel, 0.001, d * (0.6 + vel * 0.4));
  noiseBurst(ctx, out, t, noise.white, 'lowpass', 1200, 0.7, 0.35 * vel, 0.06);
}

/** Cooper's mallet on a stave or hoop: hollow wooden knock. */
export function knock(ctx: BaseAudioContext, out: AudioNode, t: number, noise: Noise, f: number, vel: number): void {
  const o = tone(ctx, out, t, 'sine', f, 0.5 * vel, 0.002, 0.16);
  o.frequency.exponentialRampToValueAtTime(f * 0.78, t + 0.08);
  tone(ctx, out, t, 'triangle', f * 2.3, 0.12 * vel, 0.001, 0.07);
  noiseBurst(ctx, out, t, noise.white, 'bandpass', 900, 2.5, 0.5 * vel, 0.04);
}

/** One saw stroke: raspy band of noise, buzzed by the teeth rate. */
export function sawStroke(ctx: BaseAudioContext, out: AudioNode, t: number, noise: Noise, dur: number, push: boolean): void {
  const bp = filtered(ctx, 'bandpass', push ? 2900 : 2300, 1.6);
  const hp = filtered(ctx, 'highpass', 700, 0.7);
  const g = ctx.createGain();
  const peak = push ? 0.32 : 0.2;
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(peak, t + dur * 0.25);
  g.gain.linearRampToValueAtTime(peak * 0.8, t + dur * 0.75);
  g.gain.linearRampToValueAtTime(0, t + dur);
  // teeth buzz: amplitude modulation
  const am = ctx.createGain();
  am.gain.value = 0.6;
  const lfo = ctx.createOscillator();
  lfo.type = 'square';
  lfo.frequency.setValueAtTime(push ? 95 : 75, t);
  const depth = ctx.createGain();
  depth.gain.value = 0.4;
  lfo.connect(depth).connect(am.gain);
  lfo.start(t);
  lfo.stop(t + dur + 0.05);
  bp.frequency.linearRampToValueAtTime(push ? 3300 : 2000, t + dur);
  noiseSource(ctx, noise.white, t, dur).connect(hp).connect(bp).connect(am).connect(g).connect(out);
}

/** Loom: the shuttle swishes through, then the beater clacks twice. */
export function loomCycle(ctx: BaseAudioContext, out: AudioNode, t: number, noise: Noise): void {
  const bp = filtered(ctx, 'bandpass', 1200, 1.2);
  bp.frequency.setValueAtTime(1200, t);
  bp.frequency.linearRampToValueAtTime(3000, t + 0.22);
  const g = ctx.createGain();
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(0.12, t + 0.08);
  g.gain.linearRampToValueAtTime(0, t + 0.24);
  noiseSource(ctx, noise.white, t, 0.25).connect(bp).connect(g).connect(out);
  for (const [dt, v] of [[0.38, 1], [0.6, 0.6]]) {
    noiseBurst(ctx, out, t + dt, noise.white, 'bandpass', 1700, 4, 0.5 * v, 0.03);
    tone(ctx, out, t + dt, 'sine', 330, 0.25 * v, 0.001, 0.06);
  }
}

/** Mill wheel: the oak axle groaning in its bearing, a slow rubbed creak (stick-slip:
 *  a pulse train sliding in pitch through a wooden body resonance). */
export function wheelCreak(ctx: BaseAudioContext, out: AudioNode, t: number, noise: Noise, f: number, dur: number, vel: number): void {
  const o = ctx.createOscillator();
  o.type = 'sawtooth';
  o.frequency.setValueAtTime(f, t);
  o.frequency.linearRampToValueAtTime(f * 1.35, t + dur * 0.6);
  o.frequency.linearRampToValueAtTime(f * 1.15, t + dur);
  const body = filtered(ctx, 'bandpass', 520, 3);
  const body2 = filtered(ctx, 'bandpass', 1350, 5);
  const g = ctx.createGain();
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(0.16 * vel, t + dur * 0.2);
  g.gain.linearRampToValueAtTime(0.1 * vel, t + dur * 0.8);
  g.gain.linearRampToValueAtTime(0, t + dur);
  o.connect(body).connect(g);
  o.connect(body2).connect(g);
  g.connect(out);
  o.start(t);
  o.stop(t + dur + 0.05);
  noiseBurst(ctx, out, t, noise.white, 'bandpass', 800, 2, 0.06 * vel, dur * 0.8, dur * 0.3);
}

/** A paddle slapping into the race and the water it throws: a low slosh and a bright spray. */
export function paddleSplash(ctx: BaseAudioContext, out: AudioNode, t: number, noise: Noise, vel: number): void {
  noiseBurst(ctx, out, t, noise.pink, 'lowpass', 520, 0.8, 0.5 * vel, 0.32, 0.01);
  noiseBurst(ctx, out, t + 0.02, noise.white, 'bandpass', 2600, 0.9, 0.16 * vel, 0.45, 0.03);
  tone(ctx, out, t, 'sine', 140 + Math.random() * 40, 0.12 * vel, 0.004, 0.12);
}

/** An iron pick or wedge on limestone: a short dull clink (anvil-like but damped, little
 *  ring) and a gritty chip of noise. */
export function pickStrike(ctx: BaseAudioContext, out: AudioNode, t: number, noise: Noise, f0: number, vel: number): void {
  tone(ctx, out, t, 'triangle', f0, 0.24 * vel, 0.001, 0.09);
  tone(ctx, out, t, 'sine', f0 * 2.4, 0.1 * vel, 0.001, 0.05);
  noiseBurst(ctx, out, t, noise.white, 'bandpass', 2400, 1.2, 0.6 * vel, 0.07);
  noiseBurst(ctx, out, t + 0.01, noise.pink, 'lowpass', 600, 0.7, 0.25 * vel, 0.12);
}

/** One push of a foot bellows: a breathy swell of filtered noise, falling as the bag empties. */
export function bellowsBreath(ctx: BaseAudioContext, out: AudioNode, t: number, noise: Noise, dur: number, vel: number): void {
  const lp = filtered(ctx, 'lowpass', 900, 0.8);
  lp.frequency.setValueAtTime(500, t);
  lp.frequency.linearRampToValueAtTime(1100, t + dur * 0.3);
  lp.frequency.linearRampToValueAtTime(400, t + dur);
  const g = ctx.createGain();
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(0.2 * vel, t + dur * 0.3);
  g.gain.linearRampToValueAtTime(0, t + dur);
  noiseSource(ctx, noise.pink, t, dur).connect(lp).connect(g).connect(out);
}

/** A stretch of fire roar: a low rumbling bed of noise with a few crackles in it. */
export function fireRoar(ctx: BaseAudioContext, out: AudioNode, t: number, noise: Noise, dur: number, vel: number): void {
  const lp = filtered(ctx, 'lowpass', 260, 0.9);
  const g = ctx.createGain();
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(0.3 * vel, t + 0.4);
  g.gain.setValueAtTime(0.3 * vel, t + dur - 0.4);
  g.gain.linearRampToValueAtTime(0, t + dur);
  noiseSource(ctx, noise.brown, t, dur).connect(lp).connect(g).connect(out);
  const n = Math.floor(dur * 3 * Math.random());
  for (let i = 0; i < n; i++) {
    noiseBurst(ctx, out, t + Math.random() * dur, noise.white, 'highpass', 3000, 0.7, 0.12 * vel, 0.015);
  }
}

// ---------------------------------------------------------------- voices and animals

const VOWELS: [number, number][] = [[800, 1200], [500, 1800], [320, 2300], [500, 900], [360, 750], [650, 1500]];

/** One murmured syllable: a glottal sawtooth through two vowel formants. */
export function syllable(ctx: BaseAudioContext, out: AudioNode, t: number, pitch: number, dur: number, peak: number): void {
  const [f1, f2] = VOWELS[Math.floor(Math.random() * VOWELS.length)];
  const o = ctx.createOscillator();
  o.type = 'sawtooth';
  o.frequency.setValueAtTime(pitch, t);
  o.frequency.linearRampToValueAtTime(pitch * (0.85 + Math.random() * 0.3), t + dur);
  const g = ctx.createGain();
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(peak, t + dur * 0.3);
  g.gain.linearRampToValueAtTime(0, t + dur);
  const a = filtered(ctx, 'bandpass', f1, 6);
  const b = filtered(ctx, 'bandpass', f2, 9);
  const bGain = ctx.createGain();
  bGain.gain.value = 0.6;
  o.connect(a).connect(g);
  o.connect(b).connect(bGain).connect(g);
  g.connect(out);
  o.start(t);
  o.stop(t + dur + 0.02);
}

/** A short spoken phrase (a speech bubble): returns its duration. */
export function phrase(ctx: BaseAudioContext, out: AudioNode, t: number, pitch: number, peak: number): number {
  let at = t;
  const n = 4 + Math.floor(Math.random() * 6);
  for (let i = 0; i < n; i++) {
    const dur = 0.09 + Math.random() * 0.13;
    const stress = i === 0 || Math.random() < 0.25 ? 1.25 : 1;
    syllable(ctx, out, at, pitch * stress * (1 - i * 0.015), dur, peak);
    at += dur * (0.85 + Math.random() * 0.3) + (Math.random() < 0.15 ? 0.12 : 0);
  }
  return at - t;
}

/** Songbird call: a run of quick frequency-swept chirps or a trill. */
export function birdCall(ctx: BaseAudioContext, out: AudioNode, t: number, peak: number): void {
  const base = 2400 + Math.random() * 2600;
  const trill = Math.random() < 0.35;
  const n = trill ? 6 + Math.floor(Math.random() * 8) : 2 + Math.floor(Math.random() * 4);
  let at = t;
  for (let i = 0; i < n; i++) {
    const f = trill ? base : base * (0.8 + Math.random() * 0.5);
    const dur = trill ? 0.035 : 0.06 + Math.random() * 0.06;
    const o = ctx.createOscillator();
    o.type = 'sine';
    o.frequency.setValueAtTime(f, at);
    o.frequency.exponentialRampToValueAtTime(f * (trill ? 1.15 : 1.5), at + dur * 0.5);
    o.frequency.exponentialRampToValueAtTime(f * 0.9, at + dur);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, at);
    g.gain.linearRampToValueAtTime(peak, at + dur * 0.2);
    g.gain.linearRampToValueAtTime(0, at + dur);
    o.connect(g).connect(out);
    o.start(at);
    o.stop(at + dur + 0.01);
    at += dur + (trill ? 0.02 : 0.05 + Math.random() * 0.08);
  }
}

/** Rook "kaah" (or a jackdaw's higher, shorter "tchak"): a rough, falling sawtooth through
 *  two nasal formants, roughened by a fast amplitude wobble, once to three times. */
export function caw(ctx: BaseAudioContext, out: AudioNode, t: number, noise: Noise, peak: number, jackdaw: boolean): void {
  const n = 1 + Math.floor(Math.random() * (jackdaw ? 2 : 3));
  let at = t;
  for (let i = 0; i < n; i++) {
    const dur = jackdaw ? 0.09 + Math.random() * 0.05 : 0.2 + Math.random() * 0.12;
    const f0 = (jackdaw ? 640 : 380) * (0.9 + Math.random() * 0.2);
    const o = ctx.createOscillator();
    o.type = 'sawtooth';
    o.frequency.setValueAtTime(f0 * 1.1, at);
    o.frequency.linearRampToValueAtTime(f0 * 0.82, at + dur);
    const rough = ctx.createGain();
    rough.gain.value = 0.6;
    const lfo = ctx.createOscillator();
    lfo.frequency.value = 55 + Math.random() * 30;
    const depth = ctx.createGain();
    depth.gain.value = 0.4;
    lfo.connect(depth).connect(rough.gain);
    const env = ctx.createGain();
    env.gain.setValueAtTime(0, at);
    env.gain.linearRampToValueAtTime(peak, at + 0.02);
    env.gain.setValueAtTime(peak * 0.8, at + dur * 0.7);
    env.gain.linearRampToValueAtTime(0, at + dur);
    const a = filtered(ctx, 'bandpass', jackdaw ? 1700 : 1250, 2.2);
    const b = filtered(ctx, 'bandpass', jackdaw ? 3200 : 2500, 4);
    const bg = ctx.createGain();
    bg.gain.value = 0.5;
    o.connect(rough);
    rough.connect(a).connect(env);
    rough.connect(b).connect(bg).connect(env);
    env.connect(out);
    o.start(at); lfo.start(at);
    o.stop(at + dur + 0.02); lfo.stop(at + dur + 0.02);
    noiseBurst(ctx, out, at, noise.white, 'bandpass', 1900, 1.5, peak * 0.15, dur * 0.8, 0.02);
    at += dur + 0.12 + Math.random() * 0.15;
  }
}

/** Red kite: a thin, wavering whistle "weee-ooo" with a few quick notes after.
 *  Buzzard: one plaintive, falling mew "pee-yow". */
export function raptorCall(ctx: BaseAudioContext, out: AudioNode, t: number, peak: number, kite: boolean): void {
  const notes: [number, number, number, number][] = kite // [start, dur, f from, f to]
    ? [[0, 0.7, 2500, 1500], [0.8, 0.12, 2300, 2000], [0.95, 0.12, 2300, 2000], [1.1, 0.12, 2200, 1900]]
    : [[0, 0.95, 2000, 950]];
  for (const [dt, dur, f1, f2] of notes) {
    const at = t + dt;
    const o = ctx.createOscillator();
    o.type = kite ? 'sine' : 'triangle';
    o.frequency.setValueAtTime(f1 * 0.9, at);
    o.frequency.linearRampToValueAtTime(f1, at + dur * 0.2);
    o.frequency.exponentialRampToValueAtTime(f2, at + dur);
    const vib = ctx.createOscillator();
    vib.frequency.value = kite ? 9 : 6;
    const vd = ctx.createGain();
    vd.gain.value = kite ? 60 : 25;
    vib.connect(vd).connect(o.frequency);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, at);
    g.gain.linearRampToValueAtTime(peak, at + 0.06);
    g.gain.setValueAtTime(peak * 0.8, at + dur * 0.6);
    g.gain.linearRampToValueAtTime(0, at + dur);
    o.connect(g).connect(out);
    o.start(at); vib.start(at);
    o.stop(at + dur + 0.02); vib.stop(at + dur + 0.02);
  }
}

/** Grey heron taking off: a harsh, low "fraank". */
export function heronCroak(ctx: BaseAudioContext, out: AudioNode, t: number, noise: Noise, peak: number): void {
  const dur = 0.35;
  const o = ctx.createOscillator();
  o.type = 'sawtooth';
  o.frequency.setValueAtTime(200, t);
  o.frequency.linearRampToValueAtTime(140, t + dur);
  const chop = ctx.createGain();
  chop.gain.value = 0.5;
  const lfo = ctx.createOscillator();
  lfo.type = 'square';
  lfo.frequency.value = 38;
  const depth = ctx.createGain();
  depth.gain.value = 0.5;
  lfo.connect(depth).connect(chop.gain);
  const env = ctx.createGain();
  env.gain.setValueAtTime(0, t);
  env.gain.linearRampToValueAtTime(peak, t + 0.03);
  env.gain.linearRampToValueAtTime(0, t + dur);
  o.connect(filtered(ctx, 'bandpass', 950, 1.1)).connect(chop).connect(env).connect(out);
  o.start(t); lfo.start(t);
  o.stop(t + dur + 0.02); lfo.stop(t + dur + 0.02);
  noiseBurst(ctx, out, t, noise.pink, 'bandpass', 1400, 1, peak * 0.3, dur, 0.02);
}

/** Cricket: a train of three to four 4.4 kHz pulses. */
export function cricket(ctx: BaseAudioContext, out: AudioNode, t: number, f: number, peak: number): void {
  const n = 3 + Math.floor(Math.random() * 2);
  for (let i = 0; i < n; i++) tone(ctx, out, t + i * 0.032, 'sine', f, peak, 0.004, 0.022);
}

/** Tawny owl: "hoo ... hoo-hoo-hoooo". */
export function owl(ctx: BaseAudioContext, out: AudioNode, t: number, noise: Noise, peak: number): void {
  const notes: [number, number, number][] = [[0, 0.4, 1], [0.9, 0.12, 0.6], [1.12, 0.12, 0.6], [1.35, 0.7, 0.9]];
  for (const [dt, dur, v] of notes) {
    const o = ctx.createOscillator();
    o.type = 'sine';
    o.frequency.setValueAtTime(390, t + dt);
    o.frequency.linearRampToValueAtTime(360, t + dt + dur);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t + dt);
    g.gain.linearRampToValueAtTime(peak * v, t + dt + 0.06);
    g.gain.setValueAtTime(peak * v, t + dt + dur * 0.6);
    g.gain.linearRampToValueAtTime(0, t + dt + dur);
    o.connect(g).connect(out);
    o.start(t + dt);
    o.stop(t + dt + dur + 0.02);
    noiseBurst(ctx, out, t + dt, noise.pink, 'lowpass', 600, 0.7, peak * 0.15 * v, dur, 0.05);
  }
}

// ---------------------------------------------------------------- doors

/** Iron latch lifting or dropping: a bright click with a short ring. */
function latch(ctx: BaseAudioContext, out: AudioNode, t: number, noise: Noise, peak: number): void {
  noiseBurst(ctx, out, t, noise.white, 'bandpass', 3200, 3, peak * 0.6, 0.03, 0.001);
  tone(ctx, out, t, 'triangle', 1750 + Math.random() * 300, peak * 0.12, 0.001, 0.06);
}

/** door_open: the latch, then the hinge creak (stick-slip: a buzzy tone chopped ~30 times a
 *  second, gliding up as the leaf swings). */
export function doorOpen(ctx: BaseAudioContext, out: AudioNode, t: number, noise: Noise, peak: number): void {
  latch(ctx, out, t, noise, peak);
  if (Math.random() < 0.35) return; // well-greased hinges
  const at = t + 0.05 + Math.random() * 0.04;
  const dur = 0.25 + Math.random() * 0.2;
  const f0 = 120 + Math.random() * 80;
  const o = ctx.createOscillator();
  o.type = 'sawtooth';
  o.frequency.setValueAtTime(f0, at);
  o.frequency.exponentialRampToValueAtTime(f0 * (1.3 + Math.random() * 0.4), at + dur);
  const bp = filtered(ctx, 'bandpass', 1100 + Math.random() * 500, 2.5);
  const env = ctx.createGain();
  env.gain.setValueAtTime(0, at);
  env.gain.linearRampToValueAtTime(peak * 0.35, at + 0.06);
  env.gain.setTargetAtTime(0, at + dur * 0.7, dur * 0.15);
  // Stick-slip chop: a square LFO on a second gain stage.
  const chop = ctx.createGain();
  chop.gain.value = 0.5;
  const lfo = ctx.createOscillator();
  lfo.type = 'square';
  lfo.frequency.value = 24 + Math.random() * 14;
  const depth = ctx.createGain();
  depth.gain.value = 0.5;
  lfo.connect(depth).connect(chop.gain);
  o.connect(bp).connect(chop).connect(env).connect(out);
  o.start(at); lfo.start(at);
  o.stop(at + dur + 0.2); lfo.stop(at + dur + 0.2);
}

/** door_close: the plank leaf thudding into its frame, then the latch dropping. */
export function doorClose(ctx: BaseAudioContext, out: AudioNode, t: number, noise: Noise, peak: number): void {
  const o = tone(ctx, out, t, 'sine', 85 + Math.random() * 20, peak * 0.8, 0.003, 0.22);
  o.frequency.exponentialRampToValueAtTime(52, t + 0.12);
  noiseBurst(ctx, out, t, noise.brown, 'lowpass', 520, 0.7, peak * 0.9, 0.12, 0.002);
  noiseBurst(ctx, out, t, noise.white, 'bandpass', 900, 2, peak * 0.25, 0.05);
  latch(ctx, out, t + 0.03 + Math.random() * 0.03, noise, peak * 0.7);
}

/** Dog bark: a falling, nasal sawtooth with a breathy edge. */
export function bark(ctx: BaseAudioContext, out: AudioNode, t: number, noise: Noise, peak: number): void {
  const n = 1 + Math.floor(Math.random() * 3);
  const f0 = 380 + Math.random() * 160;
  for (let i = 0; i < n; i++) {
    const at = t + i * (0.22 + Math.random() * 0.1);
    const o = ctx.createOscillator();
    o.type = 'sawtooth';
    o.frequency.setValueAtTime(f0 * 1.15, at);
    o.frequency.exponentialRampToValueAtTime(f0 * 0.7, at + 0.13);
    const bp = filtered(ctx, 'bandpass', 1100, 1.4);
    const g = envGain(ctx, at, peak, 0.008, 0.14);
    o.connect(bp).connect(g).connect(out);
    o.start(at);
    o.stop(at + 0.2);
    noiseBurst(ctx, out, at, noise.white, 'bandpass', 1800, 1, peak * 0.4, 0.08, 0.005);
  }
}

/** Herald's horn for a fair proclamation: a natural-horn call on the harmonic series. */
export function heraldHorn(ctx: BaseAudioContext, out: AudioNode, t: number, peak: number): number {
  const f = 174.6; // F3 fundamental, played on harmonics 3,4,5,6
  const call: [number, number][] = [[3, 0.22], [4, 0.22], [5, 0.22], [6, 0.5], [5, 0.2], [6, 0.2], [4, 1.1]];
  let at = t;
  for (const [h, dur] of call) {
    const o = ctx.createOscillator();
    o.type = 'sawtooth';
    o.frequency.setValueAtTime(f * h * 0.985, at);
    o.frequency.linearRampToValueAtTime(f * h, at + 0.04);
    const vib = ctx.createOscillator();
    vib.frequency.value = 5.2;
    const vibDepth = ctx.createGain();
    vibDepth.gain.value = dur > 0.4 ? 3 : 0;
    vib.connect(vibDepth).connect(o.frequency);
    const lp = filtered(ctx, 'lowpass', 1400, 0.9);
    lp.frequency.setValueAtTime(700, at);
    lp.frequency.linearRampToValueAtTime(1800, at + 0.06);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, at);
    g.gain.linearRampToValueAtTime(peak, at + 0.04);
    g.gain.setValueAtTime(peak, at + dur - 0.05);
    g.gain.linearRampToValueAtTime(0, at + dur);
    o.connect(lp).connect(g).connect(out);
    for (const n of [o, vib]) { n.start(at); n.stop(at + dur + 0.02); }
    at += dur + 0.03;
  }
  return at - t;
}

// ---------------------------------------------------------------- horses and the wagon (stable)

/** One hoof setting down: a dull thud and a scuff on soft earth, a hard clop with a short
 *  ring on cobbles or boards. */
export function hoof(ctx: BaseAudioContext, out: AudioNode, t: number, noise: Noise, hard: boolean, vel: number): void {
  const f = (hard ? 320 : 150) * (0.9 + Math.random() * 0.2);
  const o = tone(ctx, out, t, 'sine', f, (hard ? 0.35 : 0.5) * vel, 0.002, hard ? 0.09 : 0.14);
  o.frequency.exponentialRampToValueAtTime(f * 0.6, t + 0.06);
  noiseBurst(ctx, out, t, noise.brown, 'lowpass', hard ? 900 : 420, 0.7, 0.6 * vel, 0.08, 0.002);
  if (hard) {
    noiseBurst(ctx, out, t, noise.white, 'bandpass', 2600, 2.5, 0.25 * vel, 0.04, 0.001);
    tone(ctx, out, t, 'triangle', 1250 + Math.random() * 300, 0.06 * vel, 0.001, 0.05);
  } else noiseBurst(ctx, out, t + 0.01, noise.pink, 'bandpass', 1500, 1, 0.12 * vel, 0.06, 0.005);
}

/** A horse blowing through its nostrils: a rough, fluttering burst of breath. */
export function snort(ctx: BaseAudioContext, out: AudioNode, t: number, noise: Noise, peak: number): void {
  const dur = 0.35 + Math.random() * 0.3;
  const f = filtered(ctx, 'bandpass', 700 + Math.random() * 300, 0.9);
  const env = ctx.createGain();
  env.gain.setValueAtTime(0, t);
  env.gain.linearRampToValueAtTime(peak, t + 0.03);
  env.gain.setTargetAtTime(0, t + dur * 0.4, dur * 0.2);
  // nostril flutter: a square LFO on the level
  const chop = ctx.createGain();
  chop.gain.value = 0.6;
  const lfo = ctx.createOscillator();
  lfo.type = 'square';
  lfo.frequency.value = 22 + Math.random() * 10;
  const depth = ctx.createGain();
  depth.gain.value = 0.4;
  lfo.connect(depth).connect(chop.gain);
  noiseSource(ctx, noise.pink, t, dur).connect(f).connect(chop).connect(env).connect(out);
  lfo.start(t);
  lfo.stop(t + dur + 0.05);
}

/** A whinny: a high call breaking into a falling, shaking neigh. */
export function whinny(ctx: BaseAudioContext, out: AudioNode, t: number, noise: Noise, peak: number): void {
  const dur = 1.1 + Math.random() * 0.4;
  const f0 = 620 + Math.random() * 160;
  const o = ctx.createOscillator();
  o.type = 'sawtooth';
  o.frequency.setValueAtTime(f0 * 0.8, t);
  o.frequency.linearRampToValueAtTime(f0 * 1.15, t + 0.12);
  o.frequency.exponentialRampToValueAtTime(f0 * 0.45, t + dur);
  const vib = ctx.createOscillator();
  vib.frequency.setValueAtTime(9, t);
  vib.frequency.linearRampToValueAtTime(14, t + dur);
  const vd = ctx.createGain();
  vd.gain.setValueAtTime(f0 * 0.02, t);
  vd.gain.linearRampToValueAtTime(f0 * 0.09, t + dur);
  vib.connect(vd).connect(o.frequency);
  const env = ctx.createGain();
  env.gain.setValueAtTime(0, t);
  env.gain.linearRampToValueAtTime(peak, t + 0.06);
  env.gain.setValueAtTime(peak * 0.8, t + dur * 0.5);
  env.gain.linearRampToValueAtTime(0, t + dur);
  o.connect(filtered(ctx, 'bandpass', 1500, 0.8)).connect(env).connect(out);
  o.start(t); vib.start(t);
  o.stop(t + dur + 0.05); vib.stop(t + dur + 0.05);
  snort(ctx, out, t + dur - 0.1, noise, peak * 0.5);
}

/** Straw shifting under a hoof, or a mouthful of hay pulled from the rack. */
export function straw(ctx: BaseAudioContext, out: AudioNode, t: number, noise: Noise, peak: number): void {
  const n = 2 + Math.floor(Math.random() * 4);
  for (let i = 0; i < n; i++) {
    noiseBurst(ctx, out, t + i * (0.05 + Math.random() * 0.08), noise.white, 'bandpass', 3200 + Math.random() * 2500, 1.5,
      peak * (0.4 + Math.random() * 0.6), 0.07, 0.01);
  }
}

/** Harness jingling: buckles and rings knocking at the horses' step. */
export function jingle(ctx: BaseAudioContext, out: AudioNode, t: number, peak: number): void {
  const n = 2 + Math.floor(Math.random() * 3);
  for (let i = 0; i < n; i++) {
    const at = t + i * (0.03 + Math.random() * 0.05);
    const f = 2400 + Math.random() * 2200;
    tone(ctx, out, at, 'sine', f, peak * (0.5 + Math.random() * 0.5), 0.001, 0.12);
    tone(ctx, out, at, 'sine', f * 2.7, peak * 0.25, 0.001, 0.06);
  }
}

/** The wagon's wheels on the road: a low rumble of grit under iron tyres (dur s). */
export function wheelRumble(ctx: BaseAudioContext, out: AudioNode, t: number, noise: Noise, dur: number, vel: number): void {
  noiseBurst(ctx, out, t, noise.brown, 'lowpass', 260, 0.7, 0.5 * vel, dur, dur * 0.3);
  noiseBurst(ctx, out, t, noise.pink, 'bandpass', 900, 0.8, 0.08 * vel, dur, dur * 0.3);
}