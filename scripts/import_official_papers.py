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
    # The official archive lists English and Hindi links in the same table row.
    # Determine language from the actual PDF URL, never from the surrounding row.
    soup = BeautifulSoup(page("https://jeeadv.ac.in/archive.html"), "html.parser")
    for a in soup.find_all("a", href=True):
        href = urljoin("https://jeeadv.ac.in/archive.html", a["href"]).split("#")[0]
        if not href.lower().split("?")[0].endswith(".pdf"):
            continue
        filename = urlparse(href).path.rsplit("/", 1)[-1]
        if re.search(r"_Hindi\\.pdf$", filename, re.I):
            continue
        year_match = re.search(r"/(20\\d{2}|200[7-9]|201\\d)_([12])(?:_English)?\\.pdf$", href, re.I)
        if not year_match:
            continue
        year, paper_no = int(year_match.group(1)), int(year_match.group(2))
        label = f"JEE Advanced {year} Paper {paper_no} English"
        add_candidate(href, "JEE Advanced", label, year, paper=paper_no, language="English")

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
            if len(native) < 120 or (item["exam"] == "JEE Main" and "Question Number" in native):
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
            joined = "\n".join(p.get("text", "") for p in pages)
            stems = re.findall(r"(?im)^\s*Q\s*\.?\s*\d+\b", joined)
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
    # Remove Hindi PDFs/text from earlier runs; this archive is English-only.
    for stale in PAPERS.glob("*Hindi*.pdf"):
        stale.unlink(missing_ok=True)
    for stale in TEXT.glob("*Hindi*.json"):
        stale.unlink(missing_ok=True)
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
    main()def discover_main():
    # Direct NTA links for every 2026 Session 2 B.E./B.Tech shift.
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

    # NTA's public Question Papers pages expose the 2025 B.E./B.Tech papers.
    # Only engineering Paper 1 rows are imported; B.Arch/B.Planning are excluded.
    for year in (2025, 2024, 2023, 2022, 2021):
        archive = f"https://jeemain.nta.nic.in/question-papers-{year}/"
        try:
            soup = BeautifulSoup(page(archive), "html.parser")
        except Exception as e:
            print(f"NOTICE: could not read official NTA question-paper page {year}: {e}")
            continue
        for a in soup.find_all("a", href=True):
            href = urljoin(archive, a["href"]).split("#")[0]
            if not href.lower().split("?")[0].endswith(".pdf") or not official(href):
                continue
            row = a.find_parent("tr")
            context = " ".join(row.stripped_strings) if row else " ".join(a.parent.stripped_strings) if a.parent else a.get_text(" ", strip=True)
            combined = context + " " + a.get_text(" ", strip=True)
            if not re.search(r"\\bB\\s*Tech\\b|B\\.E\\./B\\.Tech", combined, re.I):
                continue
            if re.search(r"B\\s*Arch|B\\s*Planning", combined, re.I):
                continue
            ym = re.search(r"\\b(20\\d{2})\\b", combined)
            dm = re.search(r"(\\d{1,2})(?:st|nd|rd|th)?\\s+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)", combined, re.I)
            sm = re.search(r"Shift\\s*([12])", combined, re.I)
            if not (ym and dm and sm):
                continue
            year_found = int(ym.group(1))
            month = dm.group(2).title()
            month = {"Jan":"January","Feb":"February","Mar":"March","Apr":"April","Jun":"June","Jul":"July","Aug":"August","Sep":"September","Sept":"September","Oct":"October","Nov":"November","Dec":"December"}.get(month, month)
            day, shift = int(dm.group(1)), int(sm.group(1))
            label = f"JEE Main {year_found} {day} {month} Shift {shift}"
            add_candidate(href, "JEE Main", label, year_found, month, shift)

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
            joined = "\n".join(p.get("text", "") for p in pages)
            stems = re.findall(r"(?im)^\s*Q\s*\.?\s*\d+\b", joined)
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
