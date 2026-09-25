import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone

import pandas as pd

from .crowd import latest_crowd_snapshot,constrained_anti_crowd_remap,score_ticket_frame
from .data import load_draws_df,load_results_meta
from .modes import generate_mode
from .version import APP_VERSION,MODEL_642,MODEL_649

ROOT=Path(__file__).resolve().parents[1]
SHADOW_PATH=ROOT/"data"/"shadow_experiments.jsonl"

SHADOW_CONFIG=[
    {"game":"6/49","mode_id":"649_k22_4","strength":0.00,"label":"K22-4 base"},
    {"game":"6/49","mode_id":"649_k22_4","strength":0.10,"label":"K22-4 crowd 10%"},
    {"game":"6/49","mode_id":"649_k22_6","strength":0.00,"label":"K22-6 base"},
    {"game":"6/49","mode_id":"649_k22_6","strength":0.30,"label":"K22-6 crowd 30%"},
    {"game":"6/42","mode_id":"642_18","strength":0.00,"label":"K28-18 base"},
    {"game":"6/42","mode_id":"642_18","strength":0.10,"label":"K28-18 crowd 10%"},
    {"game":"6/42","mode_id":"642_30","strength":0.00,"label":"K28-30 base"},
    {"game":"6/42","mode_id":"642_30","strength":0.10,"label":"K28-30 crowd 10%"},
    {"game":"6/42","mode_id":"642_50","strength":0.00,"label":"K28-50 base"},
    {"game":"6/42","mode_id":"642_50","strength":0.10,"label":"K28-50 crowd 10%"},
]

def _model_version(game):
    return MODEL_642 if game=="6/42" else MODEL_649

def _shadow_id(game,target_draw_no,mode_id,strength):
    raw=f"{game}|{int(target_draw_no)}|{mode_id}|{float(strength):.4f}|{_model_version(game)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]

def read_shadow_rows():
    if not SHADOW_PATH.exists():
        return []
    rows=[]
    for line in SHADOW_PATH.read_text().splitlines():
        line=line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows

def write_shadow_rows(rows):
    text="".join(json.dumps(r,separators=(",",":"),sort_keys=True)+"\n" for r in rows)
    SHADOW_PATH.write_text(text)

def build_shadow_batch(game,target,draws):
    crowd=latest_crowd_snapshot(game)
    created=datetime.now(timezone.utc).isoformat()
    out=[]
    for cfg in [x for x in SHADOW_CONFIG if x["game"]==game]:
        state=generate_mode(game,cfg["mode_id"],draws,target["draw_no"])
        base=list(state["tickets"])
        strength=float(cfg["strength"])
        tickets=base
        meta=None
        if strength>0:
            if crowd.empty:
                continue
            tickets,_,meta=constrained_anti_crowd_remap(
                state["pool"],base,crowd,state["diagnostics"],strength
            )
        crowd_index=None
        snapshot_draw=None
        snapshot_date=None
        if not crowd.empty:
            crowd_index=float(score_ticket_frame(tickets,crowd).crowd_index.mean())
            snapshot_draw=int(crowd.iloc[0].snapshot_draw)
            snapshot_date=str(crowd.iloc[0].snapshot_date)

        out.append({
            "shadow_id":_shadow_id(game,target["draw_no"],cfg["mode_id"],strength),
            "created_at":created,
            "game":game,
            "target_draw_no":int(target["draw_no"]),
            "target_date":target["date"],
            "label":cfg["label"],
            "mode_id":cfg["mode_id"],
            "crowd_strength":strength,
            "model_version":_model_version(game),
            "app_version":APP_VERSION,
            "pool":list(map(int,state["pool"])),
            "repeat_additions":list(map(int,state["additions"])),
            "tickets":[list(map(int,t)) for t in tickets],
            "notional_stake_eur":float(state["cost"]),
            "crowd_snapshot_draw":snapshot_draw,
            "crowd_snapshot_date":snapshot_date,
            "avg_crowd_index":crowd_index,
            "optimizer_swaps":0 if meta is None else int(meta.attrs.get("swaps",0)),
            "is_shadow":True,
            "actual_money_spent_eur":0.0,
        })
    return out

def append_shadow_batch(game,target,draws):
    rows=read_shadow_rows()
    existing={r.get("shadow_id") for r in rows}
    new=[r for r in build_shadow_batch(game,target,draws) if r["shadow_id"] not in existing]
    if new:
        rows.extend(new)
        rows.sort(key=lambda r:(int(r["target_draw_no"]),r["game"],r["mode_id"],float(r["crowd_strength"])))
        write_shadow_rows(rows)
    return new

def score_shadow(row):
    game=row["game"]
    df=load_draws_df(game)
    cols=[f"n{i}" for i in range(1,7)]
    m=df[pd.to_numeric(df.draw_no,errors="coerce")==int(row["target_draw_no"])]
    if m.empty:
        return {**row,"status":"pending"}

    actual=set(map(int,m.iloc[0][cols].tolist()))
    hits=[len(set(map(int,t)).intersection(actual)) for t in row["tickets"]]
    payout=None
    meta=load_results_meta(game)
    mm=meta[pd.to_numeric(meta.draw_no,errors="coerce")==int(row["target_draw_no"])] if not meta.empty else pd.DataFrame()
    if not mm.empty:
        r=mm.iloc[0]
        payout=0.0
        for h in hits:
            if h<3:
                continue
            val=r.get(f"payout{h}_eur",0.0)
            if pd.notna(val):
                payout+=float(val)

    stake=float(row["notional_stake_eur"])
    return {
        **row,
        "status":"scored",
        "actual":sorted(actual),
        "pool_hits":len(set(map(int,row["pool"])).intersection(actual)),
        "best_ticket_hits":max(hits) if hits else 0,
        "winning_lines_3plus":sum(1 for h in hits if h>=3),
        "notional_payout_eur":payout,
        "notional_net_eur":None if payout is None else payout-stake,
        "notional_roi":None if payout is None or stake<=0 else payout/stake-1,
    }

def score_all_shadows():
    return [score_shadow(r) for r in read_shadow_rows()]
