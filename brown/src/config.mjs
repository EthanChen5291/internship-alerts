import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
export const DATA_DIR = path.join(ROOT, "data");
export const DEBUG_DIR = path.join(DATA_DIR, "debug");
export const PROFILE_DIR = path.join(ROOT, ".browser-profile");

try {
  process.loadEnvFile(path.join(ROOT, ".env"));
} catch {
  // no .env is fine
}

fs.mkdirSync(DATA_DIR, { recursive: true });

export const config = {
  workdayUrl: process.env.WORKDAY_URL || "https://wd5.myworkday.com/brown/d/task/1422$7750.htmld",
  anthropicKey: process.env.ANTHROPIC_API_KEY || "",
  ntfyTopic: process.env.NTFY_TOPIC || "",
  discordWebhook: process.env.DISCORD_WEBHOOK_URL || "",
  // Same three names the GitHub Actions workflow uses for the internship engine's personal alerts.
  brevoKey: process.env.BREVO_API_KEY || "",
  mailFrom: process.env.MAIL_FROM || "",
  alertEmailTo: process.env.ALERT_EMAIL_TO || "",
  alertOnMaybe: process.env.ALERT_ON_MAYBE === "1",
  headless: process.env.HEADLESS !== "0",
};

export function readJson(file, fallback) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return fallback;
  }
}

export function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(value, null, 2));
}

export function log(...args) {
  const ts = new Date().toISOString().replace("T", " ").slice(0, 19);
  console.log(`[${ts}]`, ...args);
}
