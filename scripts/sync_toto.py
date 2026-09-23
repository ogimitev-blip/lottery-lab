#!/usr/bin/env python3
import json,re,time
from pathlib import Path
from datetime import datetime
from io import StringIO
import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
STATE_PATH=ROOT/"data"/"sync_state.json"
UA={"User-Agent":"Mozilla/5.0 LotteryLab/1.0 (+https://github.com/ogimitev-blip/lottery-lab)"}
GAME_FILES={"6/42":"draws_642.csv","6/49":"draws_649.csv"}
META_FILES={"6/42":"results_meta_642.csv","6/49":"results_meta_649.csv"}

def euro(s):
    return float(s.replace("\xa0"," ").replace(" ","").replace(",",".").replace("euro","").strip())

def parse_result(url,expected_draw,maxn):
    r=requests.get(url,headers=UA,timeout=25)
    if r.status_code==404:return None
    r.raise_for_status()
    text=" ".join(BeautifulSoup(r.text,"html.parser").stripped_strings)
    head=re.search(r"Тираж\s+(\d+)\s*-\s*(\d{2}\.\d{2}\.\d{4})",text)
    if not head or int(head.group(1))!=expected_draw:return None
    tail=text[head.end():]
    wm=re.search(r"Печеливши числа\s+((?:\d+\s+){5}\d+)",tail)
    if not wm:return None
    nums=[int(x) for x in wm.group(1).split()]
    if len(nums)!=6 or len(set(nums))!=6 or min(nums)<1 or max(nums)>maxn:return None
    jm=re.search(r"Джакпот\s+([\d\s]+[\.,]\d{2})\s*euro",tail)
    jackpot=euro(jm.group(1)) if jm else None
    tiers={}
    for hits in [6,5,4,3]:
        pat=rf"{hits}\s*числа\s+(\d+)\s+([\d\s]+[\.,]\d{{2}})\s*euro"
        m=re.search(pat,tail)
        tiers[hits]=(int(m.group(1)),euro(m.group(2))) if m else (None,None)
    d=datetime.strptime(head.group(2),"%d.%m.%Y").date().isoformat()
    return {"draw_no":expected_draw,"date":d,"numbers":sorted(nums),"jackpot_eur":jackpot,"tiers":tiers,"source_url":url}

def prepend_draw(path,result):
    df=pd.read_csv(path,dtype={"date":"string"})
    cols=[f"n{i}" for i in range(1,7)]
    if "draw_no" not in df.columns:df.insert(0,"draw_no",pd.NA)
    if len(df) and str(df.iloc[0].get("draw_no",""))==str(result["draw_no"]):return False
    row={"draw_no":result["draw_no"],"date":result["date"],**{c:n for c,n in zip(cols,result["numbers"])}}
    df=pd.concat([pd.DataFrame([row]),df],ignore_index=True)
    df.to_csv(path,index=False)
    return True

def prepend_meta(path,result):
    cols=["draw_no","date","jackpot_eur","winners6","payout6_eur","winners5","payout5_eur","winners4","payout4_eur","winners3","payout3_eur","source_url"]
    if path.exists():df=pd.read_csv(path)
    else:df=pd.DataFrame(columns=cols)
    if len(df) and int(result["draw_no"]) in set(pd.to_numeric(df.draw_no,errors="coerce").dropna().astype(int)):return
    row={"draw_no":result["draw_no"],"date":result["date"],"jackpot_eur":result["jackpot_eur"],"source_url":result["source_url"]}
    for h in [6,5,4,3]:
        row[f"winners{h}"],row[f"payout{h}_eur"]=result["tiers"][h]
    pd.concat([pd.DataFrame([row]),df],ignore_index=True)[cols].to_csv(path,index=False)

def main():
    state=json.loads(STATE_PATH.read_text())
    changed=False
    for game,cfg in state.items():
        maxn=42 if game=="6/42" else 49
        current=int(cfg["latest_draw_no"])
        for n in range(current+1,current+4):
            url=f"https://info.toto.bg/results/{cfg['slug']}/{cfg['year']}-{n}"
            try:res=parse_result(url,n,maxn)
            except requests.RequestException as e:
                print(game,n,"request error",e);break
            if not res:
                print(game,n,"not published");break
            print("found",game,res)
            prepend_draw(ROOT/"data"/GAME_FILES[game],res)
            prepend_meta(ROOT/"data"/META_FILES[game],res)
            cfg["latest_draw_no"]=n;cfg["latest_date"]=res["date"];changed=True
            time.sleep(.5)
    if changed:STATE_PATH.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n")
    print("changed=",changed)

if __name__=="__main__":main()
