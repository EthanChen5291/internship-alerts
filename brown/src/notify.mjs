import { execFile } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { promisify } from "node:util";
import { config, DATA_DIR, log } from "./config.mjs";

const run = promisify(execFile);
const ALERTS_MD = path.join(DATA_DIR, "alerts.md");

function esc(s) {
  return String(s).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}

async function hasTerminalNotifier() {
  try {
    await run("which", ["terminal-notifier"]);
    return true;
  } catch {
    return false;
  }
}

export async function macNotify({ title, subtitle = "", message, url }) {
  if (process.platform !== "darwin") return;
  try {
    if (await hasTerminalNotifier()) {
      const args = ["-title", title, "-message", message, "-sound", "Glass"];
      if (subtitle) args.push("-subtitle", subtitle);
      if (url) args.push("-open", url);
      await run("terminal-notifier", args);
      return;
    }
    const script = `display notification "${esc(message)}" with title "${esc(title)}"${
      subtitle ? ` subtitle "${esc(subtitle)}"` : ""
    } sound name "Glass"`;
    await run("osascript", ["-e", script]);
  } catch (err) {
    log("macOS notification failed:", err.message);
  }
}

async function ntfy({ title, message, url }) {
  if (!config.ntfyTopic) return;
  try {
    const headers = { Title: title, Priority: "high", Tags: "briefcase" };
    if (url) headers.Click = url;
    await fetch(`https://ntfy.sh/${encodeURIComponent(config.ntfyTopic)}`, { method: "POST", body: message, headers });
  } catch (err) {
    log("ntfy failed:", err.message);
  }
}

async function discord({ title, message, url }) {
  if (!config.discordWebhook) return;
  try {
    await fetch(config.discordWebhook, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: `**${title}**\n${message}${url ? `\n${url}` : ""}` }),
    });
  } catch (err) {
    log("discord failed:", err.message);
  }
}

export function emailConfigured() {
  return Boolean(config.brevoKey && config.mailFrom && config.alertEmailTo);
}

function parseSender(raw) {
  const m = raw.match(/^\s*(.*?)\s*<\s*([^<>\s]+@[^<>\s]+)\s*>\s*$/);
  return m ? { name: m[1].trim() || "Brown Job Alerts", email: m[2] } : { name: "Brown Job Alerts", email: raw.trim() };
}

const escapeHtml = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

/** Sends one transactional email through Brevo. Returns true on success. */
export async function brevoSend({ subject, html, text }) {
  if (!emailConfigured()) return false;
  try {
    const res = await fetch("https://api.brevo.com/v3/smtp/email", {
      method: "POST",
      headers: { "api-key": config.brevoKey, "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        sender: parseSender(config.mailFrom),
        to: [{ email: config.alertEmailTo }],
        subject,
        htmlContent: html,
        textContent: text,
      }),
    });
    if (!res.ok) {
      log(`Brevo rejected the email (${res.status}): ${(await res.text()).slice(0, 300)}`);
      return false;
    }
    return true;
  } catch (err) {
    log("Brevo send failed:", err.message);
    return false;
  }
}

