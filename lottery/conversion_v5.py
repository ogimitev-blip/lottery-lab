from __future__ import annotations

import itertools
import json
from collections import Counter
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
CAL_PATH=ROOT/"systems"/"k22_conversion_v5_rank_weights.json"
PROPOSALS=64
BASE_SEED=20260928
ANCHOR_DRAW=76

def _weights():
    return np.asarray(json.loads(CAL_PATH.read_text())["weights"],dtype=float)

def _subset_values(weights,r):
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

def _ranked_pool(pool,diagnostics):
    rank_map={
        int(r.number):int(r["rank"])
        for _,r in diagnostics[diagnostics.in_pool].iterrows()
    }
    ranked=sorted([int(n) for n in pool],key=lambda n:(rank_map[int(n)],int(n)))
    if len(ranked)!=22:
        raise RuntimeError("K22 v5 requires a 22-number pool")
    return ranked

def _seed_for_draw(target_draw_no):
    # Historical validation anchor: draw 76 used BASE_SEED, older draws
    # incremented by one. Extrapolate prospectively without using outcomes.
    return int(BASE_SEED + (ANCHOR_DRAW-int(target_draw_no)))

def build_rank_aware_v5(base_six,pool,diagnostics,max_lines,target_draw_no):
    """Extend the existing production six-line K22 wheel using frozen rank calibration.

    The first six tickets are passed through unchanged. New lines are chosen in
    score-rank position space. Pairwise line intersections are capped at three,
    preserving maximal uniform 5+ neighborhoods while weighted 4-set novelty
    favors historically stronger K22 rank bands.
    """
    if int(max_lines)<6:
        raise ValueError("v5 requires at least six lines")
    ranked=_ranked_pool(pool,diagnostics)
    pos={int(n):i+1 for i,n in enumerate(ranked)}
    selected=[tuple(sorted(pos[int(n)] for n in t)) for t in base_six]
    if len(selected)!=6:
        raise ValueError("v5 requires exactly six production base tickets")
    selected_set=set(selected)

    weights=_weights()
    q4val=_subset_values(weights,4)
    q5val=_subset_values(weights,5)
    c4=Counter(x for t in selected for x in itertools.combinations(t,4))
    c3=Counter(x for t in selected for x in itertools.combinations(t,3))
    c2=Counter(x for t in selected for x in itertools.combinations(t,2))
    exp=Counter(x for t in selected for x in t)
    rng=np.random.default_rng(_seed_for_draw(target_draw_no))

    while len(selected)<int(max_lines):
        proposals=set()
        tries=0
        exp_arr=np.array([exp[i] for i in range(1,23)],dtype=float)
        sample_w=weights/np.sqrt(1.0+exp_arr)
        sample_w/=sample_w.sum()
        while len(proposals)<PROPOSALS and tries<PROPOSALS*100:
            tries+=1
            t=tuple(sorted(map(int,rng.choice(np.arange(1,23),6,replace=False,p=sample_w))))
            if t in selected_set:
                continue
            if any(len(set(t)&set(s))>3 for s in selected):
                continue
            proposals.add(t)
        if not proposals:
            raise RuntimeError("K22 v5 extension candidate exhaustion")

        target=weights/weights.sum()*6.0*(len(selected)+1)
        best=None
        bestkey=None
        for t in proposals:
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
            key=(weighted_new4,weighted5,new4,-dup4,-dup3,-dup2,-balance_delta)
            if bestkey is None or key>bestkey:
                bestkey=key
                best=t

        selected.append(best)
        selected_set.add(best)
        for x in itertools.combinations(best,4): c4[x]+=1
        for x in itertools.combinations(best,3): c3[x]+=1
        for x in itertools.combinations(best,2): c2[x]+=1
        for n in best: exp[n]+=1

    return [tuple(ranked[p-1] for p in t) for t in selected]
