#!/usr/bin/env python3
"""用 UR Fall 深度特征训练可复现的二分类跌倒候选模型。

仅将标签 1 作为“躺倒”，标签 -1 作为非躺倒；标签 0（过渡姿态）被排除，
模型输出只能作为 V0 候选观察，不能直接触发安全动作。
"""
from __future__ import annotations

import argparse, csv, hashlib, json
from pathlib import Path
import numpy as np

def load(paths: list[Path]):
    rows=[]
    for path in paths:
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.reader(f):
                if len(r) != 11 or int(r[2]) == 0: continue
                rows.append((r[0], int(r[2]), [float(x) for x in r[3:11]]))
    seq=sorted({r[0] for r in rows})
    return rows, seq

def sigmoid(z): return 1.0/(1.0+np.exp(-np.clip(z,-40,40)))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("falls",type=Path); ap.add_argument("adls",type=Path); ap.add_argument("--out",type=Path,required=True); ap.add_argument("--seed",type=int,default=20260825); args=ap.parse_args()
    rows, seq=load([args.falls,args.adls]); rng=np.random.default_rng(args.seed); rng.shuffle(seq)
    n=max(1,int(len(seq)*.2)); test=set(seq[:n]); train=[r for r in rows if r[0] not in test]; valid=[r for r in rows if r[0] in test]
    x=np.asarray([r[2] for r in train]); y=np.asarray([r[1]==1 for r in train],dtype=float); xv=np.asarray([r[2] for r in valid]); yv=np.asarray([r[1]==1 for r in valid],dtype=float)
    mu=x.mean(0); sd=x.std(0); sd[sd<1e-9]=1; x=(x-mu)/sd; xv=(xv-mu)/sd
    w=np.zeros(x.shape[1]); b=0.; lr=.05
    for _ in range(1200):
        p=sigmoid(x@w+b); w-=lr*(x.T@(p-y)/len(y)+1e-3*w); b-=lr*float(np.mean(p-y))
    pred=sigmoid(xv@w+b)>=.5; tp=int(np.sum(pred & (yv==1))); fp=int(np.sum(pred & (yv==0))); fn=int(np.sum((~pred) & (yv==1))); tn=int(np.sum((~pred) & (yv==0)))
    precision=tp/(tp+fp) if tp+fp else 0.; recall=tp/(tp+fn) if tp+fn else 0.
    out=args.out; out.mkdir(parents=True,exist_ok=True); payload={"dataset":"UR Fall","seed":args.seed,"train_sequences":sorted(set(r[0] for r in train)),"test_sequences":sorted(test),"features":8,"excluded_transition_label":0,"metrics":{"tp":tp,"fp":fp,"fn":fn,"tn":tn,"precision":precision,"recall":recall},"mean":mu.tolist(),"scale":sd.tolist(),"weights":w.tolist(),"bias":b}
    model=out/"fall-logreg.json"; model.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8"); payload["model_sha256"]=hashlib.sha256(model.read_bytes()).hexdigest(); (out/"metrics.json").write_text(json.dumps(payload["metrics"],indent=2),encoding="utf-8"); print(json.dumps({"model":str(model),"model_sha256":payload["model_sha256"],"metrics":payload["metrics"]},ensure_ascii=False))

if __name__ == "__main__": main()
