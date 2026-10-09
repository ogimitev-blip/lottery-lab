from __future__ import annotations

import itertools
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from lottery.data import load_draws_df, load_research_archive, load_custom_wheel
from lottery.models import current_pool_642, current_pool_649
from lottery.wheels import build_broad_six, extend_sequence, map_positions

ROOT=Path(__file__).resolve().parents[1]
SEED=20261009
SAMPLE_N=120000
LATEST_N=50
ARCHIVE_N=250
MIN_HISTORY=100
PREFIXES={"6/49":(5,6,10,11,16,22),"6/42":(6,11,18,30,50)}
MAX_LINES={"6/49":22,"6/42":50}

# A-priori motif families from the user's hypothesis. No target-draw outcomes
# are used in these definitions or in the reordering algorithm.
MOTIFS=(
    "adjacent",
    "gap2",
    "three_consecutive",
    "three_step2",
    "parity_extreme",
    "five_plus_even",
    "five_plus_low25",
    "five_plus_high20",
    "all_low25",
    "all_high20",
    "same_last_pair",
    "same_last_triple",
    "tight_span",
)


def motif_flags(ticket):
    t=tuple(sorted(map(int,ticket)))
    s=set(t)
    gaps=[b-a for a,b in zip(t,t[1:])]
    ev=sum(n%2==0 for n in t)
    low25=sum(n<=25 for n in t)
    high20=sum(n>=20 for n in t)
    last=Counter(n%10 for n in t)
    return {
        "adjacent": int(1 in gaps),
        "gap2": int(2 in gaps),
        "three_consecutive": int(any(a+1 in s and a+2 in s for a in t)),
        "three_step2": int(any(a+2 in s and a+4 in s for a in t)),
        "parity_extreme": int(ev<=1 or ev>=5),
        "five_plus_even": int(ev>=5),
        "five_plus_low25": int(low25>=5),
        "five_plus_high20": int(high20>=5),
        "all_low25": int(low25==6),
        "all_high20": int(high20==6),
        "same_last_pair": int(max(last.values())>=2),
        "same_last_triple": int(max(last.values())>=3),
        "tight_span": int(t[-1]-t[0]<=20),
    }


def population_probs(nmax,seed):
    rng=np.random.default_rng(seed+nmax)
    counts=Counter()
    for _ in range(SAMPLE_N):
        t=tuple(sorted(map(int,rng.choice(np.arange(1,nmax+1),6,replace=False))))
        f=motif_flags(t)
        counts.update({k:v for k,v in f.items() if v})
    return {k:counts[k]/SAMPLE_N for k in MOTIFS}


def z(v):
    a=np.asarray(v,float)
    sd=a.std()
    return np.zeros_like(a) if sd<1e-12 else (a-a.mean())/sd


def structural_features(ticket,selected,exp,pool,c4,c3,c2):
    t=tuple(sorted(ticket))
    new4=sum(c4[x]==0 for x in itertools.combinations(t,4))
    new3=sum(c3[x]==0 for x in itertools.combinations(t,3))
    new2=sum(c2[x]==0 for x in itertools.combinations(t,2))
    overlaps=[len(set(t)&set(s)) for s in selected]
    max_inter=max(overlaps) if overlaps else 0
    target=6.0*(len(selected)+1)/len(pool)
    before=sum((exp[n]-target)**2 for n in pool)
    after=sum(((exp[n]+(1 if n in t else 0))-target)**2 for n in pool)
    exp_gain=before-after
    return new4,new3,new2,exp_gain,-max_inter


def shape_gain(ticket,selected_counts,pop_probs,next_n,variant):
    flags=motif_flags(ticket)
    # Improvement in a variance-scaled marginal-calibration loss. This makes
    # the line set resemble the actual combinatorial shape distribution rather
    # than treating visually "normal" lines as preferred.
    before=0.0;after=0.0
    for k,p in pop_probs.items():
        var=max(p*(1-p),0.03)
        target_before=(next_n-1)*p
        target_after=next_n*p
        c=selected_counts[k]
        before += ((c-target_before)**2)/var
        after += ((c+flags[k]-target_after)**2)/var
    gain=before-after

    if variant=="diverse":
        # Small capped bonus for representing a motif not yet present. It is
        # intentionally modest and ignores ultra-rare (<2%) categories.
        bonus=0.0
        for k,p in pop_probs.items():
            if 0.02<=p<=0.35 and flags[k] and selected_counts[k]==0:
                bonus += min(2.0,0.12/max(p,0.02)**0.5)
        gain += bonus
    return gain


