import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { config, DATA_DIR, PROFILE_DIR, log } from "./config.mjs";

const COOKIE_FILE = path.join(DATA_DIR, "cookies.json");

export class LoginRequired extends Error {
  constructor(url) {
    super(`Workday redirected to login: ${url}`);
    this.name = "LoginRequired";
  }
}

export function isLoginUrl(url) {
  return /authgwy|login\.htmld|login\.flex|sso\.brown\.edu|idp|shibboleth|duosecurity|\/saml\//i.test(url);
}

export async function openBrowser({ headless = config.headless } = {}) {
  const ctx = await chromium.launchPersistentContext(PROFILE_DIR, {
    headless,
    viewport: { width: 1400, height: 1000 },
    args: ["--disable-blink-features=AutomationControlled"],
    ignoreDefaultArgs: ["--enable-automation"],
  });
  // Chromium drops session cookies (no expiry) when the browser closes. Workday and
  // Brown's SSO use session cookies, so we restore the ones we saved last run.
  const saved = readCookies();
  if (saved.length) {
    const now = Date.now() / 1000;
    const live = saved.filter((c) => !c.expires || c.expires < 0 || c.expires > now);
    try {
      await ctx.addCookies(live);
    } catch (err) {
      log("could not restore cookies:", err.message);
    }
  }
  return ctx;
}

function readCookies() {
  try {
    return JSON.parse(fs.readFileSync(COOKIE_FILE, "utf8"));
  } catch {
    return [];
  }
}

export async function saveCookies(ctx) {
  const cookies = await ctx.cookies();
  fs.writeFileSync(COOKIE_FILE, JSON.stringify(cookies, null, 2));
  return cookies.length;
}
