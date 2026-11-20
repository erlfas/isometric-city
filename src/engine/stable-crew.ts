import type { Citizen } from '../types';
import type { Building, BuildingIndex, Slot, Spot, Stall } from './building-anchors';
import type { Horses } from './horses';
import type { SimulationEngine } from './simulation';

/**
 * The stable's crew at work (stable plan M5). The citizens are moved to the stable by
 * generate_city_plan.py (STABLE_CREWS: stablemaster, 4 grooms, postilion, farrier, saddler, hay
 * boy) and drawn with char_groom (char_blacksmith for the farrier, char_tanner for the saddler;
 * kit.trades picks each one's look and loop).
 *
 * Who works where (Simulation.workFits): in the stable's buildings a spot naming a loop
 * (anchor_spot tag in build_assets.py) is taken only by the trades in LOOP_TRADES, and a
 * work slot indoors only by those in PROP_TRADES for its furniture. A stall's slot (brush) is
 * open only while its horse stands in the stall; the farrier's shoe spot only while a horse is
 * tied at his post. Everyone else in town is unaffected.
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

export class StableCrew {
  private sim: SimulationEngine;
  private horses: Horses;
  private site = new Set<Building>();
  /** A stall's work slot -> the horse stall it faces. */
  private slotStall = new Map<Slot, Stall>();
  private shoeSpots = new Set<Spot>();
  private farrierTie: Building | null = null;

  constructor(sim: SimulationEngine, buildings: BuildingIndex, horses: Horses) {
    this.sim = sim;
    this.horses = horses;
    for (const b of buildings.all) if (b.parcelId?.startsWith('p_stable_')) this.site.add(b);
    const stalls = [...this.site].flatMap((b) => b.stalls.filter((s) => s.tag === 'horse'));
    for (const b of this.site) {
      for (const s of b.interior?.slots ?? []) {
        if (s.prop !== 'stall') continue;
        let best: Stall | null = null, bd = 3.5;
        for (const st of stalls) {
          const d = Math.hypot(st.x - s.x, st.z - s.z);
          if (d < bd) { bd = d; best = st; }
        }
        if (best) this.slotStall.set(s, best);
      }
      for (const s of b.spots) if (s.anim === 'shoe') this.shoeSpots.add(s);
      if (b.name === 'farrier_forge') this.farrierTie = b;
    }
    if (this.site.size) sim.workFits = (c, b, s) => this.fits(c, b, s);
  }

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
    if (this.shoeSpots.has(s)) return this.tiedAtForge();
    return true;
  }

  private horseIn(st: Stall): boolean {
    return this.horses.horses.some((h) => h.stall === st && h.inStall && !h.held);
  }

  /** A horse tied at the farrier's post (stable M5 leading puts one there). */
  private tiedAtForge(): boolean {
    return !!this.farrierTie?.ties.some((t) => t.taken > 0);
  }

  stats() {
    return { buildings: this.site.size, stallSlots: this.slotStall.size, shoeSpots: this.shoeSpots.size,
      sim: this.sim.citizens.length };
  }
}
