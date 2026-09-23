import base64,hmac
from io import StringIO
import pandas as pd
import requests

REPO="ogimitev-blip/lottery-lab"
PATHS={"6/42":"data/draws_642.csv","6/49":"data/draws_649.csv"}

def parse_numbers(text,game):
    raw=text.replace(","," ").replace(";"," ").split()
    try: nums=[int(x) for x in raw]
    except Exception: raise ValueError("Enter six whole numbers separated by spaces or commas.")
    maxn=42 if game=="6/42" else 49
    if len(nums)!=6: raise ValueError("Exactly six numbers are required.")
    if len(set(nums))!=6: raise ValueError("The six numbers must be distinct.")
    if min(nums)<1 or max(nums)>maxn: raise ValueError(f"Numbers must be between 1 and {maxn}.")
    return sorted(nums)

def updated_csv(df,date,numbers):
    cols=[f"n{i}" for i in range(1,7)]
    if list(map(int,df.loc[0,cols]))==list(map(int,numbers)):
        raise ValueError("This draw is already the newest row.")
    row={"date":date,**{c:n for c,n in zip(cols,numbers)}}
    return pd.concat([pd.DataFrame([row]),df],ignore_index=True).to_csv(index=False)

def github_commit_draw(game,date,numbers,token):
    path=PATHS[game]; headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}
    url=f"https://api.github.com/repos/{REPO}/contents/{path}"
    r=requests.get(url,headers=headers,params={"ref":"main"},timeout=20); r.raise_for_status(); meta=r.json()
    current=base64.b64decode(meta["content"]).decode("utf-8"); df=pd.read_csv(StringIO(current),dtype={"date":"string"})
    body=updated_csv(df,date,numbers)
    payload={"message":f"Add {game} draw {date}: {' '.join(map(str,numbers))}","content":base64.b64encode(body.encode()).decode(),"sha":meta["sha"],"branch":"main"}
    u=requests.put(url,headers=headers,json=payload,timeout=20); u.raise_for_status()
    return u.json()["commit"]["html_url"]

def password_ok(given,expected):
    return hmac.compare_digest(str(given),str(expected))
