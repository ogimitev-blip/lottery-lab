from __future__ import annotations

import json
import pandas as pd

from lottery.data import load_draws_df,load_research_archive
from lottery.models import current_pool_649
from lottery.k22_vnext import current_pool_649_vnext,VNAME
from lottery.wheels import build_broad_six,extend_sequence

MIN_HISTORY=100
SIZES=(6,10,11,22)
SEED=20260917+490000


def sequence(pool,score,maxn=22):
    base=build_broad_six(pool,score,649)
    return extend_sequence(base,pool,score,maxn,SEED)


def metrics(tickets,actual):
    a=set(actual)
    h=[len(set(t)&a) for t in tickets]
    return {
        "best":max(h),
        "n3":sum(x>=3 for x in h),
        "n4":sum(x>=4 for x in h),
        "n5":sum(x>=5 for x in h),
        "n6":sum(x>=6 for x in h),
    }


def evaluate(draws,max_targets,label):
    n=min(max_targets,len(draws)-MIN_HISTORY)
    rows=[]
    for i in range(n):
        actual=draws[i]
        hist=draws[i+1:]
        bp,ba,bd,bs=current_pool_649(hist,22)
        cp,ca,cd,cs=current_pool_649_vnext(hist,22)
        bph=len(set(bp)&set(actual))
        cph=len(set(cp)&set(actual))
        bseq=sequence(bp,bs,22)
        cseq=sequence(cp,cs,22)
        for size in SIZES:
            bm=metrics(bseq[:size],actual)
            cm=metrics(cseq[:size],actual)
            rows.append({
                "dataset":label,"target":i,"size":size,
                "pool_hits_base":bph,"pool_hits_cand":cph,
                "pool_delta":cph-bph,
                "pool_overlap":len(set(bp)&set(cp)),
                "best_base":bm["best"],"best_cand":cm["best"],
                "best_delta":cm["best"]-bm["best"],
                "n3_base":bm["n3"],"n3_cand":cm["n3"],
                "n4_base":bm["n4"],"n4_cand":cm["n4"],
                "n5_base":bm["n5"],"n5_cand":cm["n5"],
                "n6_base":bm["n6"],"n6_cand":cm["n6"],
            })
    return pd.DataFrame(rows)


def summarize(df):
    out={}
    g=df[df["size"]==min(SIZES)]
    out["pool"]={
        "draws":int(len(g)),
        "mean_hits_base":float(g.pool_hits_base.mean()),
        "mean_hits_cand":float(g.pool_hits_cand.mean()),
        "p4plus_base":float((g.pool_hits_base>=4).mean()),
        "p4plus_cand":float((g.pool_hits_cand>=4).mean()),
        "p5plus_base":float((g.pool_hits_base>=5).mean()),
        "p5plus_cand":float((g.pool_hits_cand>=5).mean()),
        "p6_base":float((g.pool_hits_base>=6).mean()),
        "p6_cand":float((g.pool_hits_cand>=6).mean()),
        "wins":int((g.pool_delta>0).sum()),
        "ties":int((g.pool_delta==0).sum()),
        "losses":int((g.pool_delta<0).sum()),
        "mean_delta":float(g.pool_delta.mean()),
        "mean_pool_overlap":float(g.pool_overlap.mean()),
        "on_base_5plus":{
            "draws":int((g.pool_hits_base>=5).sum()),
            "mean_delta":float(g.loc[g.pool_hits_base>=5,"pool_delta"].mean()) if (g.pool_hits_base>=5).any() else None,
            "wins":int(((g.pool_hits_base>=5)&(g.pool_delta>0)).sum()),
            "losses":int(((g.pool_hits_base>=5)&(g.pool_delta<0)).sum()),
        },
    }
    for size in SIZES:
        s=df[df["size"]==size]
        out[str(size)]={
            "draws":int(len(s)),
            "mean_best_base":float(s.best_base.mean()),
            "mean_best_cand":float(s.best_cand.mean()),
            "p3plus_base":float((s.best_base>=3).mean()),
            "p3plus_cand":float((s.best_cand>=3).mean()),
            "p4plus_base":float((s.best_base>=4).mean()),
            "p4plus_cand":float((s.best_cand>=4).mean()),
            "p5plus_base":float((s.best_base>=5).mean()),
            "p5plus_cand":float((s.best_cand>=5).mean()),
            "p6_base":float((s.best_base>=6).mean()),
            "p6_cand":float((s.best_cand>=6).mean()),
            "wins":int((s.best_delta>0).sum()),
            "ties":int((s.best_delta==0).sum()),
            "losses":int((s.best_delta<0).sum()),
            "mean_delta":float(s.best_delta.mean()),
            "mean_n3_delta":float((s.n3_cand-s.n3_base).mean()),
            "mean_n4_delta":float((s.n4_cand-s.n4_base).mean()),
        }
    return out


def exact_76_78(current):
    df=load_draws_df("6/49")
    nums=pd.to_numeric(df.draw_no,errors="coerce").tolist()
    out={}
    for dn in (76,77,78):
        if dn not in nums: continue
        i=nums.index(dn);actual=current[i];hist=current[i+1:]
        bp,_,_,bs=current_pool_649(hist,22)
        cp,_,_,cs=current_pool_649_vnext(hist,22)
        bseq=sequence(bp,bs,22);cseq=sequence(cp,cs,22)
        out[str(dn)]={
            "actual":sorted(actual),
            "pool_base":bp,"pool_cand":cp,
            "pool_hits_base":len(set(bp)&set(actual)),
            "pool_hits_cand":len(set(cp)&set(actual)),
            "lines10_base":metrics(bseq[:10],actual),
            "lines10_cand":metrics(cseq[:10],actual),
        }
    return out


def main():
    cur=load_draws_df("6/49")
    cols=[f"n{i}" for i in range(1,7)]
    current=[list(map(int,r)) for r in cur[cols].to_numpy().tolist()]
    _,archive=load_research_archive("6/49")

    c=evaluate(current,150,"current150")
    a=evaluate(archive,300,"archive300")
    latest=c[c.target<50].copy()
    prior=c[(c.target>=50)&(c.target<150)].copy()

    result={
        "challenger":VNAME,
        "design":{
            "PS":"lz .40 unchanged; rz .20→.25; ch .15→.10; rp .15; dh .10",
            "Momentum":"rz .35→.40; tz .25→.20; rp .15; dh .15; ch .10",
            "unchanged":"FM/ensemble outer weights, smooth, overdue λ=.75, flex/repeat overlay, wheel algorithm",
            "no_grid_search":True,
        },
        "current150":summarize(c),
        "latest50":summarize(latest),
        "prior100":summarize(prior),
        "archive300":summarize(a),
        "prospective_76_78":exact_76_78(current),
        "shadow_safety_rule":"Eligible for prospective shadow if archive300 pool p5+/p6 are not below production and current150 does not show material tail degradation. Shadow status never promotes production."
    }
    print("K22_VNEXT_BEGIN")
    print(json.dumps(result,indent=2))
    print("K22_VNEXT_END")


if __name__=="__main__":
    main()
