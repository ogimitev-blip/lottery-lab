from __future__ import annotations

import json
import numpy as np
import pandas as pd

from lottery.data import load_draws_df,load_research_archive
from lottery.models import _z,fm_score,smooth_score,overdue,flex_pool

N=49
K=22
LAM=.75
MIN_HISTORY=100
CURRENT_TARGETS=150
ARCHIVE_TARGETS=300
FEATURES=("rz","lz","tz","rp","dh","ch")

PS_WEIGHTS={"lz":.40,"rz":.20,"rp":.15,"ch":.15,"dh":.10}
MOM_WEIGHTS={"rz":.35,"tz":.25,"rp":.15,"dh":.15,"ch":.10}
FM_WEIGHTS={"ps":.45,"mom":.35,"motif":.20}
ENSEMBLE_WEIGHTS={"ps":.50,"fm":.30,"smooth":.20}


def zseries(v,index):
    return pd.Series(_z(np.asarray(v,float)),index=index,dtype=float)


def weighted_z(parts,weights,index):
    active=[k for k in weights if k in parts]
    den=sum(weights[k] for k in active)
    vals=np.zeros(len(index),dtype=float)
    for k in active:
        vals += (weights[k]/den)*_z(parts[k].values)
    return zseries(vals,index)


def hierarchy(history,drop=None):
    # fm_score gives the exact raw diagnostic columns used by production.
    _,d=fm_score(history,N)
    idx=np.arange(1,N+1)
    raw={k:pd.Series(d[k].astype(float).values,index=idx,dtype=float) for k in FEATURES}

    # Drop the raw feature wherever it participates in the hierarchy.
    active={k:v for k,v in raw.items() if k!=drop}

    ps_parts={k:active[k] for k in PS_WEIGHTS if k in active}
    ps=weighted_z(ps_parts,{k:PS_WEIGHTS[k] for k in ps_parts},idx)

    mom_parts={k:active[k] for k in MOM_WEIGHTS if k in active}
    mom=weighted_z(mom_parts,{k:MOM_WEIGHTS[k] for k in mom_parts},idx)

    motif_cols=[k for k in ("rp","dh","ch") if k in active]
    if motif_cols:
        motif_raw=sum((active[k] for k in motif_cols),start=pd.Series(0.0,index=idx))
        motif=zseries(motif_raw.values,idx)
    else:
        motif=pd.Series(np.zeros(N),index=idx,dtype=float)

    fm_vals=(
        FM_WEIGHTS["ps"]*_z(ps.values)
        +FM_WEIGHTS["mom"]*_z(mom.values)
        +FM_WEIGHTS["motif"]*_z(motif.values)
    )
    fm=zseries(fm_vals,idx)

    sm=smooth_score(history,N).astype(float)
    ensemble_vals=(
        ENSEMBLE_WEIGHTS["ps"]*_z(ps.values)
        +ENSEMBLE_WEIGHTS["fm"]*_z(fm.values)
        +ENSEMBLE_WEIGHTS["smooth"]*_z(sm.values)
    )
    ensemble=zseries(ensemble_vals,idx)
    production,gaps=overdue(ensemble,history,N,LAM,20)
    pool,adds=flex_pool(production,history,K)

    return {
        "pool":list(map(int,pool)),
        "additions":list(map(int,adds)),
        "production":production.astype(float),
        "ensemble":ensemble,
        "ps":ps,
        "mom":mom,
        "motif":motif,
        "fm":fm,
        "smooth":sm,
        "raw":raw,
    }


def topk(score):
    return [int(n) for n in score.sort_values(ascending=False).index[:K]]


def auc_like(score,actual):
    winners=set(actual)
    win=[float(score.loc[n]) for n in winners]
    lose=[float(score.loc[n]) for n in range(1,N+1) if n not in winners]
    better=ties=0
    for a in win:
        for b in lose:
            if a>b: better+=1
            elif a==b: ties+=1
    return (better+0.5*ties)/(len(win)*len(lose))


def eval_dataset(draws,max_targets,label):
    n=min(max_targets,len(draws)-MIN_HISTORY)
    rows=[]
    standalone=[]
    details=[]

    for i in range(n):
        actual=list(map(int,draws[i]))
        aset=set(actual)
        hist=draws[i+1:]

        base=hierarchy(hist,None)
        base_hits=len(set(base["pool"])&aset)

        variants={"full":base}
        for feat in FEATURES:
            variants[f"drop_{feat}"]=hierarchy(hist,feat)

        for name,v in variants.items():
            h=len(set(v["pool"])&aset)
            rows.append({
                "dataset":label,
                "target":i,
                "variant":name,
                "hits":h,
                "delta_vs_full":h-base_hits,
                "full_hits":base_hits,
                "pool_overlap_with_full":len(set(v["pool"])&set(base["pool"])),
                "repeat_additions":len(v["additions"]),
            })

        for feat in FEATURES:
            score=zseries(base["raw"][feat].values,np.arange(1,N+1))
            p=topk(score)
            standalone.append({
                "dataset":label,
                "target":i,
                "feature":feat,
                "top22_hits":len(set(p)&aset),
                "auc":auc_like(score,actual),
                "mean_winner_rank":float(score.rank(ascending=False,method="average")[actual].mean()),
            })

        if base_hits>=4:
            item={
                "target":i,
                "actual":sorted(actual),
                "full_hits":base_hits,
                "repeat_additions":base["additions"],
                "drops":{},
                "winner_ranks":{},
            }
            for feat in FEATURES:
                item["drops"][feat]=len(set(variants[f"drop_{feat}"]["pool"])&aset)
                rr=zseries(base["raw"][feat].values,np.arange(1,N+1)).rank(
                    ascending=False,method="average"
                )
                item["winner_ranks"][feat]={str(x):float(rr.loc[x]) for x in sorted(actual)}
            details.append(item)

    return pd.DataFrame(rows),pd.DataFrame(standalone),details


