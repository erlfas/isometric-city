// Evaluate a JS expression in the running dev server (npm run dev) and print it as JSON.
//
// usage: node scripts/probe.mjs [hash] [expression] [--url http://localhost:5173/]
//   node scripts/probe.mjs "cam=0,0,40,0&pause&hour=11" "__lublin.stats()"
//   node scripts/probe.mjs pause "__lublin.find('house_baker').length"
// The expression runs after the scene is ready and one more second of frames.
// Window globals: see src/debug-hooks.ts (window.__lublin).
import { chromium } from 'playwright-core';

const args = process.argv.slice(2);
const ui = args.indexOf('--url');
const url = ui >= 0 ? args.splice(ui, 2)[1] : 'http://localhost:5173/';
const [hash = 'pause', expr = '__lublin.stats()'] = args;

const browser = await chromium.launch({
  channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge',
  headless: true,
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'],
});
const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
page.on('pageerror', (e) => console.error(`[pageerror] ${e.message}`));
await page.goto(`${url}#${hash}`);
await page.waitForFunction(() => window.__lublin?.ready === true, null, { timeout: 120000 });
await page.waitForTimeout(1000);
const out = await page.evaluate((e) => (0, eval)(e), expr);
console.log(JSON.stringify(out, null, 1));
await browser.close();
