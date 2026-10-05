from __future__ import annotations

import json
import math
from collections import defaultdict

import numpy as np
import pandas as pd

from lottery.data import load_draws_df,load_research_archive
from lottery.models import _z,fm_score,smooth_score,overdue,flex_pool,production_score_649

MIN_HISTORY=100
K=22
N=49
LAM=.75
CURRENT_TARGETS=150
ARCHIVE_TARGETS=300
VARIANTS=(
    "full_flex",
    "full_top22",
    "no_overdue",
    "no_repeat_overlay",
    "drop_smooth",
    "drop_fm",
    "drop_ps",
)
STANDALONE=(
    "smooth",
    "ps",
    "fm",
    "overdue_gap",
    "ensemble",
    "production_score",
)


def components(history):
    fm,d=fm_score(history,N)
    psc=.40*_z(d.lz)+.20*_z(d.rz)+.15*_z(d.rp)+.15*_z(d.ch)+.10*_z(d.dh)
    ps=pd.Series(_z(psc),index=np.arange(1,N+1),dtype=float)
    sm=smooth_score(history,N).astype(float)
    ensemble=pd.Series(
        _z(.5*_z(ps.values)+.3*_z(fm.values)+.2*_z(sm.values)),
        index=np.arange(1,N+1),dtype=float
    )
    prod,gaps=overdue(ensemble,history,N,LAM,20)
    gap_raw=pd.Series(
        [max(0.0,(gaps[n]-20)/10.0) for n in range(1,N+1)],
        index=np.arange(1,N+1),dtype=float
    )
    gap_score=pd.Series(_z(gap_raw.values),index=np.arange(1,N+1),dtype=float)
    return {
        "ps":ps,"fm":fm.astype(float),"smooth":sm,
        "ensemble":ensemble,"production_score":prod.astype(float),
        "overdue_gap":gap_score,
    },gaps


def mix(parts,weights):
    vals=np.zeros(N,dtype=float)
    total=sum(weights)
    for s,w in zip(parts,weights):
        vals += (w/total)*_z(s.values)
    return pd.Series(_z(vals),index=np.arange(1,N+1),dtype=float)


def with_overdue(base,history):
    return overdue(base,history,N,LAM,20)[0]


def topk(score,k=K):
    return [int(n) for n in score.sort_values(ascending=False).index[:k]]


def pools_for(history):
    c,gaps=components(history)
    prod=c["production_score"]
    full_flex,adds=flex_pool(prod,history,K)

    # Full score but no repeat overlay = pure score top-22.
    full_top=topk(prod)

    # Same ensemble without overdue.
    no_overdue,adds_nood=flex_pool(c["ensemble"],history,K)

    # Explicit alias for testing flex overlay marginally against pure top-22.
    no_repeat=full_top

    # Hierarchical leave-one-family-out, preserving original relative weights.
    no_sm=with_overdue(mix([c["ps"],c["fm"]],[.5,.3]),history)
    no_fm=with_overdue(mix([c["ps"],c["smooth"]],[.5,.2]),history)
    no_ps=with_overdue(mix([c["fm"],c["smooth"]],[.3,.2]),history)

    p1,_=flex_pool(no_sm,history,K)
    p2,_=flex_pool(no_fm,history,K)
    p3,_=flex_pool(no_ps,history,K)

    return {
        "full_flex":full_flex,
        "full_top22":full_top,
        "no_overdue":no_overdue,
        "no_repeat_overlay":no_repeat,
        "drop_smooth":p1,
        "drop_fm":p2,
        "drop_ps":p3,
    },c,adds


def auc_like(score,actual):
    winners=set(actual)
    win=[float(score.loc[n]) for n in winners]
    lose=[float(score.loc[n]) for n in range(1,N+1) if n not in winners]
    better=ties=0
    for a in win:
        for b in lose:
            if a>b: better+=1
            elif a==b: ties+=1
    return (better+0.5*ties)/(len(win)*len(lose))


def eval_dataset(draws,max_targets,label):
    n=min(max_targets,len(draws)-MIN_HISTORY)
    pool_rows=[]
    stand_rows=[]
    win_detail=[]
    for i in range(n):
        actual=list(map(int,draws[i]))
        hist=draws[i+1:]
        pools,c,adds=pools_for(hist)

        base_hits=len(set(pools["full_flex"]) & set(actual))
        for name,pool in pools.items():
            h=len(set(pool)&set(actual))
            pool_rows.append({
                "dataset":label,"target":i,"variant":name,
                "hits":h,"delta_vs_full":h-base_hits,
                "full_hits":base_hits,
            })

        for name in STANDALONE:
            score=c[name]
            p=topk(score)
            stand_rows.append({
                "dataset":label,"target":i,"component":name,
                "top22_hits":len(set(p)&set(actual)),
                "winner_vs_loser_auc":auc_like(score,actual),
                "mean_winner_rank":float(pd.Series(score.rank(ascending=False,method="average"))[actual].mean()),
            })

        if base_hits>=4:
            ranks={}
            for name in ("ps","fm","smooth","overdue_gap","ensemble","production_score"):
                rr=c[name].rank(ascending=False,method="first")
                ranks[name]={str(n):int(rr.loc[n]) for n in actual}
            win_detail.append({
                "target":i,
                "actual":sorted(actual),
                "full_hits":base_hits,
                "repeat_additions":[int(x) for x in adds],
                "component_ranks":ranks,
            })

    return pd.DataFrame(pool_rows),pd.DataFrame(stand_rows),win_detail


