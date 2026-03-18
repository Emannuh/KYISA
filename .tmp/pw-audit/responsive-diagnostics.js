const { chromium } = require('playwright');
const fs = require('fs');

const BASE = 'http://127.0.0.1:8000';
const routes = ['/', '/about/', '/leadership/', '/results/', '/contact/', '/portal/login/'];
const viewports = [
  { name: 'mobile-360', width: 360, height: 800 },
  { name: 'mobile-390', width: 390, height: 844 },
  { name: 'tablet-768', width: 768, height: 1024 },
  { name: 'laptop-1366', width: 1366, height: 768 },
  { name: 'desktop-1920', width: 1920, height: 1080 },
];

function selectorFor(el) {
  if (!el || !el.tagName) return '';
  const tag = el.tagName.toLowerCase();
  const id = el.id ? `#${el.id}` : '';
  const cls = (el.className && typeof el.className === 'string')
    ? '.' + el.className.trim().split(/\s+/).slice(0, 3).join('.')
    : '';
  return `${tag}${id}${cls}`;
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const out = [];

  for (const route of routes) {
    for (const vp of viewports) {
      const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
      const page = await context.newPage();
      const url = `${BASE}${route}`;

      try {
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForTimeout(900);

        const diagnostics = await page.evaluate(() => {
          const doc = document.documentElement;
          const body = document.body || doc;
          const scrollWidth = Math.max(doc.scrollWidth, body.scrollWidth);
          const clientWidth = doc.clientWidth;

          const overflowOffenders = [];
          for (const el of document.querySelectorAll('*')) {
            const r = el.getBoundingClientRect();
            if (r.right - clientWidth > 1) {
              overflowOffenders.push({
                selector: (() => {
                  const tag = el.tagName.toLowerCase();
                  const id = el.id ? `#${el.id}` : '';
                  const cls = (el.className && typeof el.className === 'string')
                    ? '.' + el.className.trim().split(/\s+/).slice(0, 3).join('.')
                    : '';
                  return `${tag}${id}${cls}`;
                })(),
                overflow: Number((r.right - clientWidth).toFixed(1)),
              });
              if (overflowOffenders.length >= 8) break;
            }
          }

          const tinyText = [];
          for (const el of document.querySelectorAll('p, span, li, a, button, label, small')) {
            const style = getComputedStyle(el);
            const size = parseFloat(style.fontSize || '0');
            if (size > 0 && size < 12) {
              const text = (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 80);
              tinyText.push({
                selector: (() => {
                  const tag = el.tagName.toLowerCase();
                  const id = el.id ? `#${el.id}` : '';
                  const cls = (el.className && typeof el.className === 'string')
                    ? '.' + el.className.trim().split(/\s+/).slice(0, 3).join('.')
                    : '';
                  return `${tag}${id}${cls}`;
                })(),
                size,
                text,
              });
              if (tinyText.length >= 15) break;
            }
          }

          return {
            overflowPx: scrollWidth - clientWidth,
            overflowOffenders,
            tinyText,
          };
        });

        out.push({ route, viewport: vp.name, ...diagnostics });
      } catch (e) {
        out.push({ route, viewport: vp.name, error: e.message });
      } finally {
        await context.close();
      }
    }
  }

  await browser.close();
  fs.writeFileSync('../responsive-multipage/diagnostics.json', JSON.stringify(out, null, 2));
  console.log('wrote ../responsive-multipage/diagnostics.json with', out.length, 'entries');
})();
