const { test } = require('playwright/test');

const URL = 'http://127.0.0.1:8000/';
const viewports = [
  { name: '360x800', width: 360, height: 800 },
  { name: '390x844', width: 390, height: 844 },
  { name: '768x1024', width: 768, height: 1024 },
  { name: '1366x768', width: 1366, height: 768 },
  { name: '1920x1080', width: 1920, height: 1080 },
];

for (const vp of viewports) {
  test(`responsive metrics ${vp.name}`, async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
    const page = await context.newPage();
    await page.goto(URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    const m = await page.evaluate(() => {
      const doc = document.documentElement;
      const body = document.body || doc;
      const scrollWidth = Math.max(doc.scrollWidth, body.scrollWidth);
      const clientWidth = doc.clientWidth;
      const overflow = scrollWidth - clientWidth;

      const offenders = [];
      for (const el of document.querySelectorAll('*')) {
        const r = el.getBoundingClientRect();
        if (r.right - clientWidth > 1) {
          offenders.push({
            tag: el.tagName,
            className: String(el.className || '').slice(0, 60),
            overflow: Number((r.right - clientWidth).toFixed(1)),
          });
          if (offenders.length >= 5) break;
        }
      }
      return { title: document.title, clientWidth, scrollWidth, overflow, offenders };
    });

    console.log(`RESPONSIVE ${vp.name} http=ok title="${m.title}" client=${m.clientWidth} scroll=${m.scrollWidth} overflow=${m.overflow}`);
    if (m.offenders.length) {
      for (const o of m.offenders) {
        console.log(`OFFENDER ${vp.name} ${o.tag} class="${o.className}" overflow=${o.overflow}`);
      }
    }

    await context.close();
  });
}
