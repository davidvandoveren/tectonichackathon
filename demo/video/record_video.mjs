// Records kate2-video.html to a silent MP4 (1920x1080) and writes the scene timeline for the voice-over.
// Usage: node record_video.mjs <workDir containing kate2-video.html + shots/> <ffmpeg>
import { chromium } from "/opt/node22/lib/node_modules/playwright/index.mjs";
import { execFileSync } from "node:child_process";
import { writeFileSync, readdirSync } from "node:fs";
const [DIR, FFMPEG] = process.argv.slice(2);
const b = await chromium.launch();
const t0 = Date.now();
const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, recordVideo: { dir: `${DIR}/raw`, size: { width: 1920, height: 1080 } } });
const page = await ctx.newPage();
await page.goto(`file://${DIR}/kate2-video.html`);
await page.evaluate(() => Promise.all([...document.images].map((i) => i.complete || new Promise((r) => (i.onload = i.onerror = r)))));
await page.waitForTimeout(500);
const scenes = await page.evaluate(() => window.SCENES);
const total = await page.evaluate(() => window.TOTAL);
const offset = (Date.now() - t0) / 1000;
await page.evaluate(() => window.start());
await page.waitForTimeout((total + 0.8) * 1000);
await ctx.close();
await b.close();
const raw = readdirSync(`${DIR}/raw`).find((f) => f.endsWith(".webm"));
execFileSync(FFMPEG, ["-y", "-loglevel", "error", "-ss", String(offset), "-i", `${DIR}/raw/${raw}`, "-t", String(total),
  "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-movflags", "+faststart",
  `${DIR}/kate2-demo-silent.mp4`]);
let start = 0;
writeFileSync(`${DIR}/timeline.json`, JSON.stringify(scenes.map((s) => { const r = { ...s, start }; start += s.duration; return r; }), null, 2));
console.log("done", { offset, total });
