#!/usr/bin/env python3
import json,time
from pathlib import Path
import pandas as pd
from sync_toto import parse_result,prepend_meta

ROOT=Path(__file__).resolve().parents[1]
STATE=json.loads((ROOT/"data"/"sync_state.json").read_text())
GAME_FILES={"6/42":"draws_642.csv","6/49":"draws_649.csv"}
META_FILES={"6/42":"results_meta_642.csv","6/49":"results_meta_649.csv"}
MARKER=ROOT/"data"/".backfill_2026_complete"

def main():
    if MARKER.exists():
        print("2026 backfill already completed")
        return
    failures=[]
    for game,cfg in STATE.items():
        maxn=42 if game=="6/42" else 49
        path=ROOT/"data"/GAME_FILES[game]
        df=pd.read_csv(path,dtype={"date":"string"})
        cols=[f"n{i}" for i in range(1,7)]
        if "draw_no" not in df.columns:df.insert(0,"draw_no",pd.NA)
        if "date" not in df.columns:df.insert(1,"date",pd.NA)
        assigned=set(pd.to_numeric(df.draw_no,errors="coerce").dropna().astype(int))
        for n in range(1,int(cfg["latest_draw_no"])+1):
            if n in assigned:continue
            url=f"https://info.toto.bg/results/{cfg['slug']}/{cfg['year']}-{n}"
            try:res=parse_result(url,n,maxn)
            except Exception as e:
                print("error",game,n,e);failures.append((game,n));continue
            if not res:
                print("missing",game,n);failures.append((game,n));continue
            target=tuple(sorted(res["numbers"]))
            matches=[]
            for i,row in df.iterrows():
                if pd.notna(row.get("draw_no")):continue
                vals=tuple(sorted(int(row[c]) for c in cols))
                if vals==target:matches.append(i)
            if matches:
                i=matches[0];df.at[i,"draw_no"]=n;df.at[i,"date"]=res["date"]
            else:
                print("official result not found in local history",game,n,target)
            prepend_meta(ROOT/"data"/META_FILES[game],res)
            time.sleep(.15)
        df.to_csv(path,index=False)
    if not failures:
        MARKER.write_text("Backfilled 2026 draw numbers, dates and payout metadata from info.toto.bg\n")
    else:
        print("Backfill had missing pages; it will retry next scheduled run:",failures[:10])

if __name__=="__main__":main()
