#!/usr/bin/env python3
"""Download English JEE question papers from official NTA/IIT sources and extract page text."""
from __future__ import annotations
import hashlib, json, re, sys, time
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import fitz

ROOT = Path(__file__).resolve().parents[1]
PAPERS = ROOT / "papers"
TEXT = ROOT / "data" / "paper-text"
PAPERS.mkdir(exist_ok=True)
TEXT.mkdir(parents=True, exist_ok=True)
UA = "jeepre-public-paper-archive/1.0 (educational archive)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA})
MAX_FILE = 35 * 1024 * 1024
MAX_TOTAL = 850 * 1024 * 1024
ALLOWED = ("jeeadv.ac.in", "jeemain.nta.nic.in", "cdnbbsr.s3waas.gov.in", "nta.ac.in")
records, seen = [], set()
total_bytes = 0

def safe_name(s):
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", s).strip("-")[:150]

def official(url):
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in ALLOWED)

def add_candidate(url, exam, label, year=None, session=None, shift=None, paper=None, language="English"):
    url = urljoin("https://jeeadv.ac.in/", url).split("#")[0]
    if not official(url) or url in seen or not url.lower().split("?")[0].endswith(".pdf"):
        return
    if language != "English":
        return
    seen.add(url)
    records.append({"url": url, "exam": exam, "label": label, "year": year,
                    "session": session, "shift": shift, "paper": paper, "language": "English"})

def page(url):
    response = SESSION.get(url, timeout=45)
    response.raise_for_status()
    return response.text

def discover_advanced():
    # Language is determined from the actual URL, never from a shared table-row label.
    soup = BeautifulSoup(page("https://jeeadv.ac.in/archive.html"), "html.parser")
    for anchor in soup.find_all("a", href=True):
        href = urljoin("https://jeeadv.ac.in/archive.html", anchor["href"]).split("#")[0]
        if not href.lower().split("?")[0].endswith(".pdf"):
            continue
        filename = urlparse(href).path.rsplit("/", 1)[-1]
        if re.search(r"_Hindi\.pdf$", filename, re.I):
            continue
        match = re.search(r"/(20\d{2}|200[7-9]|201\d)_([12])(?:_English)?\.pdf$", href, re.I)
        if not match:
            continue
        year, paper_no = int(match.group(1)), int(match.group(2))
        add_candidate(href, "JEE Advanced",
                      f"JEE Advanced {year} Paper {paper_no} English",
                      year, paper=paper_no, language="English")


def download_and_extract(item):
    global total_bytes
    url = item["url"]
    name = safe_name(item["label"]) + ".pdf"
    path = PAPERS / name
    text_path = TEXT / (path.stem + ".json")
    try:
        # Reuse only when the stored page text belongs to this exact source URL.
        if path.exists() and text_path.exists() and path.read_bytes()[:5] == b"%PDF-":
            try:
                saved = json.loads(text_path.read_text(encoding="utf-8"))
            except Exception:
                saved = {}
            if saved.get("source") == url:
                doc = fitz.open(path)
                size = path.stat().st_size
                item.update({"file": str(path.relative_to(ROOT)), "text_file": str(text_path.relative_to(ROOT)),
                             "bytes": size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                             "page_count": len(doc), "status": "downloaded_with_page_text",
                             "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
                doc.close()
                print(f"REUSE {name}")
                return
        response = SESSION.get(url, timeout=90, stream=True)
        response.raise_for_status()
        ctype = response.headers.get("Content-Type", "").lower()
        length = int(response.headers.get("Content-Length") or 0)
        if length > MAX_FILE or total_bytes + length > MAX_TOTAL:
            raise RuntimeError(f"size limit reached ({length} bytes)")
        digest, size = hashlib.sha256(), 0
        with path.open("wb") as handle:
            for chunk in response.iter_content(1024 * 256):
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_FILE or total_bytes + size > MAX_TOTAL:
                    raise RuntimeError("download exceeded configured size limit")
                digest.update(chunk)
                handle.write(chunk)
        if size < 1000 or path.read_bytes()[:5] != b"%PDF-":
            path.unlink(missing_ok=True)
            raise RuntimeError(f"response was not a PDF (content-type={ctype})")
        total_bytes += size
        doc = fitz.open(path)
        pages = []
        for i, pdf_page in enumerate(doc):
            native = pdf_page.get_text("text").strip()
            text_value, method = native, "native"
            # NTA question PDFs are image-heavy; OCR every page to recover question bodies.
            if item["exam"] == "JEE Main" or len(native) < 120:
                try:
                    text_page = pdf_page.get_textpage_ocr(language="eng", dpi=180, full=True)
                    ocr_text = pdf_page.get_text("text", textpage=text_page).strip()
                    if len(ocr_text) > len(native) or (item["exam"] == "JEE Main" and len(ocr_text) > 80):
                        text_value, method = ocr_text, "tesseract_ocr_unverified"
                except Exception as ocr_error:
                    print(f"NOTICE: OCR page {i+1} failed for {item['label']}: {ocr_error}")
            pages.append({"page": i + 1, "text": text_value, "extraction": method})
        if item["exam"] == "JEE Main":
            joined = "\n".join(p.get("text", "") for p in pages)
            stems = re.findall(
                r"(?im)^\s*(?:Q\s*\.?\s*\d+\b|Question\s+Number\s*:\s*\d+\b)", joined)
            if len(stems) < 5 or len(joined) < 1500:
                doc.close()
                path.unlink(missing_ok=True)
                item.update({"status": "rejected_not_question_paper",
                             "error": "No reliable question-page text extracted"})
                print(f"REJECT non-question document: {item['label']}")
                return
        text_path.write_text(json.dumps({"source": url, "pages": pages}, ensure_ascii=False),
                             encoding="utf-8")
        item.update({"file": str(path.relative_to(ROOT)), "text_file": str(text_path.relative_to(ROOT)),
                     "bytes": size, "sha256": digest.hexdigest(), "page_count": len(doc),
                     "status": "downloaded_with_page_text",
                     "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        doc.close()
        print(f"OK {name} ({size} bytes, {len(pages)} pages)")
    except Exception as error:
        item.update({"status": "unavailable", "error": str(error)})
        print(f"SKIP {item['label']}: {error}")

def main():
    # This phase is JEE Advanced only: remove Hindi and all JEE Main artifacts.
    for stale in PAPERS.glob("JEE-Main-*.pdf"):
        stale.unlink(missing_ok=True)
    for stale in TEXT.glob("JEE-Main-*.json"):
        stale.unlink(missing_ok=True)
    for stale in PAPERS.glob("*Hindi*.pdf"):
        stale.unlink(missing_ok=True)
    for stale in TEXT.glob("*Hindi*.json"):
        stale.unlink(missing_ok=True)
    discover_advanced()
    print(f"Discovered {len(records)} English official candidate PDFs")
    for item in records:
        download_and_extract(item)
        time.sleep(0.5)
    manifest = {
        "schema_version": 2,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "policy": "JEE Advanced English-only official-source PDFs. No JEE Main or Hindi papers. OCR/native text is unverified transcription; answers are not included.",
        "count_downloaded": sum(x.get("status") == "downloaded_with_page_text" for x in records),
        "papers": records
    }
    (ROOT / "data" / "papers.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if not manifest["count_downloaded"]:
        print("ERROR: No English official PDF was downloaded.")
        sys.exit(2)
    print(f"Saved {manifest['count_downloaded']} English PDFs and page-text files.")

if __name__ == "__main__":
    main()
