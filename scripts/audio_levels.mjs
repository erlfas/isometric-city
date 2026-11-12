// Measure the soundscape headless: RMS and peak per audio bus in preset scenes.
// The only way to check the mix without ears: compare buses against each other and the music.
//
// usage: node scripts/audio_levels.mjs [scene ...] [--url http://localhost:5173/]
//   scenes: market forge cooper saw loom water bells herald night (default: all)
// Needs `npm run dev`. Bus names and debugState(): src/engine/audio.ts.
// Rough targets: music -23..-27 dB, a workshop you are zoomed onto -30..-40, crowd at the
// market about -40, bells above the ducked music.
import { chromium } from 'playwright-core';

const args = process.argv.slice(2);
const ui = args.indexOf('--url');
const url = ui >= 0 ? args.splice(ui, 2)[1] : 'http://localhost:5173/';
const BUSES = ['musicBus', 'sfx', 'ambience', 'crowdBus', 'reverbSend'];

// [setup run in the page, seconds to measure]; `emitter(kind)` snaps to the first emitter of a kind
const SCENES = {
  market: ['__lublin.sim.setTime(10); __lublin.snapTo(0, 0, 25)', 5],
  forge: ['emitter("forge")', 6],
  cooper: ['emitter("cooper")', 6],
  saw: ['emitter("saw")', 6],
  loom: ['emitter("loom")', 6],
  water: ['const w = __lublin.audio.water[0]; __lublin.snapTo(w.x, w.z, 15)', 4],
  bells: ['__lublin.snapTo(0, 0, 40); __lublin.audio.tollHour(9)', 8],
  herald: ['__lublin.snapTo(0, 0, 30); __lublin.audio.herald()', 4],
  night: ['__lublin.sim.setTime(23); __lublin.snapTo(-60, -140, 30)', 6],
};
const chosen = args.length ? args : Object.keys(SCENES);

const browser = await chromium.launch({
  channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge',
  headless: true,
  args: ['--autoplay-policy=no-user-gesture-required', '--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'],
});
const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
page.on('pageerror', (e) => console.error(`[pageerror] ${e.message}`));
await page.goto(`${url}#cam=0,0,25&hour=10`);
await page.waitForFunction(() => window.__lublin?.ready === true, null, { timeout: 120000 });

await page.evaluate((buses) => {
  const a = window.__lublin.audio;
  a.init();
  const meters = buses.map((name) => {
    const an = a.ctx.createAnalyser();
    an.fftSize = 2048;
    a[name].connect(an);
    return { name, an, sum: 0, n: 0, peak: 0 };
  });
  const buf = new Float32Array(2048);
  setInterval(() => {
    for (const m of meters) {
      m.an.getFloatTimeDomainData(buf);
      let s = 0;
      for (const v of buf) { s += v * v; m.peak = Math.max(m.peak, Math.abs(v)); }
      m.sum += s / buf.length; m.n++;
    }
  }, 50);
  window.__levels = {
    reset: () => meters.forEach((m) => { m.sum = 0; m.n = 0; m.peak = 0; }),
    read: () => Object.fromEntries(meters.map((m) =>
      [m.name, `${(10 * Math.log10(m.sum / Math.max(1, m.n) + 1e-12)).toFixed(1)} dB (peak ${m.peak.toFixed(2)})`])),
  };
  window.emitter = (kind) => {
    const e = a.emitters.find((x) => x.kind === kind);
    __lublin.sim.setTime(10);
    __lublin.snapTo(e.x, e.z, 12);
  };
}, BUSES);

for (const name of chosen) {
  const scene = SCENES[name];
  if (!scene) { console.error(`unknown scene "${name}"; known: ${Object.keys(SCENES).join(' ')}`); continue; }
  const [setup, seconds] = scene;
  await page.evaluate(setup);
  await page.waitForTimeout(500);
  await page.evaluate(() => window.__levels.reset());
  await page.waitForTimeout(seconds * 1000);
  const r = await page.evaluate(() => ({ levels: window.__levels.read(), state: window.__lublin.audio.debugState() }));
  console.log(`\n== ${name}  (crowd ${r.state.crowd}, audible workshops: ${r.state.activeEmitters.join(' ') || '-'})`);
  for (const [bus, v] of Object.entries(r.levels)) console.log(`  ${bus.padEnd(11)} ${v}`);
}
await browser.close();
