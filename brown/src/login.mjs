import { config, log } from "./config.mjs";
import { isLoginUrl, openBrowser, saveCookies } from "./browser.mjs";

const ctx = await openBrowser({ headless: false });
const page = ctx.pages()[0] ?? (await ctx.newPage());
await page.goto(config.workdayUrl, { waitUntil: "domcontentloaded" });

log("A browser window is open. Sign in with your Brown username, password and Duo.");
log('If Duo offers "Remember me" / "Trust this browser", accept it so headless runs keep working.');
log("Waiting up to 10 minutes for the Workday page to load...");

await page.waitForURL(
  (u) => u.hostname === "wd5.myworkday.com" && !isLoginUrl(u.href),
  { timeout: 10 * 60 * 1000 },
);
await page.waitForLoadState("networkidle", { timeout: 60_000 }).catch(() => {});
await page.waitForTimeout(3000);

const n = await saveCookies(ctx);
log(`Logged in. Saved ${n} cookies. You can close the window; the session is stored in data/cookies.json and .browser-profile/.`);
await ctx.close();
