from __future__ import annotations
import json, math
import numpy as np
import pandas as pd

from lottery.data import load_draws_df, load_results_meta, load_custom_wheel
from lottery.models import current_pool_649, current_pool_642
from lottery.wheels import build_broad_four, build_broad_six, extend_sequence, map_positions

MAX_TARGETS=150
MIN_HISTORY=100
PRICE49=0.90
PRICE42=0.80
BUDGET_LO=18.0
BUDGET_HI=20.0
J49=4849337.75
J42=1303985.99
C49=math.comb(49,6)
C42=math.comb(42,6)
N49=[0,4]+list(range(6,23))
N42=[0]+list(range(6,26))

def _draws(game):
    df=load_draws_df(game)
    cols=[f"n{i}" for i in range(1,7)]
    return [list(map(int,r)) for r in df[cols].to_numpy().tolist()]

def _medians(game):
    m=load_results_meta(game)
    out={}
    for h in (3,4,5):
        s=pd.to_numeric(m[f"payout{h}_eur"],errors="coerce")
        s=s[s>0]
        out[h]=float(s.median())
    return out

def _game_prefix_stats(game,counts):
    draws=_draws(game)
    limit=min(MAX_TARGETS,len(draws)-MIN_HISTORY)
    records={n:[] for n in counts}
    wheel42=load_custom_wheel() if game=="6/42" else None
    maxn=max(counts) if counts else 0
    for i in range(limit):
        actual=set(draws[i])
        hist=draws[i+1:]
        if game=="6/49":
            pool,adds,diag,score=current_pool_649(hist,22)
            broad4=build_broad_four(pool,score)
            base6=build_broad_six(pool,score,649)
            seq=extend_sequence(base6,pool,score,max(6,maxn),20260917+490000)
        else:
            pool,adds,diag=current_pool_642(hist,28)
            seq=map_positions(pool,wheel42[:maxn])
            broad4=None
        for n in counts:
            if n==0:
                tickets=[]
            elif game=="6/49" and n==4:
                tickets=broad4
            else:
                tickets=seq[:n]
            hits=[len(set(t)&actual) for t in tickets]
            exact={h:sum(x==h for x in hits) for h in range(7)}
            records[n].append({
                "best":max(hits) if hits else 0,
                "pool_hits":len(set(pool)&actual),
                **{f"e{h}":exact[h] for h in range(3,7)}
            })
    refs=_medians(game)
    out={}
    for n,rr in records.items():
        df=pd.DataFrame(rr)
        if n==0:
            out[n]={
                "draws":limit,"p3":0.0,"p4":0.0,"p5":0.0,"p6":0.0,
                "mean_best":0.0,"mean_pool_hits":float("nan"),
                "mean_exact3":0.0,"mean_exact4":0.0,"mean_exact5":0.0,
                "stable_lower_proxy":0.0,"full_lower_proxy":0.0
            }
            continue
        e3=float(df.e3.mean());e4=float(df.e4.mean());e5=float(df.e5.mean())
        out[n]={
            "draws":int(len(df)),
            "p3":float((df.best>=3).mean()),
            "p4":float((df.best>=4).mean()),
            "p5":float((df.best>=5).mean()),
            "p6":float((df.best>=6).mean()),
            "mean_best":float(df.best.mean()),
            "mean_pool_hits":float(df.pool_hits.mean()),
            "mean_exact3":e3,"mean_exact4":e4,"mean_exact5":e5,
            # Primary proxy deliberately excludes 5+ because 150 draws are too sparse
            # for a stable empirical 5-hit expectation.
            "stable_lower_proxy":e3*refs[3]+e4*refs[4],
            "full_lower_proxy":e3*refs[3]+e4*refs[4]+e5*refs[5],
        }
    return out,refs

