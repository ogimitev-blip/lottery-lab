from __future__ import annotations
import itertools, json, math
from pathlib import Path
import numpy as np
import pandas as pd

from lottery.data import load_draws_df, load_results_meta, load_custom_wheel
from lottery.models import current_pool_649, current_pool_642
from lottery.wheels import build_broad_four, build_broad_six, extend_sequence, map_positions

ROOT=Path(__file__).resolve().parents[1]
MIN_HISTORY=100
MAX_TARGETS=150
BUDGET_LO=18.0
BUDGET_HI=20.0
PRICE49=0.90
PRICE42=0.80

# Current-price candidate grid. 649 supports 4 or >=6; 642 uses nested K28 custom wheel.
N49=[0,4]+list(range(6,23))
N42=[0]+list(range(6,19))
ALLOC=[(a,b,round(a*PRICE49+b*PRICE42,2)) for a in N49 for b in N42
       if BUDGET_LO <= a*PRICE49+b*PRICE42 <= BUDGET_HI and not (a==0 and b==0)]


def tickets49(hist,n,draw_no):
    if n==0:return [],[]
    pool,adds,diag,score=current_pool_649(hist,22)
    if n==4:
        tickets=build_broad_four(pool,score)
    else:
        base=build_broad_six(pool,score,649)
        tickets=base if n==6 else extend_sequence(base,pool,score,n,20260917+490000)
    return tickets,pool


def tickets42(hist,n):
    if n==0:return [],[]
    pool,adds,diag=current_pool_642(hist,28)
    wheel=load_custom_wheel()
    if n>len(wheel):raise ValueError(n)
    return map_positions(pool,wheel[:n]),pool


def hit_stats(tickets,actual):
    if not tickets:return {"best":0,"n3":0,"n4":0,"n5":0,"n6":0}
    aset=set(actual)
    h=[len(set(t)&aset) for t in tickets]
    return {"best":max(h),"n3":sum(x>=3 for x in h),"n4":sum(x>=4 for x in h),
            "n5":sum(x>=5 for x in h),"n6":sum(x>=6 for x in h)}


def payout_for(tickets,actual,mrow):
    if not tickets or mrow is None:return 0.0
    aset=set(actual);total=0.0
    for t in tickets:
        h=len(set(t)&aset)
        if h<3:continue
        if h==6:
            v=float(mrow.get("payout6_eur",0) or 0)
            if v<=0 and int(mrow.get("winners6",0) or 0)==0:
                v=float(mrow.get("jackpot_eur",0) or 0)
        else:
            v=float(mrow.get(f"payout{h}_eur",0) or 0)
        total+=v
    return total


def prep_meta(game):
    m=load_results_meta(game).copy()
    if m.empty:return {},{}
    m["draw_no"]=pd.to_numeric(m.draw_no,errors="coerce")
    m=m.dropna(subset=["draw_no"]);m["draw_no"]=m.draw_no.astype(int)
    idx={int(r.draw_no):r for _,r in m.iterrows()}
    refs={}
    for h in (3,4,5):
        vals=pd.to_numeric(m[f"payout{h}_eur"],errors="coerce")
        vals=vals[vals>0]
        refs[h]=float(vals.median()) if len(vals) else 0.0
    return idx,refs


def normalized_for(tickets,actual,refs):
    if not tickets:return 0.0
    aset=set(actual);x=0.0
    for t in tickets:
        h=len(set(t)&aset)
        if h in refs:x+=refs[h]
    return x


