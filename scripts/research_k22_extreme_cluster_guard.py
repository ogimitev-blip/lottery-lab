from __future__ import annotations

import itertools
import json
from collections import Counter

import numpy as np
import pandas as pd

from lottery.data import load_draws_df,load_research_archive
from lottery.models import current_pool_649
from lottery.wheels import build_broad_six,extend_sequence

POOL_K=22
MAX_SWAPS=2
BOTTOM_REMOVABLE=8
OUTSIDE_CANDIDATES=8
SIZES=(6,10,11,22)
MIN_HISTORY=100
RANDOM_POOLS=250000
SEED=20261005


def inventory(pool):
    s=set(map(int,pool))
    adj=sum(1 for x in range(1,49) if x in s and x+1 in s)
    tri=sum(1 for x in range(1,48) if x in s and x+1 in s and x+2 in s)
    return adj,tri


def random_threshold():
    rng=np.random.default_rng(SEED)
    universe=np.arange(1,50,dtype=int)
    scores=[]
    pairs=[]
    for _ in range(RANDOM_POOLS):
        pool=rng.choice(universe,POOL_K,replace=False)
        a,t=inventory(pool)
        # Triples are rarer/more concentrated, so weight them double.
        scores.append(a+2*t)
        pairs.append((a,t))
    scores=np.asarray(scores,dtype=int)
    q95=int(np.quantile(scores,0.95,method="higher"))
    trigger_min=q95+1
    trigger_rate=float((scores>=trigger_min).mean())
    return {
        "score_formula":"adjacent_pairs + 2*consecutive_triples",
        "q95_score":q95,
        "trigger_score_min":trigger_min,
        "random_trigger_rate":trigger_rate,
        "samples":RANDOM_POOLS,
        "adj_mean":float(np.mean([a for a,t in pairs])),
        "tri_mean":float(np.mean([t for a,t in pairs])),
        "score_mean":float(scores.mean()),
    }


def cluster_score(pool):
    a,t=inventory(pool)
    return a+2*t,a,t


def guard(pool,additions,score,threshold):
    pool=list(map(int,pool))
    before_score,a0,t0=cluster_score(pool)
    if before_score < threshold:
        return sorted(pool,key=lambda n:(-float(score.loc[n]),n)),{
            "triggered":False,"swaps":0,"swap_pairs":[],
            "cluster_score_before":before_score,"cluster_score_after":before_score,
            "adj_before":a0,"adj_after":a0,"triples_before":t0,"triples_after":t0,
            "score_before":sum(float(score.loc[n]) for n in pool),
            "score_after":sum(float(score.loc[n]) for n in pool),
        }

    pset=set(pool)
    protected=set(map(int,additions))
    ranked=[int(n) for n in score.sort_values(ascending=False).index]
    removable=sorted(
        [n for n in pool if n not in protected],
        key=lambda n:(float(score.loc[n]),-n)
    )[:BOTTOM_REMOVABLE]
    outsiders=[n for n in ranked if n not in pset][:OUTSIDE_CANDIDATES]

    base_total=sum(float(score.loc[n]) for n in pool)
    best=list(pool)
    best_swaps=[]

    def candidate_key(candidate,nswap):
        cs,aa,tt=cluster_score(candidate)
        total_score=sum(float(score.loc[n]) for n in candidate)
        # Primary objective: exit the extreme zone. Once outside it, prefer
        # the fewest swaps before seeking any further reduction in clustering.
        # If no candidate can exit, minimize residual clustering first.
        if cs < threshold:
            return (0,nswap,cs,-total_score,tuple(sorted(candidate)))
        return (1,cs,nswap,-total_score,tuple(sorted(candidate)))

    best_key=candidate_key(best,0)

    for nswap in range(1,MAX_SWAPS+1):
        for rems in itertools.combinations(removable,nswap):
            for adds in itertools.combinations(outsiders,nswap):
                cand=[n for n in pool if n not in rems]+list(adds)
                if len(set(cand))!=POOL_K:
                    continue
                key=candidate_key(cand,nswap)
                if key<best_key:
                    best,best_key,best_swaps=cand,key,list(zip(rems,adds))

    best=sorted(best,key=lambda n:(-float(score.loc[n]),n))
    after_score,a1,t1=cluster_score(best)
    return best,{
        "triggered":True,"swaps":len(best_swaps),
        "swap_pairs":[[int(a),int(b)] for a,b in best_swaps],
        "cluster_score_before":before_score,"cluster_score_after":after_score,
        "adj_before":a0,"adj_after":a1,"triples_before":t0,"triples_after":t1,
        "score_before":base_total,
        "score_after":sum(float(score.loc[n]) for n in best),
    }


def sequence(pool,score,maxn=22):
    base=build_broad_six(pool,score,649)
    return extend_sequence(base,pool,score,maxn,20260917+490000)


def hit_metrics(tickets,actual):
    a=set(actual)
    hs=[len(set(t)&a) for t in tickets]
    return {
        "best":max(hs),
        "n3":sum(h>=3 for h in hs),
        "n4":sum(h>=4 for h in hs),
        "n5":sum(h>=5 for h in hs),
        "n6":sum(h>=6 for h in hs),
    }


