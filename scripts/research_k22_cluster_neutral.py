from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from lottery.data import load_draws_df,load_research_archive
from lottery.models import current_pool_649
from lottery.wheels import build_broad_six,extend_sequence

POOL_K=22
MAX_SWAPS=2
BOTTOM_REMOVABLE=8
OUTSIDE_CANDIDATES=8
TARGET_ADJ=10
TARGET_TRIPLES=4
SIZES=(6,10,11,22)
MIN_HISTORY=100


def inventory(pool):
    s=set(map(int,pool))
    adj=sum(1 for x in range(1,49) if x in s and x+1 in s)
    tri=sum(1 for x in range(1,48) if x in s and x+1 in s and x+2 in s)
    return adj,tri


def neutralize(pool,additions,score):
    pool=list(map(int,pool))
    pset=set(pool)
    protected=set(map(int,additions))
    ranked=[int(n) for n in score.sort_values(ascending=False).index]
    removable=sorted(
        [n for n in pool if n not in protected],
        key=lambda n:(float(score.loc[n]),-n)
    )[:BOTTOM_REMOVABLE]
    outsiders=[n for n in ranked if n not in pset][:OUTSIDE_CANDIDATES]

    def evaluate(candidate,swaps):
        adj,tri=inventory(candidate)
        excess_adj=max(0,adj-TARGET_ADJ)
        excess_tri=max(0,tri-TARGET_TRIPLES)
        total_score=sum(float(score.loc[n]) for n in candidate)
        # Structural objective first; then minimal intervention; then score retention.
        return (
            2*excess_tri+excess_adj,
            excess_tri,
            excess_adj,
            swaps,
            -total_score,
            tuple(sorted(candidate)),
        )

    best=list(pool);best_key=evaluate(best,0);best_swaps=[]
    # one swap
    for rem in removable:
        for add in outsiders:
            cand=[n for n in pool if n!=rem]+[add]
            key=evaluate(cand,1)
            if key<best_key:
                best,best_key,best_swaps=cand,key,[(rem,add)]
    # two simultaneous swaps
    for rems in itertools.combinations(removable,2):
        for adds in itertools.combinations(outsiders,2):
            cand=[n for n in pool if n not in rems]+list(adds)
            if len(set(cand))!=POOL_K:
                continue
            key=evaluate(cand,2)
            if key<best_key:
                best,best_key,best_swaps=cand,key,list(zip(rems,adds))

    # Return in score-rank order; flex repeat additions remain members when present.
    best=sorted(best,key=lambda n:(-float(score.loc[n]),n))
    a0,t0=inventory(pool);a1,t1=inventory(best)
    return best,{
        "swaps":len(best_swaps),
        "swap_pairs":[[int(a),int(b)] for a,b in best_swaps],
        "adj_before":a0,"adj_after":a1,
        "triples_before":t0,"triples_after":t1,
        "score_before":sum(float(score.loc[n]) for n in pool),
        "score_after":sum(float(score.loc[n]) for n in best),
    }


def best_hits(tickets,actual):
    a=set(actual)
    hs=[len(set(t)&a) for t in tickets]
    return max(hs),sum(h>=3 for h in hs),sum(h>=4 for h in hs),sum(h>=5 for h in hs)


def sequence(pool,score,maxn=22):
    base=build_broad_six(pool,score,649)
    return extend_sequence(base,pool,score,maxn,20260917+490000)


def evaluate_draws(draws,max_targets,label):
    target_count=min(max_targets,len(draws)-MIN_HISTORY)
    rows=[]
    for i in range(target_count):
        actual=draws[i]
        hist=draws[i+1:]
        base,adds,diag,score=current_pool_649(hist,22)
        cand,meta=neutralize(base,adds,score)
        bh=len(set(base)&set(actual));ch=len(set(cand)&set(actual))
        bseq=sequence(base,score,max(SIZES))
        cseq=sequence(cand,score,max(SIZES))
        for n in SIZES:
            bb=best_hits(bseq[:n],actual)
            cc=best_hits(cseq[:n],actual)
            rows.append({
                "dataset":label,"target_index":i,"size":n,
                "pool_hits_base":bh,"pool_hits_cand":ch,
                "pool_hit_delta":ch-bh,
                "best_base":bb[0],"best_cand":cc[0],
                "best_delta":cc[0]-bb[0],
                "n3_base":bb[1],"n3_cand":cc[1],
                "n4_base":bb[2],"n4_cand":cc[2],
                "n5_base":bb[3],"n5_cand":cc[3],
                **meta,
            })
    return pd.DataFrame(rows)


