#!/usr/bin/env python3
"""Build question-level records from English official JEE papers.

Question text/options are extracted from source PDFs. Answer-key material is
removed from practice prompts; no answer is exposed during a CBT attempt.
"""
import json, re, calendar
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = ROOT / "data" / "paper-text"
OUT = ROOT / "data" / "questions.json"

qstart = re.compile(r"(?mi)^\s*(?:Q\s*\.?\s*(\d{1,3})\b|Question\s+Number\s*:\s*(\d{1,3})\b)")
opt = re.compile(r"(?mi)^\s*(?:\(([A-D])\)|\[([A-D])\]|([A-D])\s*[.)])\s*")
ANSWER_MARKER = re.compile(
    r"(?i)(?:Answer\s+for\s+(?:the\s+)?above\s+question|"
    r"Ans\s+for\s+Q\.?\s*\d+|Correct\s+Answer\s*:|Answer\s+Key\s*:|"
    r"^\s*Ans\s*[:.])"
)

def subject_for(s, fallback="General"):
    # Prefer the latest subject heading in the page text.
    found = list(re.finditer(r"\b(PHYSICS|CHEMISTRY|MATHEMATICS|MATHS)\b", s[:1800], re.I))
    if found:
        value = found[-1].group(1).upper()
        return {"MATHS": "Mathematics"}.get(value, value.title())
    return fallback

def meta(stem):
    m = re.match(r"(JEE-(?:Main|Advanced))-(\d{4})(?:-(.*))?", stem)
    if not m:
        return "JEE", None, "", None
    exam = "JEE Main" if "Main" in m.group(1) else "JEE Advanced"
    year = int(m.group(2))
    tail = m.group(3) or ""
    pm = re.search(r"Paper-(\d)", tail)
    return exam, year, tail, int(pm.group(1)) if pm else None

