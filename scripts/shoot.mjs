// Screenshot the running dev server (npm run dev) with headless Edge + GPU.
//
// usage: node scripts/shoot.mjs <out.png> [hash] [--url http://localhost:5173/] [--size 1600x900]
//   hash examples (see src/debug-hooks.ts):
//     "model=house_half_timber,0,14"     first half-timber house, 14 world units visible
//     "cam=0,0,24,2&pause&hour=12"       Rynek, NE quadrant, paused at noon
//     "hour=6.95&follow=walk,16" --wait 8000   camera on someone walking to work
// Prints page errors and warnings; exit code 1 if the page logged an error.
import { openPage } from './lib/open-page.mjs';

const args = process.argv.slice(2);
const opt = (name, dflt) => {
  const i = args.indexOf(name);
  if (i < 0) return dflt;
  const v = args[i + 1];
  args.splice(i, 2);
  return v;
};
const url = opt('--url', 'http://localhost:5173/');
const [width, height] = opt('--size', '1600x900').split('x').map(Number);
// --wait: ms of running frames after the scene is ready (default 1.5 s: shadows and texture
// uploads settle). Longer lets the simulation play, e.g. from &hour=6.95 into the commute.
const settleMs = Number(opt('--wait', '1500'));
const [outFile, hash = 'pause'] = args;
if (!outFile) {
  console.error('usage: node scripts/shoot.mjs <out.png> [hash] [--url URL] [--size WxH] [--wait ms]');
  process.exit(2);
}

const { browser, page, problems, failed } = await openPage(url, hash, { width, height, settleMs });
await page.screenshot({ path: outFile });
await browser.close();

for (const p of problems) console.log(p);
console.log(`saved ${outFile}`);
process.exit(failed() ? 1 : 0);
