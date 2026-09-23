import numpy as np
import pandas as pd

def _z(v):
    a=np.asarray(v,float); s=a.std()
    return np.zeros_like(a) if s<1e-12 else (a-a.mean())/s

def smooth_score(history,n_numbers=42):
    cl=[set(map(int,d)) for d in history]; vals=[]
    for n in range(1,n_numbers+1):
        b=0.0
        for win,w in [(20,.25),(50,.30),(100,.30),(len(cl),.15)]:
            ew=min(win,len(cl)); b+=w*sum(n in d for d in cl[:ew])/ew
        vals.append(b)
    return pd.Series(_z(vals),index=np.arange(1,n_numbers+1),name='smooth')

def gaps(history,n_numbers=42):
    return {n:next((i for i,d in enumerate(history) if n in d),len(history))+1 for n in range(1,n_numbers+1)}

def production_score_642(history,lam=1.0,threshold=20):
    base=smooth_score(history,42); gp=gaps(history,42); score=base.copy().astype(float)
    for n,g in gp.items():
        if g>threshold: score.loc[n]+=lam*(g-threshold)/10
    return score.rename('score'),gp

def flex_pool(score,history,k=28):
    rank=[int(n) for n in score.sort_values(ascending=False).index]
    pool=rank[:k-2].copy(); S=set(pool); additions=[]
    for src in history[:2]:
        outs=[int(n) for n in src if int(n) not in S]
        if outs:
            x=max(outs,key=lambda n:float(score.loc[n])); pool.append(x); S.add(x); additions.append(x)
    for n in rank:
        if len(pool)>=k: break
        if n not in S: pool.append(n); S.add(n)
    return pool[:k],additions

def current_pool_642(history):
    score,gp=production_score_642(history); pool,additions=flex_pool(score,history,28)
    ranks=score.rank(ascending=False,method='first').astype(int)
    pset=set(pool); aset=set(additions)
    diag=pd.DataFrame({'number':range(1,43),'score':[float(score.loc[n]) for n in range(1,43)],'rank':[int(ranks.loc[n]) for n in range(1,43)],'gap':[int(gp[n]) for n in range(1,43)],'in_pool':[n in pset for n in range(1,43)],'repeat_addition':[n in aset for n in range(1,43)]}).sort_values('rank')
    return pool,additions,diag
