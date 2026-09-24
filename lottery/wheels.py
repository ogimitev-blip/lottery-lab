import itertools
from collections import Counter
import numpy as np
import pandas as pd

BASE_PRICES={"6/42":.80,"6/49":.90}
SPECIAL_649_2026={1,4,8,12,16,18,23,26,28,35,38,40,49,50,55,64,70,75,81,84,89,96,101,103}

def line_price(game,draw_no=None,year=2026):
    if game=="6/49" and year==2026 and draw_no in SPECIAL_649_2026:return 1.00
    return BASE_PRICES[game]

def map_positions(pool,position_lines):
    return [tuple(pool[p-1] for p in line) for line in position_lines]

def ticket_frame(tickets):
    return pd.DataFrame([dict(line=i+1,**{f"n{j+1}":n for j,n in enumerate(t)}) for i,t in enumerate(tickets)])

def cost(game,n_lines,draw_no=None,year=2026): return line_price(game,draw_no,year)*n_lines

def build_broad_four(pool,score):
    """Four-line K22 conversion: cover all 22 selected numbers once, then
    repeat the two highest-scored pool numbers. Assignment is deterministic
    and minimizes repeated within-ticket pair exposure while balancing score."""
    if len(pool)>24:
        raise ValueError("Four tickets have only 24 slots; broad-four requires K<=24.")
    ranked=sorted([int(n) for n in pool],key=lambda n:(-float(score.loc[n]),n))
    repeat_n=max(0,24-len(ranked))
    repeated=ranked[:repeat_n]
    items=ranked+repeated
    items=sorted(items,key=lambda n:(-float(score.loc[n]),n))

    tickets=[[] for _ in range(4)]
    score_sums=[0.0]*4

    def pair_seen_elsewhere(n,o,current_i):
        pair={int(n),int(o)}
        return sum(1 for j,t in enumerate(tickets) if j!=current_i and pair.issubset(set(t)))

    for n in items:
        candidates=[]
        for i,t in enumerate(tickets):
            if len(t)>=6 or n in t:
                continue
            pair_penalty=sum(pair_seen_elsewhere(n,o,i) for o in t)
            candidates.append((pair_penalty,len(t),score_sums[i],i))
        if not candidates:
            raise RuntimeError("broad-four construction failed")
        _,_,_,i=min(candidates)
        tickets[i].append(int(n))
        score_sums[i]+=float(score.loc[n])

    out=[tuple(sorted(t)) for t in tickets]
    if any(len(t)!=6 or len(set(t))!=6 for t in out):
        raise RuntimeError("broad-four produced an invalid ticket")
    return out

def build_broad_six(pool,score,seed=649):
    k=len(pool); ranked=sorted(pool,key=lambda n:float(score.loc[n]),reverse=True)
    counts={int(n):1 for n in pool}
    for n in ranked[:max(0,36-k)]: counts[int(n)]+=1
    rng=np.random.default_rng(seed); best=None; best_obj=-1e99
    for _ in range(250):
        tickets=[[] for _ in range(6)]; pair_counts=Counter(); order=[]
        for n in ranked: order.extend([n]*counts[n])
        for i in range(0,len(order),8):
            block=order[i:i+8]; rng.shuffle(block); order[i:i+8]=block
        feasible=True
        for n in order:
            opts=[]
            for ti in range(6):
                if len(tickets[ti])>=6 or n in tickets[ti]: continue
                dup=sum(pair_counts[tuple(sorted((int(n),int(o))))] for o in tickets[ti])
                opts.append((-8*len(tickets[ti])-2.5*dup+rng.normal(0,.2),ti))
            if not opts: feasible=False; break
            ti=max(opts)[1]
            for o in tickets[ti]: pair_counts[tuple(sorted((int(n),int(o))))]+=1
            tickets[ti].append(int(n))
        if not feasible or any(len(t)!=6 for t in tickets): continue
        tt=[tuple(sorted(t)) for t in tickets]
        c4=Counter(x for t in tt for x in itertools.combinations(t,4));c3=Counter(x for t in tt for x in itertools.combinations(t,3));c2=Counter(x for t in tt for x in itertools.combinations(t,2))
        obj=-20*sum(max(v-1,0) for v in c4.values())-2*sum(max(v-1,0) for v in c3.values())-.35*sum(max(v-1,0) for v in c2.values())
        if obj>best_obj: best_obj=obj;best=tt
    if best is None: raise RuntimeError("broad-six construction failed")
    return best

def extend_sequence(base_tickets,pool,score,max_lines,seed):
    selected=[tuple(sorted(map(int,t))) for t in base_tickets];selected_set=set(selected)
    if max_lines<=len(selected):return selected[:max_lines]
    c4=Counter(x for t in selected for x in itertools.combinations(t,4));c3=Counter(x for t in selected for x in itertools.combinations(t,3));c2=Counter(x for t in selected for x in itertools.combinations(t,2));exp=Counter(x for t in selected for x in t)
    rng=np.random.default_rng(seed);parr=np.array(list(map(int,pool)),int);vals=np.array([float(score.loc[int(n)]) for n in parr]);sd=vals.std();sz=(vals-vals.mean())/(sd if sd>1e-12 else 1)
    while len(selected)<max_lines:
        exp_arr=np.array([exp[int(n)] for n in parr],float);weights=np.exp(.12*np.clip(sz,-3,3))/np.sqrt(1+exp_arr);weights/=weights.sum()
        props=set();tries=0
        while len(props)<18 and tries<720:
            tries+=1;t=tuple(sorted(map(int,rng.choice(parr,6,replace=False,p=weights))))
            if t not in selected_set:props.add(t)
        target=6*(len(selected)+1)/len(pool);best=None;keybest=None
        for t in props:
            key=(-sum(c4[x] for x in itertools.combinations(t,4)),-sum(c3[x] for x in itertools.combinations(t,3)),-sum(c2[x] for x in itertools.combinations(t,2)),-sum((exp[n]+1-target)**2 for n in t),sum(float(score.loc[n]) for n in t))
            if keybest is None or key>keybest:keybest=key;best=t
        if best is None:raise RuntimeError("wheel extension failed")
        selected.append(best);selected_set.add(best)
        for x in itertools.combinations(best,4):c4[x]+=1
        for x in itertools.combinations(best,3):c3[x]+=1
        for x in itertools.combinations(best,2):c2[x]+=1
        for x in best:exp[x]+=1
    return selected
