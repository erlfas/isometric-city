// Navigation check: draws the walkable grid with doors and spots, and routes between many
// door pairs to report failures and A* cost. Needs `npm run dev` running.
//
// usage: node scripts/nav_check.mjs [out.png] [x0,z0,x1,z1] [--pairs 400] [--url http://localhost:5173/]
//   out.png   map image, 2 px per 0.5 m cell inside the crop (default: whole map, 1 px per cell)
//             white = walkable, dark = blocked, green = door approach, orange = door,
//             blue = work spot, magenta = sample routes
// Prints: grid size, build ms, sealed interior cells, route pairs tried / failed, expansions
// and ms per route (mean, max). Exit code 1 if more than 2% of door pairs fail.
import { writeFileSync } from 'node:fs';
import { openPage } from './lib/open-page.mjs';

const args = process.argv.slice(2);
const opt = (name, def) => {
  const i = args.indexOf(name);
  return i >= 0 ? args.splice(i, 2)[1] : def;
};
const url = opt('--url', 'http://localhost:5173/');
const pairs = Number(opt('--pairs', '400'));
const [out = 'nav_map.png', crop = ''] = args;

const { browser, page, problems } = await openPage(url, 'pause');
const res = await page.evaluate(({ crop, pairs }) => {
  const sim = window.__lublin.sim;
  const nav = sim.nav;
  const doors = sim.buildings.all.flatMap((b) => b.doors.map((d) => ({ b: b.name, d })));
  // Deterministic sample of door pairs.
  let seed = 12345;
  const rnd = () => ((seed = (seed * 1103515245 + 12345) >>> 0) / 4294967296);
  const results = [];
  const fails = [];
  const drawRoutes = [];
  for (let k = 0; k < pairs; k++) {
    const A = doors[Math.floor(rnd() * doors.length)], B = doors[Math.floor(rnd() * doors.length)];
    // The simulation has already moved off-grid approaches onto the nearest reachable cell.
    const a = nav.nearestFree(A.d.ax, A.d.az, 6), b = nav.nearestFree(B.d.ax, B.d.az, 6);
    if (a < 0 || b < 0) { fails.push({ why: a < 0 ? 'start' : 'goal', from: A.b, to: B.b, at: a < 0 ? [A.d.ax, A.d.az] : [B.d.ax, B.d.az] }); continue; }
    const t0 = performance.now();
    const r = nav.route(a, b);
    const ms = performance.now() - t0;
    if (!r) { fails.push({ why: 'route', from: A.b, to: B.b, a: [A.d.ax, A.d.az], b: [B.d.ax, B.d.az] }); continue; }
    results.push({ ms, exp: r.expanded, len: r.length });
    if (drawRoutes.length < 40) drawRoutes.push(Array.from(r.pts));
  }
  // Map image.
  const [x0, z0, x1, z1] = crop ? crop.split(',').map(Number) : [nav.minX, nav.minZ, nav.minX + nav.w * 0.5, nav.minZ + nav.h * 0.5];
  const scale = crop ? 4 : 2; // px per metre
  const W = Math.round((x1 - x0) * scale), H = Math.round((z1 - z0) * scale);
  const cv = new OffscreenCanvas(W, H);
  const g = cv.getContext('2d');
  const img = g.createImageData(W, H);
  for (let py = 0; py < H; py++) for (let px = 0; px < W; px++) {
    const x = x0 + (px + 0.5) / scale, z = z0 + (py + 0.5) / scale;
    const i = nav.cellOf(x, z);
    const o = (py * W + px) * 4;
    let v = 40;
    if (i >= 0 && !nav.blocked[i]) v = 150 + nav.dist[i] * 17;
    img.data[o] = img.data[o + 1] = img.data[o + 2] = v; img.data[o + 3] = 255;
  }
  g.putImageData(img, 0, 0);
  const P = (x, z) => [(x - x0) * scale, (z - z0) * scale];
  g.strokeStyle = 'rgba(220,0,200,0.8)'; g.lineWidth = 1.5;
  for (const r of drawRoutes) {
    g.beginPath();
    for (let k = 0; k < r.length; k += 2) { const [px, py] = P(r[k], r[k + 1]); k ? g.lineTo(px, py) : g.moveTo(px, py); }
    g.stroke();
  }
  const dot = (x, z, c, s) => { const [px, py] = P(x, z); g.fillStyle = c; g.fillRect(px - s / 2, py - s / 2, s, s); };
  for (const { d } of doors) { dot(d.x, d.z, '#f80', 3 + scale / 2); dot(d.ax, d.az, '#0c0', 3 + scale / 2); }
  for (const b of sim.buildings.all) for (const s of b.spots) dot(s.x, s.z, '#06f', 2 + scale / 2);
  return cv.convertToBlob({ type: 'image/png' }).then(async (blob) => {
    const buf = new Uint8Array(await blob.arrayBuffer());
    let bin = '';
    for (let k = 0; k < buf.length; k += 0x8000) bin += String.fromCharCode(...buf.subarray(k, k + 0x8000));
    const ms = results.map((r) => r.ms), exp = results.map((r) => r.exp);
    const mean = (a) => a.reduce((s, v) => s + v, 0) / Math.max(1, a.length);
    return {
      png: btoa(bin),
      grid: `${nav.w}x${nav.h}`, buildMs: Math.round(nav.buildMs), sealedCells: nav.enclosedCells,
      components: nav.components, graph: `${nav.graphNodes} nodes / ${nav.graphEdges} edges`, gridFallbacks: nav.gridFallbacks, offGridDoors: sim.navStats().offGridDoors,
      doors: doors.length, tried: pairs, failed: fails.length, failures: fails.slice(0, 12),
      msMean: +mean(ms).toFixed(2), msMax: +Math.max(0, ...ms).toFixed(2),
      expandedMean: Math.round(mean(exp)), expandedMax: Math.max(0, ...exp), lengthMean: Math.round(mean(results.map((r) => r.len))),
    };
  });
}, { crop, pairs });
await browser.close();
writeFileSync(out, Buffer.from(res.png, 'base64'));
delete res.png;
console.log(JSON.stringify(res, null, 1));
for (const p of problems) console.error(p);
process.exit(res.failed > pairs * 0.02 ? 1 : 0);
