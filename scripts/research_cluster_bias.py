from __future__ import annotations

import itertools
import json
import math
from collections import defaultdict

import numpy as np
import pandas as pd

from lottery.data import load_draws_df, load_custom_wheel
from lottery.models import current_pool_642, current_pool_649
from lottery.wheels import build_broad_six, extend_sequence, map_positions

MIN_HISTORY=100
MAX_TARGETS=150
SAMPLE_PER_POOL=6000
SEED=20261005

MODES={
    "6/42":[18,30,50],
    "6/49":[6,11,22],
}


def features(nums):
    x=sorted(map(int,nums))
    gaps=[x[i+1]-x[i] for i in range(5)]
    any_pair=any(g==1 for g in gaps)
    any_triple=any(x[i+2]-x[i]==2 for i in range(4))
    any_quad=any(x[i+3]-x[i]==3 for i in range(3))
    span3_le3=any(x[i+2]-x[i]<=3 for i in range(4))
    span3_le4=any(x[i+2]-x[i]<=4 for i in range(4))
    adjacent_gaps=sum(g==1 for g in gaps)
    min_gap=min(gaps)
    return {
        "pair":int(any_pair),
        "triple":int(any_triple),
        "quad":int(any_quad),
        "span3_le3":int(span3_le3),
        "span3_le4":int(span3_le4),
        "adjacent_gaps":int(adjacent_gaps),
        "min_gap":int(min_gap),
    }


def exact_game_benchmark(maxn):
    sums=defaultdict(float); n=0
    for c in itertools.combinations(range(1,maxn+1),6):
        f=features(c);n+=1
        for k,v in f.items(): sums[k]+=v
    return {k:sums[k]/n for k in sums}|{"universe":n}


def sampled_pool_benchmark(pool,rng,n=SAMPLE_PER_POOL):
    pool=np.array(sorted(map(int,pool)),dtype=int)
    sums=defaultdict(float)
    seen=set()
    # Deterministic Monte Carlo from same selected pool. Sampling without
    # replacement within a line, independent across sampled lines.
    for _ in range(n):
        t=tuple(sorted(map(int,rng.choice(pool,6,replace=False))))
        f=features(t)
        for k,v in f.items(): sums[k]+=v
    return {k:sums[k]/n for k in sums}


def line_summary(tickets):
    sums=defaultdict(float);n=len(tickets)
    for t in tickets:
        f=features(t)
        for k,v in f.items(): sums[k]+=v
    return {k:sums[k]/n for k in sums}|{"lines":n}


def build_tickets(game,hist,n,target_no):
    if game=="6/42":
        pool,adds,diag=current_pool_642(hist,28)
        wheel=load_custom_wheel()
        tickets=map_positions(pool,wheel[:n])
        return tickets,pool
    pool,adds,diag,score=current_pool_649(hist,22)
    base=build_broad_six(pool,score,649)
    tickets=base if n==6 else extend_sequence(base,pool,score,n,20260917+490000)
    return tickets,pool


def main():
    bench={"6/42":exact_game_benchmark(42),"6/49":exact_game_benchmark(49)}
    rng=np.random.default_rng(SEED)
    rows=[]

    for game in ("6/42","6/49"):
        df=load_draws_df(game)
        cols=[f"n{i}" for i in range(1,7)]
        df=df[pd.to_numeric(df.draw_no,errors="coerce").notna()].copy()
        df["draw_no"]=pd.to_numeric(df.draw_no,errors="coerce").astype(int)
        draws=[list(map(int,r)) for r in df[cols].to_numpy().tolist()]
        drawnos=[int(x) for x in df.draw_no]
        limit=min(MAX_TARGETS,len(draws)-MIN_HISTORY)

        for i in range(limit):
            hist=draws[i+1:]
            target_no=drawnos[i]
            # build largest once, take prefixes
            maxn=max(MODES[game])
            all_tickets,pool=build_tickets(game,hist,maxn,target_no)
            pool_b=sampled_pool_benchmark(pool,rng)
            pool_feat=features(pool[:6]) if False else None
            # pool-level adjacency inventory independent of tickets
            ps=sorted(map(int,pool))
            pool_adj_pairs=sum(1 for x in ps if x+1 in set(ps))
            pool_triples=sum(1 for x in ps if x+1 in set(ps) and x+2 in set(ps))

            for n in MODES[game]:
                tickets=all_tickets[:n]
                ls=line_summary(tickets)
                rec={
                    "game":game,"target_draw_no":target_no,"lines":n,
                    "pool_adjacent_pairs":pool_adj_pairs,
                    "pool_consecutive_triples":pool_triples,
                }
                for k in ("pair","triple","quad","span3_le3","span3_le4","adjacent_gaps","min_gap"):
                    rec[f"wheel_{k}"]=ls[k]
                    rec[f"poolrand_{k}"]=pool_b[k]
                    rec[f"game_{k}"]=bench[game][k]
                rows.append(rec)

    d=pd.DataFrame(rows)
    out={}
    for game in ("6/42","6/49"):
        out[game]={}
        for n in MODES[game]:
            g=d[(d.game==game)&(d.lines==n)]
            item={"targets":int(len(g))}
            for k in ("pair","triple","quad","span3_le3","span3_le4","adjacent_gaps","min_gap"):
                w=float(g[f"wheel_{k}"].mean())
                p=float(g[f"poolrand_{k}"].mean())
                q=float(g[f"game_{k}"].mean())
                item[k]={
                    "wheel":w,
                    "same_pool_random":p,
                    "game_random":q,
                    "delta_vs_same_pool_pp":100*(w-p) if k not in ("adjacent_gaps","min_gap") else None,
                    "delta_vs_game_pp":100*(w-q) if k not in ("adjacent_gaps","min_gap") else None,
                }
            item["pool_inventory"]={
                "mean_adjacent_pairs":float(g.pool_adjacent_pairs.mean()),
                "mean_consecutive_triples":float(g.pool_consecutive_triples.mean()),
            }
            out[game][str(n)]=item

    print("CLUSTER_BIAS_BEGIN")
    print(json.dumps({
        "method":{
            "walkforward_targets_per_game":MAX_TARGETS,
            "min_history":MIN_HISTORY,
            "same_pool_random_samples_per_target":SAMPLE_PER_POOL,
            "game_benchmark":"exact enumeration of all 6-number combinations",
            "note":"Separates selection-pool composition from wheel conversion bias."
        },
        "exact_game_benchmarks":bench,
        "results":out,
    },indent=2))
    print("CLUSTER_BIAS_END")

if __name__=="__main__":
    main()
