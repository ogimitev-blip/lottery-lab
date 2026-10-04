from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from lottery.data import load_draws_df, load_results_meta, load_custom_wheel
from lottery.models import current_pool_642, current_pool_649
from lottery.wheels import build_broad_four, build_broad_six, extend_sequence, map_positions, line_price

MAX_TARGETS=150
MIN_HISTORY=100
BUDGET=20.0
CURRENT_JACKPOTS={"6/49":4849337.75,"6/42":1303985.99}
COMBOS={"6/49":math.comb(49,6),"6/42":math.comb(42,6)}
CURRENT_PRICES={"6/49":0.90,"6/42":0.80}
N49_VALUES=[0,4]+list(range(6,23))


def numbers(df):
    cols=[f"n{i}" for i in range(1,7)]
    return [list(map(int,row)) for row in df[cols].to_numpy().tolist()]


def payout_for_hits(hits,meta_row,include_jackpot=True):
    out=0.0
    for h in hits:
        if h<3:
            continue
        if h==6 and include_jackpot:
            val=float(meta_row.get("payout6_eur",0) or 0)
            if val<=0 and int(meta_row.get("winners6",0) or 0)==0:
                val=float(meta_row.get("jackpot_eur",0) or 0)
        elif h==6:
            val=0.0
        else:
            val=float(meta_row.get(f"payout{h}_eur",0) or 0)
        out+=val
    return out


def medians(meta):
    out={}
    for h in (3,4,5):
        s=pd.to_numeric(meta[f"payout{h}_eur"],errors="coerce")
        s=s[s>0]
        out[h]=float(s.median())
    return out


def proxy_payout(hits,refs):
    return sum(refs.get(int(h),0.0) for h in hits if int(h) in refs)


def build_target_rows():
    d49=load_draws_df("6/49").copy()
    d42=load_draws_df("6/42").copy()
    cols=[f"n{i}" for i in range(1,7)]
    d49=d49.dropna(subset=cols).reset_index(drop=True)
    d42=d42.dropna(subset=cols).reset_index(drop=True)
    all49=[list(map(int,row)) for row in d49[cols].to_numpy().tolist()]
    all42=[list(map(int,row)) for row in d42[cols].to_numpy().tolist()]

    rows=[]
    wheel42=load_custom_wheel()
    limit=min(MAX_TARGETS,len(all49)-MIN_HISTORY,len(all42)-MIN_HISTORY)
    for i in range(max(0,limit)):
        actual49=all49[i]; actual42=all42[i]
        hist49=all49[i+1:]
        hist42=all42[i+1:]

        pool49,adds49,diag49,score49=current_pool_649(hist49,22)
        broad4=build_broad_four(pool49,score49)
        broad6=build_broad_six(pool49,score49,649)
        seq49=extend_sequence(broad6,pool49,score49,22,20260917+490000)

        pool42,adds42,diag42=current_pool_642(hist42,28)
        seq42=map_positions(pool42,wheel42[:25])

        aset49=set(actual49); aset42=set(actual42)
        hit4=[len(set(t)&aset49) for t in broad4]
        hit49=[len(set(t)&aset49) for t in seq49]
        hit42=[len(set(t)&aset42) for t in seq42]

        dn49=pd.to_numeric(pd.Series([d49.loc[i,"draw_no"]]),errors="coerce").iloc[0] if "draw_no" in d49.columns else np.nan
        dn42=pd.to_numeric(pd.Series([d42.loc[i,"draw_no"]]),errors="coerce").iloc[0] if "draw_no" in d42.columns else np.nan
        draw_no=int(dn49) if pd.notna(dn49) and pd.notna(dn42) and int(dn49)==int(dn42) else None

        rows.append({
            "target_index":i,
            "draw_no":draw_no,
            "hit4":hit4,
            "hit49":hit49,
            "hit42":hit42,
            "pool49_hits":len(set(pool49)&aset49),
            "pool42_hits":len(set(pool42)&aset42),
        })
    return rows

def tickets_hits(row,n49,n42):
    if n49==0:
        h49=[]
    elif n49==4:
        h49=row["hit4"]
    else:
        h49=row["hit49"][:n49]
    h42=row["hit42"][:n42]
    return h49,h42


