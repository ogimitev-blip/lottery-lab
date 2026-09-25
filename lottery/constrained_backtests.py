import pandas as pd
import numpy as np

from .modes import generate_mode
from .crowd import constrained_anti_crowd_remap, score_ticket_frame


def _ticket_metrics(tickets, actual):
    aset=set(map(int,actual))
    hits=np.array([len(set(map(int,t)).intersection(aset)) for t in tickets],dtype=int)
    return {
        "best_hits":int(hits.max()) if len(hits) else 0,
        "n3plus":int((hits>=3).sum()),
        "n4plus":int((hits>=4).sum()),
        "n5plus":int((hits>=5).sum()),
        "n6":int((hits==6).sum()),
    }


def backtest_constrained_crowd_grid(game,mode_id,draws,crowd_history,latest_draw_no,
                                    strengths=(0.0,0.10,0.20,0.30),
                                    max_targets=100,min_history=50):
    if crowd_history is None or crowd_history.empty:
        return pd.DataFrame()

    snapshots=[]
    for keys,grp in crowd_history.groupby(["snapshot_draw","snapshot_date"],dropna=False):
        draw_no,date=keys
        snapshots.append((int(draw_no),str(date),grp.copy()))
    snapshots.sort(key=lambda x:x[0])

    rows=[]
    limit=min(int(max_targets),max(0,len(draws)-int(min_history)))
    for i in range(limit):
        draw_no=int(latest_draw_no)-i
        eligible=[s for s in snapshots if s[0] < draw_no]
        if not eligible:
            continue
        snap_no,snap_date,crowd=max(eligible,key=lambda x:x[0])
        hist=draws[i+1:]
        actual=draws[i]
        state=generate_mode(game,mode_id,hist,None)
        base=list(state["tickets"])
