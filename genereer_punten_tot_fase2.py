#!/usr/bin/env python3
from __future__ import annotations
import csv, re, unicodedata
from pathlib import Path

def norm(v):
    s=unicodedata.normalize("NFD",str(v or ""))
    s="".join(c for c in s if unicodedata.category(c)!="Mn").casefold()
    return " ".join(re.sub(r"[^a-z0-9]+"," ",s).split())

def read(p):
    with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def main():
    p1=read(Path("data/fase2/fase1_punten.csv"))
    preds=read(Path("data/fase2/voorspellingen_fase2.csv"))
    results={r["wedstrijd"]:r for r in read(Path("data/fase2/uitslagen_fase2.csv")) if r.get("werkelijk_thuis","")!="" and r.get("werkelijk_uit","")!=""}
    totals={norm(r["naam"]):[r["naam"],int(r["punten_fase1"] or 0)] for r in p1}
    for r in preds:
        if r["wedstrijd"] not in results: continue
        if r.get("voorspeld_thuis","")=="" or r.get("voorspeld_uit","")=="": continue
        a=results[r["wedstrijd"]]; ph=int(r["voorspeld_thuis"]);pa=int(r["voorspeld_uit"]); ah=int(a["werkelijk_thuis"]);aa=int(a["werkelijk_uit"])
        pr=(ph>pa)-(ph<pa); ar=(ah>aa)-(ah<aa)
        pts=5 if (ph,pa)==(ah,aa) else 3 if pr==ar else 0
        if norm(r["naam"]) in totals: totals[norm(r["naam"])][1]+=pts
    out=Path("data/fase3/punten_tot_fase2.csv");out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.writer(f);w.writerow(["naam","punten_tot_fase2"]);w.writerows(sorted(totals.values(),key=lambda x:(-x[1],x[0])))
    print(f"Geschreven: {out}")
if __name__=="__main__":main()