def reorder_shape_aware(tickets,pool,pop_probs,variant="calibrated",alpha=0.30):
    remaining=[tuple(sorted(map(int,t))) for t in tickets]
    selected=[]
    exp=Counter()
    shape_counts=Counter()
    c4=Counter(); c3=Counter(); c2=Counter()
    while remaining:
        structs=[structural_features(t,selected,exp,pool,c4,c3,c2) for t in remaining]
        cols=list(zip(*structs))
        sz=[z(c) for c in cols]
        struct_score=2.0*sz[0]+1.0*sz[1]+0.35*sz[2]+0.70*sz[3]+0.75*sz[4]
        sg=np.array([shape_gain(t,shape_counts,pop_probs,len(selected)+1,variant) for t in remaining],float)
        sgz=z(sg)
        total=(1-alpha)*z(struct_score)+alpha*sgz
        # Stable deterministic tie break by tuple.
        best=max(range(len(remaining)),key=lambda i:(float(total[i]),float(struct_score[i]),float(sg[i]),tuple(-x for x in remaining[i])))
        t=remaining.pop(best)
        selected.append(t)
        for n in t: exp[n]+=1
        for x in itertools.combinations(t,4): c4[x]+=1
        for x in itertools.combinations(t,3): c3[x]+=1
        for x in itertools.combinations(t,2): c2[x]+=1
        f=motif_flags(t)
        for k,v in f.items(): shape_counts[k]+=v
    return selected


def production_sequence(game,hist):
    if game=="6/49":
        pool,adds,diag,score=current_pool_649(hist,22)
        base=build_broad_six(pool,score,649)
        tickets=extend_sequence(base,pool,score,MAX_LINES[game],20260917+490000)
    else:
        pool,adds,diag=current_pool_642(hist,28)
        tickets=map_positions(pool,load_custom_wheel()[:MAX_LINES[game]])
    return [tuple(sorted(map(int,t))) for t in tickets],list(map(int,pool))


def score_prefix(tickets,actual,n):
    aset=set(actual)
    hits=[len(set(t)&aset) for t in tickets[:n]]
    return {
        "best":max(hits) if hits else 0,
        "n3":sum(h>=3 for h in hits),
        "n4":sum(h>=4 for h in hits),
        "n5":sum(h>=5 for h in hits),
        "n6":sum(h>=6 for h in hits),
    }


def shape_coverage(tickets,n):
    out={k:0 for k in MOTIFS}
    for t in tickets[:n]:
        f=motif_flags(t)
        for k,v in f.items(): out[k]+=v
    return out


