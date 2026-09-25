import numpy as np
import pandas as pd

from .modes import generate_mode
from .crowd import constrained_anti_crowd_remap
from .wheels import line_price


def _ticket_hits(tickets, actual):
    aset=set(map(int,actual))
    return [len(set(map(int,t)).intersection(aset)) for t in tickets]


def _ticket_payout(hits, meta_row):
    total=0.0
    by_tier={3:0.0,4:0.0,5:0.0,6:0.0}
    counts={3:0,4:0,5:0,6:0}
    for h in hits:
        if h<3:
            continue
        counts[h]+=1
        if h==6:
            published=meta_row.get("payout6_eur",0.0)
            winners=meta_row.get("winners6",0)
            if pd.notna(published) and float(published)>0:
                val=float(published)
            elif pd.notna(winners) and int(winners)==0 and pd.notna(meta_row.get("jackpot_eur")):
                # Counterfactual: if our historical ticket alone had hit 6/6
                # on a draw where BST reported no jackpot winner.
                val=float(meta_row["jackpot_eur"])
            else:
                val=0.0
        else:
            val=meta_row.get(f"payout{h}_eur",0.0)
            val=float(val) if pd.notna(val) else 0.0
        total+=val
        by_tier[h]+=val
    return total,counts,by_tier


def _reference_payouts(meta):
    refs={}
    for h in (3,4,5):
        vals=pd.to_numeric(meta[f"payout{h}_eur"],errors="coerce")
        vals=vals[vals>0]
        refs[h]=float(vals.median()) if len(vals) else 0.0
    return refs


def _normalized_payout(hits, refs):
    return sum(refs.get(int(h),0.0) for h in hits if int(h) in refs)


def payout_backtest(
    game,
    mode_id,
    draws,
    results_meta,
    latest_draw_no,
    crowd_snapshot=None,
    strengths=(0.0,),
    min_history=50,
):
    """Walk-forward payout backtest over draws for which verified BST payout
    metadata exists. Crowd variants use one supplied fixed crowd snapshot.
    """
    meta=results_meta.copy()
    if meta.empty:
        return pd.DataFrame()
    meta["draw_no"]=pd.to_numeric(meta["draw_no"],errors="coerce")
    meta=meta.dropna(subset=["draw_no"]).copy()
    meta["draw_no"]=meta["draw_no"].astype(int)
    meta_idx=meta.set_index("draw_no")
    refs=_reference_payouts(meta)

    rows=[]
    limit=max(0,len(draws)-int(min_history))
    for i in range(limit):
        draw_no=int(latest_draw_no)-i
        if draw_no not in meta_idx.index:
            continue
        actual=draws[i]
        hist=draws[i+1:]
        mrow=meta_idx.loc[draw_no]
        if isinstance(mrow,pd.DataFrame):
            mrow=mrow.iloc[0]

        state=generate_mode(game,mode_id,hist,draw_no)
        base=list(state["tickets"])
        variants={0.0:base}
        for strength in strengths:
            strength=float(strength)
            if strength<=0:
                continue
            if crowd_snapshot is None or crowd_snapshot.empty:
                continue
            tickets,_,_=constrained_anti_crowd_remap(
                state["pool"],base,crowd_snapshot,state["diagnostics"],strength
            )
            variants[strength]=tickets

        for strength,tickets in variants.items():
            hits=_ticket_hits(tickets,actual)
            payout,counts,by_tier=_ticket_payout(hits,mrow)
            normalized=_normalized_payout(hits,refs)
            stake=float(state["cost"])
            rows.append({
                "game":game,
                "mode_id":mode_id,
                "draw_no":draw_no,
                "date":mrow.get("date"),
                "strength":float(strength),
                "lines":len(tickets),
                "stake_eur":stake,
                "payout_eur":payout,
                "net_eur":payout-stake,
                "roi":payout/stake-1 if stake else np.nan,
                "normalized_payout_eur":normalized,
                "sharing_timing_eur":payout-normalized,
                "best_hits":max(hits) if hits else 0,
                "n3":counts[3],
                "n4":counts[4],
                "n5":counts[5],
                "n6":counts[6],
                "payout3_eur":by_tier[3],
                "payout4_eur":by_tier[4],
                "payout5_eur":by_tier[5],
                "payout6_eur":by_tier[6],
            })

    return pd.DataFrame(rows)


def summarize_payout_backtest(bt):
    if bt.empty:
        return pd.DataFrame()

    rows=[]
    for strength,g in bt.groupby("strength"):
        stake=float(g.stake_eur.sum())
        payout=float(g.payout_eur.sum())
        normalized=float(g.normalized_payout_eur.sum())
        rows.append({
            "strength":float(strength),
            "draws":len(g),
            "stake_eur":stake,
            "payout_eur":payout,
            "net_eur":payout-stake,
            "roi":payout/stake-1 if stake else np.nan,
            "winning_draws":int((g.payout_eur>0).sum()),
            "payout3_eur":float(g.payout3_eur.sum()),
            "payout4_eur":float(g.payout4_eur.sum()),
            "payout5_eur":float(g.payout5_eur.sum()),
            "payout6_eur":float(g.payout6_eur.sum()),
            "normalized_payout_eur":normalized,
            "sharing_timing_eur":float(g.sharing_timing_eur.sum()),
            "mean_best_hits":float(g.best_hits.mean()),
        })

    out=pd.DataFrame(rows).sort_values("strength").reset_index(drop=True)
    if len(out):
        base=out.iloc[0]
        out["payout_change_vs_base_eur"]=out.payout_eur-float(base.payout_eur)
        out["normalized_change_vs_base_eur"]=out.normalized_payout_eur-float(base.normalized_payout_eur)
        out["sharing_timing_change_vs_base_eur"]=out.sharing_timing_eur-float(base.sharing_timing_eur)
    return out
