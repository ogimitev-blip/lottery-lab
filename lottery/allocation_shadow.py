from __future__ import annotations

import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone

import pandas as pd

from .data import load_draws_df,load_results_meta
from .shadow import read_shadow_rows
from .wheels import line_price

ROOT=Path(__file__).resolve().parents[1]
ALLOCATION_SHADOW_PATH=ROOT/"data"/"allocation_shadows.jsonl"

ALLOCATION_CONFIG=[
    {"label":"OLD_6_18","n49":6,"n42":18},
    {"label":"BALANCED_8_16","n49":8,"n42":16},
    {"label":"USER_10_11","n49":10,"n42":11},
    {"label":"JACKPOT_14_9","n49":14,"n42":9},
    {"label":"MAX18_4_18","n49":4,"n42":18},
    {"label":"MAX18_12_9","n49":12,"n42":9},
]


def _id(target_draw_no,label):
    return hashlib.sha256(f"{int(target_draw_no)}|{label}|allocation-shadow-v1".encode()).hexdigest()[:20]


def read_allocation_rows():
    if not ALLOCATION_SHADOW_PATH.exists():
        return []
    out=[]
    for line in ALLOCATION_SHADOW_PATH.read_text().splitlines():
        line=line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


def write_allocation_rows(rows):
    ALLOCATION_SHADOW_PATH.write_text(
        "".join(json.dumps(r,separators=(",",":"),sort_keys=True)+"\n" for r in rows)
    )


def build_allocation_batch(target_draw_no,target_date):
    rows=read_shadow_rows()
    g49=[
        r for r in rows
        if int(r.get("target_draw_no",-1))==int(target_draw_no)
        and r.get("game")=="6/49"
        and r.get("mode_id")=="649_k22_22"
        and r.get("conversion_variant")=="production"
        and float(r.get("crowd_strength",0))==0
    ]
    g42=[
        r for r in rows
        if int(r.get("target_draw_no",-1))==int(target_draw_no)
        and r.get("game")=="6/42"
        and r.get("mode_id")=="642_18"
        and float(r.get("crowd_strength",0))==0
    ]
    if not g49 or not g42:
        return []

    r49=g49[0]
    r42=g42[0]
    created=datetime.now(timezone.utc).isoformat()
    out=[]
    for cfg in ALLOCATION_CONFIG:
        n49=int(cfg["n49"]);n42=int(cfg["n42"])
        t49=[list(map(int,t)) for t in r49["tickets"][:n49]]
        t42=[list(map(int,t)) for t in r42["tickets"][:n42]]
        if len(t49)!=n49 or len(t42)!=n42:
            raise RuntimeError(f"Insufficient frozen lines for {cfg['label']}")
        stake=n49*line_price("6/49",int(target_draw_no))+n42*line_price("6/42",int(target_draw_no))
        out.append({
            "allocation_shadow_id":_id(target_draw_no,cfg["label"]),
            "created_at":created,
            "target_draw_no":int(target_draw_no),
            "target_date":str(target_date),
            "label":cfg["label"],
            "n49":n49,
            "n42":n42,
            "tickets_649":t49,
            "tickets_642":t42,
            "pool_649":list(map(int,r49["pool"])),
            "pool_642":list(map(int,r42["pool"])),
            "notional_stake_eur":float(stake),
            "is_shadow":True,
            "actual_money_spent_eur":0.0,
            "source_shadow_649":r49["shadow_id"],
            "source_shadow_642":r42["shadow_id"],
        })
    return out


def append_allocation_batch(target_draw_no,target_date):
    rows=read_allocation_rows()
    existing={r.get("allocation_shadow_id") for r in rows}
    new=[r for r in build_allocation_batch(target_draw_no,target_date)
         if r["allocation_shadow_id"] not in existing]
    if new:
        rows.extend(new)
        rows.sort(key=lambda r:(int(r["target_draw_no"]),str(r["label"])))
        write_allocation_rows(rows)
    return new


def _payout(tickets,actual,meta):
    total=0.0
    for t in tickets:
        h=len(set(map(int,t)) & actual)
        if h<3:
            continue
        val=meta.get(f"payout{h}_eur",0.0)
        if pd.notna(val):
            total += float(val)
    return total


def score_allocation_row(row):
    dn=int(row["target_draw_no"])
    out={**row}
    results={}
    total_payout=0.0
    complete=True
    for game,key in (("6/49","tickets_649"),("6/42","tickets_642")):
        df=load_draws_df(game)
        m=df[pd.to_numeric(df.draw_no,errors="coerce")==dn]
        if m.empty:
            complete=False
            continue
        actual=set(map(int,m.iloc[0][[f"n{i}" for i in range(1,7)]].tolist()))
        hits=[len(set(map(int,t)) & actual) for t in row[key]]
        meta=load_results_meta(game)
        mm=meta[pd.to_numeric(meta.draw_no,errors="coerce")==dn] if not meta.empty else pd.DataFrame()
        payout=None
        if not mm.empty:
            payout=_payout(row[key],actual,mm.iloc[0])
            total_payout += payout
        results[game]={
            "actual":sorted(actual),
            "best":max(hits) if hits else 0,
            "n3plus":sum(h>=3 for h in hits),
            "n4plus":sum(h>=4 for h in hits),
            "n5plus":sum(h>=5 for h in hits),
            "n6":sum(h>=6 for h in hits),
            "payout_eur":payout,
        }
    out["status"]="scored" if complete else "pending"
    out["results"]=results
    if complete:
        out["notional_payout_eur"]=total_payout
        out["notional_net_eur"]=total_payout-float(row["notional_stake_eur"])
        out["notional_roi"]=total_payout/float(row["notional_stake_eur"])-1
    return out


def score_allocation_rows():
    return [score_allocation_row(r) for r in read_allocation_rows()]
