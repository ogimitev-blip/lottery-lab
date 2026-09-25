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