export function passiveJobEmail(job, analysis) {
  const verdictLabel = analysis.verdict === "passive" ? "Passive job" : "Maybe passive";
  const meta = [job.department, job.pay, job.hours, job.location].filter(Boolean);
  const subject = `[${verdictLabel}] ${job.title}${job.department ? ` · ${job.department}` : ""}${job.pay ? ` · ${job.pay}` : ""}`;
  const li = (items) => items.map((r) => `<li>${escapeHtml(r)}</li>`).join("");
  const html = `
<div style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;max-width:640px;margin:0 auto;color:#1f2328;line-height:1.5">
  <p style="font-size:12px;color:#57606a;margin:0 0 8px">Brown Workday · ${escapeHtml(verdictLabel.toLowerCase())} · confidence ${Math.round((analysis.confidence || 0) * 100)}%</p>
  <h2 style="margin:0 0 6px;font-size:20px">${escapeHtml(job.title)}</h2>
  ${meta.length ? `<p style="margin:0 0 14px;color:#57606a">${escapeHtml(meta.join(" · "))}</p>` : ""}
  ${analysis.summary ? `<p style="margin:0 0 14px;font-size:15px">${escapeHtml(analysis.summary)}</p>` : ""}
  ${job.url ? `<p style="margin:0 0 18px"><a href="${escapeHtml(job.url)}" style="background:#1f6feb;color:#fff;text-decoration:none;padding:10px 16px;border-radius:6px;display:inline-block">Open posting in Workday</a></p>` : ""}
  <p style="margin:0 0 4px;font-weight:600">Why it looks passive</p>
  <ul style="margin:0 0 14px;padding-left:20px">${li(analysis.reasons || [])}</ul>
  ${analysis.redFlags?.length ? `<p style="margin:0 0 4px;font-weight:600">Watch out</p><ul style="margin:0 0 14px;padding-left:20px">${li(analysis.redFlags)}</ul>` : ""}
  ${job.description ? `<p style="margin:0 0 4px;font-weight:600">Posting text</p><p style="white-space:pre-wrap;color:#424a53;font-size:13px">${escapeHtml(job.description.slice(0, 2500))}</p>` : ""}
  <p style="font-size:12px;color:#8c959f;margin-top:24px">Sent by the Brown passive-job watcher running on your Mac (internship-alerts/brown). Verdict source: ${escapeHtml(analysis.source || "rules")}.</p>
</div>`;
  const text = [
    `${verdictLabel}: ${job.title}`,
    meta.join(" · "),
    analysis.summary,
    job.url,
    "",
    "Why: " + (analysis.reasons || []).join("; "),
    analysis.redFlags?.length ? "Watch out: " + analysis.redFlags.join("; ") : "",
  ]
    .filter(Boolean)
    .join("\n");
  return { subject, html, text };
}

export async function alert({ title, subtitle, message, url }) {
  await Promise.all([
    macNotify({ title, subtitle, message, url }),
    ntfy({ title, message, url }),
    discord({ title, message, url }),
    brevoSend({ subject: title, html: `<p>${escapeHtml(message)}</p>${url ? `<p><a href="${escapeHtml(url)}">${escapeHtml(url)}</a></p>` : ""}`, text: `${message}${url ? `\n${url}` : ""}` }),
  ]);
}

export async function alertPassiveJob(job, analysis) {
  const pay = job.pay ? ` · ${job.pay}` : "";
  const dept = job.department ? `${job.department}${pay}` : pay.replace(/^ · /, "");
  const verdictLabel = analysis.verdict === "passive" ? "Passive job" : "Maybe passive";
  const title = `${verdictLabel}: ${job.title}`;
  const message = analysis.summary || analysis.reasons.slice(0, 2).join("; ");
  await Promise.all([
    macNotify({ title, subtitle: dept, message, url: job.url }),
    ntfy({ title, message, url: job.url }),
    discord({ title, message, url: job.url }),
    brevoSend(passiveJobEmail(job, analysis)),
  ]);

  const stamp = new Date().toISOString().slice(0, 16).replace("T", " ");
  const lines = [
    `## ${job.title}`,
    `- **When:** ${stamp}`,
    `- **Verdict:** ${analysis.verdict} (confidence ${analysis.confidence})`,
    job.department ? `- **Department:** ${job.department}` : null,
    job.pay ? `- **Pay:** ${job.pay}` : null,
    job.url ? `- **Link:** ${job.url}` : null,
    `- **Why:** ${analysis.reasons.join("; ")}`,
    analysis.redFlags?.length ? `- **Watch out:** ${analysis.redFlags.join("; ")}` : null,
    "",
  ].filter(Boolean);
  fs.appendFileSync(ALERTS_MD, lines.join("\n") + "\n");
}
