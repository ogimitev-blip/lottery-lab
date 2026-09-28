from __future__ import annotations

import itertools
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from lottery.data import load_draws_df, load_research_archive
from lottery.models import current_pool_649
from lottery.wheels import build_broad_six, extend_sequence

ROOT=Path(__file__).resolve().parents[1]
SIZES=(6,11,22,33,55)
TRAIN_LO,TRAIN_HI=50,150
VALID_LO,VALID_HI=0,50
ARCHIVE_MAX=250
PROPOSALS=64
SEED=20260928


def pav_decreasing(values):
    blocks=[]
    for i,v in enumerate(values):
        blocks.append([i,i,float(v),1.0])
        while len(blocks)>=2 and blocks[-2][2] < blocks[-1][2]:
            b=blocks.pop();a=blocks.pop()
            w=a[3]+b[3]
            m=(a[2]*a[3]+b[2]*b[3])/w
            blocks.append([a[0],b[1],m,w])
    out=np.zeros(len(values),dtype=float)
    for lo,hi,m,w in blocks:
        out[lo:hi+1]=m
    return out


def training_rank_weights(draws):
    counts=np.zeros(22,dtype=float)
    n=0
    ph=[]
    for i in range(TRAIN_LO,min(TRAIN_HI,len(draws)-100)):
        actual=set(draws[i])
        hist=draws[i+1:]
        pool,adds,diag,score=current_pool_649(hist,22)
        ranked=sorted([int(x) for x in pool],key=lambda x:(-float(score.loc[x]),x))
        counts += np.array([1.0 if x in actual else 0.0 for x in ranked])
        ph.append(sum(x in actual for x in ranked))
        n+=1
    overall=float(counts.sum()/(n*22))
    prior_strength=12.0
    rates=(counts+prior_strength*overall)/(n+prior_strength)
    iso=pav_decreasing(rates)
    weights=iso/iso.sum()
    return {
        "draws":n,
        "counts":counts.tolist(),
        "raw_rates":(counts/n).tolist(),
        "shrunk_rates":rates.tolist(),
        "isotonic_rates":iso.tolist(),
        "weights":weights.tolist(),
        "mean_pool_hits":float(np.mean(ph)),
    }


def subset_values(weights,r):
    vals={}
    for q in itertools.combinations(range(1,23),r):
        chosen=[i-1 for i in q]
        base=float(np.prod([weights[i] for i in chosen]))
        rem=[i for i in range(22) if i not in chosen]
        need=6-r
        tail=0.0
        for extra in itertools.combinations(rem,need):
            tail += float(np.prod([weights[i] for i in extra]))
        vals[q]=base*tail
    return vals


def map_base_to_positions(base_tickets,ranked):
    pos={int(n):i+1 for i,n in enumerate(ranked)}
    return [tuple(sorted(pos[int(n)] for n in t)) for t in base_tickets]


def extend_v5(base_tickets,pool,score,max_lines,rank_weights,q4val,q5val,seed=SEED):
    ranked=sorted([int(x) for x in pool],key=lambda x:(-float(score.loc[x]),x))
    selected=map_base_to_positions(base_tickets,ranked)
    selected_set=set(selected)
    c4=Counter(x for t in selected for x in itertools.combinations(t,4))
    c3=Counter(x for t in selected for x in itertools.combinations(t,3))
    c2=Counter(x for t in selected for x in itertools.combinations(t,2))
    exp=Counter(x for t in selected for x in t)
    rng=np.random.default_rng(seed)

    p=np.asarray(rank_weights,dtype=float)
    while len(selected)<max_lines:
        props=set();tries=0
        exp_arr=np.array([exp[i] for i in range(1,23)],dtype=float)
        sample_w=p/np.sqrt(1.0+exp_arr)
        sample_w/=sample_w.sum()
        while len(props)<PROPOSALS and tries<PROPOSALS*100:
            tries+=1
            t=tuple(sorted(map(int,rng.choice(np.arange(1,23),6,replace=False,p=sample_w))))
            if t in selected_set: continue
            # Preserve maximal uniform 5+ neighborhoods: no two lines intersect >3.
            if any(len(set(t)&set(s))>3 for s in selected): continue
            props.add(t)
        if not props:
            raise RuntimeError("v5 extension candidate exhaustion")

        target=np.array(rank_weights,dtype=float)
        target=target/target.sum()*6.0*(len(selected)+1)
        best=None;bestkey=None
        for t in props:
            q4=list(itertools.combinations(t,4))
            q5=list(itertools.combinations(t,5))
            q3=list(itertools.combinations(t,3))
            q2=list(itertools.combinations(t,2))
            weighted_new4=sum(q4val[x] for x in q4 if c4[x]==0)
            weighted5=sum(q5val[x] for x in q5)
            new4=sum(c4[x]==0 for x in q4)
            dup4=sum(c4[x] for x in q4)
            dup3=sum(c3[x] for x in q3)
            dup2=sum(c2[x] for x in q2)
            balance_delta=0.0
            for n in t:
                before=(exp[n]-target[n-1])**2
                after=(exp[n]+1-target[n-1])**2
                balance_delta+=after-before
            # Weighted 4-set novelty leads; weighted 5-neighborhood quality protects
            # high-rank rare-prize conversion; uniform novelty and balance break ties.
            key=(weighted_new4,weighted5,new4,-dup4,-dup3,-dup2,-balance_delta)
            if bestkey is None or key>bestkey:
                bestkey=key;best=t
        selected.append(best);selected_set.add(best)
        for x in itertools.combinations(best,4):c4[x]+=1
        for x in itertools.combinations(best,3):c3[x]+=1
        for x in itertools.combinations(best,2):c2[x]+=1
        for n in best:exp[n]+=1

    return [tuple(ranked[p-1] for p in t) for t in selected]