def evaluate(game,draws,indices,pop_probs,label):
    rows=[]
    shape_rows=[]
    for i in indices:
        if i>=len(draws) or len(draws[i+1:])<MIN_HISTORY:
            continue
        actual=draws[i]
        hist=draws[i+1:]
        base,pool=production_sequence(game,hist)
        cal=reorder_shape_aware(base,pool,pop_probs,"calibrated",0.30)
        div=reorder_shape_aware(base,pool,pop_probs,"diverse",0.30)
        pool_hits=len(set(pool)&set(actual))
        for n in PREFIXES[game]:
            for kind,tickets in [("baseline",base),("calibrated",cal),("diverse",div)]:
                s=score_prefix(tickets,actual,n)
                rows.append({"target":i,"size":n,"kind":kind,"pool_hits":pool_hits,**s})
                cov=shape_coverage(tickets,n)
                shape_rows.append({"target":i,"size":n,"kind":kind,**cov})
    df=pd.DataFrame(rows)
    sf=pd.DataFrame(shape_rows)
    out={"label":label,"prefixes":{}}
    for n in PREFIXES[game]:
        sub=df[df["size"]==n]
        ssh=sf[sf["size"]==n]
        block={}
        for kind in ("baseline","calibrated","diverse"):
            g=sub[sub.kind==kind]
            h=ssh[ssh.kind==kind]
            block[kind]={
                "draws":int(len(g)),
                "mean_best":float(g.best.mean()),
                "p3plus":float((g.best>=3).mean()),
                "p4plus":float((g.best>=4).mean()),
                "p5plus":float((g.best>=5).mean()),
                "mean_n3":float(g.n3.mean()),
                "mean_n4":float(g.n4.mean()),
                "motif_mean_counts":{k:float(h[k].mean()) for k in MOTIFS},
                "motif_mae_vs_target":float(np.mean([
                    abs(float(h[k].mean())-n*pop_probs[k]) for k in MOTIFS
                ])),
            }
        for kind in ("calibrated","diverse"):
            a=sub[sub.kind==kind].set_index("target")
            b=sub[sub.kind=="baseline"].set_index("target")
            common=a.index.intersection(b.index)
            d=a.loc[common,"best"]-b.loc[common,"best"]
            block[kind+"_vs_baseline"]={
                "wins":int((d>0).sum()),"ties":int((d==0).sum()),"losses":int((d<0).sum()),
                "mean_best_delta":float(d.mean()),
                "p3plus_delta_pp":100.0*(block[kind]["p3plus"]-block["baseline"]["p3plus"]),
                "p4plus_delta_pp":100.0*(block[kind]["p4plus"]-block["baseline"]["p4plus"]),
                "p5plus_delta_pp":100.0*(block[kind]["p5plus"]-block["baseline"]["p5plus"]),
                "motif_mae_delta":block[kind]["motif_mae_vs_target"]-block["baseline"]["motif_mae_vs_target"],
            }
        out["prefixes"][str(n)]=block

    # Conditional conversion when the selector actually supplied 4+ winning numbers.
    cond={}
    for ph in (4,5,6):
        cond[str(ph)]={}
        for n in PREFIXES[game]:
            sub=df[(df["size"]==n)&(df.pool_hits>=ph)]
            if sub.empty:
                continue
            cond[str(ph)][str(n)]={}
            for kind in ("baseline","calibrated","diverse"):
                g=sub[sub.kind==kind]
                cond[str(ph)][str(n)][kind]={
                    "draws":int(len(g)),
                    "mean_best":float(g.best.mean()),
                    "p4plus":float((g.best>=4).mean()),
                    "p5plus":float((g.best>=5).mean()),
                }
    out["conditional_pool_hits_ge"]=cond
    return out


def to_draws(df):
    cols=[f"n{i}" for i in range(1,7)]
    return [list(map(int,r)) for r in df[cols].to_numpy().tolist()]


def main():
    probs={"6/49":population_probs(49,SEED),"6/42":population_probs(42,SEED+1000)}
    result={
        "method":{
            "design":"Outcome-blind reordering of the exact same production ticket set; no new numbers and no extra spend.",
            "shape_alpha":0.30,
            "population_sample_n":SAMPLE_N,
            "motifs":list(MOTIFS),
            "latest_validation_draws":LATEST_N,
            "archive_validation_cap":ARCHIVE_N,
            "note":"Population motif targets are estimated from deterministic uniform-combination Monte Carlo, independent of historical draw outcomes."
        },
        "population_probs":probs,
        "games":{}
    }
    for game in ("6/49","6/42"):
        raw=load_draws_df(game)
        draws=to_draws(raw)
        latest=evaluate(game,draws,range(0,min(LATEST_N,len(draws)-MIN_HISTORY)),probs[game],"2026 latest holdout")
        adf,adraws=load_research_archive(game)
        lim=min(ARCHIVE_N,len(adraws)-MIN_HISTORY)
        archive=evaluate(game,adraws,range(0,lim),probs[game],"2020-2023 archive")
        result["games"][game]={"latest":latest,"archive":archive}

    print("SHAPE_AWARE_BEGIN")
    print(json.dumps(result,indent=2))
    print("SHAPE_AWARE_END")


if __name__=="__main__":
    main()
