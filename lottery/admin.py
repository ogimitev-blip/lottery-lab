import base64,hmac
from io import StringIO
import pandas as pd
import requests

REPO="ogimitev-blip/lottery-lab"
PATHS={"6/42":"data/draws_642.csv","6/49":"data/draws_649.csv"}

def parse_numbers(text,game):
    raw=text.replace(","," ").replace(";"," ").split()
    try:nums=[int(x) for x in raw]
    except Exception:raise ValueError("Enter six whole numbers separated by spaces or commas.")
    maxn=42 if game=="6/42" else 49
    if len(nums)!=6:raise ValueError("Exactly six numbers are required.")
    if len(set(nums))!=6:raise ValueError("The six numbers must be distinct.")
    if min(nums)<1 or max(nums)>maxn:raise ValueError(f"Numbers must be between 1 and {maxn}.")
    return sorted(nums)

def updated_csv(df,draw_no,date,numbers):
    cols=[f"n{i}" for i in range(1,7)]
    if "draw_no" in df.columns and pd.to_numeric(df.draw_no,errors="coerce").eq(int(draw_no)).any():
        raise ValueError(f"Draw #{draw_no} is already stored.")
    if list(map(int,df.loc[0,cols]))==list(map(int,numbers)):
        raise ValueError("This six-number result is already the newest row.")
    row={"draw_no":int(draw_no),"date":date,**{c:n for c,n in zip(cols,numbers)}}
    return pd.concat([pd.DataFrame([row]),df],ignore_index=True).to_csv(index=False)

def github_commit_draw(game,draw_no,date,numbers,token):
    path=PATHS[game];headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}
    url=f"https://api.github.com/repos/{REPO}/contents/{path}"
    r=requests.get(url,headers=headers,params={"ref":"main"},timeout=20);r.raise_for_status();meta=r.json()
    current=base64.b64decode(meta["content"]).decode("utf-8");df=pd.read_csv(StringIO(current),dtype={"date":"string"})
    body=updated_csv(df,draw_no,date,numbers)
    payload={"message":f"Add {game} draw #{draw_no} {date}: {' '.join(map(str,numbers))}","content":base64.b64encode(body.encode()).decode(),"sha":meta["sha"],"branch":"main"}
    u=requests.put(url,headers=headers,json=payload,timeout=20);u.raise_for_status()
    return u.json()["commit"]["html_url"]

def password_ok(given,expected):return hmac.compare_digest(str(given),str(expected))


def normalize_history_frame(df,game):
    cols=["draw_no","date","n1","n2","n3","n4","n5","n6"]
    out=df.copy()
    for c in cols:
        if c not in out.columns:
            out[c]=pd.NA
    out=out[cols].copy()
    out["draw_no"]=pd.to_numeric(out["draw_no"],errors="coerce").astype("Int64")
    for c in [f"n{i}" for i in range(1,7)]:
        out[c]=pd.to_numeric(out[c],errors="coerce").astype("Int64")
    out["date"]=out["date"].astype("string")
    out.loc[out["date"].isin(["","<NA>","nan","None"]),"date"]=pd.NA
    return out

def validate_history_frame(df,game):
    out=normalize_history_frame(df,game)
    maxn=42 if game=="6/42" else 49
    cols=[f"n{i}" for i in range(1,7)]
    errors=[]; warnings=[]
    for idx,row in out.iterrows():
        if any(pd.isna(row[c]) for c in cols):
            errors.append(f"Row {idx+1}: all six number fields are required.")
            continue
        vals=[int(row[c]) for c in cols]
        if len(set(vals))!=6:
            errors.append(f"Row {idx+1}: the six numbers must be distinct.")
        if min(vals)<1 or max(vals)>maxn:
            errors.append(f"Row {idx+1}: numbers must be between 1 and {maxn}.")
    known_draws=out["draw_no"].dropna().astype(int)
    dup_draw=known_draws[known_draws.duplicated(keep=False)]
    if len(dup_draw):
        errors.append("Duplicate draw number(s): "+", ".join(map(str,sorted(set(dup_draw.tolist())))))
    parsed=pd.to_datetime(out["date"],errors="coerce")
    bad_date=out["date"].notna() & parsed.isna()
    if bad_date.any():
        errors.append("Invalid date format on row(s): "+", ".join(str(i+1) for i in out.index[bad_date]))
    groups={}
    for idx,row in out.iterrows():
        if any(pd.isna(row[c]) for c in cols): continue
        key=tuple(sorted(int(row[c]) for c in cols))
        groups.setdefault(key,[]).append(idx)
    duplicate_groups=[(nums,idxs) for nums,idxs in groups.items() if len(idxs)>1]
    for nums,idxs in duplicate_groups:
        warnings.append(
            f"Repeated six-number result {' '.join(map(str,nums))} on table row(s) "
            +", ".join(str(i+1) for i in idxs)
            +". Review whether this is a genuine repeated draw or a duplicate data row."
        )
    return out,errors,warnings,duplicate_groups

def history_csv(df,game):
    out,errors,warnings,_=validate_history_frame(df,game)
    if errors:
        raise ValueError("; ".join(errors))
    return out.to_csv(index=False)

def github_replace_history(game,df,token,message=None):
    path=PATHS[game]
    headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}
    url=f"https://api.github.com/repos/{REPO}/contents/{path}"
    r=requests.get(url,headers=headers,params={"ref":"main"},timeout=20); r.raise_for_status(); meta=r.json()
    body=history_csv(df,game)
    payload={
        "message":message or f"Edit {game} draw history",
        "content":base64.b64encode(body.encode()).decode(),
        "sha":meta["sha"],
        "branch":"main",
    }
    u=requests.put(url,headers=headers,json=payload,timeout=20); u.raise_for_status()
    return u.json()["commit"]["html_url"]