def candidate_allocations():
    out=[]
    # Near-full-budget frontier. We retain at least one game unless explicitly all-in.
    for n49 in N49_VALUES:
        remain=BUDGET-CURRENT_PRICES["6/49"]*n49
        if remain<0:
            continue
        n42=int(math.floor((remain+1e-9)/CURRENT_PRICES["6/42"]))
        if n42>25:
            n42=25
        cost=CURRENT_PRICES["6/49"]*n49+CURRENT_PRICES["6/42"]*n42
        if cost<18.5:
            continue
        out.append((n49,n42,cost))
    # Explicitly retain the played/recommended 16+6 configuration.
    if not any(a==16 and b==6 for a,b,_ in out):
        out.append((16,6,16*.9+6*.8))
    return sorted(set(out))


def main():
    hist=build_target_rows()
    meta49=load_results_meta("6/49").copy()
    meta42=load_results_meta("6/42").copy()
    for m in (meta49,meta42):
        m["draw_no"]=pd.to_numeric(m.draw_no,errors="coerce").astype("Int64")
    mi49=meta49.dropna(subset=["draw_no"]).set_index("draw_no")
    mi42=meta42.dropna(subset=["draw_no"]).set_index("draw_no")
    refs49=medians(meta49); refs42=medians(meta42)

    results=[]
    for n49,n42,current_cost in candidate_allocations():
        proxy=[];proxy34=[]
        any3=[];any4=[];any5=[];any6=[]
        best49=[];best42=[]
        n3tot=[];n4tot=[];n5tot=[]
        actual_stake=0.0;actual_payout=0.0;actual_draws=0;actual_winning=0
        for row in hist:
            h49,h42=tickets_hits(row,n49,n42)
            allh=h49+h42
            proxy.append(proxy_payout(h49,refs49)+proxy_payout(h42,refs42))
            proxy34.append(
                proxy_payout(h49,{3:refs49[3],4:refs49[4]})+
                proxy_payout(h42,{3:refs42[3],4:refs42[4]})
            )
            any3.append(any(h>=3 for h in allh))
            any4.append(any(h>=4 for h in allh))
            any5.append(any(h>=5 for h in allh))
            any6.append(any(h>=6 for h in allh))
            best49.append(max(h49) if h49 else 0)
            best42.append(max(h42) if h42 else 0)
            n3tot.append(sum(h>=3 for h in allh))
            n4tot.append(sum(h>=4 for h in allh))
            n5tot.append(sum(h>=5 for h in allh))

            dn=row["draw_no"]
            if dn is not None and dn in mi49.index and dn in mi42.index:
                r49=mi49.loc[dn];r42=mi42.loc[dn]
                if isinstance(r49,pd.DataFrame):r49=r49.iloc[0]
                if isinstance(r42,pd.DataFrame):r42=r42.iloc[0]
                p=payout_for_hits(h49,r49,True)+payout_for_hits(h42,r42,True)
                s=n49*line_price("6/49",dn)+n42*line_price("6/42",dn)
                actual_payout+=p;actual_stake+=s;actual_draws+=1
                actual_winning+=int(p>0)

        jackpot_ev=n49*CURRENT_JACKPOTS["6/49"]/COMBOS["6/49"]+n42*CURRENT_JACKPOTS["6/42"]/COMBOS["6/42"]
        jackpot_prob=1-(1-1/COMBOS["6/49"])**n49*(1-1/COMBOS["6/42"])**n42
        proxy_lower=float(np.mean(proxy))
        composite=proxy_lower+jackpot_ev
        results.append({
            "n49":n49,"n42":n42,"current_cost_eur":round(current_cost,2),
            "walkforward_draws":len(hist),
            "p_any_3plus":float(np.mean(any3)),
            "p_any_4plus":float(np.mean(any4)),
            "p_any_5plus":float(np.mean(any5)),
            "p_any_6":float(np.mean(any6)),
            "mean_best_49":float(np.mean(best49)),
            "mean_best_42":float(np.mean(best42)),
            "mean_3plus_lines":float(np.mean(n3tot)),
            "mean_4plus_lines":float(np.mean(n4tot)),
            "mean_5plus_lines":float(np.mean(n5tot)),
            "lower_tier_proxy_eur_per_draw":proxy_lower,
            "lower_34_proxy_eur_per_draw":float(np.mean(proxy34)),
            "current_raw_jackpot_ev_eur":jackpot_ev,
            "current_raw_jackpot_prob":jackpot_prob,
            "current_raw_jackpot_odds":1/jackpot_prob if jackpot_prob else None,
            "composite_proxy_return_eur":composite,
            "composite_proxy_roi":composite/current_cost-1 if current_cost else None,
            "official_payout_draws":actual_draws,
            "official_sample_stake_eur":actual_stake,
            "official_sample_payout_eur":actual_payout,
            "official_sample_roi":actual_payout/actual_stake-1 if actual_stake else None,
            "official_sample_winning_draw_rate":actual_winning/actual_draws if actual_draws else None,
        })

    df=pd.DataFrame(results)
    # Robust rankings: rare-hit rate, composite proxy, actual payout sample.
    for col in ["p_any_4plus","p_any_5plus","composite_proxy_return_eur","official_sample_roi"]:
        df[f"rank_{col}"]=df[col].rank(method="min",ascending=False)
    df["balanced_rank"]=(
        df["rank_p_any_4plus"]+
        df["rank_p_any_5plus"]+
        df["rank_composite_proxy_return_eur"]+
        0.5*df["rank_official_sample_roi"]
    )

    # Current jackpot-only value per euro.
    jackpot_value={
        g:{
            "jackpot_eur":CURRENT_JACKPOTS[g],
            "combinations":COMBOS[g],
            "line_price_eur":CURRENT_PRICES[g],
            "jackpot_ev_per_line_eur":CURRENT_JACKPOTS[g]/COMBOS[g],
            "jackpot_ev_per_staked_eur":CURRENT_JACKPOTS[g]/COMBOS[g]/CURRENT_PRICES[g],
        } for g in ("6/49","6/42")
    }

    # Recommended policy is descriptive: choose a core 6 lines in each game,
    # then compare marginal budget tilts. No single historical winner drives it.
    keys=[
        (6,18),(8,16),(11,12),(14,9),(16,6),(16,7),(22,0),(0,25)
    ]
    selected=df[df.apply(lambda r:(int(r.n49),int(r.n42)) in keys,axis=1)].copy()
    top=df.sort_values("balanced_rank").head(8)

    # Stability windows for the most policy-relevant allocations.
    window_keys=[(4,20),(6,18),(8,16),(10,13),(12,11),(14,9),(16,6),(22,0),(0,25)]
    windowed={}
    for n49,n42 in window_keys:
        if not any((a==n49 and b==n42) for a,b,_ in candidate_allocations()):
            continue
        rec={}
        for wname,lo,hi in [("LATEST_50",0,50),("PRIOR_100",50,150),("FULL_150",0,150)]:
            p3=[];p4=[];p5=[];pr34=[]
            for row in hist[lo:hi]:
                h49,h42=tickets_hits(row,n49,n42)
                allh=h49+h42
                p3.append(any(h>=3 for h in allh))
                p4.append(any(h>=4 for h in allh))
                p5.append(any(h>=5 for h in allh))
                pr34.append(
                    proxy_payout(h49,{3:refs49[3],4:refs49[4]})+
                    proxy_payout(h42,{3:refs42[3],4:refs42[4]})
                )
            rec[wname]={
                "draws":len(p3),
                "p_any_3plus":float(np.mean(p3)),
                "p_any_4plus":float(np.mean(p4)),
                "p_any_5plus":float(np.mean(p5)),
                "mean_34_proxy_eur":float(np.mean(pr34)),
            }
        windowed[f"{n49}+{n42}"]=rec

    out={
        "method":{
            "budget_eur":BUDGET,
            "walkforward_draws":len(hist),
            "min_history":MIN_HISTORY,
            "official_payout_draws":int(df.official_payout_draws.max()),
            "lower_tier_proxy":"Median official 3/4/5 payouts by game applied to strict walk-forward ticket hits; jackpot excluded.",
            "jackpot_component":"Raw mathematical jackpot EV from current/last confirmed jackpot amounts; no predictive uplift assumed.",
            "caution":"Composite is a research proxy, not a true expected return estimate. Official payout sample is small."
        },
        "median_tier_payouts":{"6/49":refs49,"6/42":refs42},
        "jackpot_value":jackpot_value,
        "selected_allocations":selected.to_dict(orient="records"),
        "windowed_selected":windowed,
        "top_balanced":top.to_dict(orient="records"),
        "all_allocations":df.to_dict(orient="records"),
    }
    print("ALLOCATION_LAB_BEGIN")
    print(json.dumps(out,indent=2))
    print("ALLOCATION_LAB_END")


if __name__=="__main__":
    main()
