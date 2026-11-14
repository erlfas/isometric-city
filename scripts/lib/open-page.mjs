// Shared by shoot.mjs / probe.mjs: open the dev server in headless Edge + GPU, wait for the
// scene, and collect page problems. `failed()` is true after any page exception or console
// error (a WebGL shader compile error is one) other than a missing favicon.
import { chromium } from 'playwright-core';

// `uncapped`: no vsync / frame-rate limit (perf.mjs), else light views all read the display's
// refresh rate (144) and a change can't be seen.
export async function openPage(url, hash, { width = 1600, height = 900, settleMs = 1000, uncapped = false } = {}) {
  const browser = await chromium.launch({
    channel: process.env.PLAYWRIGHT_CHANNEL || 'msedge', // installed Edge on Windows
    headless: true,
    args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist',
      ...(uncapped ? ['--disable-gpu-vsync', '--disable-frame-rate-limit'] : [])],
  });
  const page = await browser.newPage({ viewport: { width, height } });
  const problems = [];
  let errored = false;
  // Console 404 messages carry no URL; report them from the response instead.
  page.on('response', (r) => {
    if (r.status() < 400) return;
    const ignored = r.url().endsWith('/favicon.ico');
    problems.push(`[http ${r.status()}] ${r.url()}${ignored ? ' (ignored)' : ''}`);
    if (!ignored) errored = true;
  });
  page.on('console', (m) => {
    if (m.type() !== 'error' && m.type() !== 'warning') return;
    if (m.text().startsWith('Failed to load resource')) return; // reported by 'response'
    problems.push(`[${m.type()}] ${m.text()}`);
    if (m.type() === 'error') errored = true;
  });
  page.on('pageerror', (e) => { problems.push(`[pageerror] ${e.message}`); errored = true; });

  await page.goto(`${url}#${hash}`);
  await page.waitForFunction(() => window.__lublin?.ready === true, null, { timeout: 120000 });
  await page.waitForTimeout(settleMs);
  return { browser, page, problems, failed: () => errored };
}
