import numpy as np
import pandas as pd

def _z(v):
    a=np.asarray(v,float); s=a.std()
    return np.zeros_like(a) if s<1e-12 else (a-a.mean())/s

def _ratez(c,n,p):
    den=np.sqrt(n*p*(1-p))
    return 0.0 if n<=0 or den==0 else (c-n*p)/den

def smooth_score(history,n_numbers):
    cl=[set(map(int,d)) for d in history]; vals=[]
    for n in range(1,n_numbers+1):
        b=0.0
        for win,w in [(20,.25),(50,.30),(100,.30),(len(cl),.15)]:
            ew=min(win,len(cl)); b+=w*sum(n in d for d in cl[:ew])/ew
        vals.append(b)
    return pd.Series(_z(vals),index=np.arange(1,n_numbers+1),name="smooth")

def fm_score(history,n_numbers):
    cl=[set(map(int,d)) for d in history]; nums=np.arange(1,n_numbers+1); p=6/n_numbers
    rn=min(10,len(cl)); os=rn; oe=min(50,len(cl)); on=max(0,oe-os); ln=min(100,len(cl)); mn=min(25,len(cl))
    rows=[]
    for n in nums:
        rc=sum(n in d for d in cl[:rn]); oc=sum(n in d for d in cl[os:oe]); lc=sum(n in d for d in cl[:ln])
        rr=rc/rn; orr=oc/on if on else p
        rz=_ratez(rc,rn,p); lz=_ratez(lc,ln,p)
        tz=(rr-orr)/np.sqrt(p*(1-p)*(1/rn+1/on)) if on else 0.0
        rp=sum(n in cl[i] and n in cl[i+1] for i in range(max(0,mn-1)))
        dh=sum(n in cl[i] and ((n-1 in cl[i+1]) or (n+1 in cl[i+1])) for i in range(max(0,mn-1)))
        ch=sum(n in d and ((n-1 in d) or (n+1 in d)) for d in cl[:mn])
        rows.append((n,rz,lz,tz,rp,dh,ch))
    d=pd.DataFrame(rows,columns=["n","rz","lz","tz","rp","dh","ch"]).set_index("n")
    ps=.40*_z(d.lz)+.20*_z(d.rz)+.15*_z(d.rp)+.15*_z(d.ch)+.10*_z(d.dh)
    mom=.35*_z(d.rz)+.25*_z(d.tz)+.15*_z(d.rp)+.15*_z(d.dh)+.10*_z(d.ch)
    motif=_z(d.rp+d.dh+d.ch)
    sc=.45*_z(ps)+.35*_z(mom)+.20*motif
    return pd.Series(sc,index=nums),d

def ensemble_score(history,n_numbers=49):
    fm,d=fm_score(history,n_numbers)
    psc=.40*_z(d.lz)+.20*_z(d.rz)+.15*_z(d.rp)+.15*_z(d.ch)+.10*_z(d.dh)
    ps=pd.Series(_z(psc),index=np.arange(1,n_numbers+1))
    sm=smooth_score(history,n_numbers)
    sc=.5*_z(ps.values)+.3*_z(fm.values)+.2*_z(sm.values)
    return pd.Series(_z(sc),index=np.arange(1,n_numbers+1))

def gaps(history,n_numbers):
    return {n:next((i for i,d in enumerate(history) if n in d),len(history))+1 for n in range(1,n_numbers+1)}

def overdue(base,history,n_numbers,lam,threshold=20):
    gp=gaps(history,n_numbers); score=base.copy().astype(float)
    for n,g in gp.items():
        if g>threshold: score.loc[n]+=lam*(g-threshold)/10
    return score,gp

def production_score_642(history):
    return overdue(smooth_score(history,42),history,42,1.0,20)

def production_score_649(history):
    return overdue(ensemble_score(history,49),history,49,.75,20)

def flex_pool(score,history,k):
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

def _diagnostics(score,gp,pool,additions,n_numbers):
    ranks=score.rank(ascending=False,method="first").astype(int); pset=set(pool); aset=set(additions)
    return pd.DataFrame({
        "number":range(1,n_numbers+1),
        "score":[float(score.loc[n]) for n in range(1,n_numbers+1)],
        "rank":[int(ranks.loc[n]) for n in range(1,n_numbers+1)],
        "gap":[int(gp[n]) for n in range(1,n_numbers+1)],
        "in_pool":[n in pset for n in range(1,n_numbers+1)],
        "repeat_addition":[n in aset for n in range(1,n_numbers+1)],
    }).sort_values("rank")

def current_pool_642(history,k=28):
    score,gp=production_score_642(history); pool,adds=flex_pool(score,history,k)
    return pool,adds,_diagnostics(score,gp,pool,adds,42)

def current_pool_649(history,k=22):
    score,gp=production_score_649(history); pool,adds=flex_pool(score,history,k)
    return pool,adds,_diagnostics(score,gp,pool,adds,49),score