def clean(s):
    s = s.replace("\x0c", "\n")
    s = re.sub(r"JEE\s*\(?Advanced\)?\s*20\d{2}[^\n]*", "", s, flags=re.I)
    s = re.sub(r"\n\s*\d+\s*/\s*\d+\s*\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def mode_for_pages(pages):
    modes = []
    mode = "single"
    for text in pages:
        if re.search(r"ONE OR MORE THAN ONE|ONE OR MORE OF THESE|ONE OR MORE.*CORRECT", text, re.I):
            mode = "multiple"
        elif re.search(r"ANSWER.*NUMERICAL VALUE|NUMERICAL VALUE OF THE ANSWER", text, re.I):
            mode = "numerical"
        elif re.search(r"ONLY ONE OF THESE|ONLY ONE OPTION|ONLY ONE.*CORRECT", text, re.I):
            mode = "single"
        modes.append(mode)
    return modes

def parse_block(block, mode):
    # Remove answer panels printed directly after some older Advanced questions.
    marker = ANSWER_MARKER.search(block)
    if marker:
        block = block[:marker.start()]
    block = re.sub(r"(?im)^\s*END OF THE QUESTION PAPER.*$", "", block).strip()
    matches = list(opt.finditer(block))
    stem = block[:matches[0].start()].strip() if matches else block.strip()
    options = []
    for i, match in enumerate(matches):
        label = next((g for g in match.groups() if g), None)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(block)
        value = block[match.end():end].strip()
        if label and value:
            options.append({"label": label, "text": value})
    if len(stem) < 12:
        return None
    if re.search(r"Question\s+Type\s*:\s*SA|Response\s+Type\s*:\s*Numeric", block, re.I):
        qtype = "numerical"
    elif mode == "numerical":
        qtype = "numerical"
    elif options:
        qtype = "multiple" if mode == "multiple" else "single"
    elif re.search(r"Question\s+Type\s*:\s*MCQ", block, re.I):
        qtype = "needs_review"
    else:
        qtype = "numerical"
    # Defensive check: never allow answer-panel text to leak into the prompt.
    if re.search(r"(?i)Answer\s+for\s+(?:the\s+)?above\s+question|Ans\s+for\s+Q\.?\s*\d+", stem):
        return None
    return stem, options, qtype

def order_key(q):
    label = q.get("paper_label", "")
    month_names = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
    mm = re.search(r"(?:^|[-\s])(January|February|March|April|May|June|July|August|September|October|November|December)(?:[-\s]|$)", label, re.I)
    month = month_names.get(mm.group(1).lower(), 0) if mm else 0
    dm = re.search(r"(?:^|[-\s])(\d{1,2})[-\s](?:April|January|February|March|May|June|July|August|September|October|November|December)[-\s]Shift[-\s]", label, re.I)
    day = int(dm.group(1)) if dm else 0
    sm = re.search(r"Shift[-\s](\d+)", label, re.I)
    shift = int(sm.group(1)) if sm else 0
    return (q.get("year") or 0, month, day, shift, q.get("paper") or 0,
            q.get("question_number") or 0, label)

def main():
    allq, seen = [], set()
    stats = {"files": 0, "questions": 0, "with_options": 0, "empty_files": 0,
             "answer_leaks_blocked": 0, "english_files_only": True}
    per_paper = []
    for f in sorted(TEXT.glob("*.json")):
        if "Hindi" in f.stem:
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        exam, year, tail, paper = meta(f.stem)
        stats["files"] += 1
        raw_pages = data.get("pages", [])
        page_texts = [clean(p.get("text", "")) for p in raw_pages]
        page_modes = mode_for_pages(page_texts)
        offsets, chunks, offset = [], [], 0
        for i, txt in enumerate(page_texts):
            offsets.append(offset)
            chunks.append(txt)
            offset += len(txt) + 1
        joined = "\n".join(chunks)
        starts = list(qstart.finditer(joined))
        fallback_subject = "General"
        paper_count = 0
        page_index = 0
        for i, match in enumerate(starts):
            while page_index + 1 < len(offsets) and offsets[page_index + 1] <= match.start():
                page_index += 1
                found = subject_for(page_texts[page_index], fallback_subject)
                if found != "General":
                    fallback_subject = found
            end = starts[i + 1].start() if i + 1 < len(starts) else len(joined)
            block = joined[match.end():end].strip()
            number = int(match.group(1) or match.group(2))
            parsed = parse_block(block, page_modes[page_index] if page_index < len(page_modes) else "single")
            if not parsed:
                stats["answer_leaks_blocked"] += 1
                continue
            stem, options, qtype = parsed
            source_page = raw_pages[page_index].get("page", page_index + 1)
            key = (f.stem, number, source_page)
            if key in seen:
                continue
            seen.add(key)
            subject = subject_for(page_texts[page_index], fallback_subject)
            if subject != "General":
                fallback_subject = subject
            rec = {
                "id": f"{f.stem}-p{source_page}-q{number}",
                "exam": exam, "year": year, "paper": paper,
                "paper_label": f.stem.replace("-", " "),
                "subject": subject, "question_number": number,
                "type": qtype, "text": stem, "options": options,
                "answer": None, "answer_status": "not_verified",
                "source_pdf": data.get("source"),
                "source_file": f"papers/{f.stem}.pdf",
                "source_page": source_page,
                "extraction": raw_pages[page_index].get("extraction", "native_or_ocr"),
                "needs_diagram_check": bool(re.search(r"\b(figure|shown below|given below|as shown|diagram)\b", stem, re.I)),
                "needs_review": qtype == "needs_review" or not options and qtype != "numerical"
            }
            allq.append(rec)
            paper_count += 1
            if options:
                stats["with_options"] += 1
        per_paper.append({"paper": f.stem.replace("-", " "), "questions_extracted": paper_count})
        if paper_count == 0:
            stats["empty_files"] += 1
    allq.sort(key=order_key)
    stats["questions"] = len(allq)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({
        "schema_version": 3,
        "generated_by": "scripts/build_question_bank.py",
        "ordering": "JEE Main: year, session month, exam date, shift, question number; JEE Advanced: year, Paper 1 then Paper 2, question number.",
        "policy": "English-only question text extracted from official-source PDFs. Answers are never shown during CBT and remain unverified unless matched to an official key.",
        "stats": stats,
        "papers": per_paper,
        "questions": allq
    }, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(stats))
    print(json.dumps(per_paper))

if __name__ == "__main__":
    main()
