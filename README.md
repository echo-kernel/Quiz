# jeepre — JEE Main & Advanced preparation app

A mobile-friendly, installable PWA starter web app for JEE preparation. It caches the app shell for offline reopening after the first successful load.

## Current MVP
- Dashboard with local progress counters
- Subject-filtered practice set with explanations
- Timed CBT-style test flow, question palette, answer selection, clear response, mark-for-review and submit
- JSON question-bank import with source/verification metadata
- Test history and basic analytics
- Shift-specific JEE Main marks-to-percentile interpolation only after importing sourced reference points
- Local browser storage

## Run / install
Open `index.html` in a browser, or deploy this repository with GitHub Pages. On Android Chrome, open the deployed URL and choose **Install app** (or ⋮ → **Add to Home screen**). The manifest, SVG app icon and service worker provide installability and offline app-shell caching.

GitHub Pages deployment is configured in `.github/workflows/pages.yml`. The workflow attempts to enable Pages automatically; if GitHub blocks that operation, open **Settings → Pages → Build and deployment → GitHub Actions** once, then rerun the workflow.

## Data and copyright policy
This repository does not claim to contain all JEE Main or JEE Advanced previous-year papers. Populate it with:
1. Officially released question papers and answer keys from NTA / JEE Advanced (IIT) websites.
2. Third-party question banks only where redistribution or use is permitted by their terms/licence, or with permission.
3. User-provided files the user is authorized to use.

Allen, BYJU'S and other coaching resources can be researched as discovery/reference sources. Do not scrape behind logins, bypass access controls, or republish copyrighted coaching modules without permission. Verify questions and answers against official papers wherever possible. Keep a source URL, year, session, shift, and verification status for every imported question.

## Percentile accuracy
JEE Main percentile is shift-normalized and cannot be reliably derived from raw marks alone using one universal formula. The estimator requires multiple verified marks/percentile reference points for the exact shift and interpolates between them. It is an estimate, not an NTA score or guarantee. Do not mix shifts or sessions. Advanced does not use the Main percentile estimator.

CSV schema: `shift,marks,percentile,source`

## Question-bank JSON schema
See the in-app template. Single-correct answer index is zero-based. Preserve original paper marking rules when adding more question types. The initial CBT scoring is a simple +4 / -1 practice preset; it is not a universal JEE marking scheme.

## Import workflow and limitations

The importer is restricted to official IIT/JEE Advanced and NTA hosts. It respects public access, skips blocked or oversized files, and records failures instead of fabricating missing papers. The JEE Advanced official archive currently exposes 2007–2025 Paper 1 and Paper 2; JEE Main public availability varies by year/session and some historic papers are only in candidate login. The app prefers repository-local PDFs after a successful import and falls back to the existing official-source reader list otherwise.

PDF page text is extracted for search/review. It is **not** automatically split into reliable question objects, options, answer keys, or worked solutions: mathematical notation, diagrams, multi-correct/numerical questions, and marking schemes need validation. Do not use raw extraction as an answer key or label unreviewed extraction as verified PYQ data.

## Planned next stages
- Official-source paper import workflow (`.github/workflows/import-papers.yml`): scheduled monthly and manually runnable from GitHub Actions; downloads public official PDFs, stores them under `papers/`, and extracts searchable page text under `data/paper-text/`
- Accurate question-type-specific JEE Main / Advanced marking schemes
- Multi-correct, numerical, matrix-match and partial-credit grading
- Section-specific timers and instructions
- Topic mastery, weak-area recommendations, revision queue and error notebook
- PWA installability, cloud sync and secure accounts
- Verified shift-wise percentile dataset with source audit trail
