import type { Parcel } from '../types';

/** Which building a parcel is drawn as. The renderer maps each kind to a model template
 *  (populateCityScene); the soundscape maps it to a sound (audio.ts soundOf). Order matters:
 *  the first matching branch wins, craft before building type. */
export type ParcelKind =
  | 'shed' | 'baker' | 'tanner' | 'brewer' | 'smith' | 'potter' | 'weaver'
  | 'watermill' | 'windmill' | 'quarry' | 'logging' | 'harbor'
  | 'brick' | 'half_timber' | 'log'
  | 'district'; // no rule matched: the renderer picks by district and hash

/** Stable per-parcel hash (drives fallbacks and per-instance variation). */
export function parcelHash(p: Parcel, index: number): number {
  const str = p.id || `parcel_${index}`;
  let hash = 0;
  for (let k = 0; k < str.length; k++) {
    hash = (hash << 5) - hash + str.charCodeAt(k);
    hash |= 0;
  }
  return Math.abs(hash);
}

export function parcelKind(p: Parcel, hash: number): ParcelKind {
  const craft = p.craft?.id ?? '';
  const t = p.buildingType || '';
  const has = (...parts: string[]) => parts.some((s) => t.includes(s));
  const is = (...crafts: string[]) => crafts.includes(craft);

  if (p.isShed || t.startsWith('shed_')) return 'shed';
  if (is('baker') || has('baker')) return 'baker';
  if (is('tanner') || has('tanner')) return 'tanner';
  if (is('brewer') || has('brewer')) return 'brewer';
  if (is('blacksmith', 'armorer') || has('blacksmith')) return 'smith';
  if (is('potter') || has('potter')) return 'potter';
  if (is('weaver', 'tailor') || has('weaver')) return 'weaver';
  if (has('watermill')) return 'watermill';
  if (has('windmill')) return 'windmill';
  if (has('quarry') || is('mason')) return 'quarry';
  if (has('sawmill', 'logging') || (is('carpenter') && p.district === 'krakow_suburb' && hash % 4 === 0)) return 'logging';
  if (has('harbor')) return 'harbor';
  if (has('patrician', 'kamienica', 'brick', 'stone_arches') || is('goldsmith')) return 'brick';
  if (has('fachwerk', 'half_timber', 'jettied', 'narrow_gable', 'furrier', 'shoemaker')
    || is('shoemaker', 'furrier', 'candlemaker', 'roper', 'butcher')) return 'half_timber';
  if (has('log', 'timber', 'thatched', 'cruck', 'longhouse', 'cottage', 'loess', 'cooper')
    || is('cooper', 'wheelwright', 'carpenter')) return 'log';
  return 'district';
}
