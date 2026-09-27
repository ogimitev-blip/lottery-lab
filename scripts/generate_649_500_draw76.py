from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pandas as pd

from lottery.models import production_score_649, flex_pool
from scripts.backtest_649_500 import _greedy_layout, _map_mix, _coverage

ROOT=Path(__file__).resolve().parents[1]
DRAW_PATH=ROOT/"data"/"draws_649.csv"
LEDGER_PATH=ROOT/"data"/"shadow_experiments.jsonl"
OUT_CSV=ROOT/"data"/"649_500_draw76.csv"
OUT_JSON=ROOT/"data"/"649_500_draw76_manifest.json"

TARGET_DRAW=76
TARGET_DATE="2026-09-27"
SPEC={"kind":"mix","q":(400,100,55)}
SEED=20260925


def main():
    rows=[json.loads(line) for line in LEDGER_PATH.read_text().splitlines() if line.strip()]
    frozen=[r for r in rows if r.get("game")=="6/49" and int(r.get("target_draw_no",-1))==TARGET_DRAW]
    if not frozen:
        raise RuntimeError("Frozen 6/49 draw-76 shadow batch not found")
    frozen_pool=list(map(int,frozen[0]["pool"]))

    raw=pd.read_csv(DRAW_PATH)
    cols=[f"n{i}" for i in range(1,7)]
    hist=[list(map(int,row)) for row in raw[cols].to_numpy().tolist()]
    score,_=production_score_649(hist)
    pool22,_=flex_pool(score,hist,22)
    pool22=list(map(int,pool22))
    if pool22 != frozen_pool:
        raise AssertionError(f"Current pre-draw K22 differs from frozen pool: {pool22} != {frozen_pool}")

    layout=_greedy_layout("MIX_400_100_55",SPEC,seed=SEED)
    tickets=[tuple(sorted(map(int,t))) for t in _map_mix(layout,pool22,score)]
    if len(tickets)!=555 or len(set(tickets))!=555:
        raise AssertionError("Expected 555 unique tickets")

    pset=set(pool22)
    def tier(t):
        inside=len(set(t)&pset)
        outside=6-inside
        return f"{inside}+{outside}"

    counts={}
    for t in tickets:
        counts[tier(t)]=counts.get(tier(t),0)+1
    if counts!={"6+0":400,"5+1":100,"4+2":55}:
        raise AssertionError(f"Unexpected tier counts {counts}")

    outside_ranked=sorted([n for n in range(1,50) if n not in pset], key=lambda n:(-float(score.loc[n]),n))

    with OUT_CSV.open("w",newline="") as f:
        w=csv.writer(f)
        w.writerow(["line","tier","n1","n2","n3","n4","n5","n6"])
        for i,t in enumerate(tickets,1):
            w.writerow([i,tier(t),*t])

    digest=hashlib.sha256(OUT_CSV.read_bytes()).hexdigest()
    manifest={
        "target_draw":TARGET_DRAW,
        "target_date":TARGET_DATE,
        "portfolio":"649_500_JACKPOT",
        "architecture":{"6+0":400,"5+1":100,"4+2":55},
        "lines":555,
        "cost_eur":499.50,
        "layout_seed":SEED,
        "production_pool_k22":pool22,
        "outside_ranked":outside_ranked,
        "coverage":_coverage(layout),
        "csv_sha256":digest,
        "actual_money_spent_eur":None,
        "note":"Generated before draw 76 from the frozen pre-draw K22 state. No crowd remap applied.",
    }
    OUT_JSON.write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps(manifest,indent=2))


if __name__=="__main__":
    main()
