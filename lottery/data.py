from pathlib import Path
import pandas as pd
import streamlit as st

ROOT=Path(__file__).resolve().parents[1]
GAME_FILES={"6/42":"draws_642.csv","6/49":"draws_649.csv"}

@st.cache_data
def load_draws_df(game):
    df=pd.read_csv(ROOT/"data"/GAME_FILES[game],dtype={"date":"string"})
    number_cols=[f"n{i}" for i in range(1,7)]
    return df[["date",*number_cols]].copy() if "date" in df.columns else df[number_cols].assign(date=pd.NA)[["date",*number_cols]]

def get_draws(game):
    df=load_draws_df(game)
    base=[list(map(int,row)) for row in df[[f"n{i}" for i in range(1,7)]].to_numpy().tolist()]
    extras=st.session_state.get(f"session_draws_{game}",[])
    return [list(map(int,x["numbers"])) for x in extras]+base

def get_draw_labels(game):
    df=load_draws_df(game)
    labels=[str(x) if pd.notna(x) and str(x).strip() else None for x in df["date"].tolist()]
    extras=st.session_state.get(f"session_draws_{game}",[])
    return [x.get("date") for x in extras]+labels

@st.cache_data
def load_custom_wheel():
    df=pd.read_csv(ROOT/"systems"/"k28_nested_130.csv")
    cols=[c for c in df.columns if c.startswith("pos")]
    return [tuple(map(int,row)) for row in df[cols].to_numpy().tolist()]

@st.cache_data
def load_system36():
    df=pd.read_csv(ROOT/"systems"/"official_system36.csv")
    return [tuple(map(int,row)) for row in df.to_numpy().tolist()]
