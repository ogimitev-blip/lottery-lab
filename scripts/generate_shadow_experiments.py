import sys
from datetime import date
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import lottery.data as data
from lottery.data import get_draws,next_draw_info
from lottery.shadow import append_shadow_batch,read_shadow_rows
from lottery.allocation_shadow import append_allocation_batch,read_allocation_rows

class DummyState(dict):
    pass

data.st.session_state=DummyState()

# Workflow trigger marker: freeze immediately after draw-data updates.
created=0
targets={}
for game in ("6/42","6/49"):
    target=next_draw_info(game)
    targets[game]=target
    # Never freeze a "prospective" batch for a draw whose calendar date has
    # already arrived. This prevents a delayed result sync from back-filling a
    # shadow play after the outcome could be known.
    if date.fromisoformat(target["date"]) <= date.today():
        print("SKIP_SHADOW",game,target["draw_no"],target["date"],"not future")
        continue
    new=append_shadow_batch(game,target,get_draws(game))
    created+=len(new)
    print("SHADOW_BATCH",game,target["draw_no"],target["date"],len(new))
    for row in new:
        print("SHADOW_ROW",row["shadow_id"],row["label"],row["crowd_strength"],row["notional_stake_eur"])

allocation_created=0
t42=targets.get("6/42")
t49=targets.get("6/49")
if (
    t42 and t49
    and int(t42["draw_no"])==int(t49["draw_no"])
    and str(t42["date"])==str(t49["date"])
    and date.fromisoformat(str(t42["date"])) > date.today()
):
    anew=append_allocation_batch(int(t42["draw_no"]),str(t42["date"]))
    allocation_created=len(anew)
    print("ALLOCATION_SHADOW_BATCH",t42["draw_no"],t42["date"],allocation_created)
    for row in anew:
        print("ALLOCATION_SHADOW_ROW",row["allocation_shadow_id"],row["label"],row["notional_stake_eur"])

print("SHADOW_TOTAL_CREATED",created)
print("SHADOW_LEDGER_ROWS",len(read_shadow_rows()))
print("ALLOCATION_SHADOW_TOTAL_CREATED",allocation_created)
print("ALLOCATION_SHADOW_LEDGER_ROWS",len(read_allocation_rows()))
