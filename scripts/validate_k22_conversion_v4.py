from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

from lottery.models import current_pool_649
from lottery.wheels import build_broad_six, extend_sequence

ROOT=Path(__file__).resolve().parents[1]
DRAW_PATH=ROOT/"data"/"draws_649.csv"
CAND_PATH=ROOT/"systems"/"k22_conversion_v4_candidate.csv"
SIZES=(6,11,22,33,55)
MIN_HISTORY=100
MAX_TARGETS=150

def load_candidate():
    df=pd.read_csv(CAND_PATH)
    return [tuple(map(int,row)) for row in df.to_numpy().tolist()]

def map_candidate(seq,pool,score):
    ranked=sorted([int(n) for n in pool],key=lambda n:(-float(score.loc[n]),n))
    return [tuple(ranked[p-1] for p in t) for t in seq]

def score_tickets(tickets,actual):
    aset=set(actual)
    hits=[len(set(t)&aset) for t in tickets]
    return {
        "best":max(hits),
        "n3":sum(h>=3 for h in hits),
        "n4":sum(h>=4 for h in hits),
        "n5":sum(h>=5 for h in hits),
        "n6":sum(h==6 for h in hits),
    }

def summarize(df):
    return {
        "draws":int(len(df)),
        "best_mean":float(df.best.mean()),
        "p3plus":float((df.best>=3).mean()),
        "p4plus":float((df.best>=4).mean()),
        "p5plus":float((df.best>=5).mean()),
        "p6":float((df.best>=6).mean()),
        "mean_n3":float(df.n3.mean()),
        "mean_n4":float(df.n4.mean()),
        "mean_n5":float(df.n5.mean()),
        "total_n4":int(df.n4.sum()),
        "total_n5":int(df.n5.sum()),
        "total_n6":int(df.n6.sum()),
    }

def pairwise(a,b):
    m=a.merge(b,on=["target_index","size"],suffixes=("_cand","_base"))
    d=m.best_cand-m.best_base
    return {
        "draws":int(len(m)),
        "best_wins":int((d>0).sum()),
        "best_ties":int((d==0).sum()),
        "best_losses":int((d<0).sum()),
        "mean_best_delta":float(d.mean()),
        "p4plus_delta_pp":float(100*((m.best_cand>=4).mean()-(m.best_base>=4).mean())),
        "p5plus_delta_pp":float(100*((m.best_cand>=5).mean()-(m.best_base>=5).mean())),
        "mean_n4_delta":float((m.n4_cand-m.n4_base).mean()),
        "mean_n5_delta":float((m.n5_cand-m.n5_base).mean()),
    }

def main():
    raw=pd.read_csv(DRAW_PATH)
    cols=[f"n{i}" for i in range(1,7)]
    draws=[list(map(int,row)) for row in raw[cols].to_numpy().tolist()]
    cand_seq=load_candidate()
    limit=min(MAX_TARGETS,len(draws)-MIN_HISTORY)
    rows=[]
    for i in range(limit):
        actual=draws[i]
        hist=draws[i+1:]
        pool,adds,diag,score=current_pool_649(hist,22)
        pool_hits=len(set(map(int,pool)) & set(map(int,actual)))
        base6=build_broad_six(pool,score,649)
        base55=extend_sequence(base6,pool,score,55,20260917+490000)
        cand55=map_candidate(cand_seq,pool,score)
        for size in SIZES:
            for kind,tickets in [("baseline",base55[:size]),("candidate",cand55[:size])]:
                m=score_tickets(tickets,actual)
                rows.append({"target_index":i,"size":size,"kind":kind,"pool_hits":pool_hits,**m})
    df=pd.DataFrame(rows)
    windows={"LATEST_50":(0,50),"PRIOR_100":(50,min(150,limit)),"FULL_150":(0,min(150,limit))}
    out={}
    for w,(lo,hi) in windows.items():
        if hi<=lo: continue
        out[w]={}
        for size in SIZES:
            sub=df[(df.target_index>=lo)&(df.target_index<hi)&(df["size"]==size)]
            base=sub[sub.kind=="baseline"]
            cand=sub[sub.kind=="candidate"]
            out[w][str(size)]={
                "baseline":summarize(base),
                "candidate":summarize(cand),
                "pairwise":pairwise(cand,base),
            }
    conditional={}
    for ph in [4,5,6]:
        conditional[str(ph)]={}
        for size in SIZES:
            sub=df[(df.pool_hits==ph)&(df["size"]==size)]
            if sub.empty:
                conditional[str(ph)][str(size)]={"draws":0}
                continue
            base=sub[sub.kind=="baseline"]
            cand=sub[sub.kind=="candidate"]
            conditional[str(ph)][str(size)]={
                "draws":int(len(base)),
                "baseline":summarize(base),
                "candidate":summarize(cand),
                "pairwise":pairwise(cand,base),
            }
    high=df[(df.pool_hits>=4)]
    conditional_ge4={}
    for size in SIZES:
        sub=high[high["size"]==size]
        base=sub[sub.kind=="baseline"]
        cand=sub[sub.kind=="candidate"]
        conditional_ge4[str(size)]={
            "draws":int(len(base)),
            "baseline":summarize(base),
            "candidate":summarize(cand),
            "pairwise":pairwise(cand,base),
        }

    print("K22_V4_WALKFORWARD_BEGIN")
    print(json.dumps({
        "targets":limit,
        "windows":out,
        "conditional_by_pool_hits":conditional,
        "conditional_pool_hits_ge4":conditional_ge4,
        "note":"Strict target-by-target walk-forward. Candidate conversion layout was frozen before this historical validation and mapped only by score rank within each pre-draw K22 pool."
    },indent=2))
    print("K22_V4_WALKFORWARD_END")

if __name__=="__main__":
    main()
