from __future__ import annotations
import json, math
from pathlib import Path
import pandas as pd

from lottery.data import load_draws_df, load_results_meta, load_custom_wheel
from lottery.models import current_pool_642, current_pool_649
from lottery.wheels import build_broad_six, extend_sequence, map_positions, line_price

MAX_TARGETS=150
MIN_HISTORY=100
N49_MAX=16
N42_MAX=18
BUDGET_MIN=18.0
BUDGET_MAX=20.0

def score(tickets, actual):
    aset=set(map(int,actual))
    hits=[len(set(map(int,t)) & aset) for t in tickets]
    return {
        "best":max(hits) if hits else 0,
        "n3":sum(h>=3 for h in hits),
        "n4":sum(h>=4 for h in hits),
        "n5":sum(h>=5 for h in hits),
        "n6":sum(h>=6 for h in hits),
    }

def payout_for(hits, meta_row):
    total=0.0
    for h in hits:
        if h<3: continue
        v=meta_row.get(f"payout{h}_eur",0.0)
        if pd.notna(v): total+=float(v)
    return total

def main():
    df49=load_draws_df("6/49").reset_index(drop=True)
    df42=load_draws_df("6/42").reset_index(drop=True)
    cols=[f"n{i}" for i in range(1,7)]
    d49n=pd.to_numeric(df49.draw_no,errors="coerce")
    d42n=pd.to_numeric(df42.draw_no,errors="coerce")
    common=sorted(set(map(int,d49n.dropna())) & set(map(int,d42n.dropna())), reverse=True)

    # Candidate allocations at ordinary-draw prices. Both games retain at least six lines.
    candidates=[]
    for n49 in range(6,N49_MAX+1):
        for n42 in range(6,N42_MAX+1):
            c=.90*n49+.80*n42
            if BUDGET_MIN <= c <= BUDGET_MAX:
                candidates.append((n49,n42,round(c,2)))

    rows=[]
    used=0
    for draw_no in common:
        r49i=df49.index[d49n==draw_no]
        r42i=df42.index[d42n==draw_no]
        if len(r49i)==0 or len(r42i)==0: continue
        i49=int(r49i[0]); i42=int(r42i[0])
        hist49=[list(map(int,row)) for row in df49.loc[i49+1:,cols].to_numpy().tolist()]
        hist42=[list(map(int,row)) for row in df42.loc[i42+1:,cols].to_numpy().tolist()]
        if len(hist49)<MIN_HISTORY or len(hist42)<MIN_HISTORY: continue
        actual49=list(map(int,df49.loc[i49,cols].tolist()))
        actual42=list(map(int,df42.loc[i42,cols].tolist()))

        pool49,adds49,diag49,score49=current_pool_649(hist49,22)
        base49=build_broad_six(pool49,score49,649)
        seq49=extend_sequence(base49,pool49,score49,N49_MAX,20260917+490000)
        pool42,adds42,diag42=current_pool_642(hist42,28)
        seq42=map_positions(pool42,load_custom_wheel()[:N42_MAX])

        for n49,n42,ordinary_cost in candidates:
            s49=score(seq49[:n49],actual49)
            s42=score(seq42[:n42],actual42)
            actual_cost=n49*line_price("6/49",draw_no)+n42*line_price("6/42",draw_no)
            rows.append({
                "draw_no":draw_no,"n49":n49,"n42":n42,
                "ordinary_cost":ordinary_cost,"actual_cost":actual_cost,
                "pool49":len(set(pool49)&set(actual49)),"pool42":len(set(pool42)&set(actual42)),
                **{f"g49_{k}":v for k,v in s49.items()},
                **{f"g42_{k}":v for k,v in s42.items()},
                "any3":int(s49["n3"]>0 or s42["n3"]>0),
                "any4":int(s49["n4"]>0 or s42["n4"]>0),
                "any5":int(s49["n5"]>0 or s42["n5"]>0),
                "any6":int(s49["n6"]>0 or s42["n6"]>0),
                "total3":s49["n3"]+s42["n3"],
                "total4":s49["n4"]+s42["n4"],
                "total5":s49["n5"]+s42["n5"],
            })
        used+=1
        if used>=MAX_TARGETS: break

    res=pd.DataFrame(rows)
    structural=[]
    for (n49,n42),g in res.groupby(["n49","n42"]):
        structural.append({
            "n49":int(n49),"n42":int(n42),
            "ordinary_cost_eur":float(g.ordinary_cost.iloc[0]),
            "draws":int(len(g)),
            "p_any3":float(g.any3.mean()),"p_any4":float(g.any4.mean()),
            "p_any5":float(g.any5.mean()),"p_any6":float(g.any6.mean()),
            "mean_total3":float(g.total3.mean()),"mean_total4":float(g.total4.mean()),
            "mean_total5":float(g.total5.mean()),
            "mean_best49":float(g.g49_best.mean()),"mean_best42":float(g.g42_best.mean()),
            "mean_pool49":float(g.pool49.mean()),"mean_pool42":float(g.pool42.mean()),
        })

    # Official payout evaluation on draws where both games have metadata.
    m49=load_results_meta("6/49");m42=load_results_meta("6/42")
    m49n=pd.to_numeric(m49.draw_no,errors="coerce")
    m42n=pd.to_numeric(m42.draw_no,errors="coerce")
    pcommon=sorted(set(map(int,m49n.dropna())) & set(map(int,m42n.dropna())), reverse=True)
    payout_rows=[]
    for draw_no in pcommon:
        target=res[res.draw_no==draw_no]
        if target.empty: continue
        r49=df49[pd.to_numeric(df49.draw_no)==draw_no].iloc[0]
        r42=df42[pd.to_numeric(df42.draw_no)==draw_no].iloc[0]
        actual49=list(map(int,r49[cols].tolist()));actual42=list(map(int,r42[cols].tolist()))
        i49=int(df49.index[pd.to_numeric(df49.draw_no)==draw_no][0])
        i42=int(df42.index[pd.to_numeric(df42.draw_no)==draw_no][0])
        hist49=[list(map(int,row)) for row in df49.loc[i49+1:,cols].to_numpy().tolist()]
        hist42=[list(map(int,row)) for row in df42.loc[i42+1:,cols].to_numpy().tolist()]
        pool49,_,_,score49=current_pool_649(hist49,22)
        seq49=extend_sequence(build_broad_six(pool49,score49,649),pool49,score49,N49_MAX,20260917+490000)
        pool42,_,_=current_pool_642(hist42,28)
        seq42=map_positions(pool42,load_custom_wheel()[:N42_MAX])
        meta49=m49[pd.to_numeric(m49.draw_no)==draw_no].iloc[0]
        meta42=m42[pd.to_numeric(m42.draw_no)==draw_no].iloc[0]
        for n49,n42,ordinary_cost in candidates:
            h49=[len(set(t)&set(actual49)) for t in seq49[:n49]]
            h42=[len(set(t)&set(actual42)) for t in seq42[:n42]]
            cost=n49*line_price("6/49",draw_no)+n42*.80
            p49=payout_for(h49,meta49);p42=payout_for(h42,meta42)
            jackpot_ev=n49*float(meta49.jackpot_eur)/math.comb(49,6)+n42*float(meta42.jackpot_eur)/math.comb(42,6)
            payout_rows.append({
                "draw_no":draw_no,"n49":n49,"n42":n42,"cost":cost,
                "p49":p49,"p42":p42,"payout":p49+p42,"net":p49+p42-cost,
                "jackpot_ev":jackpot_ev,
            })
    pay=pd.DataFrame(payout_rows)
    payout_summary=[]
    if not pay.empty:
        for (n49,n42),g in pay.groupby(["n49","n42"]):
            payout_summary.append({
                "n49":int(n49),"n42":int(n42),"draws":int(len(g)),
                "stake_eur":float(g.cost.sum()),"payout_eur":float(g.payout.sum()),
                "net_eur":float(g.net.sum()),"roi":float(g.payout.sum()/g.cost.sum()-1),
                "payout49_eur":float(g.p49.sum()),"payout42_eur":float(g.p42.sum()),
                "mean_jackpot_ev_eur":float(g.jackpot_ev.mean()),
                "jackpot_ev_per_eur":float(g.jackpot_ev.sum()/g.cost.sum()),
            })

    # Add a simple Pareto flag: not dominated on any4, any5, jackpot EV / euro, recent ROI.
    sdf=pd.DataFrame(structural)
    pdf=pd.DataFrame(payout_summary)
    merged=sdf.merge(pdf,on=["n49","n42"],how="left",suffixes=("","_payout"))
    pareto=[]
    for idx,r in merged.iterrows():
        dominated=False
        for j,s in merged.iterrows():
            if idx==j: continue
            metrics=["p_any4","p_any5","jackpot_ev_per_eur","roi"]
            if all(float(s[m])>=float(r[m]) for m in metrics) and any(float(s[m])>float(r[m]) for m in metrics):
                dominated=True;break
        pareto.append(not dominated)
    merged["pareto"]=pareto
    merged=merged.sort_values(["pareto","p_any4","jackpot_ev_per_eur"],ascending=[False,False,False])

    print("ALLOC_BEGIN")
    print(json.dumps({
        "method":{
            "structural_window_draws":int(res.draw_no.nunique()),
            "official_payout_common_draws":int(pay.draw_no.nunique()) if not pay.empty else 0,
            "budget_eur":[BUDGET_MIN,BUDGET_MAX],
            "candidate_count":len(candidates),
            "note":"Strict walk-forward production pools/wheels. Structural metrics use up to 150 common draws. Official payout/ROI uses only draws with metadata for both games and is therefore a small-sample secondary metric. Jackpot EV is raw theoretical jackpot component and ignores jackpot splitting."
        },
        "allocations":merged.to_dict("records")
    },indent=2))
    print("ALLOC_END")

if __name__=="__main__":
    main()