def main():
    d49=load_draws_df("6/49");d42=load_draws_df("6/42")
    cols=[f"n{i}" for i in range(1,7)]
    draws49=[list(map(int,r)) for r in d49[cols].to_numpy().tolist()]
    draws42=[list(map(int,r)) for r in d42[cols].to_numpy().tolist()]
    nums49=[int(x) for x in d49.draw_no]
    nums42=[int(x) for x in d42.draw_no]
    map42={n:i for i,n in enumerate(nums42)}
    meta49,refs49=prep_meta("6/49");meta42,refs42=prep_meta("6/42")
    common=[n for n in nums49 if n in map42]
    common=common[:MAX_TARGETS]

    # Cache generated tickets for each target and each line count.
    rows=[]
    payout_rows=[]
    for n in common:
        i49=nums49.index(n);i42=map42[n]
        if len(draws49[i49+1:])<MIN_HISTORY or len(draws42[i42+1:])<MIN_HISTORY:continue
        actual49=draws49[i49];actual42=draws42[i42]
        hist49=draws49[i49+1:];hist42=draws42[i42+1:]
        cache49={k:tickets49(hist49,k,n)[0] for k in sorted(set(a for a,b,c in ALLOC))}
        cache42={k:tickets42(hist42,k)[0] for k in sorted(set(b for a,b,c in ALLOC))}
        has_meta=(n in meta49 and n in meta42)
        for a,b,cost in ALLOC:
            s49=hit_stats(cache49[a],actual49);s42=hit_stats(cache42[b],actual42)
            rows.append({
                "draw_no":n,"n49":a,"n42":b,"cost":cost,
                "best49":s49["best"],"best42":s42["best"],
                "any3":int(s49["best"]>=3 or s42["best"]>=3),
                "any4":int(s49["best"]>=4 or s42["best"]>=4),
                "any5":int(s49["best"]>=5 or s42["best"]>=5),
                "sum_n3":s49["n3"]+s42["n3"],"sum_n4":s49["n4"]+s42["n4"],
                "sum_n5":s49["n5"]+s42["n5"],
                "combined_best":max(s49["best"],s42["best"]),
            })
            if has_meta:
                p49=payout_for(cache49[a],actual49,meta49[n])
                p42=payout_for(cache42[b],actual42,meta42[n])
                norm=normalized_for(cache49[a],actual49,refs49)+normalized_for(cache42[b],actual42,refs42)
                payout_rows.append({
                    "draw_no":n,"n49":a,"n42":b,"cost":cost,
                    "payout":p49+p42,"normalized":norm,
                    "net":p49+p42-cost
                })

    df=pd.DataFrame(rows);pdf=pd.DataFrame(payout_rows)
    sm=[]
    for (a,b,cost),g in df.groupby(["n49","n42","cost"]):
        rec={
            "n49":int(a),"n42":int(b),"cost":float(cost),"draws":int(len(g)),
            "p_any3":float(g.any3.mean()),"p_any4":float(g.any4.mean()),"p_any5":float(g.any5.mean()),
            "mean_combined_best":float(g.combined_best.mean()),
            "mean_3plus_lines":float(g.sum_n3.mean()),"mean_4plus_lines":float(g.sum_n4.mean()),
        }
        if not pdf.empty:
            pg=pdf[(pdf.n49==a)&(pdf.n42==b)]
            rec.update({
                "payout_draws":int(len(pg)),
                "actual_payout_eur":float(pg.payout.sum()),
                "actual_stake_eur":float(pg.cost.sum()),
                "actual_roi":float(pg.payout.sum()/pg.cost.sum()-1) if len(pg) else None,
                "normalized_payout_eur":float(pg.normalized.sum()),
                "normalized_roi":float(pg.normalized.sum()/pg.cost.sum()-1) if len(pg) else None,
                "winning_payout_draws":int((pg.payout>0).sum()),
            })
        sm.append(rec)
    out=pd.DataFrame(sm)

    # Current jackpot-only expected value at draw 77 jackpot levels.
    J49=4849337.75;J42=1303985.99
    out["jackpot_ev_eur"]=out.n49*J49/math.comb(49,6)+out.n42*J42/math.comb(42,6)
    out["jackpot_ev_per_euro"]=out.jackpot_ev_eur/out.cost

    # Robust ranks: each component separately; no opaque fitted weights.
    # Prefer rare-hit conversion, then any-prize frequency, then jackpot EV.
    out["rank_any4"]=out.p_any4.rank(ascending=False,method="min")
    out["rank_any3"]=out.p_any3.rank(ascending=False,method="min")
    out["rank_jev"]=out.jackpot_ev_per_euro.rank(ascending=False,method="min")
    if "normalized_roi" in out:
        out["rank_norm"]=out.normalized_roi.rank(ascending=False,method="min")
    else:
        out["rank_norm"]=len(out)
    out["rank_sum"]=out.rank_any4+out.rank_any3+out.rank_jev+out.rank_norm

    # Named allocations.
    named={}
    for name,a,b in [("OLD_6_18",6,18),("NEW_16_6",16,6),("BALANCED_10_13",10,13),
                     ("BALANCED_12_11",12,11),("BALANCED_14_8",14,8)]:
        q=out[(out.n49==a)&(out.n42==b)]
        if len(q):named[name]=q.iloc[0].to_dict()

    top=out.sort_values(["rank_sum","p_any4","p_any3","jackpot_ev_per_euro"],ascending=[True,False,False,False]).head(15)

    result={
        "method":{
            "budget_eur":[BUDGET_LO,BUDGET_HI],
            "candidate_allocations":len(ALLOC),
            "walk_forward_draws":int(df.draw_no.nunique()),
            "payout_overlap_draws":int(pdf.draw_no.nunique()) if len(pdf) else 0,
            "prices_for_candidate_budget":{"6/49":PRICE49,"6/42":PRICE42},
            "current_jackpot_reference_eur":{"6/49":J49,"6/42":J42},
            "caveat":"Payout sample is small; rank_sum is descriptive, not a fitted optimizer."
        },
        "named":named,
        "top15":top.to_dict(orient="records")
    }
    print("ALLOC_BEGIN");print(json.dumps(result,indent=2));print("ALLOC_END")

if __name__=="__main__":main()
