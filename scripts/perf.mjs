// Frame rate and draw calls of the running dev server, for before/after comparisons.
//
// usage: node scripts/perf.mjs [hash ...] [--url http://localhost:5173/] [--secs 4]
//   node scripts/perf.mjs "pause&hour=11" "cam=0,0,200&pause&hour=11"
// Default views: start view, Rynek close-up, whole city. Headless fps is relative only:
// compare two runs on the same machine. To measure another commit, serve it from a worktree:
//   git worktree add --detach <dir> <ref>; link node_modules; npm run dev -- --port 5174
// Exit code 1 if the page logged an error (see lib/open-page.mjs).
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
const secs = Number(opt('--secs', '4'));
const views = args.length ? args : ['pause&hour=11', 'cam=0,0,40&pause&hour=11', 'cam=60,0,260&pause&hour=11'];

let failed = false;
for (const hash of views) {
  const run = await openPage(url, hash);
  const out = await run.page.evaluate((ms) => new Promise((done) => {
    let frames = 0;
    const t0 = performance.now();
    const tick = () => {
      frames++;
      const dt = performance.now() - t0;
      if (dt < ms) return requestAnimationFrame(tick);
      const { calls, triangles } = window.__lublin.renderer.renderer.info.render;
      done({ fps: +(frames * 1000 / dt).toFixed(1), calls, triangles });
    };
    requestAnimationFrame(tick);
  }), secs * 1000);
  await run.browser.close();
  console.log(`${hash.padEnd(32)} fps ${String(out.fps).padStart(6)}  calls ${String(out.calls).padStart(5)}  tris ${out.triangles}`);
  for (const p of run.problems) console.error(`  ${p}`);
  failed ||= run.failed();
}
process.exit(failed ? 1 : 0);