def summarize(df):
    out={}
    # pool summary once per target, use smallest size
    g=df[df["size"]==min(SIZES)]
    out["pool"]={
        "draws":int(len(g)),
        "mean_hits_base":float(g.pool_hits_base.mean()),
        "mean_hits_cand":float(g.pool_hits_cand.mean()),
        "wins":int((g.pool_hit_delta>0).sum()),
        "ties":int((g.pool_hit_delta==0).sum()),
        "losses":int((g.pool_hit_delta<0).sum()),
        "p4plus_base":float((g.pool_hits_base>=4).mean()),
        "p4plus_cand":float((g.pool_hits_cand>=4).mean()),
        "p5plus_base":float((g.pool_hits_base>=5).mean()),
        "p5plus_cand":float((g.pool_hits_cand>=5).mean()),
        "p6_base":float((g.pool_hits_base>=6).mean()),
        "p6_cand":float((g.pool_hits_cand>=6).mean()),
        "mean_adj_base":float(g.adj_before.mean()),
        "mean_adj_cand":float(g.adj_after.mean()),
        "mean_triples_base":float(g.triples_before.mean()),
        "mean_triples_cand":float(g.triples_after.mean()),
        "changed_draws":int((g.swaps>0).sum()),
        "mean_swaps":float(g.swaps.mean()),
        "max_swaps":int(g.swaps.max()),
        "mean_score_delta":float((g.score_after-g.score_before).mean()),
    }
    for n in SIZES:
        s=df[df["size"]==n]
        out[str(n)]={
            "draws":int(len(s)),
            "mean_best_base":float(s.best_base.mean()),
            "mean_best_cand":float(s.best_cand.mean()),
            "best_wins":int((s.best_delta>0).sum()),
            "best_ties":int((s.best_delta==0).sum()),
            "best_losses":int((s.best_delta<0).sum()),
            "p3plus_base":float((s.best_base>=3).mean()),
            "p3plus_cand":float((s.best_cand>=3).mean()),
            "p4plus_base":float((s.best_base>=4).mean()),
            "p4plus_cand":float((s.best_cand>=4).mean()),
            "p5plus_base":float((s.best_base>=5).mean()),
            "p5plus_cand":float((s.best_cand>=5).mean()),
            "mean_n3_delta":float((s.n3_cand-s.n3_base).mean()),
            "mean_n4_delta":float((s.n4_cand-s.n4_base).mean()),
        }
    return out


def main():
    cur=load_draws_df("6/49")
    cols=[f"n{i}" for i in range(1,7)]
    current=[list(map(int,r)) for r in cur[cols].to_numpy().tolist()]
    _,archive=load_research_archive("6/49")

    latest=evaluate_draws(current,150,"current_150")
    arch=evaluate_draws(archive,300,"archive_300")

    print("K22_CLUSTER_NEUTRAL_BEGIN")
    print(json.dumps({
        "design":{
            "pool_k":POOL_K,"max_swaps":MAX_SWAPS,
            "protected":"repeat additions",
            "removable":"bottom 8 score-ranked non-protected selected numbers",
            "replacement":"top 8 score-ranked numbers outside K22",
            "neutral_targets":{"adjacent_pairs_max":TARGET_ADJ,"consecutive_triples_max":TARGET_TRIPLES},
            "selection":"lexicographic: minimize cluster excess, then swaps, then maximize retained score",
            "outcome_blind":True,
        },
        "current150":summarize(latest),
        "archive300":summarize(arch),
        "note":"Historical outcomes are evaluation only; challenger construction uses only pre-draw scores and combinatorial cluster targets."
    },indent=2))
    print("K22_CLUSTER_NEUTRAL_END")


if __name__=="__main__":
    main()
