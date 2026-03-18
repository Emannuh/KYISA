const { chromium } = require('playwright');

const BASE = 'http://127.0.0.1:8000';
const routes = ['/', '/about/', '/leadership/', '/results/', '/contact/'];
const viewports = [
  { name: 'mobile-390', width: 390, height: 844 },
  { name: 'desktop-1366', width: 1366, height: 768 },
];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const all = [];
  for (const route of routes) {
    for (const vp of viewports) {
      const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
      const page = await context.newPage();
      await page.goto(BASE + route, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForTimeout(800);
      const rows = await page.evaluate(() => {
        const out = [];
        const els = document.querySelectorAll('p, span, li, a, button, label, small');
        for (const el of els) {
          const size = parseFloat(getComputedStyle(el).fontSize || '0');
          if (size > 0 && size < 12) {
            const cls = typeof el.className === 'string' ? el.className.trim().split(/\s+/).slice(0,3).join('.') : '';
            const sel = `${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''}${cls ? '.' + cls : ''}`;
            out.push({ sel, size: Number(size.toFixed(2)), text: (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40) });
          }
        }
        return out;
      });
      all.push({ route, viewport: vp.name, rows });
      await context.close();
    }
  }
  await browser.close();

  const freq = new Map();
  for (const page of all) {
    for (const r of page.rows) {
      const key = `${r.sel} | ${r.size}`;
      freq.set(key, (freq.get(key) || 0) + 1);
    }
  }
  const top = [...freq.entries()].sort((a,b) => b[1]-a[1]).slice(0,40);
  console.log('TOP_TINY_SELECTORS');
  for (const [k,v] of top) console.log(v.toString().padStart(3), k);
})();
