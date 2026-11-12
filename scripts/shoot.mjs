// Screenshot the running dev server (npm run dev) with headless Edge + GPU.
//
// usage: node scripts/shoot.mjs <out.png> [hash] [--url http://localhost:5173/] [--size 1600x900]
//   hash examples (see src/debug-hooks.ts):
//     "model=house_half_timber,0,14"     first half-timber house, 14 world units visible
//     "cam=0,0,24,2&pause&hour=12"       Rynek, NE quadrant, paused at noon
// Prints browser console errors/warnings; exit code 1 if the page logged an error.
import { chromium } from 'playwright-core';

const args = process.argv.slice(2);
const opt = (name, dflt) => {
  const i = args.indexOf(name);
  if (i < 0) return dflt;
  const v = args[i + 1];
  args.splice(i, 2);
  return v;
};
const url = opt('--url', 'http://localhost:5173/');
const [w, h] = opt('--size', '1600x900').split('x').map(Number);
const [outFile, hash = 'pause'] = args;
if (!outFile) {
  console.error('usage: node scripts/shoot.mjs <out.png> [hash] [--url URL] [--size WxH]');
  process.exit(2);
}

const browser = await chromium.launch({
  channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge', // installed Edge on Windows
  headless: true,
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'],
});
const page = await browser.newPage({ viewport: { width: w, height: h } });
const problems = [];
let errored = false;
page.on('console', (m) => {
  if (m.type() === 'error' || m.type() === 'warning') problems.push(`[${m.type()}] ${m.text()}`);
  // Resource 404s (e.g. favicon) are reported but don't fail the run.
  if (m.type() === 'error' && !m.text().startsWith('Failed to load resource')) errored = true;
});
page.on('pageerror', (e) => { problems.push(`[pageerror] ${e.message}`); errored = true; });

await page.goto(`${url}#${hash}`);
await page.waitForFunction(() => window.__lublin?.ready === true, null, { timeout: 120000 });
await page.waitForTimeout(1500); // shadows / texture uploads settle
await page.screenshot({ path: outFile });
await browser.close();

for (const p of problems) console.log(p);
console.log(`saved ${outFile}`);
process.exit(errored ? 1 : 0);
