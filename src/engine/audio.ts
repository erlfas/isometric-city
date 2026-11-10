/**
 * Web Audio API Procedural Synthesizer for Lublin 1392
 * - Physically-modeled medieval church bells (non-harmonic additive partials)
 * - Dynamic medieval ambient soundscapes (market murmurs, blacksmith anvils, night breeze)
 */

export class ProceduralAudioEngine {
  private ctx: AudioContext | null = null;
  private masterGain: GainNode | null = null;
  public isMuted: boolean = false;
  private isInitialized: boolean = false;

  private ambientInterval: number | null = null;

  public init(): void {
    if (this.isInitialized) return;
    try {
      const AudioCtxClass = window.AudioContext || (window as any).webkitAudioContext;
      this.ctx = new AudioCtxClass();
      this.masterGain = this.ctx.createGain();
      this.masterGain.gain.setValueAtTime(0.45, this.ctx.currentTime);
      this.masterGain.connect(this.ctx.destination);
      this.isInitialized = true;
      this.startAmbientLoop();
      console.log('[ProceduralAudio] Web Audio context initialized.');
    } catch (e) {
      console.warn('[ProceduralAudio] Web Audio API failed to initialize:', e);
    }
  }

  public resume(): void {
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  public toggleMute(): boolean {
    this.isMuted = !this.isMuted;
    if (this.masterGain && this.ctx) {
      this.masterGain.gain.setValueAtTime(this.isMuted ? 0.0 : 0.45, this.ctx.currentTime);
    }
    return this.isMuted;
  }

  /**
   * Physically modeled medieval church bell:
   * Uses additive synthesis of the 5 canonical bell partials:
   * Hum (0.5x), Prime (1.0x), Tierce (1.19x), Quint (1.5x), Nominal (2.0x), Supernominal (3.0x).
   */
  public tollBell(baseFreq: number = 220.0, strikes: number = 3): void {
    if (!this.ctx || !this.masterGain || this.isMuted) return;
    this.resume();

    const partials = [
      { mult: 0.5, gain: 0.7, decay: 4.8 },   // Hum note
      { mult: 1.0, gain: 0.9, decay: 3.5 },   // Prime
      { mult: 1.19, gain: 0.75, decay: 2.8 }, // Tierce (minor 3rd)
      { mult: 1.5, gain: 0.6, decay: 2.2 },   // Quint (fifth)
      { mult: 2.0, gain: 0.5, decay: 1.8 },   // Nominal
      { mult: 3.0, gain: 0.35, decay: 1.2 },  // Supernominal
      { mult: 4.2, gain: 0.2, decay: 0.6 }    // Clapper strike clang
    ];

    for (let s = 0; s < strikes; s++) {
      const strikeTime = this.ctx.currentTime + s * 1.6;

      for (let i = 0; i < partials.length; i++) {
        const p = partials[i];
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        // Slight inharmonic detuning typical of medieval cast bronze
        const detuneJitter = 1.0 + (Math.random() - 0.5) * 0.008;
        osc.type = i === 0 ? 'sine' : (i < 4 ? 'sine' : 'triangle');
        osc.frequency.setValueAtTime(baseFreq * p.mult * detuneJitter, strikeTime);

        // Exponential decay envelope
        gain.gain.setValueAtTime(0.001, strikeTime);
        gain.gain.exponentialRampToValueAtTime(p.gain * 0.5, strikeTime + 0.015);
        gain.gain.exponentialRampToValueAtTime(0.0001, strikeTime + p.decay);

        osc.connect(gain);
        gain.connect(this.masterGain);

        osc.start(strikeTime);
        osc.stop(strikeTime + p.decay + 0.1);
      }
    }
  }

  /**
   * Sound of blacksmith hammer striking an anvil in the artisan quarter.
   */
  public playBlacksmithAnvil(): void {
    if (!this.ctx || !this.masterGain || this.isMuted) return;
    const now = this.ctx.currentTime;

    // High pitched metallic chime (880 Hz + 1760 Hz)
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(880 + Math.random() * 80, now);
    osc.frequency.exponentialRampToValueAtTime(600, now + 0.15);

    gain.gain.setValueAtTime(0.001, now);
    gain.gain.linearRampToValueAtTime(0.18, now + 0.005);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.35);

    osc.connect(gain);
    gain.connect(this.masterGain);
    osc.start(now);
    osc.stop(now + 0.4);
  }

  private startAmbientLoop(): void {
    // Occasional artisan sounds (anvil, wood sawing)
    if (this.ambientInterval) clearInterval(this.ambientInterval);

    this.ambientInterval = window.setInterval(() => {
      if (Math.random() < 0.45 && !this.isMuted) {
        this.playBlacksmithAnvil();
      }
    }, 4500);
  }

  public dispose(): void {
    if (this.ambientInterval) {
      clearInterval(this.ambientInterval);
      this.ambientInterval = null;
    }
    if (this.ctx) {
      this.ctx.close();
      this.ctx = null;
    }
  }
}
