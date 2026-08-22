<div align="center">

# 🎓 Summer 2027 Tech Internships

**A self-updating engine that tracks tech internships so you don't have to.**

[![CI](https://img.shields.io/github/actions/workflow/status/zshah101/Automated-List-Of-Summer-2027-and-Fall-2026-Tech-Internships/ci.yml?branch=main&label=tests&style=flat-square&color=3fb950)](https://github.com/zshah101/Automated-List-Of-Summer-2027-and-Fall-2026-Tech-Internships/actions/workflows/ci.yml)&nbsp;[![Open roles](https://img.shields.io/badge/dynamic/json?label=open%20roles&query=open_total&url=https%3A%2F%2Fzshah101.github.io%2FAutomated-List-Of-Summer-2027-and-Fall-2026-Tech-Internships%2Fapi%2Fstats.json&color=2f81f7&style=flat-square)](https://zshah101.github.io/Automated-List-Of-Summer-2027-and-Fall-2026-Tech-Internships/)&nbsp;![Updates](https://img.shields.io/badge/updates-every%2030%20min-3fb950?style=flat-square)&nbsp;[![RSS](https://img.shields.io/badge/RSS-subscribe-e67e22?style=flat-square)](https://zshah101.github.io/Automated-List-Of-Summer-2027-and-Fall-2026-Tech-Internships/feed.xml)

### 251 open roles (201 listed below) · 77 new this week

4,271 employers tracked · data as of Aug 22, 2026 at 12:10 UTC

_156 have a cycle the employer stated · 95 are recent postings whose cycle isn't stated (listed separately, never mixed in)._

**[🖥️ Live dashboard](https://zshah101.github.io/Automated-List-Of-Summer-2027-and-Fall-2026-Tech-Internships/)** · **[📡 RSS](https://zshah101.github.io/Automated-List-Of-Summer-2027-and-Fall-2026-Tech-Internships/feed.xml)** · **[⚙️ JSON API](https://zshah101.github.io/Automated-List-Of-Summer-2027-and-Fall-2026-Tech-Internships/api/jobs.json)** · **[✉️ Email alerts](https://zshah101.github.io/Automated-List-Of-Summer-2027-and-Fall-2026-Tech-Internships/#subscribe)**

</div>

> [!TIP]
> **⭐ Star this repo** to save it and get updates when new roles are added.

Instead of refreshing a dozen career pages by hand, it reads company hiring feeds directly and keeps one live list — newest roles on top, refreshed automatically throughout the day.

**🔔 New roles in your inbox:** [subscribe by email](https://zshah101.github.io/Automated-List-Of-Summer-2027-and-Fall-2026-Tech-Internships/#subscribe) - one email a day, only when new internships actually appeared, unsubscribe from any email in two clicks. (Prefer RSS-to-email? [Feedrabbit works too](https://feedrabbit.com/subscriptions/new?url=https%3A%2F%2Fraw.githubusercontent.com%2Fzshah101%2FAutomated-List-Of-Summer-2027-and-Fall-2026-Tech-Internships%2Fmain%2Fdocs%2Ffeed.xml).)

---

## What this is

This is an engine, not a hand-kept list. It polls company career feeds every 30 minutes, finds the internships, removes duplicates, and rebuilds this page on its own.

Every link comes straight from the source — so it's real and current, not a stale list someone forgot to update. Speed matters.

## What makes this different

| | |
|---|---|
| 📅 **[Drop Radar](#drop-radar)** | A forecast of **what's coming**. Each marquee company's typical opening window, replaced by the real drop date the moment the engine catches it live. Windows are estimates and labelled as such; only dates the engine saw itself are marked verified. |
| 🛂 **Visa intel, computed** | 🇺🇸 / 🛂 flags detected automatically from every job description, plus ✓ for employers with a real H-1B track record (USCIS data, FY2022-23 — a history, not a promise). The big lists crowdsource this by hand; here it's code. Most postings say nothing either way, and those show as unknown rather than guessed. |
| 📆 **A real date on nearly every role** | Taken from the job portal itself wherever the portal states one, so newest-first actually means newest. The exact coverage figure is printed at the bottom of this page every run. |
| 🧰 **Skill tags + pay, extracted** | Every posting's text is scanned for the stack it wants (Python, C++, PyTorch, …) and the pay it states — searchable on the [dashboard](https://zshah101.github.io/Automated-List-Of-Summer-2027-and-Fall-2026-Tech-Internships/), and included in the CSV and API. |
| 🔔 **Alerts your way** | [Email digests](https://zshah101.github.io/Automated-List-Of-Summer-2027-and-Fall-2026-Tech-Internships/#subscribe) or [RSS](https://zshah101.github.io/Automated-List-Of-Summer-2027-and-Fall-2026-Tech-Internships/feed.xml) — point any reader, or a Slack/Discord RSS integration, at it. Plus a [live dashboard](https://zshah101.github.io/Automated-List-Of-Summer-2027-and-Fall-2026-Tech-Internships/) with search, filters, and a saved-roles list that never leaves your browser. |
| ⚙️ **An engine, not a spreadsheet** | 4,514 job-board endpoints (4,271 distinct employers; some run more than one board) polled every 30 minutes across 12 ATS platforms. Full source and tests in this repo. |

## Scope

| | |
|---|---|
| **Roles** | Software Engineering, Data Science & Machine Learning (and closely related technical internships) |
| **Region** | United States |
| **Cycles** | Summer 2027 and Fall 2026 |

## About

I'm an international student studying in the United States, so I built this for the search I'm doing myself. The list is US roles only for now — that's where I'm searching.

Use it to spot roles early and apply before they fill up. Being first genuinely helps.

## Where this is going

I'm building this in the open and adding to it as it grows.

**Recently shipped:** email alerts · the Drop Radar · auto-detected sponsorship flags · the live dashboard

**Next up:** personalized alerts (pick your categories) · per-company hiring pages · a ghost-posting detector

If it helps you, a star means a lot and tells me to keep going.

## How to use

<details>
<summary><b>Reading the table — flags, dates, and the cycle split</b> (click to expand)</summary>

- Roles are grouped by cycle below - **newest posting on top, oldest at the bottom.**
- A cycle section holds only roles whose **employer stated that cycle** - in the title, or in the posting's own text. Postings that name no cycle anywhere are in *Recently posted — cycle not stated* further down, with **no cycle guessed for them**. Same quality bar, different amount of evidence.
- The **Posted** column is the date the company published the role.
- **_(3 openings)_ after a role title** = the employer has that many separate live requisitions for the same job, in the same place, for the same cycle. They're all real and each takes its own application, so they're linked individually (**Apply**, then **#2**, **#3**) instead of repeating the row. Counts still count requisitions, and the CSV export is never grouped.
- **🆁 after a company name** = **this role is remote** — the posting's own location or title says so. It marks the role on that row, not the whole company.
- **Flags after a role title:** 🇺🇸 = requires U.S. citizenship or a security clearance · 🛂 = the posting says it won't sponsor a work visa · 🆕 = spotted in the last 48 hours. Sponsorship flags are detected automatically from each job description - treat them as a strong hint and confirm on the posting.
- **✓ after a company name** = a real H-1B track record: USCIS approved 10+ petitions for that employer in FY2022–2023 (matched automatically against the official [H-1B Employer Data Hub](https://www.uscis.gov/tools/reports-and-studies/h-1b-employer-data-hub)). No ✓ doesn't mean they won't sponsor - it means we can't prove they have.
- Track your applications with [`data/internships.csv`](data/internships.csv) (opens in Excel / Google Sheets).
- Missing a company? Adding one takes a single line, see [CONTRIBUTING.md](CONTRIBUTING.md).

</details>

---

## Summer 2027  (88 employer-stated)

| Company | Role | Category | Location | Skills | Posted | Apply |
|---|---|---|---|---|---|---|
| Hewlett Packard (HP) | Software Internship Roles - HP Solutions (HPS) 🛂 🆕 | Software | Spring, Texas, United States of America | Python, Java, C++, TypeScript | Aug 21, 2026 | [Apply](https://hp.wd5.myworkdayjobs.com/ExternalCareerSite/job/Spring-Texas-United-States-of-America/Software-Internship-Roles---HP-Solutions--HPS-_3167906-1) |
| Philips | Graduate Level Co-op – Data Scientist – Plymouth, MN – Summer 2027 🆕 | Data & ML/AI | Plymouth, Minnesota, United States | PyTorch, TensorFlow | Aug 20, 2026 | [Apply](https://philips.wd3.myworkdayjobs.com/jobs-and-careers/job/Plymouth-Minnesota-United-States/Graduate-Level-Co-op---Data-Scientist---Plymouth--MN---Summer-2027_590567) |
| InfiniteQuant | Quantitative Researcher - Internship - Summer 2027 🆕 | Quant | New York, NY, United States | Python, C++, Pandas | Aug 20, 2026 | [Apply](https://jobs.smartrecruiters.com/InfiniteQuant/744000144592181) |
| Fannie Mae ✓ | Campus – Data Science Intern (Analytics & Modeling Program) 🛂 🆕 | Data & ML/AI | Washington, DC | Python, SQL, Git | Aug 20, 2026 | [Apply](https://fanniemae.wd1.myworkdayjobs.com/FannieMaeCareers/job/Washington-DC/Campus---Data-Science-Intern--Analytics---Modeling-Program-_JR2815) |
| AbbVie ✓ | 2027 Business Technology Solutions Intern - Data & Software Engineering (Undergraduate) 🆕 | Data & ML/AI | North Chicago +2 more | Python, Java, TypeScript, JavaScript | Aug 20, 2026 | [Apply](https://jobs.smartrecruiters.com/AbbVie/3743990014697918) |
| Fifth Third Bank | Information Security Co-op - Cyber Threat Interdiction - Summer 2027 🆕 | Security | Cincinnati, OH | No skills listed | Aug 20, 2026 | [Apply](https://fifththird.wd5.myworkdayjobs.com/53careers/job/Cincinnati-OH/Information-Security-Co-op---Cyber-Threat-Interdiction---Summer-2027_R71582) |
| Fifth Third Bank | Information Security Co-op – Identity & Access Management – Summer 2027 🆕 | Security | Cincinnati, OH | No skills listed | Aug 20, 2026 | [Apply](https://fifththird.wd5.myworkdayjobs.com/53careers/job/Cincinnati-OH/Information-Security-Co-op---Identity---Access-Management---Summer-2027_R71591) |
| Fifth Third Bank | Software Engineer Co-Op - Enterprise Finance Applications - Summer 2027 🆕 | Software | Cincinnati, OH | Java, LLMs, Node.js, Angular | Aug 20, 2026 | [Apply](https://fifththird.wd5.myworkdayjobs.com/53careers/job/Cincinnati-OH/Software-Engineer-Co-Op---Enterprise-Finance-Applications---Summer-2027_R71588) |
| General Matter | Summer 2027 Internship - Software Engineering | Software | Los Angeles, CA | Python, C++, Linux | Aug 19, 2026 | [Apply](https://job-boards.greenhouse.io/generalmatter/jobs/5377118008) |
| RTX | Software Engineering Intern (Summer 2027) | Software | US-IA-CEDAR RAPIDS-107 ~ 400 Collins Rd… | Python, C++, Git | Aug 19, 2026 | [Apply](https://globalhr.wd5.myworkdayjobs.com/Private_Posting_No_TMP/job/US-IA-CEDAR-RAPIDS-107--400-Collins-Rd-NE--BLDG-107/Software-Engineering-Intern--Summer-2027-_01868241) |
| InfiniteQuant 🆁 | Quantitative Developer - Internship - Summer 2027 | Quant | New York +2 more | Python, C++ | Aug 19, 2026 | [Apply](https://jobs.smartrecruiters.com/InfiniteQuant/744000144281579) |
| Continental Resources | Data Analyst Intern (Summer 2027) | Data & ML/AI | Oklahoma City, OK | Python, SQL, HTML/CSS | Aug 18, 2026 | [Apply](https://clr.wd5.myworkdayjobs.com/CLR_Careers/job/Oklahoma-City-OK/Data-Analyst-Intern--Summer-2027-_R02591-1) |
| American Express ✓ | Campus Undergraduate Summer Internship Program - 2027 Software Engineer, Enterprise Technology Services- Sunrise, FL | Software | Sunrise, FL, United States | Python, Java, C#, Go | Aug 18, 2026 | [Apply](https://egug.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/26011015) |
| PIMCO ✓ | 2027 Summer Intern - Technology Analyst, Software Engineering | Software | Austin, TX USA | Python, Java, C++, C# | Aug 18, 2026 | [Apply](https://pimco.wd1.myworkdayjobs.com/pimco-careers/job/Austin-TX-USA/XMLNAME-2027-Summer-Intern---Technology-Analyst--Software-Engineering_R106745) |
| Xantium | Quantitative Developer Intern | Quant | London, England, New York, New York | Python, C++ | Aug 17, 2026 | [Apply](https://job-boards.greenhouse.io/xantium/jobs/4360768009) |
| Xantium | Quantitative Researcher Internship | Quant | London, England, New York, New York | No skills listed | Aug 17, 2026 | [Apply](https://job-boards.greenhouse.io/xantium/jobs/4371217009) |
| Hilton Worldwide | 2027 Corporate Summer Internship - Technology (Software Engineering and Cyber) | Security | Memphis +8 more | No skills listed | Aug 17, 2026 | [Apply](https://efet.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1009/job/218257) |
| American Express ✓ | Campus Undergraduate Summer Internship Program - 2027 Software Engineer, Enterprise Technology Services- Phoenix, AZ | Software | Phoenix, AZ, United States | Python, Java, C#, Go | Aug 17, 2026 | [Apply](https://egug.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/26011781) |
| American Express ✓ | Campus Graduate Masters Summer Internship Program - 2027 Software Engineer, Enterprise Technology Services- Phoenix, AZ | Software | Phoenix, AZ, United States | Python, Java, C#, Go | Aug 17, 2026 | [Apply](https://egug.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/26011784) |
| Vanguard | College to Corporate IT Internship - Data Analyst (NC) 🆕 _(2 openings)_ | Data & ML/AI | Charlotte, NC | No skills listed | Aug 17, 2026 | [Apply](https://vanguard.wd5.myworkdayjobs.com/vanguard_external/job/Charlotte-NC/College-to-Corporate-IT-Internship---Data-Analyst--NC-_177677-1) [#2](https://vanguard.wd5.myworkdayjobs.com/vanguard_external/job/Charlotte-NC/College-to-Corporate-IT-Internship---Data-Analyst--NC-_181767) |
| Conagra Brands ✓ | IT Infrastructure Internship - Summer 2027 | Software | Omaha, Nebraska | No skills listed | Aug 17, 2026 | [Apply](https://conagrabrands.wd1.myworkdayjobs.com/Careers_US/job/Omaha-Nebraska/IT-Infrastructure-Internship---Summer-2027_Req-039788) |
| Conagra Brands ✓ | Software Development Internship - Summer 2027 | Software | Omaha, Nebraska | Azure, Git | Aug 17, 2026 | [Apply](https://conagrabrands.wd1.myworkdayjobs.com/Careers_US/job/Omaha-Nebraska/Software-Development-Internship---Summer-2027_Req-039787) |
| RTX | Software Engineering Intern (Summer 2027) 🇺🇸 | Software | US-IA-CEDAR RAPIDS-192 ~ 1205 Continent… | Python, C++ | Aug 17, 2026 | [Apply](https://globalhr.wd5.myworkdayjobs.com/Private_Posting_No_TMP/job/US-IA-CEDAR-RAPIDS-192--1205-Continental-Place-NE--BLDG-192/Software-Engineering-Intern--Summer-2027-_01867324) |
| Vanguard | College to Corporate IT Internship - Data Science (NC) 🆕 _(2 openings)_ | Data & ML/AI | Charlotte, NC | No skills listed | Aug 17, 2026 | [Apply](https://vanguard.wd5.myworkdayjobs.com/vanguard_external/job/Charlotte-NC/College-to-Corporate-IT-Internship---Data-Science--NC-_177682-1) [#2](https://vanguard.wd5.myworkdayjobs.com/vanguard_external/job/Charlotte-NC/College-to-Corporate-IT-Internship---Data-Science--NC-_181765) |
| Vanguard | College to Corporate IT Internship - Data Science (PA) 🆕 _(2 openings)_ | Data & ML/AI | Malvern, PA | No skills listed | Aug 17, 2026 | [Apply](https://vanguard.wd5.myworkdayjobs.com/vanguard_external/job/Malvern-PA/College-to-Corporate-IT-Internship---Data-Science--PA-_177680-1) [#2](https://vanguard.wd5.myworkdayjobs.com/vanguard_external/job/Malvern-PA/College-to-Corporate-IT-Internship---Data-Science--PA-_181766) |
| KeyBank | 2027 Summer Key Technology & Services: Cyber/Information Security Track Internship- Cleveland | Security | Brooklyn, OH | Python, C#, JavaScript, SQL | Aug 17, 2026 | [Apply](https://keybank.wd5.myworkdayjobs.com/External_Career_Site/job/Brooklyn-OH/XMLNAME-2027-Summer-Key-Technology---Services--Cyber-Information-Security-Track-Internship--Cleveland_R-41384) |
| RTX | Software Engineering Intern (Summer 2027) 🇺🇸 | Software | US-IA-CEDAR RAPIDS-166 ~ 855 35Th St NE… | Python, C++, Bash, Linux | Aug 17, 2026 | [Apply](https://globalhr.wd5.myworkdayjobs.com/Private_Posting_No_TMP/job/US-IA-CEDAR-RAPIDS-166--855-35Th-St-NE--BLDG-166/Software-Engineering-Intern--Summer-2027-_01867487) |
| Replit | Software Engineering Intern (Summer 2027) | Software | Foster City, CA | No skills listed | Aug 15, 2026 | [Apply](https://jobs.ashbyhq.com/replit/7e0dafe8-3eec-442e-aa76-a4d84d779fb1) |
| Freeform | Software Engineering Intern (Summer 2027) | Software | Los Angeles, CA (On-site) | C++, Linux | Aug 14, 2026 | [Apply](https://job-boards.greenhouse.io/freeformfuturecorp/jobs/7872198003) |
| The Nuclear Company | Summer 2027 AI Applied Research Internship 🇺🇸 | Data & ML/AI | Washington, DC | Python, PyTorch | Aug 14, 2026 | [Apply](https://job-boards.greenhouse.io/thenuclearcompany/jobs/5391923008) |
| Notion | Software Engineer Intern (Summer 2027) | Software | San Francisco, California | Python, TypeScript, LLMs, React | Aug 14, 2026 | [Apply](https://jobs.ashbyhq.com/notion/3fba1c39-c5cb-47d7-9ad2-1cec4d7e9d0c) |
| Motorola | Android Platform Software Engineering Intern - Summer 2027 🇺🇸 | Software | Plantation, FL, More... | Python, Java, C++, Linux | Aug 14, 2026 | [Apply](https://motorolasolutions.wd5.myworkdayjobs.com/Careers/job/Plantation-FL/Android-Platform-Software-Engineering-Intern---Summer-2027_R67362-1) |
| Teledyne | NHRC Software Engineering Internship (Summer 2027) 🇺🇸 _(2 openings)_ | Software | US - Huntsville, AL | Java, C++, C#, .NET | Aug 13, 2026 | [Apply](https://flir.wd1.myworkdayjobs.com/flircareers/job/US---Huntsville-AL/NHRC-Software-Engineering-Internship--Summer-2027-_REQ36193) [#2](https://flir.wd1.myworkdayjobs.com/flircareers/job/US---Huntsville-AL/NHRC-Software-Engineering-Internship--Summer-2027-_REQ36194-2) |
| Western Digital | Summer 2027 Intern - Software Engineering | Software | San Jose, CA, United States | Python, Java, C++, Go | Aug 12, 2026 | [Apply](https://jobs.smartrecruiters.com/WesternDigital/744000143171017) |
| Northwestern Mutual | Public Investments Quantitative Analyst Intern, Summer 2027 | Quant | Milwaukee, WI Corporate | Python, SQL, dbt, Snowflake | Aug 12, 2026 | [Apply](https://northwesternmutual.wd5.myworkdayjobs.com/corporate-careers/job/Milwaukee-WI-Corporate/Public-Investments-Quantitative-Analyst-Intern--Summer-2027_JR-45807) |
| Hewlett Packard (HP) | Enterprise Operations Software Internship 🛂 | Software | Spring, Texas, United States of America | Python, Java, C++, SQL | Aug 11, 2026 | [Apply](https://hp.wd5.myworkdayjobs.com/ExternalCareerSite/job/Spring-Texas-United-States-of-America/Enterprise-Operations-Software-Internship_3167271-2) |
| DV Trading | Software Engineer Intern - Summer 2027 (DV Commodities) | Software | New York | Python, C++ | Aug 10, 2026 | [Apply](https://job-boards.greenhouse.io/dvtrading/jobs/4719119005) |
| Montenson | AI Intern 🛂 | Data & ML/AI | MN, United States | LLMs, Computer Vision | Aug 10, 2026 | [Apply](https://fa-esgu-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/23339) |
| ING | Summer 2027 Internship - Tech (Information Security) | Security | New York | Python | Aug 10, 2026 | [Apply](https://ing.wd3.myworkdayjobs.com/icsgblcor/job/New-York/Summer-2027-Internship---Tech--Information-Security-_REQ-10119620) |
| ING | Summer 2027 Internship - Tech (Infrastructure) | Software | New York | Python, Azure, Git | Aug 10, 2026 | [Apply](https://ing.wd3.myworkdayjobs.com/icsgblcor/job/New-York/Summer-2027-Internship---Tech--Infrastructure-_REQ-10119621) |
| General Dynamics Information Technology ✓ | PTOC  AI/Machine Learning Internship -DC Metro Area 🇺🇸 | Data & ML/AI | USA VA Falls Church | Python | Aug 07, 2026 | [Apply](https://gdit.wd5.myworkdayjobs.com/external_career_site/job/USA-VA-Falls-Church/Summer-2027-AI-Machine-Learning-Internship--DC-Metro-Area_RQ225912) |
| The Nuclear Company | Summer 2027 AI/ML Engineering Intern 🇺🇸 | Data & ML/AI | Washington, DC | Python, PyTorch, LLMs, AWS | Aug 07, 2026 | [Apply](https://job-boards.greenhouse.io/thenuclearcompany/jobs/5383231008) |
| The Nuclear Company | Summer 2027 Software Engineering Intern 🇺🇸 | Software | Washington, DC | Python, Java, C++, Rust | Aug 07, 2026 | [Apply](https://job-boards.greenhouse.io/thenuclearcompany/jobs/5383236008) |
| General Dynamics Information Technology ✓ | Summer 2027 Software Developer Internship 🇺🇸 _(4 openings)_ | Software | USA MD Annapolis Junction | Python, Java, C++, Rust | Aug 06, 2026 | [Apply](https://gdit.wd5.myworkdayjobs.com/external_career_site/job/USA-MD-Annapolis-Junction/Summer-2027-Software-Developer-Internship_RQ225450-1) [#2](https://gdit.wd5.myworkdayjobs.com/external_career_site/job/USA-MD-Annapolis-Junction/Summer-2027-Software-Developer-Internship_RQ225456-1) [#3](https://gdit.wd5.myworkdayjobs.com/external_career_site/job/USA-MD-Annapolis-Junction/Summer-2027-Software-Developer-Internship_RQ225469-1) [#4](https://gdit.wd5.myworkdayjobs.com/external_career_site/job/USA-MD-Annapolis-Junction/Summer-2027-Software-Developer-Internship_RQ225717-1) |
| General Dynamics Information Technology ✓ | GDIT 2027 Summer AI / ML Internship 🇺🇸 | Data & ML/AI | USA VA Falls Church - 3150 Fairview Par… | No skills listed | Aug 05, 2026 | [Apply](https://gdit.wd5.myworkdayjobs.com/external_career_site/job/USA-VA-Falls-Church---3150-Fairview-Park-Dr-VAS095/GDIT-2027-Summer-AI---ML-Internship_RQ225401) |
| Northrop Grumman | 2027 Intern Software Engineer 🇺🇸 | Software | United States-Florida-Melbourne | No skills listed | Aug 05, 2026 | [Apply](https://ngc.wd1.myworkdayjobs.com/Northrop_Grumman_External_Site/job/United-States-Florida-Melbourne/XMLNAME-2027-Intern-Software-Engineer_R10243573) |
| Roblox ✓ | [Summer 2027] Software Engineer Intern | Software | San Mateo, CA, United States | Python, Java, C++, C# | Aug 05, 2026 | [Apply](https://careers.roblox.com/jobs/8072713?gh_jid=8072713) |
| Belvedere Trading | Software Engineer Intern - Summer 2027 | Software | Chicago, Illinois | Java, C++, C# | Aug 04, 2026 | [Apply](https://jobs.lever.co/belvederetrading/10746b3d-1760-4573-9b63-b93f5a5e4fc0) |
| Belvedere Trading | Quantitative Trading Intern - Summer 2027 | Quant | Chicago, Illinois | Python, C++, C# | Aug 04, 2026 | [Apply](https://jobs.lever.co/belvederetrading/cbde47db-c60b-4339-a8f4-a8e4f30505ab) |
| JPMorganChase ✓ | 2027 Quantitative Research – Markets – Summer Internship - Analyst – United States | Quant | New York, NY, United States | Python, C++ | Aug 04, 2026 | [Apply](https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/210774038) |
| JPMorganChase ✓ | 2027 Quantitative Research – Markets – Summer Internship - Associate– United States | Quant | New York, NY, United States | Python, C++ | Aug 04, 2026 | [Apply](https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/210774061) |
| JPMorganChase ✓ | 2027 Quantitative Research – Asset Management – Summer Internship – Analyst - United States | Quant | New York, NY, United States | Python, Java, C++, SQL | Aug 04, 2026 | [Apply](https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/210774074) |
| Pentair | IT & Cybersecurity Leadership Development Internship Program -  Summer 2027 🛂 | Security | Golden Valley, MN | No skills listed | Aug 03, 2026 | [Apply](https://pentair.wd5.myworkdayjobs.com/pentair_careers/job/Golden-Valley-MN/IT---Cybersecurity-Leadership-Development-Internship-Program----Summer-2027_R23700) |
| HPR (Hyannis Port Research) | Software Engineering Intern - Summer 2027 | Software | Needham, MA | Python, Java, Bash, Linux | Aug 01, 2026 | [Apply](https://job-boards.greenhouse.io/hyannisportresearch/jobs/7822989003) |
| Melius | Software Engineering Intern [Spring/Summer 2027] | Software | New York City | TypeScript, LLMs, React, Next.js | Jul 31, 2026 | [Apply](https://jobs.ashbyhq.com/melius/b61f063a-4f94-4e50-a4ef-05aaab552280) |
| Heliux | Software Engineer (Internship, Summer 2027) | Software | HQ (San Francisco, CA) | Python, Java, Rust, TypeScript | Jul 31, 2026 | [Apply](https://jobs.ashbyhq.com/heliux/ff2b6f4b-00d0-4afe-b4f5-2dbf443409ef) |
| Appian ✓ | Information Security Engineer Intern 🛂 | Security | McLean, Virginia | LLMs | Jul 27, 2026 | [Apply](https://job-boards.greenhouse.io/appian/jobs/8088496) |
| PDT Partners | Summer 2027 Software Engineering Intern | Software | New York, NY | No skills listed | Jul 24, 2026 | [Apply](https://job-boards.greenhouse.io/pdtpartners/jobs/8077685) |
| Quadrillion | Software Engineering Intern (Summer 2027) | Software | New York City | Python, Pandas, React | Jul 24, 2026 | [Apply](https://jobs.ashbyhq.com/quadrillion-labs/a4acc44c-31ce-41a0-ab44-2500487b4d05) |
| Appian ✓ | Software Engineering Intern 🛂 | Software | McLean, Virginia | LLMs | Jul 23, 2026 | [Apply](https://job-boards.greenhouse.io/appian/jobs/8041237) |
| Virtu Financial | 2027 Internship - Quantitative Trading | Quant | Austin, TX; Chicago; New York | Python, Java, C++, SQL | Jul 21, 2026 | [Apply](https://job-boards.greenhouse.io/virtu/jobs/8624408002) |
| Virtu Financial | 2027 Internship - Frontend Engineer (UI) | Software | New York | Python, Java, C++, JavaScript | Jul 21, 2026 | [Apply](https://job-boards.greenhouse.io/virtu/jobs/8657500002) |
| Chicago Trading Company | Quant Trading Internship - Summer 2027 | Quant | Chicago, Illinois, United States | Python | Jul 20, 2026 | [Apply](https://job-boards.greenhouse.io/ctccampusboard/jobs/4708188005) |
| Axon | 2027 US Software Engineering Internship | Software | Seattle, Washington, United States | Python, Java, C#, SQL | Jul 20, 2026 | [Apply](https://job-boards.greenhouse.io/axontalentcommunity/jobs/7837133003) |
| Chicago Trading Company | Software Engineering Internship - Summer 2027 | Software | Chicago, Illinois, United States | Python, Java, C++ | Jul 20, 2026 | [Apply](https://job-boards.greenhouse.io/ctccampusboard/jobs/4708230005) |
| Deepgram 🆁 | Software Engineering- Internship (Fall 2026/Summer 2027) _(also open for Fall 2026)_ | Software | USA / Remote | LLMs | Jul 17, 2026 | [Apply](https://jobs.ashbyhq.com/deepgram/dc8693b5-72ce-4ca3-ab15-9c8434d35da1) |
| Old Mission Capital | Software Engineer – 2027 Internship Program (June Start) | Software | Chicago, IL, United States | Python, C++, TypeScript | Jul 15, 2026 | [Apply](https://www.oldmissioncapital.com/careers/?gh_jid=7796180003) |
| The Trade Desk ✓ | 2027 North America Software Engineering Internship | Software | Bellevue +5 more | No skills listed | Jul 15, 2026 | [Apply](https://job-boards.greenhouse.io/thetradedesk/jobs/5187605007) |
| Five Rings | Summer Intern 2027 - Quantitative Trader | Quant | New York | No skills listed | Jul 14, 2026 | [Apply](https://job-boards.greenhouse.io/fiveringsllc/jobs/5139668008) |
| Five Rings | Summer Intern 2027 - Software Developer | Software | New York | Python, C++, Linux | Jul 14, 2026 | [Apply](https://job-boards.greenhouse.io/fiveringsllc/jobs/5349707008) |
| Akuna Capital ✓ | Quantitative Research Intern, Summer 2027 | Quant | Chicago, IL | Python | Jul 13, 2026 | [Apply](https://www.akunacapital.com/careers/job/8036614/?gh_jid=8036614) |
| Hudson River Trading ✓ | Algorithm Development (Quant Research & Trading) Internship – Summer 2027 | Quant | London +5 more | Python, C++, MATLAB, Pandas | Jul 13, 2026 | [Apply](https://www.hudsonrivertrading.com/careers/job/?gh_jid=7964062) |
| Akuna Capital ✓ | Software Engineer Intern - C++, Summer 2027 | Software | Chicago, IL | C++, Python | Jul 13, 2026 | [Apply](https://www.akunacapital.com/careers/job/8018847/?gh_jid=8018847) |
| Akuna Capital ✓ | Software Engineer Intern - Python, Summer 2027 | Software | Chicago, IL | Python | Jul 13, 2026 | [Apply](https://www.akunacapital.com/careers/job/8018853/?gh_jid=8018853) |
| Hudson River Trading ✓ | Software Engineering Internship (C++ or Python) – Summer 2027 | Software | Austin +11 more | Python, C++ | Jul 13, 2026 | [Apply](https://www.hudsonrivertrading.com/careers/job/?gh_jid=8052083) |
| Flow Traders | Quantitative Trading Intern Summer 2027 | Quant | New York | No skills listed | Jul 08, 2026 | [Apply](https://job-boards.greenhouse.io/flowtraders/jobs/8047166) |
| Tower Research Capital ✓ | Quantitative Trader/Researcher Intern - Summer 2027 | Quant | New York, Chicago | Python, C++, Linux | Jul 05, 2026 | [Apply](https://www.tower-research.com/open-positions/?gh_jid=8024128) |
| Tower Research Capital ✓ | Quantitative Developer Intern - Summer 2027 | Quant | New York, Chicago | Python, C++, Linux | Jul 05, 2026 | [Apply](https://www.tower-research.com/open-positions/?gh_jid=8044334) |
| IMC Trading ✓ | Quantitative Trader Intern - Summer 2027 | Quant | Chicago, United States | Python, MATLAB | Jul 01, 2026 | [Apply](https://job-boards.eu.greenhouse.io/imc/jobs/4823923101) |
| IMC Trading ✓ | Quantitative Research Intern (BS/MS) - Summer 2027 | Quant | Chicago, United States | Python, C++ | Jul 01, 2026 | [Apply](https://job-boards.eu.greenhouse.io/imc/jobs/4907399101) |
| IMC Trading ✓ | Software Engineer Intern - Summer 2027 | Software | Chicago, United States | Java, C++ | Jul 01, 2026 | [Apply](https://job-boards.eu.greenhouse.io/imc/jobs/4823924101) |
| Voloridge | Quantitative Research Intern 2027 | Quant | Jupiter, FL | Python | Jun 11, 2026 | [Apply](https://job-boards.greenhouse.io/voloridgeinvestmentmanagement/jobs/4226247009) |
| Voloridge | Quantitative Developer Intern 2027 | Quant | Jupiter, FL | Python, C++, C#, SQL | Jun 11, 2026 | [Apply](https://job-boards.greenhouse.io/voloridgeinvestmentmanagement/jobs/4224862009) |
| Anduril | 2027 Software Engineer Intern 🇺🇸 | Software | Atlanta +26 more | Python, Java, C++, Rust | Jun 10, 2026 | [Apply](https://boards.greenhouse.io/andurilindustries/jobs/5148079007?gh_jid=5148079007) |
| Walleye Capital | Quantic – Quantitative Developer Intern (Summer 2027) | Quant | Boston, MA | Python, Bash, PyTorch, TensorFlow | Jun 01, 2026 | [Apply](https://job-boards.greenhouse.io/walleyecapital-external-students/jobs/4679168006) |
| Ellipsis Labs | Software Engineer - 2027 Interns | Software | New York, New York | Python, Java, C++, Rust | Mar 26, 2026 | [Apply](https://jobs.ashbyhq.com/ellipsislabs/02136b22-35b1-4b3d-8bef-567c3380a849) |
| Virtu Financial | 2027 Internship - Quantitative Researcher (Undergrad) | Quant | New York | Python, C++, Pandas | Sep 12, 2025 | [Apply](https://job-boards.greenhouse.io/virtu/jobs/8142539002) |
| Point72 ✓ | Summer 2027 Quantitative Research Internship | Quant | New York | Python, C++ | Aug 15, 2024 | [Apply](https://boards.greenhouse.io/point72/jobs/7297642002?gh_jid=7297642002) |

## Fall 2026  (26 employer-stated)

| Company | Role | Category | Location | Skills | Posted | Apply |
|---|---|---|---|---|---|---|
| Phoebe | Software Engineering Intern 🆕 | Software | New York City | Python, TypeScript, LLMs, React | Aug 20, 2026 | [Apply](https://jobs.ashbyhq.com/phoebe-work/1ffe3e63-2163-447e-a8b0-1fff8b87e0ca) |
| Toshiba Global Commerce | AI Software Engineering Intern 🛂 🆕 | Data & ML/AI | Durham, NC | Java, C++, JavaScript, LLMs | Aug 20, 2026 | [Apply](https://job-boards.greenhouse.io/toshibaglobalcommercesolutions/jobs/5214224007) |
| Moog | Intern, IT Computer Science | Software | Buffalo, NY | SQL | Aug 19, 2026 | [Apply](https://moog.wd5.myworkdayjobs.com/moog_external_career_site/job/Buffalo-NY/Intern--IT-Computer-Science_R-26-19378) |
| onsemi | Fall 2026 - Tax AI and Automation Intern | Data & ML/AI | Scottsdale, AZ, United States | No skills listed | Aug 14, 2026 | [Apply](https://hctz.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/2506307) |
| The Nuclear Company | Fall 2026 AI/ML Engineering Intern 🇺🇸 | Data & ML/AI | Washington, DC | Python, PyTorch, LLMs, AWS | Aug 07, 2026 | [Apply](https://job-boards.greenhouse.io/thenuclearcompany/jobs/5383163008) |
| The Nuclear Company | Fall 2026 AI Software Engineering Intern 🇺🇸 | Data & ML/AI | Washington, DC | Python, Java, C++, Rust | Aug 07, 2026 | [Apply](https://job-boards.greenhouse.io/thenuclearcompany/jobs/5383113008) |
| Johnson & Johnson | Software Engineer Coop 🛂 | Software | Cincinnati +2 more | Python, C++, Linux | Aug 07, 2026 | [Apply](https://jj.wd5.myworkdayjobs.com/JJ/job/Cincinnati-Ohio-United-States-of-America/Software-Engineer-Coop_R-092820) |
| Warner Bros. | Bleacher Report Social Programming Intern: LA - Fall 2026 | Software | CA Burbank Bldg. 700 +2 more | No skills listed | Aug 06, 2026 | [Apply](https://warnerbros.wd5.myworkdayjobs.com/global/job/CA-Burbank-Bldg-700-Second-Century-Tower-1/Bleacher-Report-Social-Programming-Intern--LA---Fall-2026_R000107469) |
| NVIDIA ✓ | Software Engineering Intern, Dynamo - Fall 2026 | Software | US, CA, Santa Clara | Python, Go, Rust, LLMs | Aug 05, 2026 | [Apply](https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/job/US-CA-Santa-Clara/Software-Engineering-Intern--Dynamo---Fall-2026_JR2022295) |
| Melius | Software Engineering Intern [Fall/Winter 2026] | Software | New York City | TypeScript, LLMs, React, Next.js | Jul 30, 2026 | [Apply](https://jobs.ashbyhq.com/melius/6a944911-dbbf-44c7-ba52-7866f7b433cf) |
| Astranis | Software Engineer Intern - Enterprise Systems (Fall 2026) 🇺🇸 | Software | San Francisco, CA | Python | Jul 23, 2026 | [Apply](https://job-boards.greenhouse.io/astranis/jobs/4699071006) |
| Red Bull | 2026 Internship, Fall - Data Science | Data & ML/AI | Morristown, NJ, United States | SQL | Jul 22, 2026 | [Apply](https://jobs.smartrecruiters.com/RedBull/744000139168339) |
| Rendezvous Robotics | Software Engineering Intern (Fall 2026) | Software | Golden, CO | Python, C++, Linux | Jul 22, 2026 | [Apply](https://job-boards.greenhouse.io/rendezvousrobotics/jobs/4328555009) |
| Deepgram 🆁 | Software Engineering- Internship (Fall 2026/Summer 2027) _(also open for Summer 2027)_ | Software | USA / Remote | LLMs | Jul 17, 2026 | [Apply](https://jobs.ashbyhq.com/deepgram/dc8693b5-72ce-4ca3-ab15-9c8434d35da1) |
| Moog | Intern, IT Computer Science - Data Analytics | Data & ML/AI | Buffalo, NY | No skills listed | Jul 16, 2026 | [Apply](https://moog.wd5.myworkdayjobs.com/moog_external_career_site/job/Buffalo-NY/Intern--IT-Computer-Science---Data-Analytics_R-26-17145) |
| NVIDIA ✓ | Applied Research Intern, NLP - Fall 2026 | Data & ML/AI | US, CA, Santa Clara | Python, PyTorch | Jul 01, 2026 | [Apply](https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/job/US-CA-Santa-Clara/Applied-Research-Intern--NLP---Fall-2026_JR2010488) |
| Junior | Software Engineering Intern — Fall 2026 🇺🇸 | Software | New York City | TypeScript, JavaScript, LLMs, Next.js | Jun 30, 2026 | [Apply](https://jobs.ashbyhq.com/junior/23ee686b-d305-4ac9-860d-16c99ddb4891) |
| Figure | Firmware Intern [Fall 2026] | Hardware | San Jose, CA | Python, C++ | Jun 22, 2026 | [Apply](https://job-boards.greenhouse.io/figureai/jobs/4691070006) |
| SoloPulse | Software Engineer Intern/Co-Op - Fall 2026 | Software | Peachtree Corners, GA | Python, C++, PyTorch, CUDA | Jun 16, 2026 | [Apply](https://jobs.lever.co/solopulseco/00fbde18-a387-4c9f-97d4-77059aec7b56) |
| Beacon Software | Software Engineering Intern | Software | San Francisco, CA | Python, TypeScript, LLMs, dbt | Jun 02, 2026 | [Apply](https://jobs.ashbyhq.com/beaconsoftware/2452d342-a069-4eda-adbe-9df296808ca1) |
| Amazon ✓ | Software Development Engineer Intern, AWS Data Services - Fall 2026 (US) | Data & ML/AI | Seattle, Washington, USA | AWS, Python, Java, C++ | May 06, 2026 | [Apply](https://www.amazon.jobs/en/jobs/10412530/software-development-engineer-intern-aws-data-services-fall-2026-us) |
| Hermeus | Software Engineering Intern (Command & Control) - Fall 2026 🇺🇸 | Software | Atlanta, GA | C++, TypeScript, JavaScript, React | Apr 01, 2026 | [Apply](https://jobs.lever.co/hermeus/a3a1f0ea-6a4f-42e5-81c8-3b34dac22a67) |
| Motorola | Intern - Embedded Software, System, and Test Engineer - 2026 🇺🇸 | Software | Irvine, CA | No skills listed | Mar 30, 2026 | [Apply](https://motorolasolutions.wd5.myworkdayjobs.com/Careers/job/Irvine-CA/Intern---Embedded-Software--System--and-Test-Engineer---2026_R62372) |
| Hermeus | Flight Software Engineering Intern - Fall 2026 🇺🇸 | Software | Atlanta, GA | C++ | Mar 04, 2026 | [Apply](https://jobs.lever.co/hermeus/51378fa0-0327-45fd-9420-b6e7d8b56440) |
| Amazon ✓ | Robotics - Software Development Engineer Intern/Co-op - 2026 | Hardware | Westboro, Massachusetts, USA | Python, Java, C++, C# | Dec 03, 2025 | [Apply](https://www.amazon.jobs/en/jobs/3136266/robotics-software-development-engineer-intern-co-op-2026) |
| Amazon ✓ | Amazon Industrial Robotics - Applied Scientist II Intern / Co-op - 2026, Amazon Industrial Robotics | Data & ML/AI | North Reading, Massachusetts, USA | Python, Java, C++, LLMs | Nov 25, 2025 | [Apply](https://www.amazon.jobs/en/jobs/3132414/amazon-industrial-robotics-applied-scientist-ii-intern-co-op-2026-amazon-industrial-robotics) |

## Recently posted — cycle not stated  (76 roles)

These postings never name a cycle — not in the title, not in the posting text — so neither do we. They're recent tech internships (posted within the last few weeks), often exactly the early drops worth applying to first; we just can't tell you which cycle they're for, and we'd rather say so than guess. The moment a posting's own text states a cycle, the role moves up into that section automatically.

| Company | Role | Category | Location | Skills | Posted | Apply |
|---|---|---|---|---|---|---|
| Ambrook | Software Engineering Intern 🆕 | Software | New York | TypeScript, React, Next.js, GCP | Aug 21, 2026 | [Apply](https://jobs.ashbyhq.com/ambrook/e458b046-aa7f-4022-bca5-63cdfd495456) |
| Weave | Data Engineer Intern 🆕 | Data & ML/AI | Weave - Headquarters (Lehi, UT) | Python, SQL, Git, Snowflake | Aug 21, 2026 | [Apply](https://jobs.ashbyhq.com/weave/1318e017-3ea6-4a1f-aac7-1c11a46cda8d) |
| Syska Hennessy Group | Innovations Intern (Full Stack/Front End Engineering) 🆕 | Software | New York | JavaScript | Aug 21, 2026 | [Apply](https://job-boards.greenhouse.io/syskahennessy/jobs/8147733) |
| Availity 🆁 | Software Engineering Intern 🆕 | Software | Remote - United States | Python, JavaScript, SQL, React | Aug 21, 2026 | [Apply](https://availity.wd1.myworkdayjobs.com/availity_careers_us/job/Remote---United-States/Software-Engineering-Intern_R0008436) |
| Brunswick ✓ | Software Engineering Intern 🛂 🆕 | Software | Tulsa, OK | Python, Java, C++, Kotlin | Aug 21, 2026 | [Apply](https://brunswick.wd1.myworkdayjobs.com/search/job/Tulsa-OK/Software-Engineering-Intern_JR-051321) |
| H3X Technologies | Embedded Controls Intern (Spring) 🆕 | Software | Louisville, Colorado | Python, C++, Git | Aug 21, 2026 | [Apply](https://jobs.ashbyhq.com/h3x-technologies/d406e4b4-9b48-438c-a2af-b7feb8563a40) |
| Microchip Technology ✓ | Intern - Engineering (Device Software and Test) 🆕 | Software | AZ - Chandler | Python, Java, C#, Linux | Aug 20, 2026 | [Apply](https://microchiphr.wd5.myworkdayjobs.com/external/job/AZ---Chandler/Intern---Engineering--Device-Software-and-Test-_R3573-26) |
| Sony | Intern, Information Security Risk and Compliance 🆕 | Security | New York | No skills listed | Aug 20, 2026 | [Apply](https://sonyglobal.wd1.myworkdayjobs.com/SonyGlobalCareers/job/New-York/Intern--Information-Security-Risk-and-Compliance_JR-119512) |
| Intel ✓ | Software Engineer Graduate Intern 🆕 | Software | US, Arizona, Phoenix | Java, C#, .NET | Aug 20, 2026 | [Apply](https://intel.wd1.myworkdayjobs.com/external/job/US-Arizona-Phoenix/Software-Engineer-Graduate-Intern_JR0286489) |
| Intel ✓ | Software Engineer Graduate Intern 🆕 | Software | US, Oregon, Hillsboro | Python, C#, .NET | Aug 20, 2026 | [Apply](https://intel.wd1.myworkdayjobs.com/external/job/US-Oregon-Hillsboro/Software-Engineer-Graduate-Intern_JR0286491) |
| E-Space | Embedded Software Engineering Intern | Software | Arlington, TX | Python, Git | Aug 20, 2026 | [Apply](https://jobs.lever.co/espace/1e189295-a315-414d-8c0b-686f204e3cb3) |
| Western Magnetics | Software Engineering Intern | Software | South San Francisco +2 more | Python, TypeScript, JavaScript, LLMs | Aug 20, 2026 | [Apply](https://apply.workable.com/western-magnetics/j/E366930F3F/) |
| Fooji | Software Engineering Intern 🆕 | Software | Lexington, Kentucky, United States | TypeScript, JavaScript, SQL, Node.js | Aug 19, 2026 | [Apply](https://apply.workable.com/fooji/j/6563DA99B5/) |
| Copart ✓ | Site Reliability Engineer Intern | Software | Dallas, TX - Headquarters | Python, AWS, GCP, Kubernetes | Aug 19, 2026 | [Apply](https://copart.wd12.myworkdayjobs.com/copart/job/Dallas-TX---Headquarters/Site-Reliability-Engineer-Intern_JR110631) |
| N1 | Software Engineer Intern (Backend, Rust) | Software | New York City | Rust, C++ | Aug 19, 2026 | [Apply](https://jobs.ashbyhq.com/n1/afe7deb5-9cfd-4926-bcb4-058d418592a6) |
| Detroit Lions | Quantitative Research Intern | Quant | Allen Park, MI 48101 | Python | Aug 19, 2026 | [Apply](https://job-boards.greenhouse.io/detroitlions/jobs/4723291005) |
| Garda Capital Partners | Software Engineer Intern | Software | New York, New York, United States | Python, SQL | Aug 18, 2026 | [Apply](https://job-boards.greenhouse.io/gardacp/jobs/6146213004) |
| Sherwin-Williams ✓ | Year-Round IT Database Engineer Co-Op | Software | Cleveland, OH, United States | No skills listed | Aug 18, 2026 | [Apply](https://ejhp.fa.us6.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2/job/2621017) |
| Amcor | Intern - AI Innovation Engineer | Data & ML/AI | ASC Atlanta HQ GA | Python, C#, TypeScript, JavaScript | Aug 18, 2026 | [Apply](https://amcor.wd5.myworkdayjobs.com/amcor_external_career_site/job/ASC-Atlanta-HQ-GA/AI-Innovation-Engineer_REQ_93190) |
| Intel ✓ | Software Development Graduate Intern | Software | US, California, Folsom | Python, C++, PyTorch, TensorFlow | Aug 17, 2026 | [Apply](https://intel.wd1.myworkdayjobs.com/external/job/US-California-Folsom/Software-Development-Graduate-Intern_JR0285451-1) |
| ACDS | Align AI Software Development Intern | Data & ML/AI | Bentonville, AR | Python, TypeScript, JavaScript | Aug 17, 2026 | [Apply](https://jobs.lever.co/acds/5a872bb7-8d9f-46e3-9e72-f5c69445e787) |
| Photon 🆁 | Software Engineering / AI Intern - US - Remote | Data & ML/AI | United States | No skills listed | Aug 15, 2026 | [Apply](https://fa-ertb-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2/job/26738) |
| ONEOK | Cyber Security Intern - Tulsa, OK | Security | Tulsa, OK | No skills listed | Aug 14, 2026 | [Apply](https://oneok.wd1.myworkdayjobs.com/ONEOK_Early_Careers/job/Tulsa-OK/Cyber-Security-Intern---Tulsa--OK_R8449) |
| First American 🆁 | Software Engineering Intern _(2 openings)_ | Software | USA, California, Remote | Python, C#, TypeScript, SQL | Aug 14, 2026 | [Apply](https://firstam.wd1.myworkdayjobs.com/firstamericancareers/job/USA-California-Remote/Software-Engineering-Intern_R058261) [#2](https://firstam.wd1.myworkdayjobs.com/firstamericancareers/job/USA-California-Remote/Software-Engineering-Intern_R058260) |
| Crowe ✓ | Data Analytics Developer Intern | Data & ML/AI | Chicago IL USA | SQL, Azure, Tableau | Aug 14, 2026 | [Apply](https://crowe.wd12.myworkdayjobs.com/external_careers/job/Chicago-IL-USA/Data-Analytics-Developer-Intern_R-71041) |
| Valeo | Software Engineer Intern | Software | Troy, MI | Python, C++, Linux | Aug 14, 2026 | [Apply](https://valeo.wd3.myworkdayjobs.com/valeo_jobs/job/Troy-MI/Software-Engineer-Intern_REQ2026076575) |
| Generac | Intern Firmware Engineering | Hardware | Reno, NV - USA | Python, C++, Git | Aug 14, 2026 | [Apply](https://generac.wd5.myworkdayjobs.com/external/job/Reno-NV---USA/Intern-Firmware-Engineering_JR16149) |
| TransMarket Group | Software Engineering Intern | Software | Chicago, Illinois, United States | Python, C++, Linux | Aug 14, 2026 | [Apply](https://job-boards.greenhouse.io/transmarketgroup/jobs/5212335007?gh_jid=5212335007) |
| Crowe ✓ | AI Project Coordinator Intern | Data & ML/AI | Chicago IL USA | LLMs, Azure | Aug 14, 2026 | [Apply](https://crowe.wd12.myworkdayjobs.com/external_careers/job/Chicago-IL-USA/AI-Project-Coordinator-Intern_R-71007) |
| Interco | Paid Internship -- Software Development -- React 🛂 | Software | St. Louis, MO, United States | React, JavaScript, HTML/CSS | Aug 13, 2026 | [Apply](https://jobs.smartrecruiters.com/Interco/744000143346169) |
| Crowe ✓ | AI Engineering Intern | Data & ML/AI | Chicago IL USA | Python, PyTorch, TensorFlow, LLMs | Aug 13, 2026 | [Apply](https://crowe.wd12.myworkdayjobs.com/external_careers/job/Chicago-IL-USA/AI-Engineering-Intern_R-51782) |
| Exa Labs | Software Engineer, Intern | Software | San Francisco, California | C++, Rust | Aug 13, 2026 | [Apply](https://jobs.ashbyhq.com/exa/a9e01521-66f1-481b-89da-ec01d4620f16) |
| ConnectPrep 🆁 | Data Analyst Internship 🇺🇸 | Data & ML/AI | Washington +2 more | Python, SQL, Pandas, Tableau | Aug 13, 2026 | [Apply](https://apply.workable.com/connectprep/j/D1C67258C0/) |
| Securityriskadvisors | DevOps Engineering Generalist Co-op | Software | Rochester, New York, United States | Python, Java, C++, C# | Aug 12, 2026 | [Apply](https://apply.workable.com/securityriskadvisors/j/3B23FB7BEB/) |
| Oracle | Platform Software Engineer 1 - Full-time Intern Conversion | Software | United States | C++, JavaScript, SQL | Aug 12, 2026 | [Apply](https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_45001/job/342415) |
| American Fidelity | Software Dev Internship (OKC local only) | Software | Oklahoma City, Oklahoma | No skills listed | Aug 12, 2026 | [Apply](https://americanfidelity.wd5.myworkdayjobs.com/External/job/Oklahoma-City-Oklahoma/Software-Dev-Internship_JR1005) |
| Marmon Holdings | AI Project Management Intern | Data & ML/AI | Chicago, IL | No skills listed | Aug 12, 2026 | [Apply](https://marmon.wd501.myworkdayjobs.com/Marmon_Careers/job/Chicago-IL/AI-Project-Management-Intern_JR0000045089-1) |
| Copart ✓ | Data Analytics Engineer Intern | Data & ML/AI | Dallas, TX - Headquarters | No skills listed | Aug 11, 2026 | [Apply](https://copart.wd12.myworkdayjobs.com/copart/job/Dallas-TX---Headquarters/Data-Analytics-Engineer-Intern_JR110584) |
| Bosch ✓ | Powertrain Controls Software Engineering Intern (6-Months, Full-Time) | Software | Farmington Hills, MI, United States | MATLAB, Linux | Aug 11, 2026 | [Apply](https://jobs.smartrecruiters.com/BoschGroup/744000142898574) |
| Booz Allen | AI RAN Telecommunications Engineer Intern 🇺🇸 _(2 openings)_ | Data & ML/AI | McLean, VA | Python, C++, PyTorch, TensorFlow | Aug 10, 2026 | [Apply](https://bah.wd1.myworkdayjobs.com/bah_jobs/job/McLean-VA/AI-RAN-Telecommunications-Engineer-Intern_R0246415) [#2](https://bah.wd1.myworkdayjobs.com/bah_jobs/job/McLean-VA/AI-RAN-Telecommunications-Engineer-Intern_R0246869) |
| Canadian Solar | Intern, IT Infrastructure Support | Software | Walnut Creek, CA | Azure | Aug 10, 2026 | [Apply](https://canadiansolar.wd5.myworkdayjobs.com/CanadianSolar/job/Walnut-Creek-CA/Intern--IT-Infrastructure-Support_10001383) |
| Copart ✓ | Database Engineering Intern | Software | Dallas, TX - Headquarters | Python, JavaScript, SQL, Pandas | Aug 07, 2026 | [Apply](https://copart.wd12.myworkdayjobs.com/copart/job/Dallas-TX---Headquarters/Database-Engineering-Intern_JR109636) |
| Centerfield | Frontend Engineer Intern (6 month internship) | Software | Los Angeles, California | Java, TypeScript, JavaScript, React | Aug 06, 2026 | [Apply](https://jobs.ashbyhq.com/centerfield/1d7eacc1-37f7-478c-9b0a-fa7974f1a9e4) |
| Nokia | AI R&D Engineer Co-op _(3 openings)_ | Data & ML/AI | United States | PyTorch, TensorFlow, Kafka | Aug 06, 2026 | [Apply](https://fa-evmr-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/39284) [#2](https://fa-evmr-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/39285) [#3](https://fa-evmr-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/39286) |
| Nokia | AI R&D Engineering Co-op _(2 openings)_ | Data & ML/AI | United States | PyTorch, TensorFlow, Kafka | Aug 06, 2026 | [Apply](https://fa-evmr-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/39287) [#2](https://fa-evmr-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/39288) |
| KBR ✓ | Software Intern | Software | Houston, Texas | Python, C#, JavaScript, HTML/CSS | Aug 06, 2026 | [Apply](https://kbr.wd5.myworkdayjobs.com/KBR_Careers/job/Houston-Texas/Software-Intern_R2127863) |
| Draper | Embedded Quality & Fielded Systems Intern | Software | Cambridge, MA | Python, C# | Aug 05, 2026 | [Apply](https://draper.wd5.myworkdayjobs.com/Draper_Careers/job/Cambridge-MA/Embedded-Quality---Fielded-Systems-Intern_JR002718) |
| PlusAI ✓ | Deep Learning Research Intern — Multimodal BEV Perception | Data & ML/AI | Santa Clara, CA | Python, PyTorch, TensorFlow, Computer Vision | Aug 04, 2026 | [Apply](https://jobs.lever.co/plus-2/2ee24f85-bfa1-47fc-bfe3-fd07521a7b62) |
| Thales | AppSec Product Support Intern | Security | Texas | No skills listed | Aug 04, 2026 | [Apply](https://thales.wd3.myworkdayjobs.com/careers/job/Texas/AppSec-Product-Support-Intern_R0328978-1) |
| Diversified Automation | Software Engineering Co-op | Software | Louisville, KY | No skills listed | Aug 04, 2026 | [Apply](https://jobs.lever.co/diversified-automation/827a092d-b8a3-4ca9-a84a-e8c236d1aabc) |
| IDEXX | Security Operations (Cybersecurity) internship | Security | Westbrook, ME | No skills listed | Aug 03, 2026 | [Apply](https://idexx.wd1.myworkdayjobs.com/IDEXX/job/Westbrook-ME/Security-Operations--Cybersecurity--internship_J-053268) |
| Microchip Technology ✓ | Intern-Engineering (Firmware Development) | Hardware | TX - Houston - Compaq Center Dr | Python, Java, C++, C# | Aug 03, 2026 | [Apply](https://microchiphr.wd5.myworkdayjobs.com/external/job/TX---Houston---Compaq-Center-Dr/Intern-Engineering--Firmware-Development-_R3372-26) |
| Bosch ✓ | AI and SW Development Engineering Intern | Data & ML/AI | Plymouth, MI, United States | Python, C++, Computer Vision, Git | Aug 03, 2026 | [Apply](https://jobs.smartrecruiters.com/BoschGroup/744000141302469) |
| Microchip Technology ✓ | Intern-Engineering (Software Development) | Software | TX - Houston - Compaq Center Dr | Python, Java, C++, C# | Aug 03, 2026 | [Apply](https://microchiphr.wd5.myworkdayjobs.com/external/job/TX---Houston---Compaq-Center-Dr/Intern-Engineering--Software-Development-_R3371-26) |
| Yotta Labs | Research Engineer Intern - AI Systems | Data & ML/AI | United States | Python, C++, PyTorch, LLMs | Aug 02, 2026 | [Apply](https://jobs.ashbyhq.com/yotta/09821a51-fbe6-42a7-a566-0d2b5d40fae3) |
| Leidos ✓ | Application Developer Intern 🇺🇸 | Software | Indianapolis, IN | Python, JavaScript, SQL, React | Jul 29, 2026 | [Apply](https://leidos.wd5.myworkdayjobs.com/External/job/Indianapolis-IN/Application-Developer-Intern_R-00188193-1) |
| Modal | ML Research Intern | Data & ML/AI | New York | Git | Jul 28, 2026 | [Apply](https://jobs.ashbyhq.com/modal/38888294-6bc7-4dab-b072-6d0f0c2ed79a) |
| Bosch ✓ | ADAS Software Engineering Intern | Software | Plymouth, MI, United States | Python, C++, Computer Vision | Jul 28, 2026 | [Apply](https://jobs.smartrecruiters.com/BoschGroup/744000140317669) |
| Nelnet | Intern Program - Agentic AI | Data & ML/AI | Lincoln, NE | Python, Java, PyTorch, TensorFlow | Jul 27, 2026 | [Apply](https://nelnet.wd1.myworkdayjobs.com/MyNelnet/job/Lincoln-NE/Intern-Program---Agentic-AI_R22904) |
| Core & Main | Intern - AI/ML Data Engineering  -  Onsite - St. Louis | Data & ML/AI | Saint Louis, MO 63146 | Python, SQL, scikit-learn, Pandas | Jul 24, 2026 | [Apply](https://coreandmain.wd1.myworkdayjobs.com/coreandmain/job/Saint-Louis-MO-63146/Intern---Data-Engineering----Corp_45804) |
| Magna International ✓ | R&D- Computer Vision Engineering Intern | Data & ML/AI | Troy, Michigan, US | Computer Vision, Python, PyTorch, TensorFlow | Jul 24, 2026 | [Apply](https://magna.wd3.myworkdayjobs.com/Magna/job/Troy-Michigan-US/R-D--Computer-Vision-Engineering-Intern_R00253444-1) |
| Tenstorrent | Software Engineering Intern, Power Modeling & AI Tools | Data & ML/AI | Santa Clara, California, United States | Python, SQL, LLMs, Git | Jul 23, 2026 | [Apply](https://job-boards.greenhouse.io/tenstorrentuniversity/jobs/5186916007) |
| Pony.ai ✓ | Research Intern - Deep Learning | Data & ML/AI | Fremont, California, United States | Python, C++, LLMs, CUDA | Jul 22, 2026 | [Apply](https://apply.workable.com/pony-dot-ai/j/4C1F53EF5D/) |
| Pony.ai ✓ | Software Engineer Intern - Generalist | Software | Fremont, California, United States | Python, C++ | Jul 22, 2026 | [Apply](https://apply.workable.com/pony-dot-ai/j/BA5FFDBC71/) |
| Moog | Intern, Software Engineering | Software | Buffalo, NY | No skills listed | Jul 22, 2026 | [Apply](https://moog.wd5.myworkdayjobs.com/moog_external_career_site/job/Buffalo-NY/Intern--Software-Engineering_R-26-18885-1) |
| ACDS | AI Operations Intern-Caddell Reynolds | Data & ML/AI | Fort Smith, AR | LLMs | Jul 20, 2026 | [Apply](https://jobs.lever.co/acds/01fdf41b-a835-4e00-8d01-0275677a8f08) |
| WallStreetQuants | Quantitative Researcher - Internship | Quant | New York, New York, United States | Python, SQL, scikit-learn, Pandas | Jul 15, 2026 | [Apply](https://apply.workable.com/wallstreetquants/j/494E392FD3/) |
| WallStreetQuants | Quantitative Trading Intern | Quant | Miami, Florida, United States | Python | Jul 15, 2026 | [Apply](https://apply.workable.com/wallstreetquants/j/8CB119E789/) |
| Tencent | Research Intern – Video World Models (Research & ML Systems) | Data & ML/AI | US-California-Palo Alto | Python, PyTorch, LLMs, CUDA | Jul 15, 2026 | [Apply](https://tencent.wd1.myworkdayjobs.com/Tencent_Careers/job/US-California-Palo-Alto/Research-Intern---Video-World-Models--Research---ML-Systems-_R107752-1) |
| DRW ✓ | Quantitative Trading Analyst Intern | Quant | Chicago, Illinois | Python | Jul 13, 2026 | [Apply](https://job-boards.greenhouse.io/drweng/jobs/7668776) |
| DRW ✓ | Quantitative Research Intern | Quant | Chicago, New York City | Python, scikit-learn, Pandas | Jul 13, 2026 | [Apply](https://job-boards.greenhouse.io/drweng/jobs/7818540) |
| Xsolla | AI-First Engineering Intern | Data & ML/AI | Raleigh, United States | Git | Jul 10, 2026 | [Apply](https://jobs.lever.co/xsolla/5d5fd6b3-d82f-437a-b251-abf4674ac874) |
| Xsolla | AI-First Engineering Intern | Data & ML/AI | Los Angeles, United States | Git | Jul 10, 2026 | [Apply](https://jobs.lever.co/xsolla/1c0e5375-2352-4a2c-a816-48ddebbdd3d6) |
| Jump Trading ✓ | Campus Quantitative Trader (Intern) | Quant | Chicago; New York | No skills listed | Jul 08, 2026 | [Apply](https://www.jumptrading.com/hr/job?gh_jid=7848371) |
| Jump Trading ✓ | Campus Quantitative Researcher, UG/MS (Intern) | Quant | Chicago; New York | Python, C++ | Jul 08, 2026 | [Apply](https://www.jumptrading.com/hr/job?gh_jid=7982648) |
| Jump Trading ✓ | Campus AI Research Engineer (Intern) | Data & ML/AI | Chicago; New York | Python, C++, PyTorch, TensorFlow | Jul 08, 2026 | [Apply](https://www.jumptrading.com/hr/job?gh_jid=8052281) |

<a id="drop-radar"></a>

## 📅 Drop Radar — when companies usually post for Summer 2027

Stop refreshing career pages. 🎯 = the employer's **own posted date**, read from their careers API. (We may have discovered the role after it went live — the date is the employer's, not our discovery time.) The rest are typical opening **months**, hand-checked against each company's careers page and public recruiting guides. ✅ = already live in the list above.

> **Heads up:** companies trend *earlier* every cycle, and "~Aug" is a month, not a day. Treat "expected" as when to **start watching**, and "rolling" companies as worth checking year-round.

| Company | Typical opening | Expected this cycle | Status |
|---|---|---|---|
| Accenture | ~Aug | ~Aug · any day now | ⏳ waiting |
| AQR Capital Management | ~Aug | ~Aug · any day now | ⏳ waiting |
| Atlassian | ~Aug | ~Aug · any day now | ⏳ waiting |
| Bridgewater Associates | ~Aug | ~Aug · any day now | ⏳ waiting |
| Cisco | ~Aug | ~Aug · any day now | ⏳ waiting |
| Citadel | ~Aug | ~Aug · any day now | ⏳ waiting |
| Databricks | ~Aug | ~Aug · any day now | ⏳ waiting |
| DoorDash | ~Aug | ~Aug · any day now | ⏳ waiting |
| DRW | ~Aug | ~Aug · any day now | ⏳ waiting |
| Figma | ~Aug | ~Aug · any day now | ⏳ waiting |
| Google | ~Aug | ~Aug · any day now | ⏳ waiting |
| Intuit | ~Aug | ~Aug · any day now | ⏳ waiting |
| Jane Street | ~Aug | ~Aug · any day now | ⏳ waiting |
| John Deere | ~Aug | ~Aug · any day now | ⏳ waiting |
| Mastercard | ~Aug | ~Aug · any day now | ⏳ waiting |
| Meta | ~Aug | ~Aug · any day now | ⏳ waiting |
| Optiver | ~Aug | ~Aug · any day now | ⏳ waiting |
| Pinterest | ~Aug | ~Aug · any day now | ⏳ waiting |
| Salesforce | ~Aug | ~Aug · any day now | ⏳ waiting |
| SIG | ~Aug | ~Aug · any day now | ⏳ waiting |
| Snowflake | ~Aug | ~Aug · any day now | ⏳ waiting |
| Target | ~Aug | ~Aug · any day now | ⏳ waiting |
| Tesla | ~Aug | ~Aug · any day now | ⏳ waiting |
| Uber | ~Aug | ~Aug · any day now | ⏳ waiting |
| Visa | ~Aug | ~Aug · any day now | ⏳ waiting |
| Walmart | ~Aug | ~Aug · any day now | ⏳ waiting |
| 3M | ~Sep | ~Sep · in ~10d | ⏳ waiting |
| Adobe | ~Sep | ~Sep · in ~10d | ⏳ waiting |
| Airbnb | ~Sep | ~Sep · in ~10d | ⏳ waiting |
| AMD | ~Sep | ~Sep · in ~10d | ⏳ waiting |

_202 companies on the [full radar](https://zshah101.github.io/Automated-List-Of-Summer-2027-and-Fall-2026-Tech-Internships/#radar). **68** dated from our own live observations 🎯 (this grows every cycle). "~Aug" = hand-verified typical month, not a promise of the day; "rolling" = posts year-round; "waiting" = not seen in our tracked feeds yet, not a guarantee it isn't out somewhere else._

<details>
<summary><strong>Recently closed</strong> — 23 roles that left the list in the last 14 days</summary>

_Why each one left is in the last column, because the two reasons carry different evidence. **Gone from feed** = two consecutive complete reads of the employer's board no longer returned it (strong, but not the employer telling us directly). **Out of scope** = still posted, but it no longer passes our filters — our call, not theirs. **Not recorded** = closed before we started tracking the reason._

| Company | Role | Cycle | Closed | Why |
|---|---|---|---|---|
| Louisiana Blue | Healthcare Price and Transparency Data Analyst Intern | Fall 2026 | 2026-08-21 | gone from feed |
| Astranis | Software Engineer- Backend Intern (Fall 2026) | Fall 2026 | 2026-08-21 | gone from feed |
| General Dynamics Information Technology | Summer 2027 Software Development Internship | Summer 2027 | 2026-08-20 | gone from feed |
| Axon | US Firmware Engineering Internship | Summer 2027 | 2026-08-20 | gone from feed |
| InfiniteQuant | Quantitative Researcher - Internship - Summer 2027 | Summer 2027 | 2026-08-20 | gone from feed |
| Redwood Materials | Embedded Software Engineer Intern - Fall 2026 | Fall 2026 | 2026-08-20 | gone from feed |
| InfiniteQuant | Quantitative Developer - Internship - Summer 2027 | Summer 2027 | 2026-08-19 | gone from feed |
| Northrop Grumman | 2027 Intern Software Engineer | Summer 2027 | 2026-08-18 | out of scope |
| Sentry | Software Engineer, Intern (Summer 2027) | Summer 2027 | 2026-08-17 | gone from feed |
| CCC Intelligent Solutions | R&D & Data Science Internship Fall 2026 | Fall 2026 | 2026-08-17 | gone from feed |
| Intuitive Surgical | Computer Vision Engineering Intern - Fall 2026 | Fall 2026 | 2026-08-17 | gone from feed |
| Walleye Capital | Equity Volatility Quant Researcher Intern (Summer 2027) | Summer 2027 | 2026-08-15 | gone from feed |
| SharkNinja | Fall 2026: AI/Sharks Applied AI & Analytics Co-op (August to December) | Fall 2026 | 2026-08-14 | gone from feed |
| Saronic | Software Engineer Intern (Fall 2026) | Fall 2026 | 2026-08-13 | gone from feed |
| InfiniteQuant | Quantitative Researcher - Internship - Summer 2027 | Summer 2027 | 2026-08-13 | gone from feed |
| InfiniteQuant | Quantitative Researcher - Internship - Summer 2027 | Summer 2027 | 2026-08-13 | gone from feed |
| Assured Guaranty | Fall 2026 Intern - Product Software Developer | Fall 2026 | 2026-08-13 | gone from feed |
| Western Digital | Summer 2027 - Software Engineering Internship | Summer 2027 | 2026-08-12 | gone from feed |
| Densityai | Technical Intern- Software  (Fall 2026) | Fall 2026 | 2026-08-12 | gone from feed |
| Northrop Grumman | 2027 Intern Software Engineer | Summer 2027 | 2026-08-11 | out of scope |
| TMEIC | Intern - Applications, AI and Machine Learning (Fall 2026) (ET26021) | Fall 2026 | 2026-08-10 | gone from feed |
| CNO Financial Group | Artificial Intelligence (AI) IT Intern 2027 - REMOTE | Summer 2027 | 2026-08-10 | out of scope |
| InfiniteQuant | Quantitative Researcher - Internship - Summer 2027 | Summer 2027 | 2026-08-10 | gone from feed |

</details>

---

## Hiring timeline

Internships posted per week, from each role's real published date - redrawn automatically on every run. When this line takes off, recruiting season is open:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/trends-dark.svg">
  <img alt="Internships posted per week, drawn from real published dates" src="docs/trends-light.svg">
</picture>

## How it stays current

A small Python engine reads public company hiring feeds directly, keeps the roles that match the scope above, de-duplicates across sources, records each role's published date once (so it never shifts), and regenerates this page through GitHub Actions. It polls every company concurrently (async) with retry/backoff and per-host rate limits. The full source is in this repo.

_Engine (last run): 4,124 of 4,514 registered boards returned successfully across 12 ATS platforms (98% of boards attempted, 91% of the full registry) · completed in 948.5s · 531 board(s) returned a capped result set, so their roles were not eligible to be closed this run · employer or source-derived date on 100% of open roles._

## How this list is built

[METHODOLOGY.md](METHODOLOGY.md) documents exactly what every label claims — what separates a stated cycle from an inferred one, what the ✓ H-1B badge does and doesn't mean, how a role gets closed, and which limitations are known. Anything on this page that doesn't match the code is a bug worth reporting.

## Contributing

Adding a company takes one line, see [CONTRIBUTING.md](CONTRIBUTING.md), or just [open a request](../../issues/new?template=add-company.yml) with the board URL. **Spotted something wrong?** [Report the exact field](../../issues/new?template=wrong-data.yml) — wrong country, wrong cycle, closed role, bad sponsorship flag. Those reports usually fix a rule, which fixes every other role too.

Also here: [PRIVACY.md](PRIVACY.md) (what the email list stores — an address and nothing else) · [SECURITY.md](SECURITY.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [MIT licensed](LICENSE).

Built by one student with AI assistance, in the open. The part that matters isn't who typed it — it's that the rules, the tests, and every run's output are all public and checkable.

## Note on dates

The **Posted** column shows when a role was published, with the newest at the top. I pull the posting date straight from each job portal, but a lot of them don't expose one publicly, so those rows show a dash (—) for now instead of a guessed date. The ones that do publish a date are dated. Know the real date for a dashed role? Open a PR and I'll merge it.

Roles can close at any time, so always confirm on the company's own site before applying.
