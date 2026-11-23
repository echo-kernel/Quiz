#!/usr/bin/env python3
"""Convert page-level official JEE PDF text into question-level practice records.
Answers are deliberately left null unless an official key is separately verified.
"""
import json, re, calendar
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TEXT=ROOT/"data"/"paper-text"
OUT=ROOT/"data"/"questions.json"
qstart=re.compile(r"(?m)^\s*Q\s*\.\s*(\d{1,3})\s*\.?\s*")
opt=re.compile(r"(?m)^\s*\(([A-D])\)\s*")
def subject_for(s, fallback="General"):
    m=re.search(r"PART\s*[-–]?\s*(?:I|II|III)\s*(PHYSICS|CHEMISTRY|MATHEMATICS|MATHS)",s,re.I)
    if m:return {"MATHS":"Mathematics"}.get(m.group(1).upper(),m.group(1).title())
    for x in ("Physics","Chemistry","Mathematics"):
        if re.search(r"\b"+x+r"\b",s[:800],re.I): return x
    return fallback
def meta(stem):
    m=re.match(r"(JEE-(?:Main|Advanced))-(\d{4})(?:-(.*))?",stem)
    if not m:return "JEE",None,"",None
    exam="JEE Main" if "Main" in m.group(1) else "JEE Advanced"
    year=int(m.group(2)); tail=m.group(3) or ""
    paper=int(re.search(r"Paper-(\d)",tail).group(1)) if re.search(r"Paper-(\d)",tail) else None
    return exam,year,tail,paper
def clean(s):
    s=s.replace("\x0c","\n")
    s=re.sub(r"JEE\s*\(?Advanced\)?\s*20\d{2}[^\n]*","",s,flags=re.I)
    s=re.sub(r"\n\s*\d+\s*/\s*\d+\s*\n","\n",s)
    return re.sub(r"\n{3,}","\n\n",s).strip()
def parse_block(block, page_text):
    # Options are only split when they occur as line-start labels.
    matches=list(opt.finditer(block))
    stem=block[:matches[0].start()].strip() if matches else block.strip()
    options=[]
    if matches:
        for i,m in enumerate(matches):
            end=matches[i+1].start() if i+1<len(matches) else len(block)
            val=block[m.end():end].strip()
            if val: options.append({"label":m.group(1),"text":val})
    # Remove trailing paper instructions and preserve question content.
    if not stem or len(stem)<12:return None
    qtype=("multiple" if options and re.search(r"ONE OR MORE THAN ONE|MORE THAN ONE OF THESE",page_text,re.I) else "single") if options else "numerical"
    return stem,options,qtype
def order_key(q):
    # Chronological paper order: year, month/session, exam day, shift, paper, question.
    label=q.get("paper_label","")
    month_names={m.lower():i for i,m in enumerate(calendar.month_name) if m}
    mm=re.search(r"-(January|February|March|April|May|June|July|August|September|October|November|December)-",label,re.I)
    month=month_names.get(mm.group(1).lower(),0) if mm else 0
    dm=re.search(r"-(\\d{1,2})-(?:April|January|February|March|May|June|July|August|September|October|November|December)-Shift-",label,re.I)
    day=int(dm.group(1)) if dm else 0
    sm=re.search(r"Shift-(\\d+)",label,re.I)
    shift=int(sm.group(1)) if sm else 0
    return (q.get("year") or 0, month, day, shift, q.get("paper") or 0, q.get("question_number") or 0, q.get("paper_label",""))
def main():
    allq=[]; seen=set(); stats={"files":0,"questions":0,"with_options":0,"empty_files":0}
    for f in sorted(TEXT.glob("*.json")):
        try: data=json.loads(f.read_text(encoding="utf-8"))
        except Exception: continue
        stats["files"]+=1
        exam,year,tail,paper=meta(f.stem)
        fallback="General"
        for page in data.get("pages",[]):
            raw=clean(page.get("text",""))
            if len(raw)<80: continue
            # Subject headings persist across page boundaries within a paper.
            subj=subject_for(raw,fallback)
            if subj!="General": fallback=subj
            starts=list(qstart.finditer(raw))
            for i,m in enumerate(starts):
                end=starts[i+1].start() if i+1<len(starts) else len(raw)
                block=raw[m.end():end].strip()
                parsed=parse_block(block,raw)
                if not parsed:continue
                stem,options,qtype=parsed
                number=int(m.group(1))
                # Exclude page headers/answer-key-only snippets.
                if re.match(r"^(ANSWER|CORRECT OPTION)\s*:",stem,re.I):continue
                key=(f.stem,number,page.get("page"))
                if key in seen:continue
                seen.add(key)
                rec={"id":f"{f.stem}-p{page.get('page')}-q{number}","exam":exam,"year":year,
                     "paper":paper,"paper_label":f.stem.replace("-"," "),"subject":subj,
                     "question_number":number,"type":qtype,"text":stem,
                     "options":options,"answer":None,"answer_status":"not_verified",
                     "source_pdf":data.get("source"),"source_file":f"papers/{f.stem}.pdf",
                     "source_page":page.get("page"),"extraction":page.get("extraction","native_or_ocr"),
                     "needs_diagram_check":bool(re.search(r"\b(figure|shown below|given below|as shown|diagram)\b",stem,re.I))}
                allq.append(rec)
                if options:stats["with_options"]+=1
    allq.sort(key=order_key)\n    stats["questions"]=len(allq)
    stats["empty_files"]=sum(1 for f in TEXT.glob("*.json") if not any(q["paper_label"]==f.stem.replace("-"," ") for q in allq))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"schema_version":2,"generated_by":"scripts/build_question_bank.py",\n      "ordering":"JEE Main: year, session month, exam date, shift, question number; JEE Advanced: year, paper 1 then paper 2, question number.",
      "policy":"Question text is extracted from official-source PDFs. Answers are not supplied unless verified against official answer keys.",
      "stats":stats,"questions":allq},ensure_ascii=False),encoding="utf-8")
    print(json.dumps(stats))
if __name__=="__main__":main()