def summarize_ablation(df):
    out={}
    for name,g in df.groupby("variant"):
        g=g.sort_values("target")
        full4=g.full_hits>=4
        full5=g.full_hits>=5
        out[name]={
            "draws":int(len(g)),
            "mean_hits":float(g.hits.mean()),
            "p4plus":float((g.hits>=4).mean()),
            "p5plus":float((g.hits>=5).mean()),
            "p6":float((g.hits>=6).mean()),
            "wins_vs_full":int((g.delta_vs_full>0).sum()),
            "ties_vs_full":int((g.delta_vs_full==0).sum()),
            "losses_vs_full":int((g.delta_vs_full<0).sum()),
            "mean_delta_vs_full":float(g.delta_vs_full.mean()),
            "mean_pool_overlap_with_full":float(g.pool_overlap_with_full.mean()),
            "on_full_4plus":{
                "draws":int(full4.sum()),
                "mean_delta":None if not full4.any() else float(g.loc[full4,"delta_vs_full"].mean()),
                "wins":int((full4&(g.delta_vs_full>0)).sum()),
                "losses":int((full4&(g.delta_vs_full<0)).sum()),
            },
            "on_full_5plus":{
                "draws":int(full5.sum()),
                "mean_delta":None if not full5.any() else float(g.loc[full5,"delta_vs_full"].mean()),
                "wins":int((full5&(g.delta_vs_full>0)).sum()),
                "losses":int((full5&(g.delta_vs_full<0)).sum()),
            },
        }
    return out


def summarize_standalone(df):
    random_expected=K*6/N
    out={}
    for feat,g in df.groupby("feature"):
        out[feat]={
            "draws":int(len(g)),
            "mean_top22_hits":float(g.top22_hits.mean()),
            "lift_vs_random_hits":float(g.top22_hits.mean()-random_expected),
            "p4plus":float((g.top22_hits>=4).mean()),
            "p5plus":float((g.top22_hits>=5).mean()),
            "p6":float((g.top22_hits>=6).mean()),
            "mean_auc":float(g.auc.mean()),
            "mean_winner_rank":float(g.mean_winner_rank.mean()),
        }
    return {"random_expected_hits":random_expected,"features":out}


def exact_draws(current):
    df=load_draws_df("6/49")
    nums=pd.to_numeric(df.draw_no,errors="coerce").tolist()
    out={}
    for dn in (76,77,78):
        if dn not in nums:
            continue
        i=nums.index(dn)
        actual=current[i]
        aset=set(actual)
        hist=current[i+1:]
        base=hierarchy(hist,None)
        rec={
            "actual":sorted(actual),
            "full_hits":len(set(base["pool"])&aset),
            "repeat_additions":base["additions"],
            "drop_hits":{},
            "raw_winner_ranks":{},
        }
        for feat in FEATURES:
            cand=hierarchy(hist,feat)
            rec["drop_hits"][feat]=len(set(cand["pool"])&aset)
            rr=zseries(base["raw"][feat].values,np.arange(1,N+1)).rank(
                ascending=False,method="average"
            )
            rec["raw_winner_ranks"][feat]={str(x):float(rr.loc[x]) for x in sorted(actual)}
        out[str(dn)]=rec
    return out


def main():
    cur=load_draws_df("6/49")
    cols=[f"n{i}" for i in range(1,7)]
    current=[list(map(int,r)) for r in cur[cols].to_numpy().tolist()]
    _,archive=load_research_archive("6/49")

    cp,cs,cd=eval_dataset(current,CURRENT_TARGETS,"current150")
    ap,ass,ad=eval_dataset(archive,ARCHIVE_TARGETS,"archive300")

    result={
        "method":{
            "features":{
                "rz":"recent-rate z-score",
                "lz":"long-window rate z-score",
                "tz":"recent-vs-older trend z-score",
                "rp":"repeat persistence across adjacent draws",
                "dh":"directional adjacency across adjacent draws",
                "ch":"same-draw adjacency/clustering",
            },
            "ablation":"Remove one raw feature wherever it enters PS/momentum/motif, renormalize surviving internal weights, then rebuild full ensemble + overdue + flex K22.",
            "current_targets":int(cp.target.nunique()),
            "archive_targets":int(ap.target.nunique()),
            "outcome_blind":True,
        },
        "current150":{
            "ablation":summarize_ablation(cp),
            "standalone":summarize_standalone(cs),
        },
        "latest50":{
            "ablation":summarize_ablation(cp[cp.target<50].copy()),
            "standalone":summarize_standalone(cs[cs.target<50].copy()),
        },
        "prior100":{
            "ablation":summarize_ablation(cp[(cp.target>=50)&(cp.target<150)].copy()),
            "standalone":summarize_standalone(cs[(cs.target>=50)&(cs.target<150)].copy()),
        },
        "archive300":{
            "ablation":summarize_ablation(ap),
            "standalone":summarize_standalone(ass),
        },
        "prospective_76_78":exact_draws(current),
        "high_hit_examples":{
            "current_count":len(cd),
            "archive_count":len(ad),
            "current_first20":cd[:20],
        },
        "note":"Raw-feature ablations are diagnostic. Small changes in rare 5+/6+ counts should not be optimized without prospective confirmation."
    }
    print("K22_FM_RAW_ATTR_BEGIN")
    print(json.dumps(result,indent=2))
    print("K22_FM_RAW_ATTR_END")


if __name__=="__main__":
    main()
