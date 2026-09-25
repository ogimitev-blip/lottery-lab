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

def outcome_attribution(pool_hits,best_ticket_hits):
    """Decompose the six winning numbers into selection and conversion loss."""
    pool_hits=max(0,min(6,int(pool_hits)))
    best_ticket_hits=max(0,min(pool_hits,int(best_ticket_hits)))
    selection_misses=6-pool_hits
    conversion_misses=pool_hits-best_ticket_hits
    capture_pct=None if pool_hits==0 else 100.0*best_ticket_hits/pool_hits
    return {
        "selection_misses":selection_misses,
        "conversion_misses":conversion_misses,
        "conversion_capture_pct":capture_pct,
        "full_pool_capture":bool(pool_hits>0 and best_ticket_hits==pool_hits),
    }

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
    pool_hits=len(set(map(int,row["pool"])).intersection(actual))
    best_ticket_hits=max(hits) if hits else 0
    attribution=outcome_attribution(pool_hits,best_ticket_hits)
    return {
        **row,
        "status":"scored",
        "actual":sorted(actual),
        "pool_hits":pool_hits,
        "best_ticket_hits":best_ticket_hits,
        **attribution,
        "winning_lines_3plus":sum(1 for h in hits if h>=3),
        "notional_payout_eur":payout,
        "notional_net_eur":None if payout is None else payout-stake,
        "notional_roi":None if payout is None or stake<=0 else payout/stake-1,
    }

def score_all_shadows():
    return [score_shadow(r) for r in read_shadow_rows()]


PROMOTION_MIN_DRAWS=30
PROMOTION_PREFERRED_DRAWS=50

def shadow_pair_frame(scored_rows=None):
    """Build one paired baseline-vs-variant observation per mode and target draw."""
    rows=score_all_shadows() if scored_rows is None else scored_rows
    if not rows:
        return pd.DataFrame()
    df=pd.DataFrame(rows)
    if "status" not in df.columns:
        return pd.DataFrame()
    df=df[df.status=="scored"].copy()
    if df.empty:
        return pd.DataFrame()

    pairs=[]
    for (game,draw_no,mode),g in df.groupby(["game","target_draw_no","mode_id"]):
        base=g[pd.to_numeric(g.crowd_strength,errors="coerce")==0]
        variants=g[pd.to_numeric(g.crowd_strength,errors="coerce")>0]
        if base.empty or variants.empty:
            continue
        b=base.iloc[0]
        for _,v in variants.iterrows():
            bp=b.get("notional_payout_eur")
            vp=v.get("notional_payout_eur")
            payout_delta=None
            if pd.notna(bp) and pd.notna(vp):
                payout_delta=float(vp)-float(bp)
            base_ci=b.get("avg_crowd_index")
            var_ci=v.get("avg_crowd_index")
            crowd_delta=None
            crowd_reduction_pct=None
            if pd.notna(base_ci) and pd.notna(var_ci):
                crowd_delta=float(var_ci)-float(base_ci)
                if float(base_ci)!=0:
                    crowd_reduction_pct=100.0*(float(base_ci)-float(var_ci))/float(base_ci)
            base_best=int(b.get("best_ticket_hits",0) or 0)
            var_best=int(v.get("best_ticket_hits",0) or 0)
            pairs.append({
                "game":game,
                "target_draw_no":int(draw_no),
                "mode_id":mode,
                "variant_label":v.get("label"),
                "crowd_strength":float(v.get("crowd_strength",0.0)),
                "base_best_ticket_hits":base_best,
                "variant_best_ticket_hits":var_best,
                "best_ticket_delta":var_best-base_best,
                "base_3plus":int(base_best>=3),
                "variant_3plus":int(var_best>=3),
                "base_winning_lines_3plus":int(b.get("winning_lines_3plus",0) or 0),
                "variant_winning_lines_3plus":int(v.get("winning_lines_3plus",0) or 0),
                "winning_lines_delta":int(v.get("winning_lines_3plus",0) or 0)-int(b.get("winning_lines_3plus",0) or 0),
                "base_payout_eur":None if pd.isna(bp) else float(bp),
                "variant_payout_eur":None if pd.isna(vp) else float(vp),
                "payout_delta_eur":payout_delta,
                "base_crowd_index":None if pd.isna(base_ci) else float(base_ci),
                "variant_crowd_index":None if pd.isna(var_ci) else float(var_ci),
                "crowd_index_delta":crowd_delta,
                "crowd_reduction_pct":crowd_reduction_pct,
            })
    return pd.DataFrame(pairs)

