const { chromium } = require('playwright');
const fs = require('fs');

const BASE = 'http://127.0.0.1:8000';
const routes = [
  '/',
  '/about/',
  '/leadership/',
  '/results/',
  '/contact/',
  '/portal/login/'
];

const viewports = [
  { name: 'mobile-360', width: 360, height: 800 },
  { name: 'mobile-390', width: 390, height: 844 },
  { name: 'tablet-768', width: 768, height: 1024 },
  { name: 'laptop-1366', width: 1366, height: 768 },
  { name: 'desktop-1920', width: 1920, height: 1080 },
];

const outDir = '../responsive-multipage';
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const results = [];

  for (const route of routes) {
    for (const vp of viewports) {
      const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
      const page = await context.newPage();
      const url = `${BASE}${route}`;

      try {
        const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForTimeout(1200);

        const metrics = await page.evaluate(() => {
          const doc = document.documentElement;
          const body = document.body || doc;
          const scrollWidth = Math.max(doc.scrollWidth, body.scrollWidth);
          const clientWidth = doc.clientWidth;
          const overflowPx = scrollWidth - clientWidth;

          const offenders = [];
          for (const el of document.querySelectorAll('*')) {
            const r = el.getBoundingClientRect();
            if (r.right - clientWidth > 1) {
              offenders.push({
                tag: el.tagName,
                className: String(el.className || '').slice(0, 80),
                overflow: Number((r.right - clientWidth).toFixed(1)),
              });
              if (offenders.length >= 6) break;
            }
          }

          const tinyText = Array.from(document.querySelectorAll('p, span, li, a, button, label'))
            .map(el => parseFloat(getComputedStyle(el).fontSize || '0'))
            .filter(v => v > 0 && v < 12).length;

          return {
            title: document.title,
            clientWidth,
            scrollWidth,
            overflowPx,
            offenderCount: offenders.length,
            offenders,
            tinyTextCount: tinyText,
          };
        });

        const safeRoute = route === '/' ? 'home' : route.replace(/^\//, '').replace(/\/$/, '').replace(/[\/]/g, '_');
        await page.screenshot({ path: `${outDir}/${safeRoute}__${vp.name}.png`, fullPage: true });

        results.push({
          route,
          viewport: vp.name,
          url,
          status: response ? response.status() : null,
          ...metrics,
        });
      } catch (e) {
        results.push({ route, viewport: vp.name, url, error: e.message });
      } finally {
        await context.close();
      }
    }
  }

  await browser.close();
  fs.writeFileSync(`${outDir}/report.json`, JSON.stringify(results, null, 2));

  const byRoute = {};
  for (const r of results) {
    if (!byRoute[r.route]) byRoute[r.route] = [];
    byRoute[r.route].push(r);
  }

  for (const [route, rows] of Object.entries(byRoute)) {
    console.log(`ROUTE ${route}`);
    for (const r of rows) {
      if (r.error) {
        console.log(`  ${r.viewport}: ERROR ${r.error}`);
      } else {
        const flags = [];
        if (r.overflowPx > 0) flags.push(`overflow ${r.overflowPx}px`);
        if (r.offenderCount > 0) flags.push(`offenders ${r.offenderCount}`);
        if (r.tinyTextCount > 0) flags.push(`tinyText ${r.tinyTextCount}`);
        console.log(`  ${r.viewport}: HTTP ${r.status}, ${flags.length ? flags.join(', ') : 'ok'}`);
      }
    }
  }
})();
