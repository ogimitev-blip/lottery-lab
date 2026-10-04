from __future__ import annotations
import json, math
import pandas as pd

from lottery.data import load_research_archive, load_custom_wheel
from lottery.models import current_pool_642, current_pool_649
from lottery.wheels import build_broad_six, extend_sequence, map_positions

MIN_HISTORY=100
MAX_TARGETS=300
PRICE49=0.90
PRICE42=0.80
CANDIDATES=[
    (6,18),(7,17),(8,16),(9,14),(10,13),(11,12),(12,11),
    (13,9),(14,9),(15,7),(16,6)
]
J49=4849337.75
J42=1303985.99

def score(tickets,actual):
    aset=set(actual)
    h=[len(set(t)&aset) for t in tickets]
    return {
        "best":max(h) if h else 0,
        "n3":sum(x>=3 for x in h),
        "n4":sum(x>=4 for x in h),
        "n5":sum(x>=5 for x in h),
        "n6":sum(x>=6 for x in h),
    }

def main():
    df49,draws49=load_research_archive("6/49")
    df42,draws42=load_research_archive("6/42")
    key49={(int(r.year),int(r.sequence_in_year)):i for i,r in df49.iterrows()}
    key42={(int(r.year),int(r.sequence_in_year)):i for i,r in df42.iterrows()}
    common=sorted(set(key49)&set(key42),reverse=True)

    rows=[]
    used=0
    for key in common:
        i49=key49[key];i42=key42[key]
        hist49=draws49[i49+1:];hist42=draws42[i42+1:]
        if len(hist49)<MIN_HISTORY or len(hist42)<MIN_HISTORY:
            continue
        actual49=draws49[i49];actual42=draws42[i42]
        pool49,_,_,score49=current_pool_649(hist49,22)
        seq49=extend_sequence(build_broad_six(pool49,score49,649),pool49,score49,16,20260917+490000)
        pool42,_,_=current_pool_642(hist42,28)
        seq42=map_positions(pool42,load_custom_wheel()[:18])
        ph49=len(set(pool49)&set(actual49));ph42=len(set(pool42)&set(actual42))
        for n49,n42 in CANDIDATES:
            s49=score(seq49[:n49],actual49);s42=score(seq42[:n42],actual42)
            rows.append({
                "year":key[0],"seq":key[1],"n49":n49,"n42":n42,
                "cost":n49*PRICE49+n42*PRICE42,
                "pool49":ph49,"pool42":ph42,
                "any3":int(s49["best"]>=3 or s42["best"]>=3),
                "any4":int(s49["best"]>=4 or s42["best"]>=4),
                "any5":int(s49["best"]>=5 or s42["best"]>=5),
                "any6":int(s49["best"]>=6 or s42["best"]>=6),
                "combined_best":max(s49["best"],s42["best"]),
                "n3":s49["n3"]+s42["n3"],"n4":s49["n4"]+s42["n4"],"n5":s49["n5"]+s42["n5"],
            })
        used+=1
        if used>=MAX_TARGETS:break

    d=pd.DataFrame(rows)
    out=[]
    for (n49,n42),g in d.groupby(["n49","n42"]):
        cost=float(g.cost.iloc[0])
        jev=n49*J49/math.comb(49,6)+n42*J42/math.comb(42,6)
        out.append({
            "n49":int(n49),"n42":int(n42),"cost_eur":cost,"draws":int(len(g)),
            "p_any3":float(g.any3.mean()),"p_any4":float(g.any4.mean()),
            "p_any5":float(g.any5.mean()),"p_any6":float(g.any6.mean()),
            "mean_best":float(g.combined_best.mean()),
            "mean_3plus_lines":float(g.n3.mean()),"mean_4plus_lines":float(g.n4.mean()),
            "mean_pool49":float(g.pool49.mean()),"mean_pool42":float(g.pool42.mean()),
            "jackpot_ev_eur":jev,"jackpot_ev_per_euro":jev/cost,
        })
    o=pd.DataFrame(out)
    for c in ["p_any4","p_any3","mean_best","jackpot_ev_per_euro"]:
        o["rank_"+c]=o[c].rank(ascending=False,method="min")
    o["balanced_rank"]=o[["rank_p_any4","rank_p_any3","rank_mean_best","rank_jackpot_ev_per_euro"]].sum(axis=1)
    o=o.sort_values(["balanced_rank","p_any4","p_any3","jackpot_ev_per_euro"],ascending=[True,False,False,False])
    print("ARCH_ALLOC_BEGIN")
    print(json.dumps({
        "method":{"draws":int(d[["year","seq"]].drop_duplicates().shape[0]),"min_history":MIN_HISTORY,
                  "note":"2020-2023 archive only; strict walk-forward per game; no payout fitting."},
        "allocations":o.to_dict("records")
    },indent=2))
    print("ARCH_ALLOC_END")

if __name__=="__main__":main()
