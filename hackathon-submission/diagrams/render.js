// Render HTML diagrams to PNG screenshots using puppeteer
const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const HTML_FILES = [
  'diag1_pipeline.html',
  'diag2_cortex.html',
  'diag3_sandbox.html',
  'diag4_scoring.html',
];

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--font-render-hinting=none'],
  });

  try {
    for (const file of HTML_FILES) {
      const htmlPath = path.resolve(file);
      const pngPath = path.resolve(file.replace(/\.html$/, '.png'));

      if (!fs.existsSync(htmlPath)) {
        console.error(`[SKIP] Missing HTML file: ${htmlPath}`);
        continue;
      }

      const page = await browser.newPage();
      await page.setViewport({ width: 1400, height: 900, deviceScaleFactor: 2 });

      const fileUrl = 'file:///' + htmlPath.replace(/\\/g, '/');
      await page.goto(fileUrl, { waitUntil: 'networkidle0', timeout: 60000 });

      // Wait for Google Fonts (and any other webfonts) to fully load
      await page.evaluate(async () => {
        if (document.fonts && document.fonts.ready) {
          await document.fonts.ready;
        }
      });

      // Extra delay for rendering stability
      await new Promise(r => setTimeout(r, 500));

      const element = await page.$('.diagram-container');
      if (!element) {
        console.error(`[FAIL] .diagram-container not found in ${file}`);
        await page.close();
        continue;
      }

      await element.screenshot({ path: pngPath, omitBackground: false });
      const stat = fs.statSync(pngPath);
      console.log(`[OK] ${file} -> ${path.basename(pngPath)} (${stat.size} bytes)`);

      await page.close();
    }
  } finally {
    await browser.close();
  }
})().catch(err => {
  console.error('FATAL:', err);
  process.exit(1);
});