def _recent_official_same_date():
    d49=load_draws_df("6/49").copy(); d42=load_draws_df("6/42").copy()
    cols=[f"n{i}" for i in range(1,7)]
    d49["date_key"]=pd.to_datetime(d49.date,errors="coerce").dt.strftime("%Y-%m-%d")
    d42["date_key"]=pd.to_datetime(d42.date,errors="coerce").dt.strftime("%Y-%m-%d")
    m49=load_results_meta("6/49").copy();m42=load_results_meta("6/42").copy()
    m49["date_key"]=pd.to_datetime(m49.date,errors="coerce").dt.strftime("%Y-%m-%d")
    m42["date_key"]=pd.to_datetime(m42.date,errors="coerce").dt.strftime("%Y-%m-%d")
    meta49={r.date_key:r for _,r in m49.dropna(subset=["date_key"]).iterrows()}
    meta42={r.date_key:r for _,r in m42.dropna(subset=["date_key"]).iterrows()}
    common=sorted(set(meta49)&set(meta42)&set(d49.date_key.dropna())&set(d42.date_key.dropna()),reverse=True)
    rows=[]
    for date_key in common:
        i49=int(d49.index[d49.date_key==date_key][0]); i42=int(d42.index[d42.date_key==date_key][0])
        hist49=[list(map(int,r)) for r in d49.loc[i49+1:,cols].to_numpy().tolist()]
        hist42=[list(map(int,r)) for r in d42.loc[i42+1:,cols].to_numpy().tolist()]
        if len(hist49)<MIN_HISTORY or len(hist42)<MIN_HISTORY: continue
        actual49=set(map(int,d49.loc[i49,cols].tolist()))
        actual42=set(map(int,d42.loc[i42,cols].tolist()))
        pool49,_,_,score49=current_pool_649(hist49,22)
        broad4=build_broad_four(pool49,score49)
        base49=build_broad_six(pool49,score49,649)
        seq49=extend_sequence(base49,pool49,score49,22,20260917+490000)
        pool42,_,_=current_pool_642(hist42,28)
        seq42=map_positions(pool42,load_custom_wheel()[:25])
        rows.append((date_key,actual49,actual42,broad4,seq49,seq42,meta49[date_key],meta42[date_key]))
    return rows

def _payout(tickets,actual,meta):
    total=0.0
    for t in tickets:
        h=len(set(t)&actual)
        if h<3: continue
        if h==6:
            v=float(meta.get("payout6_eur",0) or 0)
            if v<=0 and int(meta.get("winners6",0) or 0)==0:
                v=float(meta.get("jackpot_eur",0) or 0)
        else:
            v=float(meta.get(f"payout{h}_eur",0) or 0)
        total+=v
    return total

def _tickets49(n,broad4,seq):
    if n==0:return []
    if n==4:return broad4
    return seq[:n]

