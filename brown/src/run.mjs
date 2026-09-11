import fs from "node:fs";
import path from "node:path";
import { config, DATA_DIR, log, readJson, writeJson } from "./config.mjs";
import { LoginRequired, openBrowser, saveCookies } from "./browser.mjs";
import { fetchJobDetails, scrapeJobs } from "./scrape.mjs";
import { classifyJob } from "./classify.mjs";
import { alert, alertPassiveJob } from "./notify.mjs";

const args = new Set(process.argv.slice(2));
const DEBUG = args.has("--debug");
const DRY = args.has("--dry-run");
const BASELINE = args.has("--baseline"); // record current jobs without alerting
const SEEN_FILE = path.join(DATA_DIR, "seen.json");
const JOBS_FILE = path.join(DATA_DIR, "jobs.json");
const STATE_FILE = path.join(DATA_DIR, "state.json");
const REPORT_FILE = path.join(DATA_DIR, "report.md");
const LOCK_FILE = path.join(DATA_DIR, ".lock");

if (fs.existsSync(LOCK_FILE) && Date.now() - fs.statSync(LOCK_FILE).mtimeMs < 20 * 60 * 1000) {
  log("another run is in progress; exiting");
  process.exit(0);
}
fs.writeFileSync(LOCK_FILE, String(process.pid));
process.on("exit", () => fs.rmSync(LOCK_FILE, { force: true }));

const seen = readJson(SEEN_FILE, {});
const state = readJson(STATE_FILE, {});
const firstRun = Object.keys(seen).length === 0;
let ctx;
try {
  ctx = await openBrowser({ headless: !args.has("--headed") && config.headless });
  const jobs = await scrapeJobs(ctx, { debug: DEBUG });
  log(`found ${jobs.length} postings`);
  if (jobs.length === 0) {
    log("no postings parsed; check data/debug/ for a snapshot of what the page looked like");
    await maybeAlertOnce("scrape-empty", 24, {
      title: "Brown job watcher: nothing parsed",
      message: "The Workday page loaded but no postings were extracted. See data/debug/.",
    });
    process.exit(3);
  }
  state.lastSuccess = new Date().toISOString();

  const fresh = jobs.filter((j) => !seen[j.id]);
  log(`${fresh.length} new since last run${firstRun ? " (first run: everything is new)" : ""}`);

  const results = [];
  for (const job of fresh) {
    const details = job.description && job.description.length > 300 ? "" : await fetchJobDetails(ctx, job);
    const analysis = await classifyJob(job, details);
    log(`  ${analysis.verdict.padEnd(11)} ${job.title}${job.department ? ` (${job.department})` : ""} [${analysis.source}]`);
    results.push({ job, analysis, details });
  }

  const shouldAlert = (a) => a.verdict === "passive" || (config.alertOnMaybe && a.verdict === "maybe");
  const hits = results.filter((r) => shouldAlert(r.analysis));
  if (!DRY && !BASELINE) {
    for (const { job, analysis } of hits) {
      await alertPassiveJob(job, analysis);
      await sleep(1500); // let macOS show each notification separately
    }
  }
  log(`${hits.length} alert(s)${DRY ? " (dry run, not sent)" : BASELINE ? " (baseline, not sent)" : " sent"}`);

  if (!DRY) {
    const now = new Date().toISOString();
    for (const { job, analysis } of results) {
      seen[job.id] = { title: job.title, department: job.department, verdict: analysis.verdict, firstSeen: now, alerted: shouldAlert(analysis) && !BASELINE };
    }
    writeJson(SEEN_FILE, seen);
  }

  const all = jobs.map((job) => {
    const r = results.find((x) => x.job.id === job.id);
    return { ...job, analysis: r?.analysis || seen[job.id]?.analysis, firstSeen: seen[job.id]?.firstSeen };
  });
  // keep prior analyses for jobs not re-classified this run
  const prior = readJson(JOBS_FILE, []);
  for (const j of all) if (!j.analysis) j.analysis = prior.find((p) => p.id === j.id)?.analysis;
  writeJson(JOBS_FILE, all);
  writeReport(all);
  await saveCookies(ctx);
} catch (err) {
  if (err instanceof LoginRequired) {
    log("Workday session expired. Run: npm run login");
    await maybeAlertOnce("login", 12, {
      title: "Brown job watcher needs a login",
      message: "Workday session expired. Open Terminal in internship-alerts and run: npm run login",
    });
    process.exitCode = 2;
  } else {
    log("run failed:", err.stack || err.message);
    process.exitCode = 1;
  }
} finally {
  writeJson(STATE_FILE, { ...state, lastRun: new Date().toISOString() });
  await ctx?.close().catch(() => {});
}

async function maybeAlertOnce(key, hours, payload) {
  const last = state[`alert:${key}`] ? Date.parse(state[`alert:${key}`]) : 0;
  if (Date.now() - last < hours * 3600 * 1000 || DRY) return;
  state[`alert:${key}`] = new Date().toISOString();
  await alert(payload);
}

function writeReport(all) {
  const order = { passive: 0, maybe: 1, not_passive: 2 };
  const rows = [...all].sort((a, b) => (order[a.analysis?.verdict] ?? 3) - (order[b.analysis?.verdict] ?? 3));
  const lines = [
    `# Brown student jobs (updated ${new Date().toLocaleString()})`,
    "",
    `${all.length} postings. Sorted with passive jobs first.`,
    "",
    "| Verdict | Title | Department | Pay | Why | Link |",
    "|---|---|---|---|---|---|",
    ...rows.map((j) => {
      const a = j.analysis || {};
      const why = (a.summary || (a.reasons || []).slice(0, 2).join("; ")).replace(/\|/g, "/");
      return `| ${a.verdict || "?"} | ${j.title.replace(/\|/g, "/")} | ${j.department || ""} | ${j.pay || ""} | ${why} | ${j.url ? `[open](${j.url})` : ""} |`;
    }),
    "",
  ];
  fs.writeFileSync(REPORT_FILE, lines.join("\n"));
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}
