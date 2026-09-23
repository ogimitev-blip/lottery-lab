from pathlib import Path
import pandas as pd
import streamlit as st
ROOT=Path(__file__).resolve().parents[1]
@st.cache_data
def load_draws_642():
    df=pd.read_csv(ROOT/'data'/'draws_642.csv')
    return [list(map(int,row)) for row in df.to_numpy().tolist()]
@st.cache_data
def load_custom_wheel():
    df=pd.read_csv(ROOT/'systems'/'k28_nested_130.csv')
    cols=[c for c in df.columns if c.startswith('pos')]
    return [tuple(map(int,row)) for row in df[cols].to_numpy().tolist()]
@st.cache_data
def load_system36():
    df=pd.read_csv(ROOT/'systems'/'official_system36.csv')
    return [tuple(map(int,row)) for row in df.to_numpy().tolist()]
