from __future__ import annotations

import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path

import pandas as pd

from .data import load_draws_df
from .models import current_pool_649
from .k22_vnext import current_pool_649_vnext,VNAME
from .wheels import build_broad_six,extend_sequence

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"data"/"k22_score_shadows.jsonl"
SEED=20260917+490000
PREFIXES=(6,10,11,22)


def read_rows():
    if not PATH.exists():
        return []
    out=[]
    for line in PATH.read_text().splitlines():
        line=line.strip()
        if line:
            out.append(json.loads(line))
    return out


def write_rows(rows):
    PATH.write_text("".join(json.dumps(r,separators=(",",":"),sort_keys=True)+"\n" for r in rows))


def _sid(draw_no):
    return hashlib.sha256(f"K22-score-shadow|{int(draw_no)}|{VNAME}".encode()).hexdigest()[:20]


def _seq(pool,score):
    base=build_broad_six(pool,score,649)
    return extend_sequence(base,pool,score,22,SEED)


def build_row(target,draws):
    bp,ba,bd,bs=current_pool_649(draws,22)
    cp,ca,cd,cs=current_pool_649_vnext(draws,22)
    return {
        "score_shadow_id":_sid(target["draw_no"]),
        "created_at":datetime.now(timezone.utc).isoformat(),
        "target_draw_no":int(target["draw_no"]),
        "target_date":str(target["date"]),
        "label":VNAME,
        "production_model":"K22-ENSEMBLE-OD075-REP2 v1",
        "challenger_model":VNAME,
        "prefixes":list(PREFIXES),
        "base_pool":list(map(int,bp)),
        "challenger_pool":list(map(int,cp)),
        "base_repeat_additions":list(map(int,ba)),
        "challenger_repeat_additions":list(map(int,ca)),
        "base_tickets":[list(map(int,t)) for t in _seq(bp,bs)],
        "challenger_tickets":[list(map(int,t)) for t in _seq(cp,cs)],
        "is_shadow":True,
        "actual_money_spent_eur":0.0,
    }


def append_row(target,draws):
    rows=read_rows()
    sid=_sid(target["draw_no"])
    if any(r.get("score_shadow_id")==sid for r in rows):
        return []
    row=build_row(target,draws)
    rows.append(row)
    rows.sort(key=lambda r:int(r["target_draw_no"]))
    write_rows(rows)
    return [row]


def _metrics(tickets,actual,n):
    a=set(actual)
    hs=[len(set(map(int,t))&a) for t in tickets[:n]]
    return {
        "best":max(hs),
        "n3plus":sum(h>=3 for h in hs),
        "n4plus":sum(h>=4 for h in hs),
        "n5plus":sum(h>=5 for h in hs),
        "n6":sum(h>=6 for h in hs),
    }


def score_row(row):
    df=load_draws_df("6/49")
    m=df[pd.to_numeric(df.draw_no,errors="coerce")==int(row["target_draw_no"])]
    if m.empty:
        return {**row,"status":"pending"}
    actual=set(map(int,m.iloc[0][[f"n{i}" for i in range(1,7)]].tolist()))
    out={**row,"status":"scored","actual":sorted(actual)}
    out["base_pool_hits"]=len(set(row["base_pool"])&actual)
    out["challenger_pool_hits"]=len(set(row["challenger_pool"])&actual)
    out["pool_delta"]=out["challenger_pool_hits"]-out["base_pool_hits"]
    out["prefix_results"]={}
    for n in PREFIXES:
        b=_metrics(row["base_tickets"],actual,n)
        c=_metrics(row["challenger_tickets"],actual,n)
        out["prefix_results"][str(n)]={
            "base":b,"challenger":c,"best_delta":c["best"]-b["best"]
        }
    return out


def score_rows():
    return [score_row(r) for r in read_rows()]
