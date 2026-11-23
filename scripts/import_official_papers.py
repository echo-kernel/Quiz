#!/usr/bin/env python3
"""Download publicly accessible official JEE papers and extract searchable page text.

Only official IIT/JEE Advanced and NTA sources are accepted. This script does not
invent questions or answers: it stores the original PDF plus page-level extracted
text for later question-level review.
"""
from __future__ import annotations
import hashlib, json, os, re, sys, time
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
import requests
from bs4 import BeautifulSoup
import fitz

ROOT = Path(__file__).resolve().parents[1]
PAPERS = ROOT / "papers"
TEXT = ROOT / "data" / "paper-text"
PAPERS.mkdir(exist_ok=True)
TEXT.mkdir(parents=True, exist_ok=True)
UA = "jeepre-public-paper-archive/1.0 (educational archive; contact via GitHub)"
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
    seen.add(url)
    records.append({"url": url, "exam": exam, "label": label, "year": year,
                    "session": session, "shift": shift, "paper": paper, "language": language})

def page(url):
    r = SESSION.get(url, timeout=45)
    r.raise_for_status()
    return r.text

def discover_advanced():
    soup = BeautifulSoup(page("https://jeeadv.ac.in/archive.html"), "html.parser")
    for a in soup.find_all("a", href=True):
        href = urljoin("https://jeeadv.ac.in/archive.html", a["href"])
        if not href.lower().split("?")[0].endswith(".pdf"):
            continue
        context = " ".join(a.parent.parent.stripped_strings) if a.parent and a.parent.parent else a.get_text(" ", strip=True)
        year_match = re.search(r"\b(20\d{2}|200[7-9]|201\d)\b", context + " " + href)
        paper_match = re.search(r"paper\s*([12])", a.get_text(" ", strip=True), re.I)
        if not year_match or not paper_match:
            continue
        year, paper_no = int(year_match.group(1)), int(paper_match.group(1))
        language = "Hindi" if re.search(r"hindi", context, re.I) else "English"
        label = f"JEE Advanced {year} Paper {paper_no} {language}"
        add_candidate(href, "JEE Advanced", label, year, paper=paper_no, language=language)

def discover_main():
    # Publicly listed 2026 NTA documents; older NTA papers may require candidate login.
    seeds = [
      ("2 April Shift 1","https://cdnbbsr.s3waas.gov.in/s3f8e59f4b2fe7c5705bf878bbd494ccdf/uploads/2026/04/202604092096865379.pdf",2,1),
      ("2 April Shift 2","https://cdnbbsr.s3waas.gov.in/s3f8e59f4b2fe7c5705bf878bbd494ccdf/uploads/2026/04/20260409481957146.pdf",2,2),
      ("4 April Shift 1","https://cdnbbsr.s3waas.gov.in/s3f8e59f4b2fe7c5705bf878bbd494ccdf/uploads/2026/04/202604091916616339.pdf",4,1),
      ("4 April Shift 2","https://cdnbbsr.s3waas.gov.in/s3f8e59f4b2fe7c5705bf878bbd494ccdf/uploads/2026/04/20260409432593766.pdf",4,2),
      ("5 April Shift 1","https://cdnbbsr.s3waas.gov.in/s3f8e59f4b2fe7c5705bf878bbd494ccdf/uploads/2026/04/20260409828731207.pdf",5,1),
      ("5 April Shift 2","https://cdnbbsr.s3waas.gov.in/s3f8e59f4b2fe7c5705bf878bbd494ccdf/uploads/2026/04/20260409829414602.pdf",5,2),
      ("6 April Shift 1","https://cdnbbsr.s3waas.gov.in/s3f8e59f4b2fe7c5705bf878bbd494ccdf/uploads/2026/04/202604092007095665.pdf",6,1),
      ("6 April Shift 2","https://cdnbbsr.s3waas.gov.in/s3f8e59f4b2fe7c5705bf878bbd494ccdf/uploads/2026/04/20260409725707538.pdf",6,2),
      ("8 April Shift 2","https://cdnbbsr.s3waas.gov.in/s3f8e59f4b2fe7c5705bf878bbd494ccdf/uploads/2026/04/20260409932754345.pdf",8,2),
    ]
    for label, url, day, shift in seeds:
        add_candidate(url, "JEE Main", f"JEE Main 2026 {label}", 2026, "April", shift)
    # Discover any PDFs directly linked by the official archive page.
    for archive in ("https://jeemain.nta.nic.in/document-category/archive/", "https://jeemain.nta.nic.in/sitemap/"):
        try:
            soup = BeautifulSoup(page(archive), "html.parser")
            for a in soup.find_all("a", href=True):
                href = urljoin(archive, a["href"])
                if not href.lower().split("?")[0].endswith(".pdf") or not official(href):
                    continue
                context = " ".join(a.parent.stripped_strings) if a.parent else a.get_text(" ", strip=True)
                combined = context + " " + a.get_text(" ", strip=True) + " " + href
                ym = re.search(r"\b(20\d{2})\b", combined)
                if not ym:
                    continue
                year = int(ym.group(1))
                sm = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)", combined, re.I)
                dm = re.search(r"(?:shift|s)\s*([12])", combined, re.I)
                label = f"JEE Main {year}" + (f" {sm.group(1)}" if sm else "") + (f" Shift {dm.group(1)}" if dm else "")
                add_candidate(href, "JEE Main", label, year, sm.group(1) if sm else None, int(dm.group(1)) if dm else None)
        except Exception as e:
            print(f"NOTICE: could not read {archive}: {e}")

