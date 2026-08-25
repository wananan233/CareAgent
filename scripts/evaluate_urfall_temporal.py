#!/usr/bin/env python3
"""评估连续帧确认规则，避免把单帧预测当作安全事实。"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from carehub.vision.fall import FallFeatureClassifier

def main():
    p=argparse.ArgumentParser(); p.add_argument("model",type=Path); p.add_argument("falls",type=Path); p.add_argument("adls",type=Path); p.add_argument("--consecutive",type=int,default=3); p.add_argument("--out",type=Path,required=True); a=p.parse_args()
    if a.consecutive < 1: raise SystemExit("consecutive must be positive")
    clf=FallFeatureClassifier(a.model); tp=fp=fn=tn=0
    for path in (a.falls,a.adls):
        by={}
        with path.open(newline="",encoding="utf-8") as f:
            for r in csv.reader(f):
                if len(r)!=11 or int(r[2])==0: continue
                by.setdefault(r[0],[]).append((int(r[1]),int(r[2]),clf.predict([float(x) for x in r[3:11]]).label=="fall_candidate"))
        for rows in by.values():
            rows.sort(); run=0
            for _,label,pred in rows:
                run=run+1 if pred else 0; confirmed=run>=a.consecutive; actual=label==1
                if confirmed and actual: tp+=1
                elif confirmed and not actual: fp+=1
                elif not confirmed and actual: fn+=1
                else: tn+=1
    report={"consecutive":a.consecutive,"tp":tp,"fp":fp,"fn":fn,"tn":tn,"precision":tp/(tp+fp) if tp+fp else 0,"recall":tp/(tp+fn) if tp+fn else 0}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(report,indent=2),encoding="utf-8"); print(json.dumps(report))
if __name__=="__main__": main()
