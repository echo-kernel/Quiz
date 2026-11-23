# jeepre — JEE preparation app

A mobile-friendly, browser-based JEE Main + JEE Advanced preparation workspace.

## Current build
- CBT-style timed test screen with question palette, navigation, answer clearing and mark-for-review.
- JEE Main-style +4/-1 scoring defaults; imported question banks can override marks and negative marks per question.
- JEE Advanced-compatible per-question marking fields (Advanced marking schemes vary by year and section).
- Result review with explanations and subject breakdown.
- Local test history and dashboard analytics (stored in the browser's localStorage).
- Import question banks as JSON; download the template from inside the app.
- Shift-specific percentile CSV importer with interpolation only inside the supplied score range. It refuses to guess when exact shift data is missing.
- Marks calculator, simple study target planner, and curated official/coaching source links.

## Run
Open `index.html` in a modern browser, or enable GitHub Pages: Settings → Pages → Deploy from a branch → main → /(root). No build step or server is required.

## Paper and data policy
Built-in questions are original interface-demo questions, not PYQs. Use the paper-source library for official NTA/JEE Advanced archives and publisher-hosted ALLEN/BYJU'S resources. Import only files/data you are permitted to use. The app does not bypass login walls or republish copyrighted coaching compilations. Prefer official final answer keys; record year, session, date, shift, language, question IDs, marking scheme and source URL for every imported paper.

## Question bank JSON format
See `data/question-bank-template.json`. Each paper has a `title`, `exam`, optional `year/session/shift/duration`, and `questions`. Each question needs `text`, `subject`, `answer`; MCQs also need `options`. Optional fields: `id`, `chapter`, `type` (`single` or `numeric`), `marks`, `negative`, `tolerance`, `explanation`, `source`.

## Percentile CSV
See `data/percentile-template.csv`. The app requires rows for the exact year + session + shift. Percentiles depend on shift normalization; marks alone do not produce a universal percentile. Estimates are interpolations from supplied data, not official predictions.

## Roadmap
1. Build a verified paper catalogue and question-level source/answer-key provenance.
2. Convert permitted PDFs/response sheets into structured question banks; human-check every extraction and key.
3. Add full-length year/shift simulations and exact year-specific JEE Advanced marking schemes.
4. Add chapter/topic tags, spaced revision, bookmarks, mistake notebook and custom tests.
5. Add optional cloud sync/authentication after deciding on a backend.

Not affiliated with NTA, IITs, ALLEN or BYJU'S.