def download_and_extract(item):
    global total_bytes
    url = item["url"]
    name = safe_name(item["label"]) + ".pdf"
    path = PAPERS / name
    text_path = TEXT / (path.stem + ".json")
    try:
        # Reuse a previously downloaded official PDF and its page text.
        if path.exists() and text_path.exists() and path.read_bytes()[:5] == b"%PDF-":
            doc = fitz.open(path)
            size = path.stat().st_size
            item.update({"file": str(path.relative_to(ROOT)), "text_file": str(text_path.relative_to(ROOT)),
                         "bytes": size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "page_count": len(doc), "status": "downloaded_with_page_text",
                         "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
            doc.close()
            print(f"REUSE {name}")
            return
        r = SESSION.get(url, timeout=90, stream=True)
        r.raise_for_status()
        ctype = r.headers.get("Content-Type", "").lower()
        length = int(r.headers.get("Content-Length") or 0)
        if length > MAX_FILE or total_bytes + length > MAX_TOTAL:
            raise RuntimeError(f"size limit reached ({length} bytes)")
        h = hashlib.sha256()
        size = 0
        with path.open("wb") as f:
            for chunk in r.iter_content(1024 * 256):
                if not chunk: continue
                size += len(chunk)
                if size > MAX_FILE or total_bytes + size > MAX_TOTAL:
                    raise RuntimeError("download exceeded configured size limit")
                h.update(chunk); f.write(chunk)
        if size < 1000 or path.read_bytes()[:5] != b"%PDF-":
            path.unlink(missing_ok=True)
            raise RuntimeError(f"response was not a PDF (content-type={ctype})")
        total_bytes += size
        doc = fitz.open(path)
        pages = []
        for i, p in enumerate(doc):
            native = p.get_text("text").strip()
            method = "native"
            # Many official JEE PDFs contain scanned question pages. OCR those pages
            # instead of silently saving blank text. OCR remains unverified source text.
            if len(native) < 120:
                try:
                    tp = p.get_textpage_ocr(language="eng", dpi=180, full=True)
                    ocr_text = p.get_text("text", textpage=tp).strip()
                    if len(ocr_text) > len(native):
                        native, method = ocr_text, "tesseract_ocr_unverified"
                except Exception as ocr_error:
                    print(f"NOTICE: OCR page {i+1} failed for {item['label']}: {ocr_error}")
            pages.append({"page": i + 1, "text": native, "extraction": method})
        # Reject NTA notices, FAQs, information bulletins and response-sheet exports.
        # A real question paper must contain actual question stems, not only exam metadata.
        if item["exam"] == "JEE Main":
            joined = "\\n".join(p.get("text", "") for p in pages)
            stems = re.findall(r"(?im)^\\s*Q\\s*\\.?\\s*\\d+\\b", joined)
            if len(stems) < 5:
                doc.close()
                path.unlink(missing_ok=True)
                text_path.unlink(missing_ok=True)
                item.update({"status": "rejected_not_question_paper",
                             "error": "No extractable question stems; excluded from PYQ archive"})
                print(f"REJECT non-question document: {item['label']}")
                return
        text_path.write_text(json.dumps({"source": url, "pages": pages}, ensure_ascii=False), encoding="utf-8")
        item.update({"file": str(path.relative_to(ROOT)), "text_file": str(text_path.relative_to(ROOT)),
                     "bytes": size, "sha256": h.hexdigest(), "page_count": len(doc),
                     "status": "downloaded_with_page_text", "retrieved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        doc.close()
        print(f"OK {name} ({size} bytes, {len(pages)} pages)")
    except Exception as e:
        item.update({"status": "unavailable", "error": str(e)})
        print(f"SKIP {item['label']}: {e}")

def main():
    discover_advanced()
    discover_main()
    print(f"Discovered {len(records)} official candidate PDFs")
    for item in records:
        download_and_extract(item)
        time.sleep(1.0)
    manifest = {"schema_version": 1, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "policy": "Official-source PDFs only. Native text and OCR page text are unverified source transcription, not a verified question/answer database.",
                "count_downloaded": sum(x.get("status") == "downloaded_with_page_text" for x in records),
                "papers": records}
    (ROOT / "data" / "papers.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if not manifest["count_downloaded"]:
        print("ERROR: No official PDF was downloaded; inspect the source errors above.")
        sys.exit(2)
    print(f"Saved {manifest['count_downloaded']} PDFs and page-text files.")

if __name__ == "__main__":
    main()
