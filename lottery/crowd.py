from collections import Counter
import math
from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st

ROOT=Path(__file__).resolve().parents[1]
CROWD_FILES={"6/42":"crowd_history_642.csv","6/49":"crowd_history_649.csv"}

@st.cache_data
def load_crowd_history(game):
    p=ROOT/"data"/CROWD_FILES[game]
    if not p.exists() or p.stat().st_size==0:
        return pd.DataFrame()
    df=pd.read_csv(p)
    return df

def latest_crowd_snapshot(game):
    df=load_crowd_history(game)
    if df.empty:
        return df
    # Draw numbers repeat across years, so date is the primary recency key.
    d=pd.to_datetime(df["snapshot_date"],errors="coerce")
    if d.notna().any():
        latest=d.max()
        return df[d.eq(latest)].copy().sort_values("number")
    return df[df["snapshot_draw"].eq(df["snapshot_draw"].max())].copy().sort_values("number")

def ticket_crowd_metrics(ticket,crowd):
    if crowd is None or crowd.empty:
        return {"crowd_index":np.nan,"birthday_n":sum(int(n)<=31 for n in ticket),"consecutive_pairs":0,"same_last_digit_pairs":0}
    counts=dict(zip(crowd.number.astype(int),crowd.played_vs_mean.astype(float)))
    rel=[max(float(counts.get(int(n),1.0)),1e-9) for n in ticket]
    # Geometric mean, scaled so 100 = an average-popularity number set.
    idx=100.0*math.exp(sum(math.log(x) for x in rel)/len(rel))
    s=sorted(map(int,ticket))
    consecutive=sum(1 for a,b in zip(s,s[1:]) if b-a==1)
    endings=Counter(n%10 for n in s)
    same_end=sum(v*(v-1)//2 for v in endings.values() if v>1)
    return {
        "crowd_index":idx,
        "birthday_n":sum(n<=31 for n in s),
        "consecutive_pairs":consecutive,
        "same_last_digit_pairs":same_end,
    }

def score_ticket_frame(tickets,crowd):
    rows=[]
    for i,t in enumerate(tickets,1):
        m=ticket_crowd_metrics(t,crowd)
        rows.append({"line":i,**m})
    out=pd.DataFrame(rows)
    if len(out):
        out["crowd_rank"]=out["crowd_index"].rank(method="min",ascending=True).astype("Int64")
    return out

def anti_crowd_remap(pool,tickets,crowd):
    """Preserve the selected pool and exact ticket incidence structure, but
    assign the least-played selected numbers to the most-exposed positions.
    This changes conversion mapping only; it does not change K, L, or coverage
    properties that are invariant to relabeling."""
    if crowd is None or crowd.empty:
        return list(tickets),{},None
    pset=list(map(int,pool))
    exposure=Counter(n for t in tickets for n in map(int,t))
    pop=dict(zip(crowd.number.astype(int),crowd.played_count.astype(float)))

    # Existing labels ordered by how often the wheel uses them.
    old_labels=sorted(pset,key=lambda n:(-exposure.get(n,0),pset.index(n)))
    # Selected numbers ordered from least to most popular among players.
    new_numbers=sorted(pset,key=lambda n:(pop.get(n,float("inf")),n))
    mapping={old:new for old,new in zip(old_labels,new_numbers)}
    remapped=[tuple(sorted(mapping.get(int(n),int(n)) for n in t)) for t in tickets]
    if len(set(remapped))!=len(remapped):
        raise RuntimeError("Anti-crowd relabeling created duplicate tickets")
    meta=pd.DataFrame({
        "original_number":old_labels,
        "ticket_exposure":[exposure.get(n,0) for n in old_labels],
        "anti_crowd_number":[mapping[n] for n in old_labels],
        "played_count":[pop.get(mapping[n],np.nan) for n in old_labels],
    })
    return remapped,mapping,meta

def snapshot_summary(crowd):
    if crowd is None or crowd.empty:
        return {}
    first=crowd.iloc[0]
    lo=crowd[crowd.number<=31].played_count.mean()
    hi=crowd[crowd.number>31].played_count.mean() if (crowd.number>31).any() else np.nan
    return {
        "draw":int(first.snapshot_draw),
        "date":str(first.snapshot_date),
        "coverage_pct":float(first.unique_coverage_pct),
        "total_combinations":int(first.total_combinations),
        "mean_played":float(crowd.played_count.mean()),
        "birthday_ratio":float(lo/hi) if pd.notna(hi) and hi else np.nan,
    }


def constrained_anti_crowd_remap(pool,tickets,crowd,diagnostics,strength=0.10):
    """Constrained anti-crowd relabeling.

    Strength is the maximum allowed model-score gap, expressed as a fraction
    of the selected pool's score range, for assigning a number to a ticket
    position. A strength of 0.10 permits only near-score substitutions; 0.30
    gives the crowd layer more freedom. The selected pool, line count, and
    incidence structure remain unchanged.
    """
    strength=float(strength)
    if strength<=0 or crowd is None or crowd.empty:
        return list(tickets),{int(n):int(n) for n in pool},None

    pset=[int(n) for n in pool]
    exposure=Counter(int(n) for t in tickets for n in t)
    pop=dict(zip(crowd.number.astype(int),crowd.played_count.astype(float)))
    rel=dict(zip(crowd.number.astype(int),crowd.played_vs_mean.astype(float)))
    score_df=diagnostics.set_index("number")
    score={n:float(score_df.loc[n,"score"]) for n in pset}

    vals=np.array([score[n] for n in pset],dtype=float)
    score_range=float(vals.max()-vals.min())
    threshold=max(0.0,strength*score_range)
    mapping={n:n for n in pset}

    def lp(n):
        return math.log(max(float(pop.get(int(n),1.0)),1e-12))

    def crowd_obj(mp):
        return sum(exposure.get(label,0)*lp(num) for label,num in mp.items())

    def model_utility(mp):
        return sum(exposure.get(label,0)*score[num] for label,num in mp.items())

    base_model=model_utility(mapping)
    swaps=0
    while True:
        best=None
        best_key=None
        labels=list(pset)
        for ia in range(len(labels)):
            a=labels[ia]; na=mapping[a]
            for ib in range(ia+1,len(labels)):
                b=labels[ib]; nb=mapping[b]
                # Every assigned number must remain close to the model score of
                # the position it is replacing. This prevents crowd drift.
                if abs(score[nb]-score[a])>threshold+1e-12:
                    continue
                if abs(score[na]-score[b])>threshold+1e-12:
                    continue
                before=exposure.get(a,0)*lp(na)+exposure.get(b,0)*lp(nb)
                after=exposure.get(a,0)*lp(nb)+exposure.get(b,0)*lp(na)
                delta=after-before
                if delta>=-1e-12:
                    continue
                old_u=exposure.get(a,0)*score[na]+exposure.get(b,0)*score[nb]
                new_u=exposure.get(a,0)*score[nb]+exposure.get(b,0)*score[na]
                utility_loss=old_u-new_u
                key=(delta,utility_loss,a,b)
                if best_key is None or key<best_key:
                    best_key=key; best=(a,b)
        if best is None:
            break
        a,b=best
        mapping[a],mapping[b]=mapping[b],mapping[a]
        swaps+=1
        if swaps>1000:
            raise RuntimeError("Constrained anti-crowd optimizer did not converge")

    remapped=[tuple(sorted(mapping.get(int(n),int(n)) for n in t)) for t in tickets]
    if len(set(remapped))!=len(remapped):
        raise RuntimeError("Constrained anti-crowd relabeling created duplicate tickets")

    meta=pd.DataFrame({
        "original_position":pset,
        "ticket_exposure":[exposure.get(n,0) for n in pset],
        "original_number":pset,
        "assigned_number":[mapping[n] for n in pset],
        "position_model_score":[score[n] for n in pset],
        "assigned_model_score":[score[mapping[n]] for n in pset],
        "score_gap":[abs(score[mapping[n]]-score[n]) for n in pset],
        "played_count":[pop.get(mapping[n],np.nan) for n in pset],
        "played_vs_mean":[rel.get(mapping[n],np.nan) for n in pset],
    })
    meta.attrs["strength"]=strength
    meta.attrs["score_threshold"]=threshold
    meta.attrs["swaps"]=swaps
    meta.attrs["base_model_utility"]=base_model
    meta.attrs["final_model_utility"]=model_utility(mapping)
    meta.attrs["base_crowd_objective"]=crowd_obj({n:n for n in pset})
    meta.attrs["final_crowd_objective"]=crowd_obj(mapping)
    return remapped,mapping,meta
