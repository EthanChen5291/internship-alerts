# Personal alerts and tailored resumes

This fork sends new-role alerts directly to one email address. It does not use
the upstream public subscription database. That service
currently has no DNS record, which is why the original dashboard reports a
network error.

## 1. Publish your fork

Create an empty GitHub repository, point this clone at it, and push the `main`
branch. In the repository settings:

1. Enable GitHub Actions.
2. Under **Pages**, choose **Deploy from a branch**, branch `main`, folder
   `/docs`.
3. Run **Update internships** once from the Actions tab. Its normal schedule is
   minute 7 and 37 of every hour.

For $0 GitHub Actions usage, keep the repository public. A private repository
uses your account's included Actions minutes, and a 30-minute schedule can
eventually exceed that allowance.

The workflow only sends an alert after the refreshed site has been published.
Failed email delivery stays queued and retries on the next successful scan.

## 2. Email alerts (Brevo)

Create a Brevo account, verify a sender address, and add these GitHub Actions
repository secrets:

| Secret | Example |
|---|---|
| `BREVO_API_KEY` | your transactional API key |
| `MAIL_FROM` | `Internship Alerts <verified-sender@example.com>` |
| `ALERT_EMAIL_TO` | the private address that should receive alerts |
| `APPLICANT_PROFILE_JSON` | optional private resume-derived profile for personalized advice |

New roles found in one scan are bundled into one email with direct application
links.

Do not place any credential or email address in `data/config.json`
or commit it to the repository. GitHub Actions secrets are the intended storage.

## 3. Tailored resumes beside every job

Each dashboard row has a **Resume** link. The first time you use it:

1. Download `docs/resume.example.json` from this repository.
2. Replace the example facts with your real resume facts.
3. Open a job's **Resume** link and load that JSON file.
4. Optionally choose **Remember on this browser**.
5. Choose **Save as PDF** and use the browser's PDF destination.

The browser tool never uploads the resume. It only reorders existing skills,
projects, and bullet points by exact keyword relevance. It never rewrites or
adds claims. The target company and job title appear in the preview but are
hidden from the printed resume.

The optional `APPLICANT_PROFILE_JSON` Actions secret can contain a minimal set
of skills and project evidence for personalized alert advice. Keep contact
details out of it. GitHub makes the secret available to the private notification
step without committing it to this public repository.

For a direct command-line PDF instead:

```bash
python tools/tailor_resume.py \
  --resume private/resume.json \
  --job-id 'greenhouse:example:123' \
  --output tailored-resumes/example-software-intern.pdf
```

The `private/` and `tailored-resumes/` directories are ignored by Git so your
resume does not accidentally become part of the public site.