def evaluate(draws,max_targets,label,threshold):
    target_count=min(max_targets,len(draws)-MIN_HISTORY)
    rows=[]
    for i in range(target_count):
        actual=draws[i]
        hist=draws[i+1:]
        base,adds,diag,score=current_pool_649(hist,22)
        cand,meta=guard(base,adds,score,threshold)

        pool_base=len(set(base)&set(actual))
        pool_cand=len(set(cand)&set(actual))
        bseq=sequence(base,score,max(SIZES))
        # If the guard did not trigger, candidate == production by definition.
        # Avoid rebuilding an identical wheel on the ~95% non-extreme draws.
        cseq=bseq if not meta["triggered"] else sequence(cand,score,max(SIZES))
        for n in SIZES:
            bm=hit_metrics(bseq[:n],actual)
            cm=bm if not meta["triggered"] else hit_metrics(cseq[:n],actual)
            rows.append({
                "dataset":label,"target_index":i,"size":n,
                "pool_hits_base":pool_base,"pool_hits_cand":pool_cand,
                "pool_hit_delta":pool_cand-pool_base,
                "best_base":bm["best"],"best_cand":cm["best"],
                "best_delta":cm["best"]-bm["best"],
                "n3_base":bm["n3"],"n3_cand":cm["n3"],
                "n4_base":bm["n4"],"n4_cand":cm["n4"],
                "n5_base":bm["n5"],"n5_cand":cm["n5"],
                "n6_base":bm["n6"],"n6_cand":cm["n6"],
                **meta,
            })
    return pd.DataFrame(rows)


def summarize(df):
    out={}
    g=df[df["size"]==min(SIZES)].copy()
    trig=g[g.triggered==True]
    out["pool"]={
        "draws":int(len(g)),
        "triggered_draws":int(g.triggered.sum()),
        "trigger_rate":float(g.triggered.mean()),
        "mean_hits_base":float(g.pool_hits_base.mean()),
        "mean_hits_cand":float(g.pool_hits_cand.mean()),
        "overall_wins":int((g.pool_hit_delta>0).sum()),
        "overall_ties":int((g.pool_hit_delta==0).sum()),
        "overall_losses":int((g.pool_hit_delta<0).sum()),
        "p4plus_base":float((g.pool_hits_base>=4).mean()),
        "p4plus_cand":float((g.pool_hits_cand>=4).mean()),
        "p5plus_base":float((g.pool_hits_base>=5).mean()),
        "p5plus_cand":float((g.pool_hits_cand>=5).mean()),
        "p6_base":float((g.pool_hits_base>=6).mean()),
        "p6_cand":float((g.pool_hits_cand>=6).mean()),
        "triggered_only":{
            "draws":int(len(trig)),
            "mean_hits_base":None if trig.empty else float(trig.pool_hits_base.mean()),
            "mean_hits_cand":None if trig.empty else float(trig.pool_hits_cand.mean()),
            "wins":int((trig.pool_hit_delta>0).sum()),
            "ties":int((trig.pool_hit_delta==0).sum()),
            "losses":int((trig.pool_hit_delta<0).sum()),
            "mean_cluster_before":None if trig.empty else float(trig.cluster_score_before.mean()),
            "mean_cluster_after":None if trig.empty else float(trig.cluster_score_after.mean()),
            "mean_swaps":None if trig.empty else float(trig.swaps.mean()),
            "mean_model_score_delta":None if trig.empty else float((trig.score_after-trig.score_before).mean()),
        }
    }
    for n in SIZES:
        s=df[df["size"]==n]
        st=s[s.triggered==True]
        out[str(n)]={
            "draws":int(len(s)),
            "p3plus_base":float((s.best_base>=3).mean()),
            "p3plus_cand":float((s.best_cand>=3).mean()),
            "p4plus_base":float((s.best_base>=4).mean()),
            "p4plus_cand":float((s.best_cand>=4).mean()),
            "p5plus_base":float((s.best_base>=5).mean()),
            "p5plus_cand":float((s.best_cand>=5).mean()),
            "mean_best_base":float(s.best_base.mean()),
            "mean_best_cand":float(s.best_cand.mean()),
            "best_wins":int((s.best_delta>0).sum()),
            "best_ties":int((s.best_delta==0).sum()),
            "best_losses":int((s.best_delta<0).sum()),
            "triggered_only":{
                "draws":int(len(st)),
                "p3plus_base":None if st.empty else float((st.best_base>=3).mean()),
                "p3plus_cand":None if st.empty else float((st.best_cand>=3).mean()),
                "p4plus_base":None if st.empty else float((st.best_base>=4).mean()),
                "p4plus_cand":None if st.empty else float((st.best_cand>=4).mean()),
                "mean_best_base":None if st.empty else float(st.best_base.mean()),
                "mean_best_cand":None if st.empty else float(st.best_cand.mean()),
                "wins":int((st.best_delta>0).sum()),
                "ties":int((st.best_delta==0).sum()),
                "losses":int((st.best_delta<0).sum()),
            }
        }
    return out


def main():
    threshold_meta=random_threshold()
    threshold=int(threshold_meta["trigger_score_min"])

    cur=load_draws_df("6/49")
    cols=[f"n{i}" for i in range(1,7)]
    current=[list(map(int,r)) for r in cur[cols].to_numpy().tolist()]
    _,archive=load_research_archive("6/49")

    cur150=evaluate(current,150,"current_150",threshold)
    arc300=evaluate(archive,300,"archive_300",threshold)

    print("K22_EXTREME_GUARD_BEGIN")
    print(json.dumps({
        "design":{
            "trigger":"cluster_score > random K22 95th-percentile value (integer trigger_score_min)",
            "threshold":threshold_meta,
            "max_swaps":MAX_SWAPS,
            "protected":"repeat additions",
            "removable":"bottom 8 score-ranked non-protected K22 numbers",
            "replacement":"top 8 score-ranked outsiders",
            "selection":"exit extreme zone if possible; then minimize clustering, swaps, and model-score loss",
            "outcome_blind":True,
        },
        "current150":summarize(cur150),
        "archive300":summarize(arc300),
        "note":"Historical outcomes are evaluation only. Trigger threshold comes solely from uniformly random 22-of-49 pools."
    },indent=2))
    print("K22_EXTREME_GUARD_END")


if __name__=="__main__":
    main()
