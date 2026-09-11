import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { config, DEBUG_DIR, log } from "./config.mjs";
import { isLoginUrl, LoginRequired } from "./browser.mjs";

const ROW_WAIT_SELECTOR = 'table tbody tr, [role="grid"] [role="row"], [data-automation-id="gridRow"], [data-automation-id*="jobTitle"]';

/**
 * Loads the Workday report and returns [{ id, title, department, pay, description, url, raw }].
 * Two extraction paths run: Workday's JSON UI model (captured from XHR) and the rendered DOM.
 */
export async function scrapeJobs(ctx, { debug = false } = {}) {
  const page = await ctx.newPage();
  const jsonBodies = [];
  page.on("response", async (res) => {
    const ct = res.headers()["content-type"] || "";
    if (!/json/i.test(ct)) return;
    try {
      const body = await res.text();
      if (body && body.length > 2) jsonBodies.push({ url: res.url(), body });
    } catch {
      /* body not available */
    }
  });

  await page.goto(config.workdayUrl, { waitUntil: "domcontentloaded", timeout: 90_000 });
  await page.waitForLoadState("networkidle", { timeout: 60_000 }).catch(() => {});
  if (isLoginUrl(page.url())) throw new LoginRequired(page.url());

  await page.waitForSelector(ROW_WAIT_SELECTOR, { timeout: 45_000 }).catch(() => {});
  if (isLoginUrl(page.url())) throw new LoginRequired(page.url());
  await page.waitForTimeout(2000);
  await loadAllRows(page);

  const domRows = await extractDomRows(page);
  const jsonRows = extractJsonGridRows(jsonBodies);
  log(`extracted ${domRows.length} DOM rows, ${jsonRows.length} JSON rows`);

  if (debug || (domRows.length === 0 && jsonRows.length === 0)) {
    await saveDebug(page, jsonBodies, { domRows, jsonRows });
  }

  const rows = jsonRows.length >= domRows.length ? jsonRows : domRows;
  const jobs = rows.map(normalizeRow).filter((j) => j.title);
  await page.close();
  return dedupe(jobs);
}

async function loadAllRows(page) {
  let last = -1;
  for (let i = 0; i < 40; i++) {
    const count = await page.locator(ROW_WAIT_SELECTOR).count();
    if (count === last) break;
    last = count;
    await page.evaluate(() => {
      const scrollers = [...document.querySelectorAll("*")].filter((el) => {
        const s = getComputedStyle(el);
        return /(auto|scroll)/.test(s.overflowY) && el.scrollHeight > el.clientHeight + 50;
      });
      for (const el of scrollers) el.scrollTop = el.scrollHeight;
      window.scrollTo(0, document.body.scrollHeight);
    });
    await page.waitForTimeout(1200);
  }
  // "Load more" / next page buttons, if present
  for (let i = 0; i < 30; i++) {
    const btn = page.locator('button:has-text("Load More"), button:has-text("Show More"), [data-automation-id="loadMoreButton"]').first();
    if (!(await btn.count()) || !(await btn.isVisible().catch(() => false))) break;
    await btn.click().catch(() => {});
    await page.waitForTimeout(1500);
  }
}

async function extractDomRows(page) {
  return page.evaluate(() => {
    const text = (el) => (el?.innerText || el?.textContent || "").replace(/\s+/g, " ").trim();
    const linkOf = (el) => {
      const a = el.querySelector?.("a[href]");
      return a ? a.href : "";
    };
    const out = [];

    // 1. Plain HTML tables
    for (const table of document.querySelectorAll("table")) {
      const headers = [...table.querySelectorAll("thead th, thead td, tr:first-child th")].map(text);
      const bodyRows = [...table.querySelectorAll("tbody tr")].filter((tr) => tr.querySelectorAll("td").length);
      if (!bodyRows.length) continue;
      for (const tr of bodyRows) {
        const cells = [...tr.querySelectorAll("td")];
        const record = {};
        cells.forEach((td, i) => {
          record[headers[i] || `col${i}`] = text(td);
        });
        out.push({ cells: record, url: linkOf(tr), rowText: text(tr) });
      }
    }
    if (out.length) return out;

    // 2. ARIA grids
    for (const grid of document.querySelectorAll('[role="grid"], [role="table"]')) {
      const headers = [...grid.querySelectorAll('[role="columnheader"]')].map(text);
      const rows = [...grid.querySelectorAll('[role="row"]')].filter((r) => r.querySelectorAll('[role="gridcell"], [role="cell"]').length);
      for (const r of rows) {
        const cells = [...r.querySelectorAll('[role="gridcell"], [role="cell"]')];
        const record = {};
        cells.forEach((c, i) => {
          record[headers[i] || `col${i}`] = text(c);
        });
        out.push({ cells: record, url: linkOf(r), rowText: text(r) });
      }
    }
    if (out.length) return out;

    // 3. Workday job cards (internal career site style)
    for (const li of document.querySelectorAll('li[class*="css"], [data-automation-id="jobCard"], section li')) {
      const a = li.querySelector('a[data-automation-id="jobTitle"], a[href*="/job/"], a[href*="/inst/"]');
      if (!a) continue;
      out.push({ cells: { Title: text(a), Details: text(li) }, url: a.href, rowText: text(li) });
    }
    return out;
  });
}

