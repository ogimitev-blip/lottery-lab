from __future__ import annotations

import json
import numpy as np
import pandas as pd

import scripts.backtest_649_500 as base
from lottery.models import production_score_649, flex_pool

SEEDS=[20260925,20260926,20260927,20260928,20260929,20260930,20261001,20261002]
CANDIDATES={
    "MIX_300_170_85":{"kind":"mix","q":(300,170,85)},
    "MIX_400_100_55":{"kind":"mix","q":(400,100,55)},
    "MIX_425_85_45":{"kind":"mix","q":(425,85,45)},
    "MIX_450_70_35":{"kind":"mix","q":(450,70,35)},
    "MIX_475_55_25":{"kind":"mix","q":(475,55,25)},
}
WINDOWS={"LATEST_50":(0,50),"FULL_150":(0,150)}


def stats(values):
    a=np.asarray(values,float)
    return {
        "mean":float(a.mean()),
        "std":float(a.std(ddof=1)) if len(a)>1 else 0.0,
        "min":float(a.min()),
        "max":float(a.max()),
    }


def main():
    base.PROPOSALS=64
    raw=pd.read_csv(base.DRAW_PATH)
    cols=[f"n{i}" for i in range(1,7)]
    draws=[list(map(int,row)) for row in raw[cols].to_numpy().tolist()]
    limit=min(150,len(draws)-base.MIN_HISTORY)

    states=[]
    for i in range(limit):
        actual=draws[i]
        hist=draws[i+1:]
        score,_=production_score_649(hist)
        pool22,_=flex_pool(score,hist,22)
        states.append((actual,pool22,score))

    records=[]
    layout_cov=[]
    for seed in SEEDS:
        for name,spec in CANDIDATES.items():
            layout=base._greedy_layout(name,spec,seed=seed)
            cov=base._coverage(layout)
            layout_cov.append({"seed":seed,"portfolio":name,**cov})
            for i,(actual,pool22,score) in enumerate(states):
                tickets=base._map_mix(layout,pool22,score)
                tm=base._metrics(tickets,actual)
                records.append({"seed":seed,"portfolio":name,"target_index":i,**tm})

    df=pd.DataFrame(records)
    covdf=pd.DataFrame(layout_cov)
    out={}
    for w,(lo,hi) in WINDOWS.items():
        out[w]={}
        for name in CANDIDATES:
            seed_rows=[]
            for seed in SEEDS:
                g=df[(df.seed==seed)&(df.portfolio==name)&(df.target_index>=lo)&(df.target_index<hi)]
                seed_rows.append({
                    "seed":seed,
                    "best_mean":float(g.best_hits.mean()),
                    "p3plus":float((g.best_hits>=3).mean()),
                    "p4plus":float((g.best_hits>=4).mean()),
                    "p5plus":float((g.best_hits>=5).mean()),
                    "mean_4plus_lines":float(g.n4plus.mean()),
                    "mean_5plus_lines":float(g.n5plus.mean()),
                })
            sd=pd.DataFrame(seed_rows)
            jc=base._jackpot_conversion(name,CANDIDATES[name])
            out[w][name]={
                "conditional_jackpot_odds_1_in":jc["conditional_jackpot_odds_1_in"],
                "best_mean":stats(sd.best_mean),
                "p3plus":stats(sd.p3plus),
                "p4plus":stats(sd.p4plus),
                "p5plus":stats(sd.p5plus),
                "mean_4plus_lines":stats(sd.mean_4plus_lines),
                "mean_5plus_lines":stats(sd.mean_5plus_lines),
            }

    coverage={}
    for name in CANDIDATES:
        g=covdf[covdf.portfolio==name]
        coverage[name]={
            "unique_4sets":stats(g.unique_4sets),
            "duplicate_4set_incidence":stats(g.duplicate_4set_incidence),
            "unique_3sets":stats(g.unique_3sets),
        }

    print("ROBUSTNESS_649_500_JSON_BEGIN")
    print(json.dumps({
        "seeds":SEEDS,
        "proposals_per_step":base.PROPOSALS,
        "windows":out,
        "coverage":coverage,
        "note":"Different deterministic wheel-construction seeds; selection model and target history unchanged. Used to measure conversion-layout sensitivity, not to select the best historical seed.",
    },indent=2,sort_keys=True))
    print("ROBUSTNESS_649_500_JSON_END")


if __name__=="__main__":
    main()
