import type { Citizen } from '../types';

/** What people say (speech bubbles): greetings between acquaintances, sellers' cries. */

const pick = <T>(a: readonly T[]) => a[Math.floor(Math.random() * a.length)];
const first = (c: Citizen) => c.name.split(' ')[0];

const GREET = ['God give you good day, {n}!', 'Well met, {n}!', 'Praised be Jesus Christ, {n}.', '{n}! How fares your house?'];
const TOPICS: Record<string, readonly string[]> = {
  SHOPPING: ['The rye is dear this week.', 'Fresh loaves still warm!'],
  FETCHING: ['The well line was long today.', 'Mind the bucket, it is full.'],
  PRAYING: ['Are you for vespers?', 'The friars sing well tonight.'],
  DRINKING: ['A mug at the brewer\'s?', 'The new ale is good.'],
  SOCIALIZING: ['Have you seen the Hungarian wine?', 'Such crowds for the fair!', 'Flemish cloth at the Szmatruz!'],
  WORKING: ['Back to the bench.', 'Too much work, too few hands.'],
  ERRAND: ['Master sent me running!', 'Can\'t stop, the master waits!'],
  RESTING: ['Home before the curfew bell.', 'A long day.'],
  EATING: ['Hungry? There is pie by the hall.', 'Smoked herring, at last.'],
};
const SAME_TRADE = ['How goes the guild, {t}?', 'Is the master pleased with your work?', 'The guild meets after nones.'];

export function talkLine(a: Citizen, b: Citizen): string {
  const r = Math.random();
  if (r < 0.4) return pick(GREET).replace('{n}', first(b));
  if (a.trade === b.trade && r < 0.6) return pick(SAME_TRADE).replace('{t}', first(b));
  return pick(TOPICS[a.state ?? ''] ?? TOPICS.SOCIALIZING);
}

const WARES: Record<string, readonly string[]> = {
  'Amber & Salt Merchant': ['Rock salt from Wieliczka!', 'Baltic amber, fine and clear!'],
  'Hanseatic Merchant': ['Flemish broadcloth here!', 'Wool from Bruges and Ghent!'],
  'Royal Factor': ['By the King\'s leave - silver and books!'],
  'Ruthenian Fur Merchant': ['Sable and marten from Rus\'!', 'Wax, dark and pure!'],
  'Hungarian Wine Merchant': ['Tokaj wine fresh from Hungary!'],
  Baker: ['Rye bread, fresh from the oven!', 'Pretzels! Warm pretzels!'],
  Butcher: ['Pork for the roast!', 'Sausages, smoked today!'],
  Potter: ['Jugs and bowls, sound and glazed!'],
  Shoemaker: ['Boots for the road!'],
  Weaver: ['Linen by the ell!'],
  Brewer: ['Small beer for a halfpenny!'],
  Candlemaker: ['Tallow candles, long-burning!'],
  Cooper: ['Casks and buckets, tight as a drum!'],
};
const GENERIC = ['Good wares, fair prices!', 'Come, look, no harm in looking!', 'Praise King Jagiełło for this fair!'];

export function barkLine(c: Citizen): string {
  return pick(WARES[c.trade] ?? GENERIC);
}