function extractJsonGridRows(bodies) {
  const rows = [];
  for (const { body } of bodies) {
    let doc;
    try {
      doc = JSON.parse(body);
    } catch {
      continue;
    }
    walk(doc, (node) => {
      if (node && typeof node === "object" && (node.widget === "grid" || Array.isArray(node.rows)) && Array.isArray(node.rows)) {
        const columns = Array.isArray(node.columns) ? node.columns : [];
        const labelFor = (id, i) => columns.find((c) => c.columnId === id)?.label || columns[i]?.label || id;
        for (const row of node.rows) {
          const cellsMap = row.cellsMap || row.cells || {};
          const record = {};
          let url = "";
          Object.entries(cellsMap).forEach(([colId, cell], i) => {
            const label = labelFor(colId, i);
            record[label] = cellText(cell);
            const inst = findInstance(cell);
            if (inst && !url) url = instanceUrl(inst);
          });
          if (Object.keys(record).length) rows.push({ cells: record, url, rowText: Object.values(record).join(" | "), rowId: row.id });
        }
      }
    });
  }
  return rows;
}

function walk(node, fn, depth = 0) {
  if (!node || typeof node !== "object" || depth > 40) return;
  fn(node);
  for (const v of Array.isArray(node) ? node : Object.values(node)) walk(v, fn, depth + 1);
}

function cellText(cell) {
  if (cell == null) return "";
  if (typeof cell === "string") return cell.trim();
  if (Array.isArray(cell)) return cell.map(cellText).filter(Boolean).join(" ");
  if (typeof cell === "object") {
    if (cell.value != null && typeof cell.value !== "object") return String(cell.value).trim();
    if (cell.text) return String(cell.text).trim();
    if (cell.instances) return cellText(cell.instances);
    if (cell.children) return cellText(cell.children);
  }
  return "";
}

function findInstance(cell) {
  let found = null;
  walk(cell, (n) => {
    if (!found && n && typeof n === "object" && typeof n.instanceId === "string" && n.text) found = n;
  });
  return found;
}

function instanceUrl(inst) {
  // Workday instance ids look like "1$17188.17188$12345"; the detail page is /d/inst/<id>.htmld
  const base = new URL(config.workdayUrl).origin;
  return `${base}/brown/d/inst/${inst.instanceId}.htmld`;
}

const FIELD = {
  title: /job\s*(posting)?\s*title|^title$|position|posting|job$/i,
  department: /department|supervisory|organization|hiring\s*(manager|unit)|office|division/i,
  pay: /pay|rate|wage|compens|salary|hourly/i,
  description: /description|summary|details|duties|responsibilit/i,
  location: /location/i,
  posted: /posted|date|start/i,
  hours: /hours|schedule|shift|time\s*type/i,
};

function normalizeRow(row) {
  const cells = row.cells || {};
  const pick = (re, exclude = []) => {
    const key = Object.keys(cells).find((k) => re.test(k) && !exclude.some((x) => x.test(k)));
    return key ? cells[key] : "";
  };
  let title = pick(FIELD.title, [FIELD.pay, FIELD.description]);
  if (!title) title = cells.Title || Object.values(cells)[0] || "";
  const job = {
    title: title.trim(),
    department: pick(FIELD.department),
    pay: pick(FIELD.pay),
    description: pick(FIELD.description),
    location: pick(FIELD.location),
    posted: pick(FIELD.posted, [FIELD.title]),
    hours: pick(FIELD.hours),
    url: row.url || "",
    raw: cells,
  };
  const idSource = idFromUrl(job.url) || row.rowId || `${job.title}|${job.department}|${job.pay}`;
  job.id = idFromUrl(job.url) ? idSource : crypto.createHash("sha1").update(idSource).digest("hex").slice(0, 12);
  return job;
}

function idFromUrl(url) {
  if (!url) return "";
  const inst = url.match(/\/inst\/(.+?)\.htmld/);
  if (inst) return inst[1];
  const m = url.match(/REQ\d+|_R\d+|\/job\/[^/?#]+/);
  return m ? m[0] : "";
}

function dedupe(jobs) {
  const seen = new Map();
  for (const j of jobs) if (!seen.has(j.id)) seen.set(j.id, j);
  return [...seen.values()];
}

/** Opens a posting and returns its visible text (used for classification). */
export async function fetchJobDetails(ctx, job) {
  if (!job.url) return "";
  const page = await ctx.newPage();
  try {
    await page.goto(job.url, { waitUntil: "domcontentloaded", timeout: 60_000 });
    await page.waitForLoadState("networkidle", { timeout: 30_000 }).catch(() => {});
    if (isLoginUrl(page.url())) throw new LoginRequired(page.url());
    await page.waitForTimeout(1500);
    const text = await page.evaluate(() => {
      const main = document.querySelector('[data-automation-id="pageContent"], main, [role="main"]') || document.body;
      return (main.innerText || "").replace(/\n{3,}/g, "\n\n").trim();
    });
    return text.slice(0, 12_000);
  } catch (err) {
    if (err instanceof LoginRequired) throw err;
    log(`details failed for "${job.title}": ${err.message}`);
    return "";
  } finally {
    await page.close().catch(() => {});
  }
}

async function saveDebug(page, jsonBodies, extracted) {
  fs.mkdirSync(DEBUG_DIR, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const dir = path.join(DEBUG_DIR, stamp);
  fs.mkdirSync(dir, { recursive: true });
  await page.screenshot({ path: path.join(dir, "page.png"), fullPage: true }).catch(() => {});
  fs.writeFileSync(path.join(dir, "page.html"), await page.content().catch(() => ""));
  fs.writeFileSync(path.join(dir, "page.txt"), await page.evaluate(() => document.body.innerText).catch(() => ""));
  jsonBodies.forEach((b, i) => fs.writeFileSync(path.join(dir, `xhr-${String(i).padStart(3, "0")}.json`), `// ${b.url}\n${b.body}`));
  fs.writeFileSync(path.join(dir, "extracted.json"), JSON.stringify(extracted, null, 2));
  log(`debug snapshot saved to ${dir}`);
}
