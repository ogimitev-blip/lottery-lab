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

def next_draw_info(game):
    s=load_sync_state()[game]
    last=date.fromisoformat(s["latest_date"])
    nxt=_next_thu_or_sun(last)
    return {"draw_no":int(s["latest_draw_no"])+1,"date":nxt.isoformat()}

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
    dup=df.duplicated(subset=cols,keep=False)
    if dup.any(): warnings.append(f"{int(dup.sum())} rows share an identical six-number result; review for genuine repeats vs duplicate data.")
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
