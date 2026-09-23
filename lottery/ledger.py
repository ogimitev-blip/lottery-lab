import base64,json,uuid
from datetime import datetime,timezone
from io import StringIO
import pandas as pd
import requests
from .data import load_draws_df,load_results_meta

REPO="ogimitev-blip/lottery-lab"
PATH="data/prospective_plays.jsonl"

def make_play(game,mode_id,target,pool,additions,tickets,stake,model_version,app_version):
    return {
        "play_id":str(uuid.uuid4()),
        "created_at":datetime.now(timezone.utc).isoformat(),
        "game":game,"mode_id":mode_id,
        "target_draw_no":int(target["draw_no"]),"target_date":target["date"],
        "model_version":model_version,"app_version":app_version,
        "pool":list(map(int,pool)),"repeat_additions":list(map(int,additions)),
        "tickets":[list(map(int,t)) for t in tickets],"stake_eur":float(stake)
    }

def append_session(play,session_state):
    rows=session_state.setdefault("prospective_plays",[])
    if not any(x["play_id"]==play["play_id"] for x in rows):rows.append(play)

def github_append_play(play,token):
    headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}
    url=f"https://api.github.com/repos/{REPO}/contents/{PATH}"
    r=requests.get(url,headers=headers,params={"ref":"main"},timeout=20);r.raise_for_status();meta=r.json()
    current=base64.b64decode(meta["content"]).decode() if meta.get("content") else ""
    body=current.rstrip()+"\n"+json.dumps(play,separators=(",",":"))+"\n" if current.strip() else json.dumps(play,separators=(",",":"))+"\n"
    payload={"message":f"Record prospective play {play['game']} draw {play['target_draw_no']}","content":base64.b64encode(body.encode()).decode(),"sha":meta["sha"],"branch":"main"}
    u=requests.put(url,headers=headers,json=payload,timeout=20);u.raise_for_status()
    return u.json()["commit"]["html_url"]

def parse_jsonl(text):
    out=[]
    for line in text.splitlines():
        line=line.strip()
        if line:
            try:out.append(json.loads(line))
            except Exception:pass
    return out

def score_play(play):
    game=play["game"];df=load_draws_df(game);cols=[f"n{i}" for i in range(1,7)]
    if "draw_no" not in df.columns:return {**play,"status":"pending"}
    m=df[pd.to_numeric(df.draw_no,errors="coerce")==int(play["target_draw_no"])]
    if m.empty:return {**play,"status":"pending"}
    actual=set(map(int,m.iloc[0][cols].tolist()))
    ticket_hits=[len(set(map(int,t))&actual) for t in play["tickets"]]
    pool_hits=len(set(map(int,play["pool"]))&actual)
    payout=None
    meta=load_results_meta(game)
    if not meta.empty:
        mm=meta[pd.to_numeric(meta.draw_no,errors="coerce")==int(play["target_draw_no"])]
        if not mm.empty:
            r=mm.iloc[0];payout=0.0
            for h in ticket_hits:
                if h>=3:
                    val=r.get(f"payout{h}_eur",0)
                    if pd.notna(val):payout+=float(val)
    return {**play,"status":"scored","actual":sorted(actual),"pool_hits":pool_hits,"best_ticket_hits":max(ticket_hits) if ticket_hits else 0,"payout_eur":payout,"roi":(payout/float(play["stake_eur"])-1) if payout is not None and float(play["stake_eur"]) else None}
