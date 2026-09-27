from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from lottery.data import load_draws_df
from lottery.models import current_pool_649
from lottery.wheels import build_broad_six,extend_sequence

ROOT=Path(__file__).resolve().parents[1]
CANDIDATE_PATH=ROOT/"systems"/"k22_conversion_v4_candidate.csv"
SIZES=(6,11,22,33,55)
MIN_HISTORY=100
MAX_TARGETS=150


def load_candidate():
    df=pd.read_csv(CANDIDATE_PATH)
    cols=[f"pos{i}" for i in range(1,7)]
    return [tuple(map(int,row)) for row in df[cols].to_numpy().tolist()]


def metrics(hits):
    a=np.asarray(hits,dtype=int)
    return {
        "draws":int(len(a)),
        "best_mean":float(a.mean()),
        "p3plus":float((a>=3).mean()),
        "p4plus":float((a>=4).mean()),
        "p5plus":float((a>=5).mean()),
        "p6":float((a>=6).mean()),
    }


def paired(g):
    d=g.candidate_best-g.baseline_best
    return {
        "candidate_wins":int((d>0).sum()),
        "ties":int((d==0).sum()),
        "baseline_wins":int((d<0).sum()),
        "mean_best_delta":float(d.mean()),
        "p3plus_delta_pp":float(100*((g.candidate_best>=3).mean()-(g.baseline_best>=3).mean())),
        "p4plus_delta_pp":float(100*((g.candidate_best>=4).mean()-(g.baseline_best>=4).mean())),
        "p5plus_delta_pp":float(100*((g.candidate_best>=5).mean()-(g.baseline_best>=5).mean())),
        "mean_3plus_lines_delta":float((g.candidate_n3-g.baseline_n3).mean()),
        "mean_4plus_lines_delta":float((g.candidate_n4-g.baseline_n4).mean()),
        "mean_5plus_lines_delta":float((g.candidate_n5-g.baseline_n5).mean()),
    }


def main():
    candidate=load_candidate()
    raw=load_draws_df("6/49")
    cols=[f"n{i}" for i in range(1,7)]
    draws=[list(map(int,row)) for row in raw[cols].to_numpy().tolist()]
    limit=min(MAX_TARGETS,len(draws)-MIN_HISTORY)
    if limit<50:
        raise RuntimeError("Insufficient history")

    rows=[]
    first6_mismatches=0
    for i in range(limit):
        actual=set(draws[i])
        hist=draws[i+1:]
        pool,adds,diag,score=current_pool_649(hist,22)
        ranked=sorted([int(n) for n in pool],key=lambda n:(-float(score.loc[n]),n))

        base6=build_broad_six(pool,score,649)
        baseline55=extend_sequence(base6,pool,score,55,20260917+490000)
        cand55=[tuple(ranked[p-1] for p in line) for line in candidate]

        if {tuple(sorted(t)) for t in baseline55[:6]} != {tuple(sorted(t)) for t in cand55[:6]}:
            first6_mismatches+=1

        pool_hits=len(set(pool)&actual)
        for n in SIZES:
            bh=[len(set(t)&actual) for t in baseline55[:n]]
            ch=[len(set(t)&actual) for t in cand55[:n]]
            rows.append({
                "target_index":i,
                "size":n,
                "pool_hits":pool_hits,
                "baseline_best":max(bh),
                "candidate_best":max(ch),
                "baseline_n3":sum(h>=3 for h in bh),
                "candidate_n3":sum(h>=3 for h in ch),
                "baseline_n4":sum(h>=4 for h in bh),
                "candidate_n4":sum(h>=4 for h in ch),
                "baseline_n5":sum(h>=5 for h in bh),
                "candidate_n5":sum(h>=5 for h in ch),
            })

    df=pd.DataFrame(rows)
    windows={
        "LATEST_50":(0,50),
        "PRIOR_100":(50,min(150,limit)),
        "FULL_150":(0,min(150,limit)),
    }
    out={}
    conditional={}
    for w,(lo,hi) in windows.items():
        if hi<=lo: continue
        out[w]={}
        conditional[w]={}
        for n in SIZES:
            g=df[(df["size"]==n)&(df.target_index>=lo)&(df.target_index<hi)].copy()
            out[w][str(n)]={
                "baseline":metrics(g.baseline_best),
                "candidate":metrics(g.candidate_best),
                "paired":paired(g),
            }
            conditional[w][str(n)]={}
            for threshold in (4,5,6):
                h=g[g.pool_hits>=threshold]
                if len(h):
                    conditional[w][str(n)][f"pool_{threshold}plus"]={
                        "draws":int(len(h)),
                        "baseline_p4plus":float((h.baseline_best>=4).mean()),
                        "candidate_p4plus":float((h.candidate_best>=4).mean()),
                        "baseline_p5plus":float((h.baseline_best>=5).mean()),
                        "candidate_p5plus":float((h.candidate_best>=5).mean()),
                        "mean_best_delta":float((h.candidate_best-h.baseline_best).mean()),
                    }

    result={
        "design":{
            "targets":limit,
            "min_history":MIN_HISTORY,
            "sizes":list(SIZES),
            "first6_mismatches":first6_mismatches,
            "candidate_is_outcome_blind":True,
            "note":"Strict walk-forward selection. Candidate wheel was selected from uniform C(22,6) combinatorial coverage before this historical scoring; target outcomes were not used to construct it.",
        },
        "summary":out,
        "conditional":conditional,
    }
    print("K22_V4_WALKFORWARD_BEGIN")
    print(json.dumps(result,indent=2))
    print("K22_V4_WALKFORWARD_END")


if __name__=="__main__":
    main()
