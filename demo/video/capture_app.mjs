// Captures the app screens used in the demo video (synthetic data only).
// Usage: node capture_app.mjs <baseUrl> <outDir>   (server with PASSWORDLESS_LOGIN=true, ADMIN_USERNAMES=jan)
import { chromium } from "/opt/node22/lib/node_modules/playwright/index.mjs";
const [BASE, OUT] = [process.argv[2] ?? "http://localhost:8801", process.argv[3] ?? "."];
const b = await chromium.launch();
// Film only: hide the developer "demo mode" hints (no Gemini key in the filming session).
const clean = (page) =>
  page.evaluate(() => {
    document.querySelectorAll('[class*="demoBanner"]').forEach((el) => el.remove());
    document.querySelectorAll("p").forEach((el) => {
      for (const node of el.childNodes)
        if (node.nodeType === 3 && node.textContent.includes("demo-modus")) node.textContent = node.textContent.replace(" · demo-modus", "");
    });
  });
const shot = async (page, name) => { await page.waitForTimeout(700); await clean(page); await page.screenshot({ path: `${OUT}/${name}.png` }); console.log("shot", name); };

async function phone(persona) {
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => console.log("PAGEERROR", e.message));
  for (let i = 0; i < 30; i++) { try { await page.goto(`${BASE}/login`); break; } catch { await page.waitForTimeout(500); } }
  await page.getByRole("radio", { name: new RegExp(`^(Aanmelden als )?${persona}`) }).first().click();
  const submit = page.locator('button[type="submit"]');
  if (await submit.count()) await submit.click().catch(() => {});
  await page.waitForURL(`${BASE}/`, { timeout: 15000 });
  await page.waitForTimeout(1200);
  return { ctx, page };
}

// 1. Emma: home + "Waarom zie ik dit?"
{
  const { ctx, page } = await phone("Emma Peeters");
  await shot(page, "01-home");
  const why = page.getByRole("button", { name: /Waarom zie ik dit/ }).first();
  if (await why.count()) { await why.click(); await shot(page, "02-why"); }
  // 2. Kate chat: welcome, transfer, confirm
  await page.getByRole("button", { name: /Open Kate|Vraag het Kate/ }).first().click();
  await shot(page, "03-kate-welcome");
  await page.getByLabel("Bericht aan Kate").fill("Stuur Lucas 25 euro voor de pizza");
  await shot(page, "04-kate-typing");
  await page.getByRole("button", { name: "Stuur", exact: true }).click();
  await page.getByText("Overschrijving klaargezet").waitFor();
  await shot(page, "05-kate-transfer");
  const confirm = page.getByRole("button", { name: "Bevestigen" });
  if (await confirm.count()) { await confirm.click(); await page.waitForURL(/transfer/); await shot(page, "06-transfer-prefilled"); }
  // 3. Bereavement: empathy -> offer -> advisor hand-off
  await page.goto(`${BASE}/`); await page.waitForTimeout(800);
  await page.getByRole("button", { name: /Open Kate|Vraag het Kate/ }).first().click();
  await page.getByLabel("Bericht aan Kate").fill("Mijn mama is overleden, wat moet ik met de erfenis doen?");
  await page.getByRole("button", { name: "Stuur", exact: true }).click();
  await page.getByText(/gecondoleerd/i).first().waitFor();
  await shot(page, "07-kate-empathy");
  await page.getByLabel("Bericht aan Kate").fill("ja graag");
  await page.getByRole("button", { name: "Stuur", exact: true }).click();
  await page.getByText("Gesprek voorbereid").waitFor();
  await page.getByText("Gesprek voorbereid").scrollIntoViewIfNeeded();
  await shot(page, "08-kate-advisor");
  // 4. Subscriptions
  await page.goto(`${BASE}/subscriptions`); await page.getByText("Alle abonnementen").waitFor();
  await shot(page, "09-subscriptions");
  // 5. Consent screen
  await page.goto(`${BASE}/kate`); await page.waitForTimeout(1200);
  await shot(page, "10-consent");
  await ctx.close();
}
// 6. Jury dashboard (desktop, admin Jan)
{
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.5 });
  const page = await ctx.newPage();
  await page.goto(`${BASE}/login`); await page.waitForTimeout(800);
  await page.getByRole("radio", { name: /^(Aanmelden als )?Jan Maes/ }).first().click();
  const submit = page.locator('button[type="submit"]');
  if (await submit.count()) await submit.click().catch(() => {});
  await page.waitForURL(`${BASE}/`, { timeout: 15000 });
  await page.goto(`${BASE}/jury`);
  await page.getByText("Kregen bewust niets").waitFor({ timeout: 90000 });
  await shot(page, "11-jury");
  await ctx.close();
}
await b.close();