def summarize_shadow_pairs(scored_rows=None,min_review_draws=PROMOTION_MIN_DRAWS,preferred_draws=PROMOTION_PREFERRED_DRAWS):
    """
    Summarize genuinely prospective paired evidence.

    The gate is intentionally structural, not payout-led:
    - < min_review_draws: ACCUMULATING
    - min_review_draws..preferred_draws-1: INTERIM_REVIEW_ONLY
    - >= preferred_draws: ELIGIBLE_FOR_PROMOTION_REVIEW only when the
      variant reduces crowd exposure and does not degrade paired best-ticket
      hits or 3+ draw frequency. Otherwise HOLD.
    A gate result never changes production automatically.
    """
    pairs=shadow_pair_frame(scored_rows)
    if pairs.empty:
        return pd.DataFrame()

    out=[]
    for (game,mode,strength,label),g in pairs.groupby(["game","mode_id","crowd_strength","variant_label"],dropna=False):
        n=int(len(g))
        base_p3=float(g.base_3plus.mean())
        var_p3=float(g.variant_3plus.mean())
        mean_best_delta=float(g.best_ticket_delta.mean())
        mean_lines_delta=float(g.winning_lines_delta.mean())

        crowd_valid=pd.to_numeric(g.crowd_reduction_pct,errors="coerce").dropna()
        crowd_reduction=float(crowd_valid.mean()) if len(crowd_valid) else None

        payout_delta_series=pd.to_numeric(g.payout_delta_eur,errors="coerce").dropna()
        payout_delta=float(payout_delta_series.sum()) if len(payout_delta_series) else None

        if n < int(min_review_draws):
            gate="ACCUMULATING"
        elif n < int(preferred_draws):
            gate="INTERIM_REVIEW_ONLY"
        else:
            structure_ok=(
                crowd_reduction is not None and crowd_reduction>0
                and mean_best_delta>=0
                and (var_p3-base_p3)>=0
            )
            gate="ELIGIBLE_FOR_PROMOTION_REVIEW" if structure_ok else "HOLD"

        out.append({
            "game":game,
            "mode_id":mode,
            "variant_label":label,
            "crowd_strength":float(strength),
            "prospective_draws":n,
            "sample_gate":gate,
            "draws_to_min_review":max(0,int(min_review_draws)-n),
            "draws_to_preferred":max(0,int(preferred_draws)-n),
            "avg_crowd_reduction_pct":crowd_reduction,
            "base_3plus_rate_pct":100.0*base_p3,
            "variant_3plus_rate_pct":100.0*var_p3,
            "delta_3plus_pp":100.0*(var_p3-base_p3),
            "mean_best_ticket_hit_delta":mean_best_delta,
            "mean_winning_lines_delta":mean_lines_delta,
            "cumulative_payout_delta_eur":payout_delta,
        })
    return pd.DataFrame(out).sort_values(["game","mode_id","crowd_strength"]).reset_index(drop=True)


def _wilson_interval(successes,total,z=1.959963984540054):
    """95% Wilson score interval for a binomial proportion."""
    total=int(total)
    successes=int(successes)
    if total<=0:
        return (None,None)
    p=successes/total
    z2=z*z
    den=1.0+z2/total
    center=(p+z2/(2.0*total))/den
    half=(z*((p*(1.0-p)/total+z2/(4.0*total*total))**0.5))/den
    return (max(0.0,center-half),min(1.0,center+half))

