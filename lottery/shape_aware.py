from __future__ import annotations

import itertools
from collections import Counter

import numpy as np

# Frozen from the outcome-blind 120k-combination Monte Carlo used by
# scripts/research_shape_aware_conversion.py on 2026-10-09.
POPULATION_PROBS={
    "6/49":{
        "adjacent":0.4943666666666667,
        "gap2":0.44931666666666664,
        "three_consecutive":0.048258333333333334,
        "three_step2":0.04438333333333333,
        "parity_extreme":0.18958333333333333,
        "five_plus_even":0.08641666666666667,
        "five_plus_low25":0.103625,
        "five_plus_high20":0.23579166666666668,
        "all_low25":0.012841666666666666,
        "all_high20":0.042491666666666664,
        "same_last_pair":0.7948166666666666,
        "same_last_triple":0.092875,
        "tight_span":0.03605,
    },
    "6/42":{
        "adjacent":0.55565,
        "gap2":0.501875,
        "three_consecutive":0.06464166666666667,
        "three_step2":0.060191666666666664,
        "parity_extreme":0.18350833333333333,
        "five_plus_even":0.09281666666666667,
        "five_plus_low25":0.205725,
        "five_plus_high20":0.141525,
        "all_low25":0.033683333333333336,
        "all_high20":0.019075,
        "same_last_pair":0.784,
        "same_last_triple":0.08319166666666666,
        "tight_span":0.07236666666666666,
    },
}
MOTIFS=tuple(POPULATION_PROBS["6/49"].keys())
SHAPE_ALPHA=0.30


def motif_flags(ticket):
    t=tuple(sorted(map(int,ticket)))
    s=set(t)
    gaps=[b-a for a,b in zip(t,t[1:])]
    ev=sum(n%2==0 for n in t)
    low25=sum(n<=25 for n in t)
    high20=sum(n>=20 for n in t)
    last=Counter(n%10 for n in t)
    return {
        "adjacent":int(1 in gaps),
        "gap2":int(2 in gaps),
        "three_consecutive":int(any(a+1 in s and a+2 in s for a in t)),
        "three_step2":int(any(a+2 in s and a+4 in s for a in t)),
        "parity_extreme":int(ev<=1 or ev>=5),
        "five_plus_even":int(ev>=5),
        "five_plus_low25":int(low25>=5),
        "five_plus_high20":int(high20>=5),
        "all_low25":int(low25==6),
        "all_high20":int(high20==6),
        "same_last_pair":int(max(last.values())>=2),
        "same_last_triple":int(max(last.values())>=3),
        "tight_span":int(t[-1]-t[0]<=20),
    }


def _z(v):
    a=np.asarray(v,float)
    sd=a.std()
    return np.zeros_like(a) if sd<1e-12 else (a-a.mean())/sd


def _structural_features(ticket,selected,exp,pool,c4,c3,c2):
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


def _shape_gain(ticket,selected_counts,pop_probs,next_n,diverse=True):
    flags=motif_flags(ticket)
    before=0.0
    after=0.0
    for k,p in pop_probs.items():
        var=max(p*(1-p),0.03)
        target_before=(next_n-1)*p
        target_after=next_n*p
        c=selected_counts[k]
        before += ((c-target_before)**2)/var
        after += ((c+flags[k]-target_after)**2)/var
    gain=before-after
    if diverse:
        for k,p in pop_probs.items():
            if 0.02<=p<=0.35 and flags[k] and selected_counts[k]==0:
                gain += min(2.0,0.12/max(p,0.02)**0.5)
    return gain


def reorder_shape_diverse(tickets,pool,game,alpha=SHAPE_ALPHA):
    """Outcome-blind reordering of an existing production ticket set.

    No ticket contents, pool numbers, or spend are changed. The order is chosen
    to balance structural coverage with draw-shape coverage, so low-budget
    prefixes sample a wider set of empirically/combinatorially plausible motifs.
    """
    pop_probs=POPULATION_PROBS[game]
    remaining=[tuple(sorted(map(int,t))) for t in tickets]
    selected=[]
    exp=Counter()
    shape_counts=Counter()
    c4=Counter();c3=Counter();c2=Counter()

    while remaining:
        structs=[_structural_features(t,selected,exp,pool,c4,c3,c2) for t in remaining]
        cols=list(zip(*structs))
        sz=[_z(c) for c in cols]
        struct_score=2.0*sz[0]+1.0*sz[1]+0.35*sz[2]+0.70*sz[3]+0.75*sz[4]
        sg=np.array([_shape_gain(t,shape_counts,pop_probs,len(selected)+1,True) for t in remaining],float)
        total=(1-float(alpha))*_z(struct_score)+float(alpha)*_z(sg)
        best=max(
            range(len(remaining)),
            key=lambda i:(float(total[i]),float(struct_score[i]),float(sg[i]),tuple(-x for x in remaining[i]))
        )
        t=remaining.pop(best)
        selected.append(t)
        for n in t: exp[n]+=1
        for x in itertools.combinations(t,4): c4[x]+=1
        for x in itertools.combinations(t,3): c3[x]+=1
        for x in itertools.combinations(t,2): c2[x]+=1
        f=motif_flags(t)
        for k,v in f.items(): shape_counts[k]+=v

    return selected