def main():
    s49,refs49=_game_prefix_stats("6/49",N49)
    s42,refs42=_game_prefix_stats("6/42",N42)
    official=_recent_official_same_date()

    candidates=[]
    for n49 in N49:
        for n42 in N42:
            cost=n49*PRICE49+n42*PRICE42
            if not (BUDGET_LO-1e-9<=cost<=BUDGET_HI+1e-9): continue
            a=s49[n49];b=s42[n42]
            # Independent-game union approximation; draws are separate random games.
            p3=1-(1-a["p3"])*(1-b["p3"])
            p4=1-(1-a["p4"])*(1-b["p4"])
            p5=1-(1-a["p5"])*(1-b["p5"])
            p6=1-(1-a["p6"])*(1-b["p6"])
            stable=a["stable_lower_proxy"]+b["stable_lower_proxy"]
            full=a["full_lower_proxy"]+b["full_lower_proxy"]
            jackpot_ev=n49*J49/C49+n42*J42/C42
            jackpot_prob=1-(1-1/C49)**n49*(1-1/C42)**n42

            opayout=0.0;ostake=0.0;owin=0
            for _,actual49,actual42,b4,seq49,seq42,m49,m42 in official:
                p=_payout(_tickets49(n49,b4,seq49),actual49,m49)+_payout(seq42[:n42],actual42,m42)
                opayout+=p;ostake+=cost;owin+=int(p>0)

            candidates.append({
                "n49":n49,"n42":n42,"cost_eur":round(cost,2),
                "p_any3_proxy":p3,"p_any4_proxy":p4,"p_any5_proxy":p5,"p_any6_proxy":p6,
                "mean_best49":a["mean_best"],"mean_best42":b["mean_best"],
                "stable_3_4_proxy_eur":stable,
                "full_3_4_5_proxy_eur":full,
                "jackpot_ev_eur":jackpot_ev,
                "jackpot_ev_per_staked_eur":jackpot_ev/cost,
                "raw_any_jackpot_prob":jackpot_prob,
                "raw_any_jackpot_odds":1/jackpot_prob,
                "stable_plus_jackpot_proxy_eur":stable+jackpot_ev,
                "stable_plus_jackpot_proxy_roi":(stable+jackpot_ev)/cost-1,
                "official_draws":len(official),
                "official_stake_eur":ostake,
                "official_payout_eur":opayout,
                "official_roi":opayout/ostake-1 if ostake else None,
                "official_winning_draw_rate":owin/len(official) if official else None,
            })

    df=pd.DataFrame(candidates)

    # Pareto frontier on stable attributes only. Recent realized ROI is secondary
    # and intentionally excluded because 13 draws is too small.
    metrics=["p_any3_proxy","p_any4_proxy","p_any5_proxy","jackpot_ev_per_staked_eur","stable_3_4_proxy_eur"]
    pareto=[]
    for i,r in df.iterrows():
        dom=False
        for j,s in df.iterrows():
            if i==j:continue
            if all(float(s[m])>=float(r[m])-1e-15 for m in metrics) and any(float(s[m])>float(r[m])+1e-15 for m in metrics):
                dom=True;break
        pareto.append(not dom)
    df["pareto"]=pareto

    # Practical balanced score: percentile ranks, transparent equal weights on
    # prize frequency, 4+ conversion, stable lower-tier value and jackpot value.
    for m in ["p_any3_proxy","p_any4_proxy","stable_3_4_proxy_eur","jackpot_ev_per_staked_eur"]:
        df["pct_"+m]=df[m].rank(pct=True)
    df["balanced_score"]=df[[c for c in df.columns if c.startswith("pct_")]].mean(axis=1)

    named={}
    for name,a,b in [
        ("OLD_6_18",6,18),("TILT_8_16",8,16),("MID_10_13",10,13),
        ("MID_12_11",12,11),("MID_14_9",14,9),("NEW_16_6",16,6)
    ]:
        q=df[(df.n49==a)&(df.n42==b)]
        if len(q): named[name]=q.iloc[0].to_dict()

    top_balanced=df.sort_values(["balanced_score","p_any4_proxy"],ascending=[False,False]).head(10)
    pareto_df=df[df.pareto].sort_values(["n49","n42"])

    # Break-even jackpot ratio for 6/49 vs 6/42 per staked euro.
    # J49/C49/P49 = J42/C42/P42.
    breakeven_ratio=(C49*PRICE49)/(C42*PRICE42)

    out={
        "method":{
            "per_game_walkforward_draws":MAX_TARGETS,
            "cross_game_combination":"Marginal per-game results estimated separately; combined hit probability uses independent-game union approximation.",
            "official_same_date_draws":len(official),
            "primary_lower_tier_proxy":"3-hit + 4-hit only, using median official payouts; 5+ excluded from primary proxy due sparse events.",
            "payout_caution":"Recent official ROI is secondary only and not used in Pareto or balanced score."
        },
        "median_payouts":{"6/49":refs49,"6/42":refs42},
        "current_jackpot_reference":{"6/49":J49,"6/42":J42,"ratio_49_to_42":J49/J42},
        "jackpot_ev_per_euro":{"6/49":J49/C49/PRICE49,"6/42":J42/C42/PRICE42},
        "jackpot_value_breakeven_ratio_49_to_42":breakeven_ratio,
        "named":named,
        "top_balanced":top_balanced.to_dict(orient="records"),
        "pareto":pareto_df.to_dict(orient="records"),
        "all":df.to_dict(orient="records"),
    }
    print("ALLOC_V2_BEGIN")
    print(json.dumps(out,indent=2))
    print("ALLOC_V2_END")

if __name__=="__main__":
    main()