def shadow_research_scoreboard(scored_rows=None):
    """
    Descriptive paired prospective scoreboard. It never ranks or promotes variants.

    Main stability measure is the share of draws where the variant does not
    reduce best-ticket hits versus its same-draw baseline, with a Wilson 95% CI.
    """
    pairs=shadow_pair_frame(scored_rows)
    if pairs.empty:
        return pd.DataFrame()

    out=[]
    for (game,mode,strength,label),g in pairs.groupby(
        ["game","mode_id","crowd_strength","variant_label"],dropna=False
    ):
        n=int(len(g))
        best=pd.to_numeric(g.best_ticket_delta,errors="coerce").dropna()
        wins=int((best>0).sum())
        ties=int((best==0).sum())
        losses=int((best<0).sum())
        nondeg=int((best>=0).sum())
        lo,hi=_wilson_interval(nondeg,len(best))

        p3_gain=int(((g.base_3plus==0)&(g.variant_3plus==1)).sum())
        p3_loss=int(((g.base_3plus==1)&(g.variant_3plus==0)).sum())
        p3_same=n-p3_gain-p3_loss

        crowd=pd.to_numeric(g.crowd_reduction_pct,errors="coerce").dropna()
        crowd_positive=int((crowd>0).sum()) if len(crowd) else 0

        payout=pd.to_numeric(g.payout_delta_eur,errors="coerce").dropna()
        payout_up=int((payout>0).sum()) if len(payout) else 0
        payout_down=int((payout<0).sum()) if len(payout) else 0

        if n<10:
            maturity="VERY_EARLY"
        elif n<PROMOTION_MIN_DRAWS:
            maturity="EARLY"
        elif n<PROMOTION_PREFERRED_DRAWS:
            maturity="INTERIM"
        else:
            maturity="MATURE_REVIEW_SAMPLE"

        out.append({
            "game":game,
            "mode_id":mode,
            "variant_label":label,
            "crowd_strength":float(strength),
            "prospective_draws":n,
            "evidence_maturity":maturity,
            "best_hit_wins":wins,
            "best_hit_ties":ties,
            "best_hit_losses":losses,
            "best_hit_net":wins-losses,
            "nondegradation_rate_pct":100.0*nondeg/len(best) if len(best) else None,
            "nondegradation_ci95_lo_pct":None if lo is None else 100.0*lo,
            "nondegradation_ci95_hi_pct":None if hi is None else 100.0*hi,
            "p3_gains":p3_gain,
            "p3_same":p3_same,
            "p3_losses":p3_loss,
            "p3_net":p3_gain-p3_loss,
            "crowd_reduction_positive_draws":crowd_positive,
            "crowd_reduction_positive_pct":100.0*crowd_positive/len(crowd) if len(crowd) else None,
            "avg_crowd_reduction_pct":float(crowd.mean()) if len(crowd) else None,
            "median_crowd_reduction_pct":float(crowd.median()) if len(crowd) else None,
            "payout_up_draws":payout_up,
            "payout_down_draws":payout_down,
            "cumulative_payout_delta_eur":float(payout.sum()) if len(payout) else None,
        })
    return pd.DataFrame(out).sort_values(
        ["game","mode_id","crowd_strength"]
    ).reset_index(drop=True)


def shadow_cycle_health(scored_rows=None):
    """Report whether each game's next complete prospective batch is frozen in time."""
    rows=score_all_shadows() if scored_rows is None else scored_rows
    if not rows:
        return pd.DataFrame()
    df=pd.DataFrame(rows)
    out=[]
    for game in sorted(df.game.dropna().unique()):
        g=df[df.game==game].copy()
        scored=g[g.status=="scored"] if "status" in g.columns else pd.DataFrame()
        pending=g[g.status=="pending"] if "status" in g.columns else pd.DataFrame()
        latest_scored=int(pd.to_numeric(scored.target_draw_no,errors="coerce").max()) if len(scored) else None

        if latest_scored is not None:
            pending=pending[pd.to_numeric(pending.target_draw_no,errors="coerce")>latest_scored]
        if pending.empty:
            out.append({
                "game":game,
                "latest_scored_draw":latest_scored,
                "next_shadow_draw":None,
                "target_date":None,
                "frozen_variants":0,
                "expected_variants":sum(1 for x in SHADOW_CONFIG if x["game"]==game),
                "freeze_before_target":False,
                "cycle_status":"NO_FUTURE_BATCH",
            })
            continue

        next_draw=int(pd.to_numeric(pending.target_draw_no,errors="coerce").min())
        batch=pending[pd.to_numeric(pending.target_draw_no,errors="coerce")==next_draw].copy()
        expected=sum(1 for x in SHADOW_CONFIG if x["game"]==game)
        frozen=int(batch.shadow_id.nunique()) if "shadow_id" in batch.columns else len(batch)
        target_date=str(batch.target_date.iloc[0]) if "target_date" in batch.columns and len(batch) else None

        created=pd.to_datetime(batch.created_at,errors="coerce",utc=True) if "created_at" in batch.columns else pd.Series(dtype="datetime64[ns, UTC]")
        target=pd.to_datetime(target_date,errors="coerce",utc=True) if target_date else pd.NaT
        before=False
        if len(created) and created.notna().all() and pd.notna(target):
            before=bool((created < target).all())

        complete=frozen==expected
        if complete and before:
            status="READY"
        elif not complete:
            status="INCOMPLETE_BATCH"
        else:
            status="LATE_FREEZE"

        out.append({
            "game":game,
            "latest_scored_draw":latest_scored,
            "next_shadow_draw":next_draw,
            "target_date":target_date,
            "frozen_variants":frozen,
            "expected_variants":expected,
            "freeze_before_target":before,
            "cycle_status":status,
        })
    return pd.DataFrame(out)