def score(tickets,actual):
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


def paired(cand,base):
    m=cand.merge(base,on=["target","size"],suffixes=("_cand","_base"))
    d=m.best_cand-m.best_base
    return {
        "wins":int((d>0).sum()),"ties":int((d==0).sum()),"losses":int((d<0).sum()),
        "mean_best_delta":float(d.mean()),
        "p4plus_delta_pp":float(100*((m.best_cand>=4).mean()-(m.best_base>=4).mean())),
        "p5plus_delta_pp":float(100*((m.best_cand>=5).mean()-(m.best_base>=5).mean())),
        "mean_n4_delta":float((m.n4_cand-m.n4_base).mean()),
        "mean_n5_delta":float((m.n5_cand-m.n5_base).mean()),
    }


def eval_dataset(draws,indices,rank_weights,q4val,q5val,label):
    rows=[]
    for i in indices:
        actual=draws[i]
        hist=draws[i+1:]
        if len(hist)<100: continue
        pool,adds,diag,scorev=current_pool_649(hist,22)
        base6=build_broad_six(pool,scorev,649)
        base55=extend_sequence(base6,pool,scorev,55,20260917+490000)
        cand55=extend_v5(base6,pool,scorev,55,rank_weights,q4val,q5val,SEED+i)
        pool_hits=len(set(pool)&set(actual))
        for size in SIZES:
            for kind,tickets in [("baseline",base55[:size]),("candidate",cand55[:size])]:
                rows.append({"target":i,"size":size,"kind":kind,"pool_hits":pool_hits,**score(tickets,actual)})
    df=pd.DataFrame(rows)
    out={}
    for size in SIZES:
        sub=df[df["size"]==size]
        b=sub[sub.kind=="baseline"];c=sub[sub.kind=="candidate"]
        out[str(size)]={"baseline":summarize(b),"candidate":summarize(c),"pairwise":paired(c,b)}
    high={}
    for phkey,mask in [("ge4",df.pool_hits>=4),("eq5",df.pool_hits==5),("eq6",df.pool_hits==6)]:
        high[phkey]={}
        for size in SIZES:
            sub=df[mask & (df["size"]==size)]
            if sub.empty:
                high[phkey][str(size)]={"draws":0};continue
            b=sub[sub.kind=="baseline"];c=sub[sub.kind=="candidate"]
            high[phkey][str(size)]={"draws":int(len(b)),"baseline":summarize(b),"candidate":summarize(c),"pairwise":paired(c,b)}
    return {"label":label,"summary":out,"conditional":high}


def main():
    raw=load_draws_df("6/49")
    draws=[list(map(int,row)) for row in raw[[f"n{i}" for i in range(1,7)]].to_numpy().tolist()]
    cal=training_rank_weights(draws)
    weights=cal["weights"]
    q4val=subset_values(weights,4)
    q5val=subset_values(weights,5)

    valid_idx=range(VALID_LO,min(VALID_HI,len(draws)-100))
    latest=eval_dataset(draws,valid_idx,weights,q4val,q5val,"2026 latest-50 validation")

    adf,adraws=load_research_archive("6/49")
    max_i=min(ARCHIVE_MAX,len(adraws)-100)
    archive=eval_dataset(adraws,range(0,max_i),weights,q4val,q5val,"2020-2023 archive validation")

    # Post-selection diagnostic only; not part of candidate design or validation.
    actual76=[8,9,17,27,37,48]
    pool76,adds76,diag76,score76=current_pool_649(draws,22)
    base6=build_broad_six(pool76,score76,649)
    base55=extend_sequence(base6,pool76,score76,55,20260917+490000)
    cand55=extend_v5(base6,pool76,score76,55,weights,q4val,q5val,SEED+76)
    post76={}
    for size in SIZES:
        post76[str(size)]={"baseline":score(base55[:size],actual76),"candidate":score(cand55[:size],actual76)}

    print("K22_V5_BEGIN")
    print(json.dumps({
        "training":{"window":"2026 prior 100 only","calibration":cal},
        "algorithm":{"proposals":PROPOSALS,"seed":SEED,"first6":"unchanged dynamic production broad-six","pairwise_intersection_cap":3},
        "latest50":latest,
        "archive":archive,
        "draw76_posthoc":post76,
        "note":"Rank calibration uses only the older 100-draw development window. Latest-50 and 2020-2023 archive outcomes are not used to build the extension. First six tickets are always the existing production broad-six."
    },indent=2))
    print("K22_V5_END")


if __name__=="__main__":
    main()