def summarize_pools(df):
    base=df[df.variant=="full_flex"].set_index("target")
    out={}
    for name,g in df.groupby("variant"):
        g=g.sort_values("target")
        out[name]={
            "draws":int(len(g)),
            "mean_hits":float(g.hits.mean()),
            "p4plus":float((g.hits>=4).mean()),
            "p5plus":float((g.hits>=5).mean()),
            "p6":float((g.hits>=6).mean()),
            "wins_vs_full":int((g.delta_vs_full>0).sum()),
            "ties_vs_full":int((g.delta_vs_full==0).sum()),
            "losses_vs_full":int((g.delta_vs_full<0).sum()),
            "mean_delta_vs_full":float(g.delta_vs_full.mean()),
            "on_full_4plus":{
                "draws":int((g.full_hits>=4).sum()),
                "mean_hits":float(g.loc[g.full_hits>=4,"hits"].mean()) if (g.full_hits>=4).any() else None,
                "mean_delta":float(g.loc[g.full_hits>=4,"delta_vs_full"].mean()) if (g.full_hits>=4).any() else None,
                "losses":int(((g.full_hits>=4)&(g.delta_vs_full<0)).sum()),
                "wins":int(((g.full_hits>=4)&(g.delta_vs_full>0)).sum()),
            },
            "on_full_5plus":{
                "draws":int((g.full_hits>=5).sum()),
                "mean_hits":float(g.loc[g.full_hits>=5,"hits"].mean()) if (g.full_hits>=5).any() else None,
                "mean_delta":float(g.loc[g.full_hits>=5,"delta_vs_full"].mean()) if (g.full_hits>=5).any() else None,
                "losses":int(((g.full_hits>=5)&(g.delta_vs_full<0)).sum()),
                "wins":int(((g.full_hits>=5)&(g.delta_vs_full>0)).sum()),
            },
        }
    return out


def summarize_standalone(df):
    out={}
    random_mean=K*6/N
    for name,g in df.groupby("component"):
        out[name]={
            "draws":int(len(g)),
            "mean_top22_hits":float(g.top22_hits.mean()),
            "lift_vs_random_mean_hits":float(g.top22_hits.mean()-random_mean),
            "p4plus":float((g.top22_hits>=4).mean()),
            "p5plus":float((g.top22_hits>=5).mean()),
            "p6":float((g.top22_hits>=6).mean()),
            "mean_winner_vs_loser_auc":float(g.winner_vs_loser_auc.mean()),
            "mean_winner_rank":float(g.mean_winner_rank.mean()),
        }
    return {"random_expected_hits":random_mean,"components":out}


def prospective_76_78(draws):
    # Current file is newest-first. Locate exact draw numbers to report, but
    # compute each using only older history.
    df=load_draws_df("6/49")
    nums=pd.to_numeric(df.draw_no,errors="coerce").tolist()
    out={}
    for dn in (76,77,78):
        if dn not in nums:
            continue
        i=nums.index(dn)
        actual=draws[i]
        hist=draws[i+1:]
        pools,c,adds=pools_for(hist)
        row={
            "actual":sorted(actual),
            "repeat_additions":[int(x) for x in adds],
            "variants":{k:len(set(v)&set(actual)) for k,v in pools.items()},
            "winner_ranks":{}
        }
        for comp in ("ps","fm","smooth","overdue_gap","ensemble","production_score"):
            rr=c[comp].rank(ascending=False,method="first")
            row["winner_ranks"][comp]={str(n):int(rr.loc[n]) for n in sorted(actual)}
        out[str(dn)]=row
    return out


def main():
    cur=load_draws_df("6/49")
    cols=[f"n{i}" for i in range(1,7)]
    current=[list(map(int,r)) for r in cur[cols].to_numpy().tolist()]
    _,archive=load_research_archive("6/49")

    cp,cs,cd=eval_dataset(current,CURRENT_TARGETS,"current150")
    ap,ass,ad=eval_dataset(archive,ARCHIVE_TARGETS,"archive300")

    result={
        "method":{
            "k":K,"n":N,"min_history":MIN_HISTORY,
            "current_targets":int(cp.target.nunique()),
            "archive_targets":int(ap.target.nunique()),
            "ablation":"Leave-one-family-out from ensemble; surviving original weights renormalized; overdue and flex overlay preserved unless they are the ablated element.",
            "standalone":"Each family ranked alone to top-22; AUC-like winner-vs-loser ranking diagnostic.",
            "outcome_blind":True,
        },
        "current150":{
            "ablation":summarize_pools(cp),
            "standalone":summarize_standalone(cs),
        },
        "latest50":{
            "ablation":summarize_pools(cp[cp.target<50].copy()),
            "standalone":summarize_standalone(cs[cs.target<50].copy()),
        },
        "prior100":{
            "ablation":summarize_pools(cp[(cp.target>=50)&(cp.target<150)].copy()),
            "standalone":summarize_standalone(cs[(cs.target>=50)&(cs.target<150)].copy()),
        },
        "archive300":{
            "ablation":summarize_pools(ap),
            "standalone":summarize_standalone(ass),
        },
        "prospective_76_78":prospective_76_78(current),
        "high_hit_examples":{
            "current_full_4plus_count":len(cd),
            "archive_full_4plus_count":len(ad),
            "current_examples":cd[:20],
        },
        "note":"Ablation deltas are descriptive historical evidence. Do not infer causal predictability from a small number of 5/6 or 6/6 events."
    }
    print("K22_ATTRIBUTION_BEGIN")
    print(json.dumps(result,indent=2))
    print("K22_ATTRIBUTION_END")


if __name__=="__main__":
    main()
