from __future__ import annotations

import itertools
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np

from lottery.data import load_draws_df
from lottery.models import current_pool_649
from lottery.wheels import build_broad_six,extend_sequence

ROOT=Path(__file__).resolve().parents[1]
SIZES=(6,11,22,33,55)
N_SEEDS=128
PROPOSALS=160
BASE_SEED=20260927


def combo_counter_add(counter,line,r):
    for x in itertools.combinations(line,r):
        counter[x]+=1


def structural_sequence(seed,fixed_prefix=None):
    rng=np.random.default_rng(seed)
    universe=np.arange(1,23,dtype=int)
    selected=[tuple(map(int,t)) for t in (fixed_prefix or [])]
    selected_set=set(selected)
    c4,c3,c2=Counter(),Counter(),Counter()
    exp=Counter()
    for t in selected:
        combo_counter_add(c4,t,4)
        combo_counter_add(c3,t,3)
        combo_counter_add(c2,t,2)
        for n in t: exp[n]+=1

    while len(selected)<max(SIZES):
        step=len(selected)
        target=6.0*(step+1)/22.0
        proposals=set()
        tries=0
        while len(proposals)<PROPOSALS and tries<PROPOSALS*30:
            tries+=1
            t=tuple(sorted(map(int,rng.choice(universe,6,replace=False))))
            if t not in selected_set:
                proposals.add(t)
        best=None
        bestkey=None
        for t in proposals:
            q4=list(itertools.combinations(t,4))
            q3=list(itertools.combinations(t,3))
            q2=list(itertools.combinations(t,2))
            dup4=sum(c4[x] for x in q4)
            dup3=sum(c3[x] for x in q3)
            dup2=sum(c2[x] for x in q2)
            new4=sum(c4[x]==0 for x in q4)
            new3=sum(c3[x]==0 for x in q3)
            # Penalize high pairwise ticket intersection directly. 5+ coverage
            # neighborhoods only overlap if two lines share >=4 positions.
            pair4=pair5=0
            max_inter=0
            for s in selected:
                inter=len(set(t)&set(s))
                max_inter=max(max_inter,inter)
                if inter>=4: pair4+=1
                if inter>=5: pair5+=1
            balance_delta=sum((exp[n]+1-target)**2-(exp[n]-target)**2 for n in t)
            # Lexicographic: protect 5+ neighborhoods, then broaden 4+ neighborhoods,
            # then 3-subset/pair diversity and exposure balance.
            key=(-pair5,-pair4,new4,-dup4,new3,-dup3,-dup2,-balance_delta,-max_inter)
            if bestkey is None or key>bestkey:
                bestkey=key;best=t
        if best is None:
            raise RuntimeError("structural search failed")
        selected.append(best);selected_set.add(best)
        combo_counter_add(c4,best,4)
        combo_counter_add(c3,best,3)
        combo_counter_add(c2,best,2)
        for n in best: exp[n]+=1
    return selected


def baseline_sequence():
    # Freeze today's pre-draw production state and convert actual numbers back to
    # K22 positions. Full-space evaluation is permutation-invariant.
    df=load_draws_df("6/49")
    draws=[list(map(int,row)) for row in df[[f"n{i}" for i in range(1,7)]].to_numpy().tolist()]
    pool,adds,diag,score=current_pool_649(draws,22)
    base=build_broad_six(pool,score,649)
    tickets=extend_sequence(base,pool,score,55,20260917+490000)
    ranked=sorted([int(n) for n in pool],key=lambda n:(-float(score.loc[n]),n))
    pos={int(n):i+1 for i,n in enumerate(ranked)}
    return [tuple(sorted(pos[int(n)] for n in t)) for t in tickets],ranked


TARGETS=list(itertools.combinations(range(1,23),6))
TARGET_MATRIX=np.zeros((len(TARGETS),22),dtype=np.uint8)
for i,t in enumerate(TARGETS):
    TARGET_MATRIX[i,np.array(t)-1]=1


def exact_prefix_metrics(seq):
    cols=np.zeros((len(TARGETS),len(seq)),dtype=np.uint8)
    for j,t in enumerate(seq):
        v=np.zeros(22,dtype=np.uint8);v[np.array(t)-1]=1
        cols[:,j]=TARGET_MATRIX@v
    running=np.maximum.accumulate(cols,axis=1)
    out={}
    for n in SIZES:
        best=running[:,n-1]
        hist={str(h):int((best==h).sum()) for h in range(7)}
        out[str(n)]={
            "p3plus":float((best>=3).mean()),
            "p4plus":float((best>=4).mean()),
            "p5plus":float((best>=5).mean()),
            "p6":float((best>=6).mean()),
            "count4plus":int((best>=4).sum()),
            "count5plus":int((best>=5).sum()),
            "count6":int((best>=6).sum()),
            "mean_best":float(best.mean()),
            "hist":hist,
        }
    return out


