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

## Planned next stages
- Full official paper archive with metadata and paper viewer
- Accurate question-type-specific JEE Main / Advanced marking schemes
- Multi-correct, numerical, matrix-match and partial-credit grading
- Section-specific timers and instructions
- Topic mastery, weak-area recommendations, revision queue and error notebook
- PWA installability, cloud sync and secure accounts
- Verified shift-wise percentile dataset with source audit trail
