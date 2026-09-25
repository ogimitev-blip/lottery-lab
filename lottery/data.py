from pathlib import Path
from datetime import date,datetime,timedelta
import json
import pandas as pd
import streamlit as st

ROOT=Path(__file__).resolve().parents[1]
GAME_FILES={"6/42":"draws_642.csv","6/49":"draws_649.csv"}
META_FILES={"6/42":"results_meta_642.csv","6/49":"results_meta_649.csv"}

@st.cache_data
def load_draws_df(game):
    df=pd.read_csv(ROOT/"data"/GAME_FILES[game],dtype={"date":"string"})
    number_cols=[f"n{i}" for i in range(1,7)]
    keep=[c for c in ["draw_no","date",*number_cols] if c in df.columns]
    return df[keep].copy()

def get_draws(game):
    df=load_draws_df(game)
    base=[list(map(int,row)) for row in df[[f"n{i}" for i in range(1,7)]].to_numpy().tolist()]
    extras=st.session_state.get(f"session_draws_{game}",[])
    return [list(map(int,x["numbers"])) for x in extras]+base

def get_draw_labels(game):
    df=load_draws_df(game)
    labels=[str(x) if "date" in df.columns and pd.notna(x) and str(x).strip() else None for x in (df["date"].tolist() if "date" in df.columns else [None]*len(df))]
    extras=st.session_state.get(f"session_draws_{game}",[])
    return [x.get("date") for x in extras]+labels

@st.cache_data
def load_sync_state():
    return json.loads((ROOT/"data"/"sync_state.json").read_text())

def _next_thu_or_sun(d):
    for i in range(1,8):
        x=d+timedelta(days=i)
        if x.weekday() in (3,6): return x
    return d+timedelta(days=4)

def latest_stored_info(game):
    df=load_draws_df(game)
    known=df.dropna(subset=["draw_no"]).copy() if "draw_no" in df.columns else pd.DataFrame()
    if len(known):
        known["draw_no"]=pd.to_numeric(known["draw_no"],errors="coerce")
        known=known.dropna(subset=["draw_no"]).sort_values("draw_no",ascending=False)
    if len(known):
        r=known.iloc[0]
        d=str(r["date"]) if "date" in known.columns and pd.notna(r["date"]) else None
        return {"draw_no":int(r["draw_no"]),"date":d}
    s=load_sync_state()[game]
    return {"draw_no":int(s["latest_draw_no"]),"date":s["latest_date"]}

def next_draw_info(game):
    latest=latest_stored_info(game)
    last=date.fromisoformat(latest["date"]) if latest.get("date") else date.today()
    nxt=_next_thu_or_sun(last)
    return {"draw_no":int(latest["draw_no"])+1,"date":nxt.isoformat()}

@st.cache_data
def load_results_meta(game):
    p=ROOT/"data"/META_FILES[game]
    return pd.read_csv(p) if p.exists() and p.stat().st_size else pd.DataFrame()

def validate_history(game):
    df=load_draws_df(game); maxn=42 if game=="6/42" else 49; cols=[f"n{i}" for i in range(1,7)]
    errors=[]; warnings=[]
    for idx,row in df.iterrows():
        try: vals=[int(row[c]) for c in cols]
        except Exception:
            errors.append(f"Row {idx+1}: non-integer or missing number"); continue
        if len(set(vals))!=6: errors.append(f"Row {idx+1}: numbers are not distinct")
        if min(vals)<1 or max(vals)>maxn: errors.append(f"Row {idx+1}: number outside 1–{maxn}")
    groups={}
    for idx,row in df.iterrows():
        try:
            key=tuple(sorted(int(row[c]) for c in cols))
        except Exception:
            continue
        groups.setdefault(key,[]).append(int(idx)+1)
    for key,rows in groups.items():
        if len(rows)>1:
            warnings.append(
                f"Repeated result {' '.join(map(str,key))} appears on stored row(s) "
                +", ".join(map(str,rows))
                +". Open Draw Database to review/correct it."
            )
    if "date" in df.columns:
        dates=pd.to_datetime(df.date,errors="coerce")
        known=dates.dropna()
        if len(known)>1 and not known.is_monotonic_decreasing: warnings.append("Known draw dates are not strictly newest-first.")
    return errors,warnings

@st.cache_data
def load_custom_wheel():
    df=pd.read_csv(ROOT/"systems"/"k28_nested_130.csv")
    cols=[c for c in df.columns if c.startswith("pos")]
    return [tuple(map(int,row)) for row in df[cols].to_numpy().tolist()]

@st.cache_data
def load_system36():
    df=pd.read_csv(ROOT/"systems"/"official_system36.csv")
    return [tuple(map(int,row)) for row in df.to_numpy().tolist()]

@st.cache_data
def load_system104():
    df=pd.read_csv(ROOT/"systems"/"official_system104.csv")
    cols=[c for c in df.columns if c.startswith("pos")]
    return [tuple(map(int,row)) for row in df[cols].to_numpy().tolist()]

@st.cache_data
def load_system118():
    df=pd.read_csv(ROOT/"systems"/"official_system118.csv")
    cols=[c for c in df.columns if c.startswith("pos")]
    return [tuple(map(int,row)) for row in df[cols].to_numpy().tolist()]

@st.cache_data
def load_curated_exact_systems():
    return json.loads((ROOT/"systems"/"official_exact_curated.json").read_text())

def load_curated_exact_system(system_no):
    spec=load_curated_exact_systems()[str(int(system_no))]
    return {
        "k":int(spec["k"]),
        "guarantees":[tuple(map(int,g)) for g in spec["guarantees"]],
        "layout":[tuple(map(int,row)) for row in spec["layout"]],
    }

@st.cache_data
def load_research_archive(game):
    suffix="642" if game=="6/42" else "649"
    p=ROOT/"data"/f"research_archive_{suffix}_2020_2023.csv"
    df=pd.read_csv(p)
    df=df.sort_values(["year","sequence_in_year"],ascending=[False,False]).reset_index(drop=True)
    draws=[list(map(int,row)) for row in df[[f"n{i}" for i in range(1,7)]].to_numpy().tolist()]
    return df,draws
