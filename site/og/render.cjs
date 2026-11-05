// Renders site/og/og-image.html to site/public/og-image.png (1200x630), the
// social preview image that index.html points at with og:image and twitter:image.
//
// How to run: from the repo root, after `npm ci` in site/:
//   node site/og/render.cjs
// It needs the `playwright` package and a Chromium it can launch.

const path = require('path');
const { pathToFileURL } = require('url');
const { chromium } = require('playwright');

const WIDTH = 1200;
const HEIGHT = 630;

async function main() {
  const htmlPath = path.resolve(__dirname, 'og-image.html');
  const outPath = path.resolve(__dirname, '..', 'public', 'og-image.png');

  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({
      viewport: { width: WIDTH, height: HEIGHT },
      deviceScaleFactor: 1,
    });
    await page.goto(pathToFileURL(htmlPath).href);
    await page.evaluate(() => document.fonts.ready);

    const fontStatus = await page.evaluate(() =>
      Array.from(document.fonts).map((face) => `${face.family} ${face.weight}: ${face.status}`),
    );
    const failed = fontStatus.filter((line) => !line.endsWith('loaded'));
    if (failed.length > 0) {
      throw new Error(`Fonts did not load: ${failed.join('; ')}`);
    }

    await page.screenshot({ path: outPath, clip: { x: 0, y: 0, width: WIDTH, height: HEIGHT } });
    console.log(`Wrote ${outPath} (${WIDTH}x${HEIGHT})`);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
