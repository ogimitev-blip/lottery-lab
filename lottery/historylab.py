import pandas as pd
from .models import current_pool_642,current_pool_649

def _pool(game,history):
    if game=="6/42":
        return current_pool_642(history,28)[0]
    return current_pool_649(history,22)[0]

def compare_history_depth(game,current_draws,archive_draws,max_targets=150,min_history=50):
    rows=[]
    limit=min(max_targets,max(0,len(current_draws)-min_history))
    for i in range(limit):
        actual=set(map(int,current_draws[i]))
        recent_hist=current_draws[i+1:]
        extended_hist=recent_hist+archive_draws
        p0=_pool(game,recent_hist)
        p1=_pool(game,extended_hist)
        h0=len(set(p0)&actual);h1=len(set(p1)&actual)
        rows.append({
            "draw_index_newest_first":i,
            "baseline_hits":h0,
            "extended_hits":h1,
            "delta":h1-h0,
            "baseline_pool":tuple(p0),
            "extended_pool":tuple(p1),
            "actual":tuple(sorted(actual)),
        })
    return pd.DataFrame(rows)

def summarize_depth(bt):
    if bt.empty:return {}
    return {
        "draws":len(bt),
        "baseline_mean":bt.baseline_hits.mean(),
        "extended_mean":bt.extended_hits.mean(),
        "baseline_p5":(bt.baseline_hits>=5).mean(),
        "extended_p5":(bt.extended_hits>=5).mean(),
        "baseline_p6":(bt.baseline_hits==6).mean(),
        "extended_p6":(bt.extended_hits==6).mean(),
        "extended_wins":int((bt.delta>0).sum()),
        "ties":int((bt.delta==0).sum()),
        "baseline_wins":int((bt.delta<0).sum()),
    }
