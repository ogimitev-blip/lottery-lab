import pandas as pd
import numpy as np

from .modes import generate_mode
from .crowd import anti_crowd_remap,score_ticket_frame

def _ticket_metrics(tickets,actual):
    aset=set(map(int,actual))
    hits=np.array([len(set(map(int,t))&aset) for t in tickets],dtype=int)
    return {
        "best_hits":int(hits.max()) if len(hits) else 0,
        "n3plus":int((hits>=3).sum()),
        "n4plus":int((hits>=4).sum()),
        "n5plus":int((hits>=5).sum()),
        "n6":int((hits==6).sum()),
    }

def backtest_mode(game,mode_id,draws,max_targets=100,min_history=50):
    rows=[]
    limit=min(int(max_targets),max(0,len(draws)-int(min_history)))
    for i in range(limit):
        hist=draws[i+1:]
        actual=draws[i]
        state=generate_mode(game,mode_id,hist,None)
        tm=_ticket_metrics(state["tickets"],actual)
        rows.append({
            "draw_index_newest_first":i,
            "pool_hits":len(set(state["pool"])&set(actual)),
            **tm,
        })
    return pd.DataFrame(rows)

def summarize_mode_backtest(bt):
    if bt.empty:return {}
    return {
        "draws":len(bt),
        "pool_mean":float(bt.pool_hits.mean()),
        "pool_p5plus":float((bt.pool_hits>=5).mean()),
        "pool_p6":float((bt.pool_hits==6).mean()),
        "best_mean":float(bt.best_hits.mean()),
        "p3plus":float((bt.best_hits>=3).mean()),
        "p4plus":float((bt.best_hits>=4).mean()),
        "p5plus":float((bt.best_hits>=5).mean()),
        "p6":float((bt.best_hits==6).mean()),
        "total_3plus":int(bt.n3plus.sum()),
        "total_4plus":int(bt.n4plus.sum()),
        "total_5plus":int(bt.n5plus.sum()),
        "total_6":int(bt.n6.sum()),
    }

def backtest_crowd_layer(game,mode_id,draws,crowd_history,latest_draw_no,max_targets=100,min_history=50):
    """Use only crowd snapshots strictly older than each target draw.
    For 2026 regular draws, target draw numbers are inferred newest-first from
    latest_draw_no. This is prospective with respect to the crowd snapshot."""
    if crowd_history is None or crowd_history.empty:
        return pd.DataFrame()

    snapshots=[]
    for (draw_no,date),grp in crowd_history.groupby(["snapshot_draw","snapshot_date"],dropna=False):
        snapshots.append((int(draw_no),str(date),grp.copy()))
    snapshots.sort(key=lambda x:x[0])

    rows=[]
    limit=min(int(max_targets),max(0,len(draws)-int(min_history)))
    for i in range(limit):
        target_no=int(latest_draw_no)-i
        eligible=[s for s in snapshots if s[0] < target_no]
        if not eligible:
            continue
        snap_no,snap_date,crowd=max(eligible,key=lambda x:x[0])
        hist=draws[i+1:]
        actual=draws[i]
        state=generate_mode(game,mode_id,hist,None)
        base=list(state["tickets"])
        anti,_,_=anti_crowd_remap(state["pool"],base,crowd)
        bm=_ticket_metrics(base,actual)
        am=_ticket_metrics(anti,actual)
        bscore=score_ticket_frame(base,crowd)
        ascore=score_ticket_frame(anti,crowd)
        rows.append({
            "target_draw":target_no,
            "snapshot_draw":snap_no,
            "snapshot_date":snap_date,
            "pool_hits":len(set(state["pool"])&set(actual)),
            "base_best":bm["best_hits"],
            "anti_best":am["best_hits"],
            "base_n3plus":bm["n3plus"],
            "anti_n3plus":am["n3plus"],
            "base_n4plus":bm["n4plus"],
            "anti_n4plus":am["n4plus"],
            "base_n5plus":bm["n5plus"],
            "anti_n5plus":am["n5plus"],
            "base_n6":bm["n6"],
            "anti_n6":am["n6"],
            "base_crowd_index":float(bscore.crowd_index.mean()),
            "anti_crowd_index":float(ascore.crowd_index.mean()),
        })
    return pd.DataFrame(rows)

def summarize_crowd_backtest(bt):
    if bt.empty:return {}
    return {
        "draws":len(bt),
        "base_crowd":float(bt.base_crowd_index.mean()),
        "anti_crowd":float(bt.anti_crowd_index.mean()),
        "crowd_reduction_pct":float(1-bt.anti_crowd_index.mean()/bt.base_crowd_index.mean()),
        "base_best_mean":float(bt.base_best.mean()),
        "anti_best_mean":float(bt.anti_best.mean()),
        "base_p3plus":float((bt.base_best>=3).mean()),
        "anti_p3plus":float((bt.anti_best>=3).mean()),
        "base_p4plus":float((bt.base_best>=4).mean()),
        "anti_p4plus":float((bt.anti_best>=4).mean()),
        "base_p5plus":float((bt.base_best>=5).mean()),
        "anti_p5plus":float((bt.anti_best>=5).mean()),
        "anti_better":int((bt.anti_best>bt.base_best).sum()),
        "ties":int((bt.anti_best==bt.base_best).sum()),
        "base_better":int((bt.anti_best<bt.base_best).sum()),
    }
