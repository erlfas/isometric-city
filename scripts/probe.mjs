// Evaluate a JS expression in the running dev server (npm run dev) and print it as JSON.
//
// usage: node scripts/probe.mjs [hash] [expression] [--url http://localhost:5173/]
//   node scripts/probe.mjs "cam=0,0,40,0&pause&hour=11" "__lublin.stats()"
//   node scripts/probe.mjs pause "__lublin.find('house_baker').length"
// The expression runs after the scene is ready and one more second of frames.
// Window globals: see src/debug-hooks.ts (window.__lublin).
// Prints page errors to stderr; exit code 1 if the page logged one (e.g. a shader failed to
// compile), because the numbers are then not of the scene you meant to measure.
import { openPage } from './lib/open-page.mjs';

const args = process.argv.slice(2);
const ui = args.indexOf('--url');
const url = ui >= 0 ? args.splice(ui, 2)[1] : 'http://localhost:5173/';
const [hash = 'pause', expr = '__lublin.stats()'] = args;

const { browser, page, problems, failed } = await openPage(url, hash);
const out = await page.evaluate((e) => (0, eval)(e), expr);
await browser.close();

console.log(JSON.stringify(out, null, 1));
for (const p of problems) console.error(p);
process.exit(failed() ? 1 : 0);
