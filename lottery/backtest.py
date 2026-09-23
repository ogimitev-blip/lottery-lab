import numpy as np
import pandas as pd
import streamlit as st
from .models import production_score_642,production_score_649,flex_pool
from .wheels import map_positions

@st.cache_data(show_spinner=False)
def walk_forward_642(draws_tuple,wheel_tuple,min_history=50,n_lines=50):
    draws=[list(d) for d in draws_tuple];wheel=[tuple(x) for x in wheel_tuple][:n_lines];rows=[]
    for i in range(len(draws)-min_history):
        actual=set(draws[i]);hist=draws[i+1:];score,_=production_score_642(hist);pool,adds=flex_pool(score,hist,28)
        tickets=map_positions(pool,wheel);hits=np.array([len(set(t)&actual) for t in tickets])
        rows.append({"draw_index_newest_first":i,"pool_hits":len(set(pool)&actual),"best_ticket_hits":int(hits.max()),"n_3plus":int((hits>=3).sum()),"n_4plus":int((hits>=4).sum()),"n_5plus":int((hits>=5).sum()),"n_6":int((hits==6).sum()),"pool":tuple(pool),"repeat_additions":tuple(adds),"actual":tuple(sorted(actual))})
    return pd.DataFrame(rows)

@st.cache_data(show_spinner=False)
def walk_forward_pool_649(draws_tuple,min_history=50,k=22):
    draws=[list(d) for d in draws_tuple];rows=[]
    for i in range(len(draws)-min_history):
        actual=set(draws[i]);hist=draws[i+1:];score,_=production_score_649(hist);pool,adds=flex_pool(score,hist,k)
        rows.append({"draw_index_newest_first":i,"pool_hits":len(set(pool)&actual),"pool":tuple(pool),"repeat_additions":tuple(adds),"actual":tuple(sorted(actual))})
    return pd.DataFrame(rows)

def summarize_backtest(bt):
    return {"draws":len(bt),"pool_mean":bt.pool_hits.mean(),"pool_p5plus":(bt.pool_hits>=5).mean(),"pool_p6":(bt.pool_hits==6).mean(),"ticket_p3plus":(bt.best_ticket_hits>=3).mean(),"ticket_p4plus":(bt.best_ticket_hits>=4).mean(),"ticket_p5plus":(bt.best_ticket_hits>=5).mean(),"ticket_p6":(bt.best_ticket_hits==6).mean()}
