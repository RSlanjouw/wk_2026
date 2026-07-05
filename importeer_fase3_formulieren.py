#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, re, sys, unicodedata
from pathlib import Path
from docx import Document
import pdfplumber

ROUNDS={"ACHTSTE":"r16","KWART":"qf","HALVE":"sf","FINALE":"f"}
FIELDS=["naam","ronde","wedstrijd","thuis","voorspeld_thuis","uit","voorspeld_uit","winnaar","bronbestand"]

def norm(v):
    s=unicodedata.normalize("NFD",str(v or ""))
    s="".join(c for c in s if unicodedata.category(c)!="Mn").casefold()
    return " ".join(re.sub(r"[^a-z0-9]+"," ",s).split())

def read_csv(p):
    if not p.exists(): return []
    with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def official_name(name, known):
    k=norm(name)
    if k in known:return known[k]
    first=k.split()
    if len(first)==1:
        hits=[v for n,v in known.items() if n.split()[:1]==first]
        if len(hits)==1:return hits[0]
    hits=[v for n,v in known.items() if n.startswith(k+" ") or k.startswith(n+" ")]
    if len(hits)==1:return hits[0]
    raise ValueError(f"naam {name!r} kan niet uniek worden gekoppeld")

def parse_rows(rows, source):
    current=None; out=[]
    for raw in rows:
        cells=[re.sub(r"\s+"," ",str(x or "")).strip() for x in raw]
        joined=" ".join(cells).upper()
        if "ACHTSTE" in joined: current="r16"; continue
        if "KWART" in joined: current="qf"; continue
        if "HALVE" in joined: current="sf"; continue
        if joined.strip()=="FINALE" or ("FINALE" in joined and "HALVE" not in joined): current="f"; continue
        if not current or len(cells)<5: continue
        mid=cells[0].strip()
        valid = (current=="r16" and mid in list("ABCDEFGH")) or (current=="qf" and mid in list("1234")) or (current=="sf" and mid in ["X","Y"]) or current=="f"
        if not valid: continue
        if current=="f" and not mid: mid="F"
        home=cells[1]; away=cells[3]
        hs=cells[2]; as_=cells[4]
        if not re.fullmatch(r"\d*",hs) or not re.fullmatch(r"\d*",as_): continue
        winner=cells[5] if len(cells)>5 else ""
        if hs and as_ and int(hs)!=int(as_): winner=home if int(hs)>int(as_) else away
        out.append({"ronde":current,"wedstrijd":mid,"thuis":home,"voorspeld_thuis":hs,"uit":away,"voorspeld_uit":as_,"winnaar":winner})
    expected=15
    if len(out)!=expected: raise ValueError(f"{source.name}: {len(out)} van {expected} wedstrijden gelezen")
    return out

def read_docx(p):
    d=Document(p); name=""
    for t in d.tables:
        for r in t.rows:
            c=[x.text.strip() for x in r.cells]
            if len(c)>=2 and norm(c[0]).startswith("naam"): name=c[1].strip()
    rows=[]
    for t in d.tables:
        rows += [[c.text for c in r.cells] for r in t.rows]
    return name,parse_rows(rows,p)

def read_pdf(p):
    name=""; rows=[]
    with pdfplumber.open(p) as pdf:
        text="\n".join(pg.extract_text() or "" for pg in pdf.pages)
        m=re.search(r"\bnaam\s*:\s*([^\n\r]+)",text,re.I)
        if m:name=m.group(1).strip()
        for pg in pdf.pages:
            for table in pg.extract_tables() or []: rows += table or []
    return name,parse_rows(rows,p)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--data-dir",type=Path,default=Path("data/fase3")); a=ap.parse_args()
    forms=a.data_dir/"formulieren"; output=a.data_dir/"voorspellingen_fase3.csv"
    base=read_csv(a.data_dir/"punten_tot_fase2.csv")
    known={norm(r.get("naam","")):r.get("naam","").strip() for r in base if r.get("naam","").strip()}
    existing=read_csv(output); byname={}
    for r in existing: byname.setdefault(norm(r.get("naam","")),[]).append(r)
    errors=0
    for p in sorted(forms.iterdir(),key=lambda x:(x.stat().st_mtime,x.name.casefold())):
        if p.suffix.casefold() not in {".docx",".pdf"}: continue
        try:
            name,rows=(read_docx(p) if p.suffix.casefold()==".docx" else read_pdf(p))
            official=official_name(name,known)
            byname[norm(official)]=[{"naam":official,**r,"bronbestand":p.name} for r in rows]
            print(f"OK: {p.name} -> {official} ({len(rows)} wedstrijden)")
        except Exception as e:
            errors+=1; print(f"FOUT: {e}",file=sys.stderr)
    allrows=[r for rows in byname.values() for r in rows]
    order={"r16":0,"qf":1,"sf":2,"f":3}
    allrows.sort(key=lambda r:(norm(r["naam"]),order[r["ronde"]],str(r["wedstrijd"])))
    with output.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(allrows)
    print(f"Geschreven: {output.resolve()} ({len(allrows)} regels)")
    return 1 if errors else 0
if __name__=="__main__": raise SystemExit(main())
