#!/usr/bin/env python3
"""Generate one conservative job-specific PDF from a private resume JSON."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, os.fspath(ROOT / "src"))

from intern_engine import paths, resume_tailor  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", required=True, help="Private base resume JSON")
    parser.add_argument("--job-id", required=True, help="Role id from docs/api/jobs.json")
    parser.add_argument("--output", required=True, help="Destination .pdf")
    args = parser.parse_args()
    with open(args.resume, encoding="utf-8") as stream:
        resume = json.load(stream)
    with open(paths.JOBS_PATH, encoding="utf-8") as stream:
        jobs = json.load(stream)
    job = jobs.get(args.job_id)
    if not job:
        raise SystemExit(f"Unknown job id: {args.job_id}")
    tailored = resume_tailor.tailor(resume, job)
    resume_tailor.write_pdf(tailored, args.output)
    print(f"Wrote {args.output} for {job.get('company')} - {job.get('title')}")


if __name__ == "__main__":
    main()
