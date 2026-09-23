from collections import Counter
import pandas as pd
from .models import production_score_642,production_score_649

def position_exposure(layout):
    c=Counter()
    for row in layout:
        for x in row:
            c[int(x)]+=1
    return c

def exposure_aware_map(layout,score,k):
    ranked=[int(n) for n in score.sort_values(ascending=False).index]
    selected=ranked[:k]
    exposure=position_exposure(layout)
    labels=list(range(1,k+1))
    label_order=sorted(labels,key=lambda x:(-exposure[x],x))
    label_to_num={lab:num for lab,num in zip(label_order,selected)}
    tickets=[tuple(sorted(label_to_num[int(x)] for x in row)) for row in layout]
    if len(set(tickets))!=len(tickets):
        raise AssertionError("Exact system mapped to duplicate tickets")
    mapping=pd.DataFrame({
        "system_position":labels,
        "exposure":[exposure[x] for x in labels],
        "number":[label_to_num[x] for x in labels],
    }).sort_values(["exposure","system_position"],ascending=[False,True]).reset_index(drop=True)
    return selected,label_to_num,tickets,mapping

def generate_exact_system(game,draws,layout,k):
    if game=="6/42":
        score,gp=production_score_642(draws); n_numbers=42
    elif game=="6/49":
        score,gp=production_score_649(draws); n_numbers=49
    else:
        raise ValueError(game)
    pool,label_to_num,tickets,mapping=exposure_aware_map(layout,score,k)
    ranks=score.rank(ascending=False,method="first").astype(int)
    pset=set(pool)
    diag=pd.DataFrame({
        "number":range(1,n_numbers+1),
        "score":[float(score.loc[n]) for n in range(1,n_numbers+1)],
        "rank":[int(ranks.loc[n]) for n in range(1,n_numbers+1)],
        "gap":[int(gp[n]) for n in range(1,n_numbers+1)],
        "in_pool":[n in pset for n in range(1,n_numbers+1)],
        "repeat_addition":[False]*n_numbers,
    }).sort_values("rank")
    return {
        "pool":pool,
        "additions":[],
        "diagnostics":diag,
        "tickets":tickets,
        "position_mapping":mapping,
        "mapping_method":"Exposure-aware (v10 primary)",
    }
