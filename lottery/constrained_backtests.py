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

        for strength in strengths:
            strength=float(strength)
            if strength<=0:
                tickets=base
                meta=None
            else:
                tickets,_,meta=constrained_anti_crowd_remap(
                    state["pool"],base,crowd,state["diagnostics"],strength=strength
                )

            tm=_ticket_metrics(tickets,actual)
            crowd_scores=score_ticket_frame(tickets,crowd)

            if meta is None:
                ratio=1.0
                swaps=0
            else:
                base_u=float(meta.attrs.get("base_model_utility",0.0))
                final_u=float(meta.attrs.get("final_model_utility",base_u))
                ratio=(final_u/base_u) if abs(base_u)>1e-12 else np.nan
                swaps=int(meta.attrs.get("swaps",0))

            rows.append({
                "target_draw":draw_no,
                "snapshot_draw":snap_no,
                "snapshot_date":snap_date,
                "strength":strength,
                "pool_hits":len(set(state["pool"]).intersection(set(actual))),
                "best_hits":tm["best_hits"],
                "n3plus":tm["n3plus"],
                "n4plus":tm["n4plus"],
                "n5plus":tm["n5plus"],
                "n6":tm["n6"],
                "crowd_index":float(crowd_scores.crowd_index.mean()),
                "swaps":swaps,
                "model_utility_ratio":ratio,
            })

    return pd.DataFrame(rows)
