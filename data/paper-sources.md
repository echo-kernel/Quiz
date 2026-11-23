# jeepre paper-source directory

Official-source import workflow: `.github/workflows/import-papers.yml` runs `scripts/import_official_papers.py`. It downloads only publicly accessible PDFs from IIT/JEE Advanced and NTA, stores them in `papers/`, and extracts page-level searchable text to `data/paper-text/`. Candidate-login-only papers are intentionally skipped.

| Source | Resource | URL |
|---|---|---|
| NTA | JEE Main official archive | https://jeemain.nta.nic.in/document-category/archive/ |
| IIT/JAB | JEE Advanced official archive | https://jeeadv.ac.in/archive.html |
| ALLEN | JEE Main previous-year papers and solutions | https://news.allen.in/download-jee-main-previous-year-question-papers-with-solutions/ |
| ALLEN | 2022 previous-year papers | https://news.allen.in/download-jee-main-previous-years-question-papers-with-solutions-chapter-wise/ |
| BYJU'S | JEE Main question papers | https://byjus.com/jee/jee-main-question-paper/ |
| BYJU'S | Chapter-wise JEE Main questions | https://byjus.com/jee/jee-main-chapter-wise-questions-and-solutions/ |

## Official sources

- JEE Advanced archive: https://jeeadv.ac.in/archive.html
- JEE Main archive: https://jeemain.nta.nic.in/document-category/archive/
- JEE Main sitemap: https://jeemain.nta.nic.in/sitemap/

## Ingestion and verification checklist

For each paper, capture:
- Exam, year, session, date, shift, paper number and language
- Original publisher URL and retrieval date
- Whether it is an official paper, a publisher solution, or a memory-based reconstruction
- Final answer-key source and question IDs
- Marking rules for that exact paper/section
- Question-level subject, chapter, type, answer, explanation and source attribution

Never label memory-based questions as official PYQs. Check current syllabus relevance and flag removed topics. For JEE Advanced, preserve the year- and section-specific marking rules; do not apply a single generic +4/-1 scheme to every question.

## Copyright

Prefer official public papers and publisher pages that expressly permit downloading. Do not scrape login-protected material, bypass paywalls, or redistribute copyrighted coaching content without permission. User-provided files should only be imported where the user has the right to use them.
