from __future__ import annotations

import numpy as np
import pandas as pd

from .models import _z,fm_score,smooth_score,overdue,flex_pool

N=49
K=22
LAM=.75

VNAME="K22-RZPLUS-LZPROTECT v1"


def _zs(v,index):
    return pd.Series(_z(np.asarray(v,float)),index=index,dtype=float)


def vnext_score_649(history):
    _,d=fm_score(history,N)
    idx=np.arange(1,N+1)

    lz=_zs(d.lz.values,idx)
    rz=_zs(d.rz.values,idx)
    tz=_zs(d.tz.values,idx)
    rp=_zs(d.rp.values,idx)
    dh=_zs(d.dh.values,idx)
    ch=_zs(d.ch.values,idx)

    # Pre-specified challenger:
    # preserve lz at 0.40, modestly increase rz, fund from ch/tz.
    ps=_zs(
        .40*lz.values + .25*rz.values + .15*rp.values + .10*ch.values + .10*dh.values,
        idx,
    )
    mom=_zs(
        .40*rz.values + .20*tz.values + .15*rp.values + .15*dh.values + .10*ch.values,
        idx,
    )
    motif=_zs(d.rp.values+d.dh.values+d.ch.values,idx)
    fm=_zs(.45*ps.values+.35*mom.values+.20*motif.values,idx)
    sm=smooth_score(history,N).astype(float)
    ensemble=_zs(.50*ps.values+.30*fm.values+.20*_z(sm.values),idx)
    prod,gaps=overdue(ensemble,history,N,LAM,20)
    return prod,gaps


def current_pool_649_vnext(history,k=K):
    score,gaps=vnext_score_649(history)
    pool,adds=flex_pool(score,history,k)
    ranks=score.rank(ascending=False,method="first").astype(int)
    pset=set(pool);aset=set(adds)
    diag=pd.DataFrame({
        "number":range(1,N+1),
        "score":[float(score.loc[n]) for n in range(1,N+1)],
        "rank":[int(ranks.loc[n]) for n in range(1,N+1)],
        "gap":[int(gaps[n]) for n in range(1,N+1)],
        "in_pool":[n in pset for n in range(1,N+1)],
        "repeat_addition":[n in aset for n in range(1,N+1)],
    }).sort_values("rank")
    return pool,adds,diag,score