def subset_stats(seq,n):
    lines=seq[:n]
    c4=Counter(x for t in lines for x in itertools.combinations(t,4))
    c5=Counter(x for t in lines for x in itertools.combinations(t,5))
    exp=Counter(x for t in lines for x in t)
    ev=np.array([exp[i] for i in range(1,23)],dtype=float)
    return {
        "unique_4sets":len(c4),
        "duplicate_4set_incidence":int(sum(max(v-1,0) for v in c4.values())),
        "unique_5sets":len(c5),
        "duplicate_5set_incidence":int(sum(max(v-1,0) for v in c5.values())),
        "exposure_min":int(ev.min()),
        "exposure_max":int(ev.max()),
        "exposure_cv":float(ev.std()/ev.mean()),
    }


def utility(metrics):
    # Full-space, multi-prefix utility. 5+ gets more weight because it is rarer
    # and financially more consequential, while 4+ and 3+ prevent concentration.
    u=0.0
    for n in SIZES:
        m=metrics[str(n)]
        u+=12.0*m["p5plus"]+2.0*m["p4plus"]+0.15*m["p3plus"]+0.05*m["mean_best"]
    return u


def dominates(a,b):
    # Require no regression at any production prefix in 4+ or 5+ coverage.
    ge=True;strict=False
    for n in SIZES:
        aa=a[str(n)];bb=b[str(n)]
        if aa["p4plus"]+1e-15<bb["p4plus"] or aa["p5plus"]+1e-15<bb["p5plus"]:
            ge=False;break
        if aa["p4plus"]>bb["p4plus"]+1e-15 or aa["p5plus"]>bb["p5plus"]+1e-15:
            strict=True
    return ge and strict


def score_draw76(seq,pool):
    winners={8,9,17,27,37,48}
    pos={n:i+1 for i,n in enumerate(pool)}
    winning_positions={pos[n] for n in winners}
    out={}
    for n in SIZES:
        hits=[len(set(t)&winning_positions) for t in seq[:n]]
        out[str(n)]={
            "best":max(hits),
            "lines_3plus":sum(h>=3 for h in hits),
            "lines_4plus":sum(h>=4 for h in hits),
            "lines_5plus":sum(h>=5 for h in hits),
            "lines_6":sum(h==6 for h in hits),
        }
    return out


def main():
    baseline,pool=baseline_sequence()
    bm=exact_prefix_metrics(baseline)
    candidates=[]
    for i in range(N_SEEDS):
        seed=BASE_SEED+i
        seq=structural_sequence(seed,fixed_prefix=baseline[:6])
        met=exact_prefix_metrics(seq)
        candidates.append((utility(met),seed,seq,met))
    candidates.sort(key=lambda x:x[0],reverse=True)

    nondominated=[x for x in candidates if dominates(x[3],bm)]
    chosen=nondominated[0] if nondominated else candidates[0]
    u,seed,seq,met=chosen

    result={
        "universe":{"k":22,"winning_sextets":math.comb(22,6),"sizes":list(SIZES)},
        "search":{"seeds":N_SEEDS,"proposals_per_step":PROPOSALS,"chosen_seed":seed,"chosen_utility":u,"dominates_baseline_all_prefixes":dominates(met,bm),"dominating_candidates":len(nondominated)},
        "baseline":{"metrics":bm,"subset_stats":{str(n):subset_stats(baseline,n) for n in SIZES}},
        "candidate":{"metrics":met,"subset_stats":{str(n):subset_stats(seq,n) for n in SIZES},"position_lines":[list(t) for t in seq]},
        "delta":{str(n):{
            "p3plus_pp":100*(met[str(n)]["p3plus"]-bm[str(n)]["p3plus"]),
            "p4plus_pp":100*(met[str(n)]["p4plus"]-bm[str(n)]["p4plus"]),
            "p5plus_pp":100*(met[str(n)]["p5plus"]-bm[str(n)]["p5plus"]),
            "mean_best":met[str(n)]["mean_best"]-bm[str(n)]["mean_best"],
        } for n in SIZES},
        # Draw 76 is evaluated only after candidate selection.
        "draw76_post_selection_check":{
            "baseline":score_draw76(baseline,pool),
            "candidate":score_draw76(seq,pool),
            "winning_numbers":[8,9,17,27,37,48],
            "pool":pool,
        },
        "note":"Candidate generation and selection are outcome-blind. The current production first 6 lines are held fixed; only lines 7-55 are redesigned. Exact metrics enumerate all C(22,6)=74,613 possible winning sextets. Draw 76 is scored only after the candidate is selected.",
    }
    print("K22_CONVERSION_V4_BEGIN")
    print(json.dumps(result,indent=2))
    print("K22_CONVERSION_V4_END")


if __name__=="__main__":
    main()
