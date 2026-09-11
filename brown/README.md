# Brown passive-job watcher

Part of the internship-alerts repo, but it runs on your Mac rather than in GitHub Actions:
Brown's student job list is behind Brown SSO and Duo, so it needs a signed-in browser session.

Polls the **Find Student Jobs** report in Brown's Workday, classifies every new posting, and sends
you one alert per job that looks *passive* (you sit at a desk, monitor a space, hand out keys, and
can do your own coursework for most of the shift).

## One-time setup

```bash
cd brown
npm install
npx playwright install chromium
cp .env.example .env          # add BREVO_API_KEY, MAIL_FROM, ALERT_EMAIL_TO (same values as the repo's Actions secrets)
npm run login                 # opens a browser: sign in with Brown SSO + Duo, then it closes itself
npm run check:debug           # first pass: classifies everything currently posted, saves a debug snapshot
npm run schedule:install      # runs every 20 minutes in the background via launchd
```

Student jobs are only visible after Brown SSO, so the watcher drives a real Chromium profile
stored in `.browser-profile/` plus `data/cookies.json`. When the session eventually expires you get a
single "needs a login" notification. Run `npm run login` again and it resumes.

## Commands

| Command | What it does |
|---|---|
| `npm run login` | Headed browser for SSO + Duo. Accept "remember this device" in Duo. |
| `npm run check` | One poll: scrape, classify new postings, alert passive ones. |
| `npm run check:debug` | Same, plus a full snapshot in `data/debug/` (screenshot, HTML, every JSON response). |
| `npm run dry` | Scrape and classify but send nothing and remember nothing. |
| `node src/run.mjs --baseline` | Record everything currently posted as seen, without alerting. |
| `npm run reset` | Forget seen jobs so the next run re-alerts. |
| `npm run schedule:install` / `schedule:remove` | Manage the launchd agent. |

## Where things land

- `data/alerts.md`: every alert ever sent, with reasons and the posting link.
- `data/report.md`: all currently open postings with verdicts, passive first.
- `data/jobs.json` / `data/seen.json`: machine state.
- `data/run.log`: scheduled-run output.

## Alert channels

**Email (Brevo):** put the same `BREVO_API_KEY`, `MAIL_FROM`, and `ALERT_EMAIL_TO` you stored as
GitHub Actions secrets into `brown/.env`. GitHub never shows secret values back, so copy them
from your Brevo dashboard and your own notes. Each passive job arrives as its own email with the
reasons and a button to the posting. The "needs a login" notice is emailed too.

macOS notifications are always on. Install `terminal-notifier` (`brew install terminal-notifier`) to
make clicking a notification open the posting. Set `NTFY_TOPIC` to get the same alerts on your phone
through the free ntfy app, or `DISCORD_WEBHOOK_URL` for a Discord channel.

## How classification works

`src/classify.mjs` scores title and posting text with keyword rules (front desk, key office,
monitor, attendant, "may study during downtime" score up; tutoring, dining, lifeguard, research,
phone calling, "fast-paced" score down). If `ANTHROPIC_API_KEY` is set, Claude reads the full
posting and its verdict replaces the rules. `ALERT_ON_MAYBE=1` also alerts on borderline jobs.

## If nothing is extracted

The Workday report layout was not visible while this was built. If a run reports "no postings
parsed", open the newest folder in `data/debug/` and look at `page.png` and `extracted.json`; the
row selectors live in `src/scrape.mjs` (`extractDomRows` and `extractJsonGridRows`).
