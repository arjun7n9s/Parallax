// Render the PARALLAX Canva diagrams (HTML -> PNG) at 3x for crisp embedding.
const puppeteer = require('puppeteer');
const path = require('path');

const files = ['pipeline', 'cortex', 'graph'];

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--font-render-hinting=none', '--force-color-profile=srgb'],
  });
  for (const name of files) {
    const page = await browser.newPage();
    await page.setViewport({ width: 1400, height: 900, deviceScaleFactor: 3 });
    const url = 'file:///' + path.resolve(__dirname, 'canva', name + '.html').replace(/\\/g, '/');
    await page.goto(url, { waitUntil: 'networkidle0' });
    await page.evaluate(() => document.fonts && document.fonts.ready);
    await new Promise((r) => setTimeout(r, 600));
    const el = await page.$('.diagram-container');
    const out = path.resolve(__dirname, 'canva', name + '.png');
    await el.screenshot({ path: out, omitBackground: false });
    console.log('wrote', out);
    await page.close();
  }
  await browser.close();
})();
